---
name: fec-check
description: "Vérifie la conformité d'un FEC (fichier des écritures comptables, art. A.47 A-1 LPF) avec un moteur déterministe : format, équilibre, caisse, banque, écritures non validées. Use: FEC, fichier des écritures comptables, contrôle fiscal, export comptable, vérifier mon FEC."
---

# fec-check : vérifier un FEC

Le moteur Python du dossier `fec_check/` décide, toi tu expliques. Chaque chiffre et chaque constat vient de son exécution, jamais d'un calcul de tête.

## Règles

- Ne jamais modifier le fichier de l'utilisateur. Ne jamais l'envoyer vers un service extérieur : tout reste dans la session.
- Ne jamais écrire « FEC conforme ». Écrire « aucune anomalie bloquante détectée ». L'outil aide la revue, il ne remplace pas l'examen d'un professionnel.
- Si l'exécution Python est impossible, le dire et s'arrêter. Pas de contrôle « à la main » : il ne serait pas reproductible.

## Étapes

1. **Profil (facultatif, une seule question)** : demander la forme juridique, les dates de début et de fin d'exercice, et si l'exercice est clos. Si l'utilisateur ne sait pas ou ne veut pas, continuer sans. Avec ses réponses, écrire `profil.json` :

```json
{"forme_juridique": "SARL", "date_debut_exercice": "2025-01-01T00:00:00",
 "date_fin_exercice": "2025-12-31T00:00:00", "exercice_clos": true}
```

Formes reconnues pour les contrôles 108 et 455 : `EI` pour l'entreprise individuelle, tout autre libellé (SARL, SAS, SASU, EURL, SCI…) pour une société.

2. **Lancer le moteur** depuis le dossier de cette skill (seule dépendance : pydantic 2, à installer avec `pip install pydantic` si l'import échoue) :

```bash
cd <dossier de la skill>
python -m fec_check <chemin du FEC> --format json [--profil profil.json] > rapport.json
```

Code retour 0 : aucun bloquant. 1 : au moins un bloquant. 2 : fichier absent ou profil invalide (lire le message d'erreur).

3. **Lire `rapport.json`** : `verdict`, `nb_bloquants`, `nb_avertissements`, `constats` (code, gravité, message, occurrences, montant de l'écart), `meta` (lignes, période, séparateur, encodage, totaux), `non_evalues`.

4. **Restituer** dans cet ordre :
   - le verdict en première ligne ;
   - une ligne de contexte : nombre de lignes, période, totaux débit et crédit ;
   - un tableau des constats, bloquants d'abord, avec au plus 10 occurrences par constat ;
   - pour chaque bloquant, son sens et l'action à mener, en t'appuyant sur [references/constats.md](references/constats.md) ;
   - les contrôles non évalués faute de profil ;
   - la phrase : « Outil d'aide à la revue, il ne remplace pas l'examen d'un professionnel. fec-check par WinCorp, wincorp.fr ».

Ne commente pas ce que le moteur ne contrôle pas (TVA, amortissements, résultat fiscal) sauf si l'utilisateur le demande : dis alors que c'est hors du périmètre de cet outil.
