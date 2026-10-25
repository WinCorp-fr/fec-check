"""Les FEC fictifs sont reproductibles et ne ressemblent à aucun dossier réel."""

import re
from pathlib import Path

import pytest
from scripts_import import generateur


def test_regeneration_identique_octet_pour_octet(tmp_path: Path, fixtures: Path) -> None:
    for chemin in generateur.generer(tmp_path):
        assert chemin.read_bytes() == (fixtures / chemin.name).read_bytes(), chemin.name


@pytest.mark.parametrize(
    "nom", sorted(p.name for p in Path(__file__).parent.glob("fixtures/*.txt"))
)
def test_aucun_identifiant_reel(nom: str, fixtures: Path) -> None:
    contenu = (fixtures / nom).read_bytes().decode("utf-8", errors="replace")
    assert not re.search(r"\b\d{9}\b|\b\d{14}\b", contenu), "SIREN/SIRET interdit"
    assert not re.search(r"\bFR\d{2}[0-9A-Z ]{10,}", contenu), "IBAN interdit"
    assert "@" not in contenu, "adresse e-mail interdite"
