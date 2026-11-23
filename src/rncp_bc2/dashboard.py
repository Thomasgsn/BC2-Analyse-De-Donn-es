"""Dashboard local inclusif : données, modèles, marché et résumés vérifiables."""
import json,os,io
from pathlib import Path
import pandas as pd,numpy as np
from dash import Dash,html,dcc,Input,Output,State,callback,ctx
from flask import jsonify,send_file
import plotly.express as px
import plotly.graph_objects as go
from .storage import latest,ROOT
from .macro import latest_macro,COHORT_START,COHORT_END

path,manifest=latest();cohort=pd.read_parquet(path/'cohort.parquet')
reports={name:json.loads((path/(name+'.json')).read_text()) for name in ['quality','eda','projections','models','market']}
market=pd.read_parquet(path/'market.parquet');selected=reports['models']['selection']['selected'];test=reports['models']['models'][selected]['test']
macro_loaded=latest_macro();macro_report,macro_series=macro_loaded if macro_loaded else (None,None)
NAMES={'forest':'Forêt aléatoire','tree':'Arbre de décision','logistic':'Régression logistique','dummy':'Référence constante'}

def percentage(value):return 'Non défini' if value is None else f'{value*100:.2f} %'.replace('.',',')
def table(headers,rows,caption):
    return html.Table([html.Caption(caption),html.Thead(html.Tr([html.Th(v,scope='col') for v in headers])),html.Tbody([html.Tr([html.Td(str(v)) for v in r]) for r in rows])])
def style(fig):
    fig.update_layout(template='plotly_white',font={'family':'Arial, sans-serif','color':'#142c43'},margin={'l':45,'r':20,'t':45,'b':55},paper_bgcolor='#ffffff',plot_bgcolor='#ffffff',legend_title_text='');return fig

def projection_alternatives():
    """Valeurs réelles des graphiques, consultables sans couleur ni survol."""
    points=pd.DataFrame(reports['projections']['points'])
    rows=[]
    for target,group in points.groupby('y'):
        quantiles=group['lda1'].quantile([.25,.5,.75])
        rows.append([int(target),len(group),*[f'{v:.4f}' for v in quantiles]])
    return html.Details([
        html.Summary('Consulter les données des corrélations et des projections'),
        html.P('Les exports donnent les valeurs exactes des graphiques. Les points ACP/AFD constituent l’échantillon déterministe affiché, pas l’ensemble du train. La cible 0 signifie absence de défaut observé et 1 défaut observé.'),
        html.A('Télécharger la matrice de Spearman en CSV',href='/download/correlations.csv'),html.Br(),
        html.A('Télécharger les coordonnées ACP et AFD en CSV',href='/download/projections.csv'),
        html.Div(table(['Défaut observé','Points affichés','AFD : premier quartile','AFD : médiane','AFD : troisième quartile'],rows,'Distribution de l’axe AFD par classe dans l’échantillon affiché'),className='table-wrap',tabIndex=0,role='region',**{'aria-label':'Quartiles de la projection AFD'}),
    ],id='projection-alternatives')

def model_figure():
    rows=[{'Modèle':NAMES[k],'Rappel':v['test']['recall'],'Précision':v['test']['precision'],'PR-AUC':v['test']['pr_auc_average_precision']} for k,v in reports['models']['models'].items()]
    return style(px.bar(pd.DataFrame(rows).melt(id_vars='Modèle',var_name='Mesure',value_name='Valeur'),x='Modèle',y='Valeur',color='Mesure',barmode='group',title='Test réservé : mesures et seuils figés sur validation',color_discrete_sequence=['#163e65','#0f766e','#b45309']))

