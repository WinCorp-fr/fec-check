"""
Ligne de commande `fec-check`.

    fec-check FEC.txt                       rapport lisible
    fec-check FEC.txt --format json         rapport JSON (pour un agent)
    fec-check FEC.txt --profil profil.json  active C6, ECF-1, ECF-2

Codes retour : 0 = aucun bloquant, 1 = au moins un bloquant,
2 = erreur d'usage (fichier absent, profil invalide).
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from fec_check import __version__
from fec_check.controles import ProfilDossier
from fec_check.rapport import formater_texte, verifier_fec


def _lire_profil(chemin: Path) -> ProfilDossier:
    return ProfilDossier.model_validate(json.loads(chemin.read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="fec-check",
        description="Vérifie la conformité d'un Fichier des Écritures Comptables (FEC).",
    )
    parser.add_argument("fichier", type=Path, help="Fichier FEC à vérifier")
    parser.add_argument("--format", choices=["texte", "json"], default="texte")
    parser.add_argument("--profil", type=Path, help="Profil dossier JSON (facultatif)")
    parser.add_argument("--version", action="version", version=f"fec-check {__version__}")
    args = parser.parse_args(argv)

    if not args.fichier.is_file():
        print(f"Fichier introuvable : {args.fichier}", file=sys.stderr)
        return 2
    profil = None
    if args.profil is not None:
        try:
            profil = _lire_profil(args.profil)
        except (OSError, ValueError, ValidationError) as erreur:
            print(f"Profil invalide ({args.profil}) : {erreur}", file=sys.stderr)
            return 2

    rapport = verifier_fec(args.fichier, profil)
    if args.format == "json":
        print(rapport.model_dump_json(indent=2))
    else:
        print(formater_texte(rapport), end="")
    return 1 if rapport.nb_bloquants else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
