"""Figures des résultats réellement persistés, sans nouvel apprentissage."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np,pandas as pd
from sklearn.metrics import precision_recall_curve,roc_curve
from rncp_bc2.storage import latest,ROOT,save,digest
path,m=latest();out=ROOT/'docs/evidence/figures';out.mkdir(exist_ok=True,parents=True)
r=json.loads((path/'models.json').read_text());p=json.loads((path/'projections.json').read_text());cohort=pd.read_parquet(path/'cohort.parquet');pred=pd.read_parquet(path/'test-predictions.parquet')
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150})
names={'dummy':'Référence constante','logistic':'Logistique','tree':'Arbre','forest':'Forêt'}
fig,axs=plt.subplots(1,2,figsize=(11,4.4))
for k,name in names.items():
 precision,recall,_=precision_recall_curve(pred.y,pred[k+'_score']);fpr,tpr,_=roc_curve(pred.y,pred[k+'_score']);axs[0].plot(recall,precision,label=name);axs[1].plot(fpr,tpr,label=name)
axs[0].axhline(pred.y.mean(),ls=':',color='gray');axs[0].set(xlabel='Rappel',ylabel='Précision',title='Précision–rappel · test réservé');axs[1].plot([0,1],[0,1],ls=':',color='gray');axs[1].set(xlabel='Taux de faux positifs',ylabel='Rappel',title='Courbes ROC · test réservé');axs[1].legend(loc='lower right');fig.tight_layout();fig.savefig(out/'performance.png');plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(11,4.4));axs[0].plot(np.arange(1,15),np.cumsum(p['explained_variance_ratio']),marker='o');axs[0].axhline(.9,ls=':',color='gray');axs[0].set(xlabel='Nombre de composantes',ylabel='Variance cumulée',title='ACP · train uniquement')
for k,name in names.items():
 c=r['models'][k]['calibration'];axs[1].plot(c['prediction_bin_mean'],c['observed_fraction'],marker='o',label=name)
axs[1].plot([0,1],[0,1],ls=':',color='gray');axs[1].set(xlabel='Score moyen',ylabel='Fréquence observée',title='Calibration descriptive · test');axs[1].legend();fig.tight_layout();fig.savefig(out/'projections-calibration.png');plt.close(fig)
train=cohort.loc[cohort.split=='train'];fig,axs=plt.subplots(1,2,figsize=(11,4.4));axs[0].hist(train.LIMIT_BAL/1000,bins=35,color='#163e65');axs[0].set(title='Distribution des plafonds · train',xlabel='Montant source (milliers de NT dollars)',ylabel='Effectif');axs[1].boxplot([train.loc[train.y==v,'LIMIT_BAL']/1000 for v in [0,1]],tick_labels=['Sans défaut','Défaut'],showfliers=True);axs[1].set(title='Plafond selon le défaut · train',ylabel='Montant source (milliers de NT dollars)');fig.tight_layout();fig.savefig(out/'univariate.png');plt.close(fig)
market=pd.read_parquet(path/'market.parquet');fig,axs=plt.subplots(1,2,figsize=(11,4.4));dates=pd.to_datetime(market.date);axs[0].plot(dates,market.base100,color='#163e65');axs[0].set(title='IBM · cours brut base 100',ylabel='Indice');axs[1].fill_between(dates,market.drawdown*100,0,color='#b45309',alpha=.5);axs[1].set(title='Recul depuis le plus haut observé',ylabel='Drawdown (%)');fig.autofmt_xdate();fig.tight_layout();fig.savefig(out/'market.png');plt.close(fig)
from rncp_bc2.macro import latest_macro,COHORT_START,COHORT_END
macro=latest_macro()
if macro:
 report,series=macro;fig,axs=plt.subplots(1,2,figsize=(11,4.4))
 for sid,label,color in [('DRCCLACBS','Retards cartes de crédit','#163e65'),('CORCCACBS','Pertes cartes de crédit','#b45309')]:
  s=series.loc[(series.series==sid)&series.value.notna()];axs[0].plot(s.date,s.value,label=label,color=color)
 fx=series.loc[(series.series=='DEXTAUS')&series.value.notna()];axs[1].plot(fx.date,fx.value,color='#0f766e')
 for ax in axs:ax.axvspan(pd.Timestamp(COHORT_START),pd.Timestamp(COHORT_END),color='#b45309',alpha=.25,label='Cohorte 2005' if ax is axs[0] else None)
 axs[0].set(title='Banques US · cartes de crédit (FRED)',ylabel='% des encours');axs[0].legend();axs[1].set(title='Dollar taïwanais pour 1 USD (FRED)',ylabel='TWD/USD')
 fig.tight_layout();fig.savefig(out/'macro.png');plt.close(fig)
save(out/'manifest.json',{'run_id':m['run_id'],'source':'Persisted model results and real source data; no new tuning','files':{f.name:digest(f) for f in out.glob('*.png')}});print('figures réelles produites')
