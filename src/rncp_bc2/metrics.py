"""Métriques binaires explicites et correction des comparaisons multiples."""
import numpy as np
from sklearn.metrics import roc_auc_score,average_precision_score,confusion_matrix,brier_score_loss

def binary_metrics(y,score,threshold=.5):
    y=np.asarray(y);score=np.asarray(score,dtype=float)
    if not len(y) or len(y)!=len(score) or not set(np.unique(y))<={0,1}:raise ValueError('Cible binaire non vide requise')
    if not np.isfinite(score).all() or (score<0).any() or (score>1).any() or not 0<=threshold<=1:raise ValueError('Score/seuil hors [0,1]')
    pred=(score>=threshold).astype(int);tn,fp,fn,tp=map(int,confusion_matrix(y,pred,labels=[0,1]).ravel())
    return {'n':len(y),'positives':int(y.sum()),'threshold':threshold,'tp':tp,'fp':fp,'tn':tn,'fn':fn,'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,'f2':5*tp/(5*tp+4*fn+fp) if 5*tp+4*fn+fp else None,'roc_auc':roc_auc_score(y,score) if len(np.unique(y))==2 else None,'pr_auc_average_precision':average_precision_score(y,score) if y.sum() else None,'brier':brier_score_loss(y,score),'assumed_cost_units':4*fn+fp,'cost_definition':'Illustrative FN=4, FP=1 units, not measured monetary cost'}

def threshold_on_validation(y,score):
    rows=[binary_metrics(y,score,float(t)) for t in np.linspace(.05,.95,19)]
    best=max(rows,key=lambda m:((m['f2'] if m['f2'] is not None else -1),m['threshold']))
    return best,rows

def bh_adjust(pvalues):
    p=np.asarray(pvalues,dtype=float)
    if len(p)==0:return []
    if not np.isfinite(p).all() or (p<0).any() or (p>1).any():raise ValueError('p-values invalides')
    order=np.argsort(p);adjusted=np.minimum.accumulate((p[order]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]
    out=np.empty(len(p));out[order]=np.minimum(adjusted,1);return out.tolist()
