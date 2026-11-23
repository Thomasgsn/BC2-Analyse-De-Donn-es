"""Synthèses locales sur faits agrégés, avec validation et comparaison au gabarit."""
from pathlib import Path
import hashlib,json,os,re,threading,time,urllib.request
from .storage import ROOT,save,now,latest,digest
LOCK=threading.Lock()
BASE=os.environ.get('BC2_LLM_BASE_URL','http://ollama:11434')
PROMPT_VERSION='bc2-facts-fr-v2-qualitative-context'
SYSTEM='''Tu rédiges en français une courte synthèse destinée à un conseiller. Utilise uniquement les faits fournis. Aucun chiffre, pourcentage ou montant dans le texte : les nombres exacts seront affichés par le logiciel dans un tableau séparé. Cite les identifiants des faits dans evidence_ids. Ne donne ni conseil d’investissement ni décision de crédit. Ne transforme jamais une association en cause et n’invente aucune variable. Ne confonds pas défaut et fraude. La synthèse est exploratoire ; la partie limits doit dire que les données sont historiques et qu’une relecture humaine est nécessaire. Réponds uniquement dans le schéma JSON demandé.'''

def facts_from_run(path):
    quality=json.loads((path/'quality.json').read_text());models=json.loads((path/'models.json').read_text());market=json.loads((path/'market.json').read_text());chosen=models['selection']['selected'];m=models['models'][chosen]['test']
    return {'portfolio':{'dataset_period':{'value':'Taiwan 2005','meaning':'cohorte historique, sans validation temporelle future'},'selected_model':{'value':chosen,'meaning':'choisi sur validation, pas sur test'},'test_recall':{'value':m['recall'],'meaning':'fraction de défauts détectés sur le test réservé'},'test_precision':{'value':m['precision'],'meaning':'fraction de défauts parmi les alertes, nombreuses fausses alertes'},'test_false_positives':{'value':m['fp'],'meaning':'charge de revue humaine, pas une mesure monétaire'},'human_review':{'value':True,'meaning':'aucune décision automatique de crédit'}},'market':{'symbol':{'value':market['symbol'],'meaning':'instrument de démonstration, pas conseil de placement'},'window':{'value':[market['first_date'],market['last_date']],'meaning':'séances historiques distinctes de la cohorte clients'},'period_return':{'value':market['period_price_return'],'meaning':'variation du cours brut, sans dividendes ni prévision','direction':'hausse' if market['period_price_return']>=0 else 'baisse'},'max_drawdown':{'value':market['max_drawdown'],'meaning':'recul depuis un plus haut sur cette fenêtre uniquement'},'data_limits':{'value':'raw daily historical prices','meaning':'pas de flux temps réel, pas de lien causal avec le défaut client'},'human_review':{'value':True,'meaning':'relecture humaine requise'}}}

def qualitative_context(facts):
    context={}
    for key,fact in facts.items():
        entry={'meaning':fact['meaning']}
        for name in ['qualifier','direction']:
            if name in fact:entry[name]=fact[name]
        value=fact.get('value')
        if isinstance(value,str) and not re.search(r'[0-9]',value):entry['value']=value
        context[key]=entry
    return context


def validate_output(output,facts):
    if not isinstance(output,dict) or set(output)!={'summary','limits','evidence_ids'}:raise ValueError('Schéma de synthèse invalide')
    for key,low,high in [('summary',60,1400),('limits',30,800)]:
        if not isinstance(output[key],str) or not low<=len(output[key])<=high:raise ValueError('Longueur ou type de texte invalide')
    ids=output['evidence_ids']
    if not isinstance(ids,list) or not 3<=len(ids)<=len(facts) or not all(isinstance(i,str) and i in facts for i in ids) or len(ids)!=len(set(ids)):raise ValueError('Références factuelles invalides')
    text=output['summary']+' '+output['limits']
    if re.search(r'[0-9]|https?://|www\.|<|>|[@€$%]',text):raise ValueError('Chiffres, HTML ou coordonnées non autorisés dans le texte narratif')
    if re.search(r'\b(garanti|garantie|certain|certaine|fraude|résiliation)\b|accorder un crédit|refuser le crédit|acheter cette action|vendre cette action|mauvais payeur|irresponsable',text,re.I):raise ValueError('Assertion ou formulation non autorisée')
    limits=output['limits'].lower()
    if not re.search('historique|ancien',limits) or not re.search('humain|humaine|relecture',limits):raise ValueError('Limites historiques et humaines absentes')
    return output

def template(facts,case):
    summary=('Le contrôle conserve les observations et distingue les cellules vides des catégories ambiguës. Les codes et profils répétés demandent une documentation avant toute analyse.' if case=='quality' else 'Les modèles ont été comparés selon un protocole de validation commun. Le temps de calcul et la mémoire apportent une lecture des ressources, distincte de la qualité prédictive.' if case=='resources' else 'Le modèle retenu sert à explorer le risque de défaut sur une cohorte bancaire. Son rappel doit être examiné avec sa précision et la charge des fausses alertes.' if case=='portfolio' else 'Le cours observé décrit une fenêtre de marché distincte du portefeuille de clients. Le recul depuis les plus hauts et la variation du cours apportent deux lectures complémentaires.')
    return validate_output({'summary':summary,'limits':'Ces données historiques ont une portée limitée. Une relecture humaine est nécessaire avant tout usage métier.','evidence_ids':list(facts)[:4]},facts)

