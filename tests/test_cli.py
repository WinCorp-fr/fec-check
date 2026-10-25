"""Ligne de commande : formats de sortie, profil, codes retour."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from fec_check.cli import main


def test_code_retour_0_sans_bloquant(fixtures: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(fixtures / "01_conforme.txt")]) == 0
    assert "aucune anomalie bloquante" in capsys.readouterr().out


def test_code_retour_1_avec_bloquant(fixtures: Path) -> None:
    assert main([str(fixtures / "02_desequilibre.txt")]) == 1


def test_sortie_json(fixtures: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main([str(fixtures / "03_caisse_creditrice.txt"), "--format", "json"])
    donnees = json.loads(capsys.readouterr().out)
    assert donnees["verdict"] == "BLOQUANTS_DETECTES"
    assert donnees["fichier"] == "03_caisse_creditrice.txt"
    assert any(c["code"] == "C9" for c in donnees["constats"])


def test_profil_active_les_controles(
    fixtures: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    profil = tmp_path / "profil.json"
    profil.write_text(
        json.dumps(
            {
                "forme_juridique": "SARL",
                "date_debut_exercice": "2025-01-01T00:00:00",
                "date_fin_exercice": "2025-12-31T00:00:00",
                "exercice_clos": True,
            }
        ),
        encoding="utf-8",
    )
    main([str(fixtures / "01_conforme.txt"), "--profil", str(profil), "--format", "json"])
    donnees = json.loads(capsys.readouterr().out)
    assert donnees["profil_fourni"] is True
    assert donnees["non_evalues"] == []


def test_fichier_absent_code_2(tmp_path: Path) -> None:
    assert main([str(tmp_path / "absent.txt")]) == 2


@pytest.mark.parametrize("contenu", ["pas du json", '{"champ_inconnu": 1}'])
def test_profil_invalide_code_2(fixtures: Path, tmp_path: Path, contenu: str) -> None:
    profil = tmp_path / "profil.json"
    profil.write_text(contenu, encoding="utf-8")
    assert main([str(fixtures / "01_conforme.txt"), "--profil", str(profil)]) == 2


def test_python_m_fec_check(fixtures: Path) -> None:
    resultat = subprocess.run(
        [sys.executable, "-m", "fec_check", str(fixtures / "02_desequilibre.txt")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert resultat.returncode == 1
    assert "C1" in resultat.stdout
