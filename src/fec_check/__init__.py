"""
fec-check : validateur gratuit du Fichier des Écritures Comptables (FEC).

API Python :

    from pathlib import Path
    from fec_check import verifier_fec

    rapport = verifier_fec(Path("FEC.txt"))
    print(rapport.verdict, rapport.nb_bloquants)

Aucun appel réseau : le fichier ne quitte jamais la machine.
"""

from fec_check.controles import Constat, ProfilDossier
from fec_check.rapport import RapportFEC, verifier_fec

__version__ = "1.0.0"

__all__ = ["Constat", "ProfilDossier", "RapportFEC", "verifier_fec", "__version__"]
