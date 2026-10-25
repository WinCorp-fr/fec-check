"""
Construit l'archive de la skill Claude : dist/fec-check-skill.zip.

L'archive contient le dossier `fec-check/` (SKILL.md, references/) et une
copie du paquet `fec_check/`, pour que Claude exécute le moteur sans rien
installer d'autre que pydantic. Archive déterministe : dates figées, ordre
trié, deux constructions donnent le même fichier octet pour octet.

Usage : python scripts/construire_skill.py [fichier_zip]
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DATE_FIGEE = (2026, 1, 1, 0, 0, 0)


def fichiers_a_inclure(racine: Path = RACINE) -> list[tuple[Path, str]]:
    """(chemin source, nom dans l'archive), triés par nom dans l'archive."""
    elements: list[tuple[Path, str]] = []
    skill = racine / "skill" / "fec-check"
    for chemin in skill.rglob("*"):
        if chemin.is_file():
            elements.append((chemin, f"fec-check/{chemin.relative_to(skill).as_posix()}"))
    paquet = racine / "src" / "fec_check"
    for chemin in paquet.glob("*.py"):
        elements.append((chemin, f"fec-check/fec_check/{chemin.name}"))
    return sorted(elements, key=lambda element: element[1])


def construire(cible: Path, racine: Path = RACINE) -> Path:
    cible.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(cible, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for chemin, nom in fichiers_a_inclure(racine):
            info = zipfile.ZipInfo(nom, date_time=DATE_FIGEE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, chemin.read_bytes())
    return cible


if __name__ == "__main__":
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "dist" / "fec-check-skill.zip"
    print(construire(sortie))
