"""Verdicts attendus sur chacun des FEC fictifs, et rapport texte."""

from datetime import datetime
from pathlib import Path

import pytest

from fec_check import ProfilDossier, verifier_fec
from fec_check.rapport import formater_texte

PROFIL_SARL_2025 = ProfilDossier(
    forme_juridique="SARL",
    date_debut_exercice=datetime(2025, 1, 1),
    date_fin_exercice=datetime(2025, 12, 31),
    exercice_clos=True,
)


def codes(chemin: Path, profil: ProfilDossier | None = PROFIL_SARL_2025) -> dict[str, str]:
    return {c.code: c.gravite for c in verifier_fec(chemin, profil).constats}


def test_conforme_sans_aucun_constat(fixtures: Path) -> None:
    rapport = verifier_fec(fixtures / "01_conforme.txt", PROFIL_SARL_2025)
    assert rapport.verdict == "AUCUN_BLOQUANT"
    assert rapport.constats == []
    assert rapport.non_evalues == []


def test_desequilibre_global_et_par_ecriture(fixtures: Path) -> None:
    rapport = verifier_fec(fixtures / "02_desequilibre.txt", PROFIL_SARL_2025)
    assert rapport.verdict == "BLOQUANTS_DETECTES"
    assert codes(fixtures / "02_desequilibre.txt") == {"C1": "bloquant", "C2": "bloquant"}
    c2 = next(c for c in rapport.constats if c.code == "C2")
    assert c2.occurrences == ["VT/1"]
    assert str(c2.montant_ecart) == "0.50"


def test_caisse_creditrice(fixtures: Path) -> None:
    assert codes(fixtures / "03_caisse_creditrice.txt") == {"C9": "bloquant"}


def test_format_casse_date_et_montant(fixtures: Path) -> None:
    trouves = codes(fixtures / "04_format_casse.txt")
    assert trouves["T5"] == "bloquant"
    assert trouves["T6"] == "bloquant"


def test_export_tabule_iso_tolere(fixtures: Path) -> None:
    rapport = verifier_fec(fixtures / "05_export_tabule_iso.txt", PROFIL_SARL_2025)
    assert rapport.verdict == "AUCUN_BLOQUANT"
    assert rapport.meta.separateur_colonnes == "\t"
    assert rapport.meta.encodage == "iso-8859-15"
    assert codes(fixtures / "05_export_tabule_iso.txt") == {"T1": "info", "T4": "info"}


def test_ecritures_non_validees_et_compte_79(fixtures: Path) -> None:
    trouves = codes(fixtures / "06_ecritures_non_validees.txt")
    assert trouves == {"C4": "avertissement", "ECF-3": "bloquant"}


def test_sans_profil_liste_les_controles_non_evalues(fixtures: Path) -> None:
    rapport = verifier_fec(fixtures / "01_conforme.txt")
    assert rapport.profil_fourni is False
    assert [n.split(" :")[0] for n in rapport.non_evalues] == ["C6", "ECF-1", "ECF-2"]


def test_ecf3_avertissement_si_exercice_non_clos(fixtures: Path) -> None:
    profil = PROFIL_SARL_2025.model_copy(update={"exercice_clos": False})
    assert codes(fixtures / "06_ecritures_non_validees.txt", profil)["ECF-3"] == "avertissement"


def test_fichier_illisible_est_un_bloquant_pas_une_exception(tmp_path: Path) -> None:
    vide = tmp_path / "vide.txt"
    vide.write_bytes(b"")
    rapport = verifier_fec(vide)
    assert rapport.verdict == "BLOQUANTS_DETECTES"


def test_deterministe(fixtures: Path) -> None:
    chemin = fixtures / "04_format_casse.txt"
    premier = verifier_fec(chemin, PROFIL_SARL_2025).model_dump_json()
    assert premier == verifier_fec(chemin, PROFIL_SARL_2025).model_dump_json()


@pytest.mark.parametrize("nom", ["01_conforme.txt", "04_format_casse.txt"])
def test_rapport_texte(nom: str, fixtures: Path) -> None:
    texte = formater_texte(verifier_fec(fixtures / nom))
    assert texte.startswith(f"FEC : {nom}\nVerdict : ")
    assert "ne remplace pas l'examen" in texte
    assert "Non évalués sans profil" in texte


def test_rapport_texte_tronque_les_occurrences(fixtures: Path) -> None:
    rapport = verifier_fec(fixtures / "02_desequilibre.txt")
    c2 = next(c for c in rapport.constats if c.code == "C2")
    c2.occurrences = [f"VT/{i}" for i in range(15)]
    texte = formater_texte(rapport, max_occurrences=10)
    assert "et 5 autre(s)" in texte
