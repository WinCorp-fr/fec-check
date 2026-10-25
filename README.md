# fec-check

**Vérifiez en une minute si votre FEC tiendrait face à un contrôle fiscal.** Gratuit, open source (licence MIT), et votre fichier ne quitte jamais votre ordinateur.

fec-check lit un Fichier des Écritures Comptables (le FEC, art. A.47 A-1 du livre des procédures fiscales) et liste ses anomalies, classées en trois niveaux : bloquant, avertissement, information. Chaque anomalie est expliquée en français, avec les lignes concernées et l'action à mener.

Il s'utilise de trois façons : dans Claude, en ligne de commande, ou depuis Python.

```text
FEC : FEC_2025.txt
Verdict : 1 anomalie(s) bloquante(s) détectée(s)
16 lignes lues, du 01/01/2025 au 05/03/2025, séparateur pipe |, encodage UTF-8

BLOQUANT (1)
  C9    Solde de caisse créditeur à partir du 20250228 — impossible physiquement (écart 80.00 €)
        concerne : 53000000
```

## Ce que fec-check contrôle

| Famille | Contrôles |
| --- | --- |
| Format (T1 à T11) | Encodage, séparateur (tabulation ou pipe), 18 colonnes, noms de colonnes, dates, montants, longueur des comptes, fins de ligne, lignes nulles, montants signés, pièces incomplètes |
| Comptabilité (C1 à C10) | Équilibre global et par écriture, débit et crédit sur la même ligne, comptes 79 supprimés, numérotation des écritures, dates hors exercice, date de pièce, auxiliaires clients et fournisseurs, **caisse négative au jour le jour**, **découvert bancaire de plus de 30 jours** |
| Forme et clôture (ECF-1 à ECF-4) | Compte 108 ou 455 selon la forme juridique, écritures non validées à la clôture, à-nouveaux déséquilibrés |

Le détail de chaque code, son sens et la correction à faire sont dans [skill/fec-check/references/constats.md](skill/fec-check/references/constats.md).

**Ce que fec-check ne contrôle pas** : la justesse du résultat, la TVA, les amortissements, la déductibilité des charges, le fond des opérations. C'est le travail de la révision des comptes.

## Et Test Compta Demat ?

La DGFiP propose gratuitement [Test Compta Demat](https://www.economie.gouv.fr/dgfip/outil-test-des-fichiers-des-ecritures-comptables-fec), l'outil officiel. D'après ses présentations publiques, il contrôle surtout la forme du fichier : structure, formats, équilibre débit et crédit. Faites les deux : Test Compta Demat reste la référence officielle de format, et fec-check ajoute des contrôles comptables (caisse, banque, comptes selon la forme juridique, validation, à-nouveaux) et l'explication de chaque anomalie.

## Utiliser fec-check dans Claude (sans rien installer)

1. Téléchargez `fec-check-skill.zip` depuis la page [Releases](https://github.com/WinCorp-fr/fec-check/releases).
2. Dans les paramètres de Claude, rubrique des Skills, ajoutez l'archive sans la décompresser.
3. Déposez votre FEC dans une conversation et demandez « vérifie ce FEC ».

Pas à pas illustré : [GUIDE.md](GUIDE.md).

## En ligne de commande

Python 3.10 ou plus récent.

```bash
pip install "git+https://github.com/WinCorp-fr/fec-check@v1.0.0"
fec-check FEC_2025.txt
fec-check FEC_2025.txt --format json --profil profil.json
```

Le profil, facultatif, active les contrôles qui dépendent du dossier (dates d'exercice, forme juridique) :

```json
{"forme_juridique": "SARL", "date_debut_exercice": "2025-01-01T00:00:00",
 "date_fin_exercice": "2025-12-31T00:00:00", "exercice_clos": true}
```

Codes retour : `0` aucun bloquant, `1` au moins un bloquant, `2` fichier absent ou profil invalide.

## Depuis Python

```python
from pathlib import Path
from fec_check import verifier_fec

rapport = verifier_fec(Path("FEC_2025.txt"))
print(rapport.verdict, rapport.nb_bloquants)
for constat in rapport.constats:
    print(constat.code, constat.gravite, constat.message, constat.occurrences[:5])
```

Pour un agent ou une intégration, voir [AGENTS.md](AGENTS.md).

## Confidentialité

- Aucun appel réseau, aucune mesure d'audience : le fichier est lu en local et rien n'est envoyé nulle part.
- Le moteur est déterministe : deux exécutions sur le même fichier donnent exactement le même résultat.
- Les fichiers de test de ce dépôt sont entièrement fictifs, générés par [scripts/generer_fec_fictifs.py](scripts/generer_fec_fictifs.py).

## Limites

fec-check est un outil d'aide à la revue, fourni sans garantie (voir [LICENSE](LICENSE)). « Aucune anomalie bloquante détectée » ne veut pas dire « FEC conforme » : il ne remplace pas l'examen d'un professionnel du chiffre.

## Contribuer

Les signalements sont bienvenus dans les [issues](https://github.com/WinCorp-fr/fec-check/issues), sans jamais joindre de FEC réel : décrivez le cas ou reproduisez-le avec des données inventées.

Les fichiers `src/fec_check/{fec,pcg,controles,pydantic_types}.py` et `tests/moteur/` sont générés depuis le moteur interne de WinCorp et ne se modifient pas à la main. Une correction proposée sur ces fichiers est reportée dans le moteur puis réexportée.

```bash
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check . && mypy src tests scripts
```

## Qui sommes-nous

fec-check est publié par [WinCorp](https://wincorp.fr), éditeur d'outils métier pour les cabinets comptables et les TPE : révision des comptes, fiscalité, juridique, paie, pilotage. Vous voulez aller plus loin que le contrôle de format ? Écrivez-nous depuis [wincorp.fr](https://wincorp.fr).
