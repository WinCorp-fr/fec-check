# Vérifier un FEC avec Claude, en trois étapes

Pour qui : un collaborateur de cabinet ou un dirigeant, sans connaissance technique. Durée : cinq minutes la première fois, une minute ensuite.

## 1. Récupérer l'outil (une seule fois)

Ouvrez la page [Releases](https://github.com/WinCorp-fr/fec-check/releases) et téléchargez le fichier `fec-check-skill.zip`. Ne le décompressez pas.

## 2. L'ajouter à Claude (une seule fois)

Dans Claude, ouvrez les paramètres, rubrique des Skills, et ajoutez le fichier `fec-check-skill.zip`. L'outil apparaît sous le nom « fec-check ». L'exécution de code doit être activée dans les paramètres : c'est elle qui fait tourner les contrôles.

## 3. Vérifier un FEC

1. Exportez le FEC depuis votre logiciel comptable (menu export, « Fichier des écritures comptables »).
2. Ouvrez une nouvelle conversation, déposez le fichier et écrivez : « vérifie ce FEC ».
3. Claude vous demande la forme juridique et les dates d'exercice. Répondez si vous les connaissez : trois contrôles de plus seront faits. Sinon, dites « continue ».

Vous recevez :

- le verdict en première ligne ;
- la liste des anomalies, les plus graves d'abord, avec les lignes concernées ;
- pour chaque anomalie bloquante, ce qu'elle veut dire et comment la corriger.

## Lire le résultat

| Niveau | Signification | Action |
| --- | --- | --- |
| Bloquant | Le fichier serait rejeté ou contesté | Corriger dans le logiciel, puis réexporter |
| Avertissement | Le fichier passe, mais la question serait posée | Justifier ou corriger |
| Information | Une tolérance a été appliquée | Rien à faire |

## À savoir

- Le fichier n'est envoyé à aucun service extérieur par l'outil : les contrôles tournent dans votre session Claude.
- « Aucune anomalie bloquante détectée » ne veut pas dire « conforme » : l'outil aide la revue, il ne remplace pas l'examen d'un professionnel.
- Une question, un cas non reconnu ? Écrivez-nous depuis [wincorp.fr](https://wincorp.fr), sans joindre de FEC réel.