def number(value,digits=2):return 'Non disponible' if value is None else f'{value:.{digits}f}'.replace('.',',')
def macro_section():
    if macro_report is None:
        return html.Section([html.H2('Contexte macro-économique du crédit',id='macro'),html.P('Aucun snapshot macro publié : lancer la commande macro du job.')],className='panel')
    rows=[[s['label'],s['unit'],number(s['cohort_window_mean']),'Non disponible' if s['cohort_mean_percentile_in_history'] is None else f"{s['cohort_mean_percentile_in_history']*100:.0f} %",number(s['last_value'])+' ('+s['last_date']+')',number(s['change_1y_points']),number(s['change_5y_points'])] for s in macro_report['series']]
    labels={s['id']:s['label'] for s in macro_report['series']}
    corr=macro_report['spearman_quarterly_changes'];ids=list(corr)
    period=macro_report['quarterly_common_period']
    return html.Section([html.H2('Contexte macro-économique du crédit',id='macro'),
        html.P('Séries publiques de la Réserve fédérale (FRED) : retards et pertes sur cartes de crédit des banques US, taux des cartes, taux d’État à 10 ans et dollar taïwanais. Elles situent la période observée de la cohorte (avril à septembre 2005, zone grisée) dans un historique long, sans jointure avec les clients.'),
        html.Div([html.Fieldset([html.Legend('Série'),dcc.RadioItems(id='macro-series',options=[{'label':s['label'],'value':s['id']} for s in macro_report['series']],value=macro_report['series'][0]['id'])]),
                  html.Fieldset([html.Legend('Période affichée'),dcc.RadioItems(id='macro-period',options=[{'label':l,'value':v} for v,l in [('all','Tout l’historique'),('20','20 ans'),('5','5 ans')]],value='all',inline=True)])],className='filters'),
        dcc.Graph(id='macro-graph',config={'displaylogo':False}),
        html.Div(table(['Série','Unité','Moyenne avril–sept. 2005','Rang de 2005 dans l’historique','Dernière valeur','Variation 1 an (points)','Variation 5 ans (points)'],rows,'Synthèse par série ; un rang de 50 % signifie un niveau médian'),className='table-wrap',tabIndex=0,role='region',**{'aria-label':'Synthèse macro-économique'}),
        html.Div(table(['Série']+[labels[i] for i in ids],[[labels[i]]+[number(corr[i][j]) for j in ids] for i in ids],f"Corrélations de Spearman des variations trimestrielles, {period['quarters']} trimestres de {period['start']} à {period['end']}"),className='table-wrap',tabIndex=0,role='region',**{'aria-label':'Corrélations macro-économiques'}),
        html.A('Télécharger la synthèse macro en CSV',href='/download/macro.csv'),
        html.P('Les séries US et le taux de change décrivent un contexte sectoriel et monétaire, pas la situation des clients taïwanais. Une corrélation n’est pas une causalité ; les valeurs manquantes ne sont pas remplies.')],className='panel')
