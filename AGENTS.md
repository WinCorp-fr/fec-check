# AGENTS.md : utiliser fec-check depuis un agent

fec-check est un validateur déterministe de FEC (fichier des écritures comptables français, art. A.47 A-1 LPF). Aucun réseau, aucun aléa, aucune écriture disque hors la sortie standard.

## Installation

```bash
pip install "git+https://github.com/WinCorp-fr/fec-check@v1.0.0"   # seule dépendance : pydantic>=2.5
```

## Appel

```bash
fec-check <fec> --format json [--profil <profil.json>]
python -m fec_check <fec> --format json        # équivalent
```

| Code retour | Sens |
| --- | --- |
| 0 | Aucun constat bloquant |
| 1 | Au moins un constat bloquant (le rapport JSON est complet) |
| 2 | Erreur d'usage : fichier absent, profil illisible ou invalide (message sur stderr, pas de JSON) |

Un fichier illisible n'est pas une erreur d'usage : il produit un constat T1 bloquant et le code 1.

## Profil (facultatif)

Objet JSON, champs tous facultatifs, champ inconnu refusé (code 2) :

| Champ | Type | Effet |
| --- | --- | --- |
| `forme_juridique` | texte (`EI` ou autre) | Active ECF-1 (108 hors EI) et ECF-2 (455 en EI) |
| `date_debut_exercice`, `date_fin_exercice` | date ISO 8601 | Active C6 (dates hors exercice) |
| `exercice_clos` | booléen | ECF-3 bloquant si vrai, avertissement sinon |
| `comptes_digits` | entier | Accepté, sans effet sur les contrôles en 1.0 |
| `journaux_an` | liste de codes journal | Remplace la détection automatique des à-nouveaux |

## Sortie JSON

```json
{
  "fichier": "FEC_2025.txt",
  "verdict": "AUCUN_BLOQUANT | BLOQUANTS_DETECTES",
  "nb_bloquants": 0, "nb_avertissements": 0, "nb_infos": 1,
  "constats": [
    {"code": "C9", "gravite": "bloquant | avertissement | info",
     "message": "…", "occurrences": ["53000000"], "montant_ecart": "80.00"}
  ],
  "meta": {"encodage": "utf-8", "separateur_colonnes": "|", "nb_lignes": 16,
           "date_min": "…", "date_max": "…", "total_debit": "…", "total_credit": "…"},
  "profil_fourni": false,
  "non_evalues": ["C6 : …", "ECF-1 : …", "ECF-2 : …"]
}
```

- Montants en chaînes décimales (jamais de flottant). Constats triés par code (T, puis C, puis ECF), occurrences triées.
- Occurrences : `L<n>` = ligne du fichier, `<journal>/<numéro>` = écriture, sinon numéro de compte ou code journal.
- Les codes sont stables d'une version à l'autre. Leur sens : [skill/fec-check/references/constats.md](skill/fec-check/references/constats.md).

## Règles pour l'agent

- Ne pas recalculer ni corriger les constats : les citer.
- Ne pas écrire « conforme » : écrire « aucune anomalie bloquante détectée ».
- Ne pas transmettre le FEC à un service tiers.

## Développer

```bash
pip install -e ".[dev]"
pytest && ruff check . && ruff format --check . && mypy src tests scripts
```

Ne pas modifier à la main `src/fec_check/{fec,pcg,controles,pydantic_types}.py` ni `tests/moteur/` : fichiers générés (empreinte de la source en tête de fichier). Le code propre au dépôt public est `rapport.py`, `cli.py`, `__init__.py`, `__main__.py`, la skill et les scripts.
