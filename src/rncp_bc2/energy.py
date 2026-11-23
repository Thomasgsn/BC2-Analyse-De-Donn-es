"""Estimation a posteriori de l'énergie et du CO2 à partir des temps mesurés.

Méthode Green Algorithms (Lannelongue et al., 2021) : énergie = temps × (puissance des
cœurs utilisés + puissance mémoire) × PUE. Aucune mesure par wattmètre ou capteur :
les résultats sont des ordres de grandeur, documentés avec leurs hypothèses.
"""
import json
import sys
from .storage import ROOT, save, now, digest

# Hypothèses sourcées, appliquées au poste de réalisation (Intel Core i9-9980HK).
CPU_MODEL = 'Intel Core i9-9980HK (8 cœurs, 16 threads)'
CPU_TDP_W = 45.0          # TDP constructeur
CPU_SUSTAINED_W = 55.0    # puissance soutenue observée en test (Notebookcheck), hypothèse haute
PHYSICAL_CORES = 8
MEMORY_W_PER_GB = 0.3725  # constante Green Algorithms (valeur discutée)
PUE = 1.0                 # poste personnel, pas de centre de données
CARBON_G_PER_KWH = 19.6   # intensité moyenne du réseau français en 2025 (RTE, bilan électrique 2025)
CARBON_MAX_G_PER_KWH = 58.0  # maximum horaire 2025 (RTE éCO2mix), hypothèse haute
SOURCES = {
    'method': 'Lannelongue, Grealey, Inouye, Green Algorithms, Advanced Science 2021, arXiv:2007.07610',
    'cpu_tdp': 'https://www.intel.com/content/www/us/en/products/sku/192990/intel-core-i99980hk-processor-16m-cache-up-to-5-00-ghz/specifications.html',
    'cpu_sustained': 'https://www.notebookcheck.net/Intel-Core-i9-9980HK-Processor-Benchmarks-and-Specs.416730.0.html',
    'carbon_intensity': 'https://analysesetdonnees.rte-france.com/en/annual-review-2025/ghg-emissions',
}


def joules(cpu_seconds, wall_seconds=0.0, memory_gb=0.0, watts_per_core=CPU_TDP_W / PHYSICAL_CORES):
    """Énergie en joules : secondes CPU × puissance par cœur, plus la mémoire sur la durée réelle."""
    if min(cpu_seconds, wall_seconds, memory_gb) < 0:
        raise ValueError('Durées et mémoire doivent être positives')
    return (cpu_seconds * watts_per_core + wall_seconds * memory_gb * MEMORY_W_PER_GB) * PUE


def summary(energy_j, carbon=CARBON_G_PER_KWH):
    wh = energy_j / 3600
    return {'joules': round(energy_j, 2), 'wh': round(wh, 4), 'co2_g': round(wh / 1000 * carbon, 6)}


def estimate(run_id='baseline-20261120-v2'):
    run = ROOT / 'docs/evidence/pipeline' / run_id
    models = json.loads((run / 'models.json').read_text())['models']
    manifest = json.loads((run / 'manifest.json').read_text())
    generation_path = ROOT / 'docs/evidence/generative/evaluation.json'
    generation = json.loads(generation_path.read_text())

    per_model, total_j, total_high_j = {}, 0.0, 0.0
    for name, record in models.items():
        memory_gb = record['memory_peak_mib_process'] / 1024
        args = (record['cpu_seconds'], record['fit_and_cv_wall_seconds'], memory_gb)
        energy = joules(*args)
        high = joules(*args, watts_per_core=CPU_SUSTAINED_W / PHYSICAL_CORES)
        total_j += energy
        total_high_j += high
        per_model[name] = {'cpu_seconds': record['cpu_seconds'], 'wall_seconds': record['fit_and_cv_wall_seconds'],
                           **summary(energy)}

    # Run complet : borne haute, deux threads occupés pendant toute la durée mesurée.
    run_cpu_bound = manifest['elapsed_seconds'] * manifest['threads']
    run_energy = joules(run_cpu_bound)

    # LLM : borne haute, processeur entier à son TDP pendant chaque génération.
    durations = [case['result']['timing_ns']['total_duration'] / 1e9
                 for case in generation['cases'] if 'result' in case]
    llm_energy = CPU_TDP_W * sum(durations)
    llm_high = CPU_SUSTAINED_W * sum(durations)

    return {
        'created_at_utc': now(),
        'status': 'estimation a posteriori, pas une mesure par capteur',
        'inputs': {'run_id': run_id, 'models_sha256': digest(run / 'models.json'),
                   'manifest_sha256': digest(run / 'manifest.json'),
                   'generation_sha256': digest(generation_path)},
        'assumptions': {'cpu': CPU_MODEL, 'cpu_tdp_w': CPU_TDP_W, 'cpu_sustained_w_high': CPU_SUSTAINED_W,
                        'watts_per_cpu_second': CPU_TDP_W / PHYSICAL_CORES,
                        'memory_w_per_gb': MEMORY_W_PER_GB, 'pue': PUE,
                        'carbon_g_per_kwh': CARBON_G_PER_KWH, 'carbon_max_g_per_kwh_high': CARBON_MAX_G_PER_KWH,
                        'sources': SOURCES},
        'training_per_model': per_model,
        'training_total': summary(total_j),
        'training_total_high': summary(total_high_j, CARBON_MAX_G_PER_KWH),
        'full_run_upper_bound': {'elapsed_seconds': manifest['elapsed_seconds'], 'threads': manifest['threads'],
                                 **summary(run_energy)},
        'llm_generations': {'count': len(durations), 'seconds': round(sum(durations), 2),
                            'upper_bound': summary(llm_energy), 'upper_bound_high': summary(llm_high, CARBON_MAX_G_PER_KWH),
                            'per_generation_wh': round(llm_energy / 3600 / len(durations), 4)},
        'llm_vs_training_ratio': round(llm_energy / len(durations) / total_j, 1),
        'not_included': ['surcoût de la machine virtuelle Docker', 'écran, disque, réseau et consommation au repos',
                         'fabrication du matériel', 'téléchargement du dataset et du modèle'],
    }


def main():
    out = ROOT / 'docs/evidence/energy' / (sys.argv[1] if len(sys.argv) > 1 else 'estimate.json')
    if out.exists():
        raise SystemExit(f'{out} existe déjà : choisir un autre nom')
    report = estimate()
    save(out, report)
    print(json.dumps({k: report[k] for k in ['training_total', 'full_run_upper_bound', 'llm_generations', 'llm_vs_training_ratio']},
                     ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
