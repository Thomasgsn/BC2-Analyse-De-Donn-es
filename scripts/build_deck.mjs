// Auteur local : @oai/artifact-tool, runtime documentaire fourni par Codex.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const root=path.resolve(process.env.BC2_ROOT||'../..');
const skill=process.env.BC2_PRESENTATION_SKILL||'/Users/thomasgassmann/.codex/plugins/cache/openai-primary-runtime/presentations/26.1119.11507/skills/presentations';
const runtime='/Users/thomasgassmann/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES=path.join(runtime,'node/node_modules');
process.env.RUNTIME_NODE=path.join(runtime,'node/bin/node');
const m=JSON.parse(await fs.readFile(path.join(root,'exports/baseline-20261120-v2/models.json'),'utf8'));
const deck=Presentation.create({slideSize:{width:1280,height:720}});
const slides=[
 ['Analyse du défaut bancaire',['Thomas Gassmann · RNCP40875 · BC2','30 000 observations historiques pour comparer les modèles et expliquer les erreurs','Travail individuel · rédaction et sourçage assistés par IA (Codex, Claude)'], 'Sujet BC2 fourni p.1–4 ; UCI https://doi.org/10.24432/C55S3H'],
 ['Données et périmètre',['UCI Default of Credit Card Clients : Taïwan, historiques de 2005','6 636 défauts observés, soit 22,12 % ; 23 explicatives source, 21 retenues','Cible défaut de paiement, dataset de référence non disponible'], 'docs/rapport.md ; docs/evidence/pipeline/baseline-20261120-v2/quality.json'],
 ['Préparer sans effacer les anomalies',['Aucune cellule brute vide ; les catégories ambiguës restent explicites','345 codes d’études inconnus ; 35 répétitions exactes hors ID','Montants négatifs et extrêmes conservés, règles et dictionnaire tracés'], 'docs/evidence/pipeline/baseline-20261120-v2/quality.json ; statistical-supplement.json'],
 ['Séparer apprentissage et évaluation',['18 000 lignes train · 6 000 validation · 6 000 test','Profils identiques groupés, aucun groupe partagé entre lots','Prétraitement appris dans les plis ; modèle et seuil figés avant test'], 'docs/evidence/pipeline/baseline-20261120-v2/selection-before-test.json ; quality.json'],
 ['Architecture locale reproductible',['Acquisition vérifiée → préparation → exploration et modèles → artefacts','Dash consulte les résultats persistés ; Ollama résume des faits agrégés','Projet Docker autonome, port loopback 8052, dépendances et poids épinglés'], 'docs/rapport.md ; compose.yml ; requirements.lock ; infra/llm.lock.json'],
 ['Statistiques et projections',['Pearson et Spearman ; Welch et Chi² avec contrôle des conditions','Correction BH par famille ; associations sans conclusion causale','ACP : 8 composantes pour 90 % de variance · AFD binaire : un seul axe'], 'docs/evidence/pipeline/baseline-20261120-v2/eda.json ; projections.json'],
 ['Comparer les méthodes',['Test réservé · seuil propre à chaque modèle fixé sur validation'], 'docs/evidence/pipeline/baseline-20261120-v2/models.json'],
 ['Détecter davantage impose des revues',['Forêt retenue : rappel 80,71 % · précision 34,17 % · seuil 0,15','1 071 défauts détectés · 256 manqués · 2 063 fausses alertes','La charge humaine et les coûts réels doivent précéder tout déploiement'], 'docs/evidence/pipeline/baseline-20261120-v2/models.json'],
 ['Incertitude, biais et sobriété',['Rappel : intervalle bootstrap 95 % de 78,78 % à 82,46 %','SEX et MARRIAGE exclus du score ; AGE conservé, équité non démontrée','Énergie estimée : 0,03 Wh pour entraîner 4 modèles, 0,21 Wh par synthèse LLM'], 'docs/evidence/pipeline/baseline-20261120-v2/models.json ; docs/evidence/energy/estimate-20261123.json ; méthode 150 rééchantillonnages de groupes fixes'],
 ['Cotations et tableau de bord',['IBM : 100 séances réelles, source Alpha Vantage, cache daté de 2026','Cours brut : −21,79 % ; drawdown maximal : −32,78 %','Filtres, vues direction/risques/data, navigation clavier et vue mobile'], 'https://www.alphavantage.co/documentation/#daily ; docs/evidence/pipeline/baseline-20261120-v2/market.json ; browser/browser-checks.json'],
 ['Contexte macro-économique du crédit',['Cinq séries publiques FRED : retards et pertes cartes US, taux, TWD/USD','Cohorte avril–sept. 2005 : retards US au rang 49 % de leur historique','Variations retards/pertes corrélées à 0,47 ; aucune jointure client'], 'FRED, snapshot fred-20261123 ; docs/evidence/macro/fred-20261123.json ; association, pas causalité'],
 ['Génération locale sous contrôle',['Qwen3:1.7b · faits qualitatifs agrégés · aucun identifiant client','Deux cas réservés × deux températures : 4 sorties passent les contrôles','Gabarit classique plus rapide ; fidélité sémantique et utilité à relire'], 'https://huggingface.co/Qwen/Qwen3-1.7B ; docs/evidence/generative/evaluation.json ; développement v1 refusé conservé'],
 ['Preuves exécutées',['39 tests unitaires et rechargement exact des quatre modèles','Deux runs : mêmes partitions et mêmes prédictions sur 6 000 tests','Chromium : filtres, clavier, vues métier, génération et mobile ; axe sans violation détectée'], 'README.md ; docs/evidence/pipeline/runtime-verification.json ; reproduction.json ; docs/evidence/browser/browser-checks.json. Un contrôle axe incomplet ; pas de certification WCAG exhaustive.'],
 ['Feuille de route métier',['Faire approuver le périmètre et les coûts des erreurs','Valider sur données récentes autorisées, puis auditer biais et calibration','Pilote supervisé, formation, suivi de dérive et retour au traitement manuel'], 'docs/rapport.md ; roadmap proposée, aucune validation de parties prenantes inventée'],
 ['Réserves avant validation officielle',['Revue métier et humaine de l’IA ; validation temporelle externe à obtenir','Démonstration et soutenance réelles à conduire ; décision finale du jury'], 'docs/rapport.md ; référentiel fourni p.7–11']
];
function text(slide,value,x,y,w,h,size=30,bold=false,color='#17364f'){
 const shape=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});shape.text=value;shape.text.style={fontFamily:'Arial',fontSize:size,bold,color};return shape;
}
for(let i=0;i<slides.length;i++){
 const [title,body,source]=slides[i];const s=deck.slides.add();s.background.fill=i===0?'#10334f':'#f8fafc';
 text(s,title,76,68,1128,i===0?150:110,i===0?64:46,true,i===0?'#ffffff':'#10334f');
 if(i===6){
  text(s,body[0],76,175,1128,50,24);
  s.charts.add('bar',{position:{left:76,top:246,width:1128,height:355},categories:['Constante','Logistique','Arbre','Forêt'],series:[{name:'Average precision',values:Object.values(m.models).map(v=>Number(v.test.pr_auc_average_precision.toFixed(4))),fill:'#163e65'},{name:'Rappel',values:Object.values(m.models).map(v=>Number(v.test.recall.toFixed(4))),fill:'#0f766e'}],hasLegend:true,yAxis:{minimumScale:0,maximumScale:1},dataLabels:{showValue:false}});
 }else body.forEach((value,j)=>text(s,value,76,(i===0?275:224)+j*112,1128,92,i===0?32:30,false,i===0?'#d8e7f3':'#17364f'));
 text(s,`${i+1} / ${slides.length}  ·  Thomas Gassmann · BC2`,76,660,1100,28,16,false,i===0?'#d8e7f3':'#536b7d');
 s.speakerNotes.text=`Sources : ${source}\nNotes : ${i===11?'Ne pas confondre contrôles syntaxiques et exactitude sémantique. Exemple ambigu conservé dans le rapport.':'Consulter le rapport BC2 pour les méthodes et limites.'}`;
}
const staging=path.join(root,'tmp/deck-build');await fs.mkdir(staging,{recursive:true});await fs.mkdir(path.join(root,'output/presentations'),{recursive:true});
const candidate=path.join(staging,'candidate.pptx');await(await PresentationFile.exportPptx(deck)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const final=process.env.BC2_DECK_OUTPUT||path.join(root,'output/presentations/soutenance-bc2-thomas-gassmann.pptx');
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:final,pythonExecutable:path.join(runtime,'python/bin/python'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:slides.length,requiredNativeChartOwnerSlides:[7],requiredNativeTableOwnerSlides:[],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(staging,'validation.json')});
for(let i=0;i<deck.slides.items.length;i++){const png=await deck.export({slide:deck.slides.items[i],format:'png',scale:1});await fs.writeFile(path.join(staging,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));}
await fs.writeFile(path.join(root,'docs/presentation-content.json'),JSON.stringify(slides,null,2)+'\n');console.log(JSON.stringify({slides:slides.length,final,validation:result}));