app=Dash(__name__,title='BC2 · Analyse du défaut bancaire',assets_folder=str(Path(__file__).parent/'assets'))
app.index_string=app.index_string.replace('<html>','<html lang="fr">')
app.layout=html.Div([
    html.A('Aller au contenu',href='#content',className='skip'),
    html.Header([html.P('RNCP40875 · BC2 · Thomas Gassmann',className='eyebrow'),html.H1('Comprendre le défaut bancaire'),html.P('Un portefeuille historique pour comparer les méthodes, examiner les erreurs et documenter les limites.'),html.Nav([html.A(label,href=href) for label,href in [('Portefeuille','#portfolio'),('Statistiques','#statistics'),('Modèles','#models'),('Cotations','#market'),('Macro-économie','#macro'),('Synthèse IA','#genai')]],**{'aria-label':'Sections du tableau de bord'})]),
    html.Main([
        html.Div([html.Strong('Périmètre observé : '),html.Span('Taïwan, historiques de 2005. Aucun score ne constitue une décision de crédit. Les cotations IBM et les séries macro-économiques sont des sources séparées, sans jointure avec les clients.')],className='notice'),
        html.Section([html.H2('Lire les résultats selon le métier'),html.P('Vues de consultation ; aucun contrôle d’accès par rôle dans cette démonstration locale.'),html.Div([html.Button(label,id='view-'+key,n_clicks=0) for key,label in [('direction','Direction'),('risk','Risques'),('data','Analyse de données')]],className='filters'),html.Div(id='audience-result',role='status',**{'aria-live':'polite'})],className='panel'),
        html.Section([html.H2('Explorer le portefeuille',id='portfolio'),html.P('Les filtres portent sur les 30 000 observations. Les résultats prédictifs ci-dessous portent uniquement sur le test réservé.'),
            html.Div([html.Div([html.Label('Variable de segmentation',htmlFor='segment'),dcc.Dropdown(id='segment',options=[{'label':l,'value':v} for v,l in [('EDUCATION','Niveau d’études'),('PAY_0','Code de remboursement récent'),('SEX','Sexe — audit descriptif')]],value='EDUCATION',clearable=False)]),html.Div([html.Label('Modalité à explorer',htmlFor='level'),dcc.Dropdown(id='level',options=[{'label':'Toutes les modalités','value':'all'}],value='all',clearable=False)]),html.Div([html.Label('Âge minimum',htmlFor='age-min'),dcc.Input(id='age-min',type='number',value=0,min=0,max=120,debounce=True)]),html.Div([html.Label('Âge maximum',htmlFor='age-max'),dcc.Input(id='age-max',type='number',value=120,min=0,max=120,debounce=True)])],className='filters'),
            html.P(id='filter-status',role='status',**{'aria-live':'polite'}),html.Div(id='cohort-cards',className='cards'),dcc.Graph(id='segment-graph',config={'displaylogo':False}),html.Div(id='segment-table',className='table-wrap',tabIndex=0,role='region',**{'aria-label':'Tableau des segments'}),html.A('Télécharger les statistiques du train en CSV',href='/download/univariate.csv')],className='panel'),
        html.Section([html.H2('Statistiques et réduction de dimension',id='statistics'),html.P('Exploration et projections ajustées sur le train uniquement. Les associations ne prouvent pas une causalité.'),dcc.Graph(figure=style(px.imshow(pd.DataFrame(reports['eda']['correlations']['spearman']),zmin=-1,zmax=1,color_continuous_scale='RdBu_r',title='Corrélations de Spearman — variables quantitatives du train')),config={'displaylogo':False}),
            table(['Analyse','Résultat'],[['ACP',str(reports['projections']['components_for_90_percent'])+' composantes pour 90 % de variance'],['AFD','Un seul axe pour deux classes'],['Ajustement','Train uniquement, validation projetée sans réapprentissage']],'Résumé accessible des projections'),
            dcc.Graph(figure=style(px.scatter(pd.DataFrame(reports['projections']['points']).assign(classe=lambda f:f.y.map({0:'Sans défaut',1:'Défaut'})),x='pc1',y='pc2',color='classe',symbol='classe',color_discrete_sequence=['#163e65','#9a3412'],title='ACP : échantillon déterministe du train',labels={'pc1':'Composante principale 1','pc2':'Composante principale 2','classe':'Défaut observé'})),config={'displaylogo':False}),
            dcc.Graph(figure=style(px.histogram(pd.DataFrame(reports['projections']['points']),x='lda1',color='y',barmode='overlay',opacity=.65,title='AFD : distribution du seul axe discriminant',labels={'lda1':'Axe discriminant 1','y':'Défaut observé'})),config={'displaylogo':False}),
            projection_alternatives(),
            table(['Variable','Test','p ajustée BH'],[[r['variable'],r['test'],f"{r.get('p_adjusted_bh'):.3g}" if r.get('p_adjusted_bh') is not None else 'Non retenue : conditions à vérifier'] for r in reports['eda']['tests']],'Tests bivariés sur le train — hypothèses et tailles d’effet dans le rapport')],className='panel'),
        html.Section([html.H2('Comparer les modèles et leurs erreurs',id='models'),html.P(f"Modèle choisi sur validation : {NAMES[selected]}. Seuil : {test['threshold']:.2f}. Aucun réglage sur le test."),dcc.Graph(figure=model_figure(),config={'displaylogo':False}),
            table(['Modèle','PR-AUC','ROC-AUC','Précision','Rappel','F1','Temps entraînement + CV (s)'],[[NAMES[k],f"{v['test']['pr_auc_average_precision']:.4f}",f"{v['test']['roc_auc']:.4f}",percentage(v['test']['precision']),percentage(v['test']['recall']),f"{v['test']['f1']:.4f}",f"{v['fit_and_cv_wall_seconds']:.2f}"] for k,v in reports['models']['models'].items()],'Résultats sur le même test réservé, seuil propre à chaque modèle fixé sur validation'),
            table(['Vrais positifs','Faux positifs','Vrais négatifs','Faux négatifs'],[[test[k] for k in ['tp','fp','tn','fn']]],'Matrice de confusion du modèle retenu'),html.P('Écoresponsabilité : temps CPU et pic mémoire mesurés ; énergie estimée à environ 0,03 Wh pour l’entraînement des quatre modèles (estimation, pas une mesure par capteur). Sexe et situation matrimoniale exclus des prédicteurs, sans garantie d’équité. Une validation temporelle future et une revue humaine restent nécessaires.')],className='panel'),
        html.Section([html.H2('Cotations et indicateurs financiers',id='market'),html.P(f"IBM · {reports['market']['rows']} séances · {reports['market']['first_date']} à {reports['market']['last_date']} · Alpha Vantage, API de démonstration officielle."),html.P('Cours quotidiens bruts, sans ajustement des dividendes. Devise non fournie dans cette réponse. Cache historique, pas un flux temps réel. Aucune jointure avec les clients de 2005.'),
            dcc.RadioItems(id='market-mode',options=[{'label':'Performance base 100','value':'base100'},{'label':'Drawdown','value':'drawdown'},{'label':'Volatilité glissante annualisée','value':'volatility20_annualized'}],value='base100',inline=True),dcc.Graph(id='market-graph',config={'displaylogo':False}),html.Div(id='market-table',className='table-wrap',tabIndex=0,role='region',**{'aria-label':'Table des indicateurs financiers'}),html.P('Volatilité : 20 rendements logarithmiques et convention √252. Les jours sans séance ne sont pas remplis. Ni prévision ni conseil d’investissement.')],className='panel'),
        macro_section(),
        html.Section([html.H2('Synthèse factuelle assistée par IA',id='genai'),html.P('Le modèle local reçoit des faits agrégés, sans identifiant client. Les chiffres restent dans les tableaux vérifiables. Chaque texte doit être relu.'),html.Button('Générer une synthèse à relire',id='generate',n_clicks=0),dcc.Loading(html.Div(id='generation-result',role='status',**{'aria-live':'polite'})),html.P('Le service peut refuser une réponse incomplète ou indisponible. Aucun message ni décision ne sont envoyés.')],className='panel'),
        html.Section([html.H2('Provenance et limites'),html.P('Dataset UCI Default of Credit Card Clients, I-Cheng Yeh, CC BY 4.0. Le dataset de référence du sujet n’étant pas disponible, la cible étudiée est le défaut de paiement du mois suivant.'),html.P('Run '+manifest['run_id']+' · Terminé '+manifest['finished_at_utc']),html.A('Source et dictionnaire UCI',href='https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients',target='_blank',rel='noopener noreferrer')],className='panel')
    ],id='content',tabIndex=-1),html.Footer('Projet individuel BC2 · Thomas Gassmann · Usage de démonstration locale')])

