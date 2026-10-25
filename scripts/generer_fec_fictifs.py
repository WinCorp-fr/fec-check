"""
Génère les FEC de démonstration et de test, 100 % fictifs.

Sociétés, SIREN, libellés et montants sont inventés. Aucun fichier réel,
même anonymisé, n'entre dans ce dépôt. Sortie déterministe : relancer le
script redonne des fichiers identiques octet pour octet.

Usage : python scripts/generer_fec_fictifs.py [dossier]  (défaut : tests/fixtures)
"""

from __future__ import annotations

import sys
from pathlib import Path

ENTETE = [
    "JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum",
    "CompteLib", "CompAuxNum", "CompAuxLib", "PieceRef", "PieceDate",
    "EcritureLib", "Debit", "Credit", "EcritureLet", "DateLet", "ValidDate",
    "Montantdevise", "Idevise",
]  # fmt: skip


def ligne(
    journal: str, journal_lib: str, num: str, date: str, compte: str, compte_lib: str,
    debit: str, credit: str, piece: str = "", lib: str = "", aux: str = "",
    aux_lib: str = "", valid: str | None = None,
) -> list[str]:  # fmt: skip
    return [
        journal, journal_lib, num, date, compte, compte_lib, aux, aux_lib,
        piece or f"P{num}", date, lib or compte_lib, debit, credit, "", "",
        date if valid is None else valid, "", "",
    ]  # fmt: skip


def _ecrire(
    chemin: Path, lignes: list[list[str]], sep: str = "|", encodage: str = "utf-8",
    entete: list[str] | None = None,
) -> None:  # fmt: skip
    contenu = "\r\n".join(sep.join(champs) for champs in [entete or ENTETE, *lignes]) + "\r\n"
    chemin.write_bytes(contenu.encode(encodage))


def _exercice_sain() -> list[list[str]]:
    """Exercice 2025 équilibré d'une SARL fictive « Atelier Fictif »."""
    return [
        ligne("AN", "A nouveaux", "1", "20250101", "10100000", "Capital", "0", "10000,00"),
        ligne("AN", "A nouveaux", "1", "20250101", "51200000", "Banque Fictive", "10000,00", "0"),
        ligne(
            "VT",
            "Ventes",
            "1",
            "20250115",
            "41100000",
            "Clients",
            "1200,00",
            "0",
            aux="CLI001",
            aux_lib="Client Imaginaire",
        ),
        ligne("VT", "Ventes", "1", "20250115", "70600000", "Prestations", "0", "1000,00"),
        ligne("VT", "Ventes", "1", "20250115", "44571000", "TVA collectée", "0", "200,00"),
        ligne("AC", "Achats", "1", "20250120", "60640000", "Fournitures", "300,00", "0"),
        ligne("AC", "Achats", "1", "20250120", "44566000", "TVA déductible", "60,00", "0"),
        ligne(
            "AC",
            "Achats",
            "1",
            "20250120",
            "40100000",
            "Fournisseurs",
            "0",
            "360,00",
            aux="FRN001",
            aux_lib="Fournisseur Imaginaire",
        ),
        ligne("BQ", "Banque", "1", "20250210", "51200000", "Banque Fictive", "1200,00", "0"),
        ligne(
            "BQ",
            "Banque",
            "1",
            "20250210",
            "41100000",
            "Clients",
            "0",
            "1200,00",
            aux="CLI001",
            aux_lib="Client Imaginaire",
        ),
        ligne("CA", "Caisse", "1", "20250301", "53000000", "Caisse", "100,00", "0"),
        ligne("CA", "Caisse", "1", "20250301", "51200000", "Banque Fictive", "0", "100,00"),
        ligne("CA", "Caisse", "2", "20250305", "62510000", "Déplacements", "40,00", "0"),
        ligne("CA", "Caisse", "2", "20250305", "53000000", "Caisse", "0", "40,00"),
    ]


def generer(dossier: Path) -> list[Path]:
    dossier.mkdir(parents=True, exist_ok=True)
    fichiers: dict[str, tuple[list[list[str]], dict[str, object]]] = {}

    fichiers["01_conforme.txt"] = (_exercice_sain(), {})

    desequilibre = _exercice_sain()
    desequilibre[3] = ligne("VT", "Ventes", "1", "20250115", "70600000", "Prestations",
                            "0", "1000,50")  # fmt: skip
    fichiers["02_desequilibre.txt"] = (desequilibre, {})

    caisse = _exercice_sain()
    # Sortie de caisse datée du 28/02, avant le premier apport du 01/03.
    caisse.append(ligne("CA", "Caisse", "3", "20250228", "53000000", "Caisse", "0", "80,00"))
    caisse.append(ligne("CA", "Caisse", "3", "20250228", "60640000", "Fournitures",
                        "80,00", "0"))  # fmt: skip
    fichiers["03_caisse_creditrice.txt"] = (caisse, {})

    format_casse = _exercice_sain()
    format_casse[5] = ligne("AC", "Achats", "1", "20251340", "60640000", "Fournitures",
                            "300,00", "0")  # fmt: skip
    format_casse[6] = ligne("AC", "Achats", "1", "20250120", "44566000", "TVA deductible",
                            "soixante", "0")  # fmt: skip
    fichiers["04_format_casse.txt"] = (format_casse, {})

    fichiers["05_export_tabule_iso.txt"] = (
        _exercice_sain(),
        {"sep": "\t", "encodage": "iso-8859-15",
         "entete": [("CompteAux" if c == "CompAuxNum" else c) for c in ENTETE]},
    )  # fmt: skip

    non_valide = _exercice_sain()
    non_valide.append(ligne("OD", "Operations diverses", "1", "20251231", "79100000",
                            "Transfert de charges", "0", "50,00", valid=""))  # fmt: skip
    non_valide.append(ligne("OD", "Operations diverses", "1", "20251231", "62510000",
                            "Deplacements", "50,00", "0", valid=""))  # fmt: skip
    fichiers["06_ecritures_non_validees.txt"] = (non_valide, {})

    ecrits: list[Path] = []
    for nom, (lignes, options) in fichiers.items():
        chemin = dossier / nom
        _ecrire(chemin, lignes, **options)  # type: ignore[arg-type]
        ecrits.append(chemin)
    return ecrits


if __name__ == "__main__":
    cible = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures")
    for chemin in generer(cible):
        print(chemin)
