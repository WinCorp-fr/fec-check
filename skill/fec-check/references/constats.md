# Les constats de fec-check, en clair

Chaque constat porte un code stable, une gravité et, si besoin, la liste des lignes ou écritures concernées.

- **Bloquant** : le fichier serait rejeté ou contesté lors d'un contrôle. À corriger avant tout envoi.
- **Avertissement** : le fichier passe, mais un vérificateur poserait la question. À justifier ou à corriger.
- **Information** : une tolérance a été appliquée ou un contrôle n'a pas pu être évalué. Rien à faire, sauf le noter.

Les occurrences prennent la forme `L12` (ligne 12 du fichier), `VT/45` (journal VT, écriture 45) ou un numéro de compte.

## Format du fichier (T1 à T11)

| Code | Gravité | Ce que ça veut dire | Que faire |
| --- | --- | --- | --- |
| T1 | bloquant | Fichier illisible (absent, vide, encodage inconnu). | Refaire l'export depuis le logiciel comptable. |
| T1 | info | Fichier lu en ISO-8859-15 au lieu d'UTF-8. L'arrêté admet les deux. | Rien. |
| T2 | bloquant | Des lignes n'ont pas le séparateur détecté sur l'en-tête (tabulation ou pipe). | Vérifier un libellé contenant le séparateur, refaire l'export. |
| T3 | bloquant | Une ligne n'a pas les 18 colonnes obligatoires. | Contrôler la ligne citée, souvent un retour à la ligne dans un libellé. |
| T4 | info ou avertissement | En-tête avec des noms de colonnes variants (toléré) ou inconnus (lus par position). | Vérifier que l'ordre des colonnes est bien l'ordre officiel. |
| T5 | bloquant | Date impossible ou au mauvais format (AAAAMMJJ attendu). | Corriger la date dans le logiciel puis réexporter. |
| T6 | bloquant | Montant illisible. | Corriger le montant à la source. |
| T7 | avertissement | Numéros de compte de moins de 6 chiffres. | Vérifier le paramétrage du plan comptable. |
| T8 | info | Fins de ligne LF au lieu de CRLF. Toléré. | Rien. |
| T9 | info | Lignes à débit et crédit nuls, conservées. | Rien, sauf si elles sont nombreuses. |
| T10 | info | Montants négatifs remis dans la colonne opposée. Les valeurs signées sont licites. | Rien. |
| T11 | info | Lignes sans référence ou sans date de pièce. | Compléter si possible : la pièce justifie l'écriture. |

## Contrôles comptables (C1 à C10)

| Code | Gravité | Ce que ça veut dire | Que faire |
| --- | --- | --- | --- |
| C1 | bloquant | Total des débits différent du total des crédits (au-delà de 0,01 €). | Chercher l'écriture déséquilibrée (voir C2). |
| C2 | bloquant ou avertissement | Une écriture ne s'équilibre pas. Jusqu'à 0,02 € : arrondi entre logiciels. | Corriger l'écriture citée. |
| C3 | avertissement | Une même ligne porte un débit et un crédit. | Scinder en deux lignes. |
| C4 | avertissement | Comptes 79 (transferts de charges), supprimés par le règlement ANC 2022-06. Le FEC reste valable. | Reclasser selon la nature (74, 75, 758, 76 ou 77). |
| C5 | avertissement | La numérotation des écritures revient en arrière dans un journal. | Vérifier qu'aucune écriture n'a été insérée après coup. |
| C6 | avertissement | Écritures datées hors de l'exercice (à-nouveaux exclus). Exige le profil. | Vérifier les dates ou les bornes d'exercice. |
| C7 | info | Pièce datée après l'écriture. | Vérifier la date de pièce. |
| C8 | avertissement | Comptes fournisseurs (401) ou clients (411) sans compte auxiliaire. | Rattacher chaque mouvement à son tiers. |
| C9 | bloquant | La caisse devient négative à une date donnée (calcul jour après jour). Une caisse ne peut pas avoir moins que zéro. | Retrouver l'apport ou la recette oubliée avant cette date. |
| C10 | avertissement | Compte banque créditeur (découvert) plus de 30 jours d'affilée. | Vérifier le rapprochement bancaire. |

## Contrôles liés à la forme et à la clôture (ECF)

| Code | Gravité | Ce que ça veut dire | Que faire |
| --- | --- | --- | --- |
| ECF-1 | bloquant | Compte de l'exploitant (108) dans une société. Exige la forme juridique. | Utiliser le compte courant d'associé (455). |
| ECF-2 | bloquant | Compte courant d'associé (455) dans une entreprise individuelle. Exige la forme juridique. | Utiliser le compte de l'exploitant (108). |
| ECF-3 | bloquant ou avertissement | Écritures sans date de validation. Bloquant si l'exercice est déclaré clos. | Valider les écritures dans le logiciel avant l'export. |
| ECF-4 | bloquant | Les à-nouveaux ne s'équilibrent pas. | Reprendre le bilan d'ouverture. |

## Ce que fec-check ne contrôle pas

La justesse du résultat, la TVA, les amortissements, la déductibilité des charges et le fond des opérations. Ces analyses relèvent de la révision des comptes par un professionnel.
