# Checklist BC2

Statuts : **À faire**, **En cours**, **Fait** (coché seulement avec une preuve). Ordre = priorité.

## 1. À faire personnellement (Thomas)

| # | Action | Pourquoi | Comment | Preuve à garder | Statut |
|---|---|---|---|---|---|
| 1 | Faire accepter le travail individuel | Le sujet prévoit un binôme | Message à l’enseignant (adresse dans le sujet) | Réponse écrite | À faire |
| 2 | Relire rapport, support, dashboard et déclaration d’usage de l’IA | Contenu assisté par IA à défendre seul ; vérifier le règlement de l’école | Lire `docs/rapport.md`, le PDF, le PPTX ; parcourir le dashboard | Version relue | À faire |
| 3 | Faire une revue humaine des synthèses générées | C5.3 demande une évaluation de clarté et pertinence ; aucune note humaine n’existe | Noter 2 à 4 synthèses (clarté, pertinence, inclusivité) ; idéalement par une autre personne | Grille remplie | À faire |
| 4 | Répéter la soutenance et la démonstration | Évaluation orale | Lancer le dashboard, suivre le support | Notes de répétition | À faire |
| 5 | Remettre le rendu | Évaluation | Déposer rapport et support sur la plateforme de l’école ; dépôt Git si demandé | Accusé de dépôt | À faire |

## 2. À autoriser ou fournir pour qu’un agent continue

| # | Action | Pourquoi | Comment | Statut |
|---|---|---|---|---|
| 6 | Fournir une clé Alpha Vantage gratuite ou un export de cotations autorisé | La clé de démonstration ne donne qu’IBM ; le sujet parle de plusieurs titres | Créer une clé gratuite sur le site du fournisseur et la donner hors chat (fichier local ignoré par Git) | À faire |
| 7 | Autoriser l’initialisation Git et le commit, ou les faire vous-même | BC2 n’a pas encore de dépôt Git ; les consignes interdisent commit et push | Dire explicitement ce qui est autorisé | À faire |

## 3. Reste technique (automatisable)

| # | Action | Pourquoi | Statut |
|---|---|---|---|
| 8 | Ajouter plusieurs titres et une comparaison entre eux | Partie 2 encore limitée à IBM | Bloqué par l’action 6 |

## 4. Améliorations facultatives

- Mesurer l’énergie avec un capteur (wattmètre ou compteurs du processeur) pour confirmer l’estimation.
- Recalibrer les scores (par exemple calibration isotonique sur validation).
- Ajouter une authentification au dashboard si une démonstration hors poste est prévue.

## Déjà fait (preuves)

- [x] Pipeline complet et reproductible — `docs/evidence/pipeline/reproduction.json`
- [x] Quatre modèles comparés sur test réservé — `docs/evidence/pipeline/baseline-20261120-v2/models.json`
- [x] Contexte macro-économique FRED — `docs/evidence/macro/fred-20261123.json`
- [x] Estimation de l’énergie et du CO₂ (méthode Green Algorithms, 39 tests unitaires) — `docs/evidence/energy/estimate-20261123.json`
- [x] Dashboard testé dans Chromium avec axe — `docs/evidence/browser/browser-checks.json`, `docs/evidence/browser/macro-checks.json`
- [x] Évaluation générative automatique — `docs/evidence/generative/evaluation.json`
- [x] Rapport PDF (14 pages) et support (15 diapositives) — `output/`