def call_model(facts,case,temperature=.1,timeout=120):
    model_lock=json.loads((ROOT/'infra/llm.lock.json').read_text())
    with urllib.request.urlopen(BASE+'/api/tags',timeout=8) as r:models=json.load(r)['models']
    if not any(m['name']==model_lock['model'] and m['digest']==model_lock['digest'] for m in models):raise ValueError('Modèle local différent du verrouillage')
    schema={'type':'object','properties':{'summary':{'type':'string'},'limits':{'type':'string'},'evidence_ids':{'type':'array','items':{'type':'string','enum':list(facts)},'minItems':3,'maxItems':len(facts)}},'required':['summary','limits','evidence_ids'],'additionalProperties':False}
    request={'model':model_lock['model'],'system':SYSTEM,'prompt':'Cas : '+case+'\nFaits qualitatifs autorisés (les valeurs chiffrées sont affichées séparément par le logiciel) : '+json.dumps(qualitative_context(facts),ensure_ascii=False),'format':schema,'think':False,'stream':False,'keep_alive':'5m','options':{'num_ctx':2048,'num_batch':64,'num_thread':2,'num_predict':360,'seed':42,'temperature':temperature,'repeat_penalty':1.1}}
    started=time.monotonic()
    with urllib.request.urlopen(urllib.request.Request(BASE+'/api/generate',data=json.dumps(request).encode(),headers={'Content-Type':'application/json'}),timeout=timeout) as r:
        raw=r.read(200001)
    if len(raw)>200000:raise ValueError('Réponse trop longue')
    payload=json.loads(raw)
    if payload.get('done') is not True or payload.get('done_reason')=='length':raise ValueError('Génération tronquée')
    output=json.loads(payload['response'])
    result={'created_at_utc':now(),'case':case,'status':'draft_requires_human_review','model':model_lock['model'],'model_digest':model_lock['digest'],'prompt_version':PROMPT_VERSION,'system_sha256':hashlib.sha256(SYSTEM.encode()).hexdigest(),'facts_sha256':hashlib.sha256(json.dumps(facts,sort_keys=True).encode()).hexdigest(),'model_context':qualitative_context(facts),'model_context_sha256':hashlib.sha256(json.dumps(qualitative_context(facts),sort_keys=True).encode()).hexdigest(),'facts':facts,'output':output,'request_options':request['options'],'think':False,'elapsed_seconds':time.monotonic()-started,'timing_ns':{k:payload.get(k) for k in ['total_duration','load_duration','prompt_eval_duration','eval_duration']},'tokens':{k:payload.get(k) for k in ['prompt_eval_count','eval_count']},'email_sent':False,'validation_scope':'Schema, fact references, numeric invention markers, limited language guards; not semantic correctness or human review'}
    try:validate_output(output,facts)
    except ValueError as error:
        result['status']='rejected';result['reason']=str(error);save(ROOT/'docs/evidence/generative'/('rejected-'+str(time.time_ns())+'.json'),result);raise
    return result

def generate(facts,case):
    if case not in facts:raise ValueError('Cas inconnu')
    if not LOCK.acquire(blocking=False):raise ValueError('Une génération est déjà en cours')
    try:
        result=call_model(facts[case],case)
        save(ROOT/'exports'/('draft-'+str(time.time_ns())+'.json'),result);return result
    finally:LOCK.release()

def evaluation():
    path,manifest=latest();cases=json.loads((ROOT/'docs/evidence/generative/heldout-facts-v2.json').read_text())['cases'];report={'created_at_utc':now(),'run_id':manifest['run_id'],'protocol':'Two fact sets held out from prompt development; qualitative context v2 frozen before these calls; no claimed generalization beyond two cases','heldout_facts_sha256':digest(ROOT/'docs/evidence/generative/heldout-facts-v2.json'),'selected_temperature_fixed_before_evaluation':.1,'temperatures_compared':[.1,.4],'seed':42,'cases':[],'human_rubric':{'status':'not performed','criteria':['clarté','pertinence métier','inclusivité','fidélité sémantique'],'no_fabricated_human_rating':True},'energy':'No energy/CO2 sensor measurement; measured wall time and tokens only'}
    for case,facts in cases.items():
        start=time.monotonic();classic=template(facts,case);elapsed=time.monotonic()-start
        report['cases'].append({'case':case,'method':'deterministic_template','valid':True,'elapsed_seconds':elapsed,'output':classic,'reference_coverage':len(classic['evidence_ids'])/len(facts)})
        for temp in [.1,.4]:
            try:
                result=call_model(facts,case,temp);entry={'case':case,'method':'llm','temperature':temp,'valid':True,'result':result,'reference_coverage':len(result['output']['evidence_ids'])/len(facts),'mean_words_per_sentence_proxy':sum(len(t.split()) for t in re.split(r'[.!?]+',result['output']['summary']) if t.strip())/max(1,len([t for t in re.split(r'[.!?]+',result['output']['summary']) if t.strip()])),'proxy_limit':'Sentence length is not a validated clarity score; lexical guards do not prove inclusivity or business accuracy'}
            except (ValueError,OSError,TimeoutError) as error:entry={'case':case,'method':'llm','temperature':temp,'valid':False,'error_type':type(error).__name__,'reason':str(error)}
            report['cases'].append(entry)
            save(ROOT/'docs/evidence/generative/evaluation.json',report)
    save(ROOT/'docs/evidence/generative/evaluation.json',report);return report
