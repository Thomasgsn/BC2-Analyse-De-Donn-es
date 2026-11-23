# Dictionnaire BC2

Termes utiles pour comprendre et défendre le projet. Chaque entrée : définition, rôle ici, exemple si besoin.

## Défaut de paiement

Le client ne rembourse pas ce qu’il doit à l’échéance.
Ici : variable cible « default payment next month » du dataset UCI ; 22,12 % des clients sont en défaut.

## Partition groupée

Découpage en lots d’apprentissage, de validation et de test où des lignes liées restent ensemble.
Ici : les profils identiques sont placés dans le même lot (StratifiedGroupKFold), pour qu’un modèle ne soit pas testé sur une copie d’une ligne apprise.

## Pearson et Spearman

Deux coefficients de corrélation entre −1 et 1. Pearson mesure un lien linéaire ; Spearman compare les rangs et résiste mieux aux valeurs extrêmes.
Ici : Spearman complète Pearson car les montants sont très asymétriques.

## Chi-deux

Test du Chi² (chi-deux) : vérifie si deux variables catégorielles sont indépendantes.
Ici : le résultat n’est publié que si chaque case du tableau attend au moins 5 observations ; sinon l’approximation n’est pas fiable.

## Welch et ANOVA

Tests qui comparent des moyennes entre groupes. Le test de Welch n’exige pas des variances égales ; l’ANOVA compare plus de deux groupes.
Ici : comparaison des montants entre clients en défaut et non en défaut, et des plafonds selon le niveau d’études.

## Benjamini-Hochberg

Correction qui limite la part de fausses découvertes quand on fait beaucoup de tests.
Ici : appliquée aux p-values de chaque famille de tests.

## ACP

Analyse en composantes principales : résume beaucoup de variables corrélées en quelques axes.
Ici : 8 axes gardent 90 % de l’information des 14 variables quantitatives.

## AFD

Analyse factorielle discriminante : cherche l’axe qui sépare le mieux des classes connues.
Ici : un seul axe, car il n’y a que deux classes (défaut ou non).

## Average precision

Résumé de la courbe précision-rappel entre 0 et 1, proche de la PR-AUC. Utile quand la classe recherchée est minoritaire.
Ici : critère de choix du modèle ; 0,547 pour la forêt contre 0,221 pour un modèle constant.

## Seuil et F2

Le seuil transforme un score en décision « alerte / pas d’alerte ». Le F2 combine précision et rappel en donnant plus de poids au rappel.
Ici : seuil 0,15 choisi pour maximiser le F2 sur la validation, car rater un défaut est jugé plus grave qu’une fausse alerte.

## Bootstrap

Méthode qui rééchantillonne les données pour estimer l’incertitude d’une mesure.
Ici : 150 rééchantillonnages donnent un rappel compris entre 78,8 % et 82,5 %.

## Calibration

Concordance entre un score et la fréquence réelle de l’événement.
Ici : décrite par groupes de scores ; aucun recalibrage n’est fait, donc le score n’est pas une probabilité garantie.

## Green Algorithms

Méthode publiée d’estimation de l’énergie d’un calcul : temps × (puissance des cœurs utilisés + puissance de la mémoire) × PUE (surcoût du bâtiment, 1 sur un poste personnel).
Ici : appliquée aux temps CPU mesurés ; l’entraînement des quatre modèles est estimé à 0,03 Wh. C’est une estimation, pas une mesure par capteur.

## Volatilité annualisée

Variabilité des rendements ramenée à un an.
Ici : écart-type de 20 rendements journaliers multiplié par √252 (nombre conventionnel de séances par an).

## Drawdown

Baisse depuis le plus haut atteint jusqu’au point courant.
Exemple : −32,78 % signifie que le cours a perdu jusqu’à un tiers par rapport à son sommet sur la période.

## FRED

Base de données économiques publique de la Réserve fédérale de Saint-Louis.
Ici : source des retards et pertes sur cartes de crédit, du taux des cartes, du taux à 10 ans et du dollar taïwanais.

## Ollama

Outil qui fait tourner un modèle de langage sur la machine locale.
Ici : exécute Qwen3 1.7B pour rédiger des synthèses, sans envoyer de données à l’extérieur.