@callback(Output('audience-result','children'),Input('view-direction','n_clicks'),Input('view-risk','n_clicks'),Input('view-data','n_clicks'))
def audience_view(*clicks):
    role=(ctx.triggered_id or 'view-direction').removeprefix('view-')
    descriptions={'direction':('Direction : décider du périmètre du pilote','Les fausses alertes imposent de dimensionner une revue humaine. Aucun déploiement de décision de crédit ni gain financier ne sont validés.'),'risk':('Risques : examiner les erreurs',f"Sur le test réservé : {test['fp']} fausses alertes et {test['fn']} défauts manqués. Le seuil est figé sur validation ; son changement nécessite un nouveau protocole."),'data':('Analyse de données : contrôler le protocole','Préparation et projections ajustées sur train, groupes de profils séparés, sélection sur validation puis test réservé. Inspecter les artefacts et les intervalles bootstrap avant interprétation.')}
    title,text=descriptions[role];return [html.H3(title),html.P(text)]

@callback(Output('level','options'),Output('level','value'),Input('segment','value'))
def levels(segment):
    if segment not in ['EDUCATION','PAY_0','SEX']:raise ValueError('Segmentation invalide')
    return [{'label':'Toutes les modalités','value':'all'}]+[{'label':str(v),'value':str(v)} for v in sorted(cohort[segment].unique())],'all'

@callback(Output('filter-status','children'),Output('cohort-cards','children'),Output('segment-graph','figure'),Output('segment-table','children'),Input('segment','value'),Input('level','value'),Input('age-min','value'),Input('age-max','value'))
def filter_data(segment,level,minimum,maximum):
    empty=style(go.Figure())
    if segment not in ['EDUCATION','PAY_0','SEX'] or minimum is None or maximum is None or not 0<=minimum<=maximum<=120:return 'Filtres invalides : vérifier les âges.',[],empty,html.P('Aucun calcul publié pour ces filtres.')
    allowed=set(cohort[segment].astype(str))
    if level not in allowed|{'all',None}:return 'Modalité invalide.',[],empty,html.P('Aucun calcul publié.')
    f=cohort.loc[cohort.AGE.between(minimum,maximum)]
    if level not in ['all',None]:f=f.loc[f[segment].astype(str)==level]
    if f.empty:return 'Aucune observation pour ces filtres.',[],empty,html.P('Tableau vide pour la sélection.')
    grouped=f.groupby(segment).y.agg(n='size',defaults='sum').reset_index();grouped['Taux de défaut']=grouped.defaults/grouped.n
    cards=[html.Div([html.Span(label),html.Strong(value)]) for label,value in [('Observations',f'{len(f):,}'.replace(',',' ')),('Défauts observés',f'{int(f.y.sum()):,}'.replace(',',' ')),('Taux observé',percentage(float(f.y.mean())))]]
    fig=style(px.bar(grouped,x=segment,y='Taux de défaut',text='n',title='Taux observé par modalité — effectifs affichés',color_discrete_sequence=['#163e65']))
    return f'{len(f)} observations dans la sélection.',cards,fig,table(['Modalité','Observations','Défauts','Taux'],[[r[segment],r['n'],r['defaults'],percentage(r['Taux de défaut'])] for r in grouped.to_dict('records')],'Valeurs exactes correspondant au graphique')

