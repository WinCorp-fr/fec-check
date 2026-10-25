"""L'archive de la skill est complète, déterministe et exécutable telle quelle."""

import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

_CHEMIN = Path(__file__).resolve().parent.parent / "scripts" / "construire_skill.py"
_SPEC = importlib.util.spec_from_file_location("construire_skill", _CHEMIN)
assert _SPEC is not None and _SPEC.loader is not None
construire_skill = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(construire_skill)


def test_archive_complete(tmp_path: Path) -> None:
    noms = zipfile.ZipFile(construire_skill.construire(tmp_path / "s.zip")).namelist()
    assert "fec-check/SKILL.md" in noms
    assert "fec-check/references/constats.md" in noms
    for module in ["__init__", "__main__", "cli", "controles", "fec", "pcg", "rapport"]:
        assert f"fec-check/fec_check/{module}.py" in noms
    assert not any("__pycache__" in nom for nom in noms)


def test_archive_deterministe(tmp_path: Path) -> None:
    premiere = construire_skill.construire(tmp_path / "a.zip").read_bytes()
    assert premiere == construire_skill.construire(tmp_path / "b.zip").read_bytes()


def test_skill_md_a_un_entete_valide() -> None:
    texte = (_CHEMIN.parent.parent / "skill" / "fec-check" / "SKILL.md").read_text("utf-8")
    entete = texte.split("---")[1]
    assert "name: fec-check" in entete
    assert "description:" in entete


def test_moteur_lance_depuis_l_archive_extraite(tmp_path: Path, fixtures: Path) -> None:
    with zipfile.ZipFile(construire_skill.construire(tmp_path / "s.zip")) as archive:
        archive.extractall(tmp_path / "x")
    dossier = tmp_path / "x" / "fec-check"
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    # Le dossier courant passe devant le paquet installé : c'est la copie de l'archive qui tourne.
    origine = subprocess.run(
        [sys.executable, "-c", "import fec_check; print(fec_check.__file__)"],
        capture_output=True, text=True, encoding="utf-8", cwd=dossier, env=env, check=True,
    )  # fmt: skip
    assert Path(origine.stdout.strip()).resolve().is_relative_to(dossier.resolve())
    resultat = subprocess.run(
        [sys.executable, "-m", "fec_check", str(fixtures / "02_desequilibre.txt"),
         "--format", "json"],
        capture_output=True, text=True, encoding="utf-8", cwd=dossier, env=env, check=False,
    )  # fmt: skip
    assert resultat.returncode == 1, resultat.stderr
    assert json.loads(resultat.stdout)["verdict"] == "BLOQUANTS_DETECTES"
