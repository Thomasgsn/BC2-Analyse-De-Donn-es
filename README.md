# BC2 — Analyse du défaut bancaire et IA générative

Le projet analyse 30 000 clients de cartes de crédit (dataset public UCI, Taïwan, 2005) pour comprendre et prédire le [défaut de paiement](docs/dictionnaire.md#défaut-de-paiement). Il compare quatre modèles, présente les résultats dans un tableau de bord interactif, ajoute des données financières et macro-économiques externes, et teste un LLM local qui rédige des synthèses à relire.

**Choix des données** : le projet utilise le dataset public UCI Default of Credit Card Clients ; la cible est donc le défaut de paiement du mois suivant, et non la résiliation.

## Documents du rendu

| Document | Contenu |
|---|---|
| [docs/rapport.md](docs/rapport.md) | Besoin, données, méthode, résultats, stratégie IA, limites, correspondance RNCP |
| [Rapport PDF](output/pdf/rapport-bc2-thomas-gassmann.pdf) | Rapport final de 14 pages |
| [Support de soutenance](output/presentations/soutenance-bc2-thomas-gassmann.pptx) | 15 diapositives |
| [docs/dictionnaire.md](docs/dictionnaire.md) | Termes statistiques et techniques expliqués |
| `docs/evidence/` | Preuves : résultats du pipeline, figures, tests navigateur, évaluation générative |

## Lancer le projet

Prérequis : Docker avec Compose v2, accès Internet pour les acquisitions initiales, environ 8 Gio de RAM libres et 10 Gio de disque. Aucun compte payant ni secret. Le port 8052 doit être libre. Commandes depuis `bc2/` :

```sh
docker compose build job
docker compose run --rm job acquire
docker compose run --rm job run --run-id essai-local-001
docker compose run --rm job macro --snapshot-id fred-local-001
docker compose up -d --wait dashboard
```

Puis ouvrir http://127.0.0.1:8052.

| Commande | Effet |
|---|---|
| `acquire` | Télécharge le fichier UCI et vérifie son empreinte SHA-256 |
| `run --run-id` | Prépare les données, calcule statistiques et projections, entraîne et évalue les modèles, récupère les cotations IBM. Un identifiant déjà utilisé est refusé |
| `macro --snapshot-id` | Télécharge une fois cinq séries FRED, sans clé, et publie un snapshot daté |

**Estimation de l’énergie** (à partir des temps mesurés, méthode Green Algorithms) :

```sh
docker compose run --rm --entrypoint python job -m rncp_bc2.energy estimate-NOUVEAU.json
```

Le résultat est écrit dans `docs/evidence/energy/` ; un nom déjà utilisé est refusé.

Le dashboard lit le dernier run complet au démarrage : le redémarrer après un nouveau run.

**IA générative** (facultative dans le sujet, couvre C5 du référentiel) :

```sh
docker compose --profile genai up -d ollama
docker compose exec ollama ollama pull qwen3:1.7b
docker compose run --rm --entrypoint python job scripts/lock_model.py
```

`lock_model.py` compare le modèle téléchargé à l’empreinte de `infra/llm.lock.json` et refuse s’il diffère.

## Tests

```sh
docker compose run --rm tests
docker compose run --rm --entrypoint python job tests/integration/verify_pipeline.py
docker compose build browser-tests
docker compose run --rm browser-tests
docker compose run --rm --entrypoint python browser-tests tests/integration/macro_browser.py
```

- `tests` : 39 tests unitaires.
- `verify_pipeline.py` : empreintes des artefacts, rechargement des quatre modèles, prédictions identiques.
- `browser-tests` : parcours réel dans Chromium (filtres, clavier, vues métier, génération, mobile, contrôle d’accessibilité axe). Demande le dashboard et le modèle Ollama démarrés.
- `macro_browser.py` : section macro-économique du dashboard.

Les résultats du rapport viennent du run `baseline-20261120-v2` et du snapshot `fred-20261123`. Une seconde exécution indépendante a donné les mêmes partitions et les mêmes prédictions (`docs/evidence/pipeline/reproduction.json`).

## Livrables générés

| Livrable | Générateur |
|---|---|
| Figures | `docker compose run --rm --entrypoint python job scripts/make_figures.py` |
| Rapport PDF | `scripts/build_report.py` (ReportLab, pypdf) |
| Support PPTX | `scripts/build_deck.mjs` (bibliothèque de présentation du runtime Codex, chemins à adapter sur une autre machine) |
| Archive locale | `python3 scripts/package_delivery.py` |

## Organisation

- `src/rncp_bc2/` : acquisition, préparation, statistiques, ACP/AFD, modèles, marché, macro-économie, génération, dashboard.
- `data/raw/` : sources téléchargées (exclues de l’archive) ; `exports/<run>/` : résultats d’un run ; `models/<run>/` : modèles.
- `requirements.lock` : 52 dépendances verrouillées par empreinte ; image Python 3.12 épinglée.

`docker compose stop` arrête sans effacer les données. Ne pas utiliser `down -v`, qui supprimerait les poids du LLM.

## Usage de l’IA

J’ai utilisé des assistants d’IA générative (Codex, puis Claude pour les derniers ajouts et la relecture) pour la réécriture des textes, la recherche et le sourçage des références et l’aide au développement. Les résultats cités viennent des exécutions du projet et renvoient à `docs/evidence/`.

## Limites principales

- Données historiques de 2005 : aucune efficacité sur des clients actuels n’est démontrée.
- Le dashboard est une démonstration locale, sans authentification ni HTTPS.
- Les textes générés sont des brouillons ; aucune décision de crédit ni aucun envoi automatique.