@callback(Output('market-graph','figure'),Output('market-table','children'),Input('market-mode','value'))
def market_view(mode):
    labels={'base100':'Base 100','drawdown':'Drawdown','volatility20_annualized':'Volatilité annualisée'}
    if mode not in labels:raise ValueError('Indicateur inconnu')
    fig=style(px.line(market,x='date',y=mode,title=labels[mode]+' — IBM',labels={'date':'Date de séance',mode:labels[mode]}))
    return fig,table(['Date',labels[mode]],[[r['date'],'Non disponible' if pd.isna(r[mode]) else f"{r[mode]:.4f}"] for r in market.tail(12).to_dict('records')],'Douze dernières séances ; export complet dans les artefacts du run')

@callback(Output('macro-graph','figure'),Input('macro-series','value'),Input('macro-period','value'))
def macro_view(series_id,period):
    if macro_report is None:return style(go.Figure())
    specs={s['id']:s for s in macro_report['series']}
    if series_id not in specs or period not in ['all','20','5']:raise ValueError('Sélection macro invalide')
    data=macro_series.loc[(macro_series.series==series_id)&macro_series.value.notna()]
    if period!='all':data=data.loc[data.date>=data.date.max()-pd.DateOffset(years=int(period))]
    spec=specs[series_id]
    fig=style(px.line(data,x='date',y='value',title=spec['label']+' ('+spec['unit']+')',labels={'date':'Date','value':spec['unit']},color_discrete_sequence=['#163e65']))
    if data.date.min()<=pd.Timestamp(COHORT_END):
        fig.add_vrect(x0=COHORT_START,x1=COHORT_END,fillcolor='#b45309',opacity=.25,line_width=0,annotation_text='Cohorte 2005',annotation_position='top left')
    return fig

@callback(Output('generation-result','children'),Input('generate','n_clicks'),prevent_initial_call=True)
def generate_summary(clicks):
    from .generation import generate,facts_from_run
    try:
        result=generate(facts_from_run(path),'portfolio')
        return html.Div([html.H3('Brouillon à relire'),html.P(result['output']['summary']),html.P(result['output']['limits']),html.P('Faits cités : '+', '.join(result['output']['evidence_ids']))])
    except (ValueError,OSError,TimeoutError) as error:return html.P('Génération indisponible ou sortie refusée. Aucun texte de substitution et aucun envoi.')

@app.server.get('/health')
def health():return jsonify({'status':'ready','run_id':manifest['run_id'],'source_sha256':reports['quality']['source_sha256']})
@app.server.get('/download/univariate.csv')
def download():return send_file(path/'univariate.csv',as_attachment=True,download_name='statistiques-train.csv')
@app.server.get('/download/<name>.csv')
def download_graph_data(name):
    if name=='correlations':
        frame=pd.DataFrame(reports['eda']['correlations']['spearman']);index=True
    elif name=='projections':
        frame=pd.DataFrame(reports['projections']['points']);index=False
    elif name=='macro' and macro_report is not None:
        frame=pd.DataFrame(macro_report['series']);index=False
    else:return jsonify({'error':'Export inconnu'}),404
    return send_file(io.BytesIO(frame.to_csv(index=index).encode('utf-8-sig')),as_attachment=True,download_name=name+'.csv',mimetype='text/csv; charset=utf-8')
@app.server.after_request
def headers(response):
    response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='no-referrer';response.headers['X-Frame-Options']='DENY';response.headers['Cache-Control']='no-store';return response
if __name__=='__main__':app.run(host='0.0.0.0',port=8052,debug=False,use_reloader=False)
