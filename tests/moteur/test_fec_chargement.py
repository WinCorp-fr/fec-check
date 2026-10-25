"""
Tests du chargement tolérant (variantes d'en-tête, encodages, séparateurs,
montants signés). Les codes Rx et ECx renvoient aux règles de la
spécification interne du moteur.
"""

# Fichier généré, ne pas modifier à la main.
# empreinte-source: 769bad5438227dd58259ff265e336b5d5482520c4ce521add01daa717409380d

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from fec_check.fec import (
    FEC_COLONNES,
    FEC_VARIANTES_ENTETE,
    ChargementFEC,
    charger_fec,
    lire_fec,
    valider_fec,
)

# En-tête v1 historique (noms NON réglementaires colonnes 7/8) — chemin variantes
ENTETE_V1 = (
    "JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|"
    "CompteAux|CompteAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|"
    "EcritureLet|DateLet|ValidDate|Montantdevise|Idevise"
)


def ligne_fec(
    journal: str = "VT",
    journal_lib: str = "Ventes",
    num: str = "1",
    date: str = "20250314",
    compte: str = "41110000",
    compte_lib: str = "Clients",
    debit: str = "0",
    credit: str = "0",
    piece_ref: str = "FAC001",
    piece_date: str = "20250314",
    valid_date: str = "20250314",
) -> str:
    """Construit une ligne FEC synthétique de 18 champs."""
    return (
        f"{journal}|{journal_lib}|{num}|{date}|{compte}|{compte_lib}|||"
        f"{piece_ref}|{piece_date}|Ecriture test|{debit}|{credit}|||{valid_date}||"
    )


def ecrire_fec(
    tmp_path: Path,
    lignes: list[str],
    entete: str | None = None,
    encodage: str = "utf-8",
    fin_ligne: str = "\r\n",
    nom: str = "fec.txt",
) -> Path:
    """Écrit un fichier FEC synthétique et retourne son chemin."""
    if entete is None:
        entete = "|".join(FEC_COLONNES)
    contenu = fin_ligne.join([entete, *lignes]) + fin_ligne
    chemin = tmp_path / nom
    chemin.write_bytes(contenu.encode(encodage))
    return chemin


class TestChargerFecNominal:
    """R12 — chargement tolérant, ordre du fichier, ligne_source."""

    def test_r12_ordre_fichier_et_ligne_source(self, tmp_path: Path) -> None:
        """R12 — écritures dans l'ordre du fichier, ligne_source renseigné (en-tête = ligne 1)."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec(num="1", compte="41110000", debit="120.00"),
                ligne_fec(num="1", compte="70600000", credit="120.00"),
            ],
        )
        chargement = charger_fec(fichier)

        assert isinstance(chargement, ChargementFEC)
        assert chargement.erreurs == []
        assert [e.ligne_source for e in chargement.ecritures] == [2, 3]
        assert [e.compte_num for e in chargement.ecritures] == ["41110000", "70600000"]

    def test_r12_ligne_rejetee_nen_bloque_pas_dautres(self, tmp_path: Path) -> None:
        """R12 / EC4 — la ligne fautive produit une erreur typée, les autres sont parsées."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec(num="1", debit="100.00"),
                "VT|Ventes|2",  # 3 champs seulement
                ligne_fec(num="3", credit="100.00"),
            ],
        )
        chargement = charger_fec(fichier)

        assert len(chargement.ecritures) == 2
        assert len(chargement.erreurs) == 1
        assert chargement.erreurs[0].code == "COLONNES"
        assert chargement.erreurs[0].ligne == 3

    def test_r9_lignes_vides_ignorees(self, tmp_path: Path) -> None:
        """R9 — ligne vide au milieu du corps : ignorée, hors nb_lignes."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec(num="1", debit="10.00"),
                "",
                ligne_fec(num="1", compte="70600000", credit="10.00"),
            ],
        )
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert len(chargement.ecritures) == 2
        assert chargement.meta.nb_lignes == 2
        # la numérotation physique saute la ligne vide
        assert [e.ligne_source for e in chargement.ecritures] == [2, 4]

    def test_r10_champs_optionnels_vides(self, tmp_path: Path) -> None:
        """R10 — CompAuxNum/CompAuxLib/EcritureLet/DateLet/Montantdevise/Idevise vides → None."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="10.00")])
        ecriture = charger_fec(fichier).ecritures[0]

        assert ecriture.compte_aux is None
        assert ecriture.compte_aux_lib is None
        assert ecriture.ecriture_let is None
        assert ecriture.date_let is None
        assert ecriture.montant_devise is None
        assert ecriture.devise_id is None

    def test_meta_statistiques(self, tmp_path: Path) -> None:
        """MetadonneesFEC — bornes de dates, totaux, nb_lignes."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec(num="1", date="20250110", debit="100.00"),
                ligne_fec(num="1", date="20250320", credit="100.00"),
            ],
        )
        meta = charger_fec(fichier).meta

        assert meta.date_min == datetime(2025, 1, 10)
        assert meta.date_max == datetime(2025, 3, 20)
        assert meta.nb_lignes == 2
        assert meta.total_debit == Decimal("100.00")
        assert meta.total_credit == Decimal("100.00")


class TestEncodage:
    """R3 — UTF-8 puis repli ISO-8859-15, BOM toléré."""

    def test_r3_ec9_repli_iso_8859_15(self, tmp_path: Path) -> None:
        """R3 / EC9 — fichier ISO-8859-15 avec accents et € → chargé, encodage tracé."""
        fichier = ecrire_fec(
            tmp_path,
            [ligne_fec(compte_lib="Clients €té", debit="100.00")],
            encodage="iso-8859-15",
        )
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.meta.encodage == "iso-8859-15"
        assert chargement.ecritures[0].compte_lib == "Clients €té"

    def test_r3_ec14_bom_utf8(self, tmp_path: Path) -> None:
        """R3 / EC14 — BOM UTF-8 consommé, en-tête reconnu."""
        fichier = ecrire_fec(
            tmp_path,
            [ligne_fec(debit="10.00")],
            encodage="utf-8-sig",
        )
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.meta.bom is True
        assert chargement.meta.encodage == "utf-8"

    def test_r3_ascii_pur_reste_utf8(self, tmp_path: Path) -> None:
        """R3 — un fichier ASCII pur est lu en UTF-8 (pas de repli)."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="10.00")])
        assert charger_fec(fichier).meta.encodage == "utf-8"


class TestEntete:
    """R4 — variantes connues, noms inconnus par position, en-tête inexploitable."""

    def test_r4_ec8_entete_v1_exactement_deux_variantes(self, tmp_path: Path) -> None:
        """R4 / EC8 — en-tête 100 % v1 → exactement 2 variantes (col 14 = nom officiel)."""
        fichier = ecrire_fec(
            tmp_path,
            [ligne_fec(debit="100.00")],
            entete=ENTETE_V1,
        )
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.meta.variantes_entete == {
            "CompteAux": "CompAuxNum",
            "CompteAuxLib": "CompAuxLib",
        }

    def test_r4_ec16_variante_ecrturelet(self, tmp_path: Path) -> None:
        """R4 / EC16 — l'orthographe tronquée EcrtureLet est une variante tolérée."""
        entete = "|".join(
            c if c != "EcritureLet" else "EcrtureLet" for c in FEC_COLONNES
        )
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="5.00")], entete=entete)
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.meta.variantes_entete == {"EcrtureLet": "EcritureLet"}

    def test_r4_nom_inconnu_traite_par_position(self, tmp_path: Path) -> None:
        """R4 — nom inconnu à une position officielle → accepté par position, tracé."""
        entete = "|".join(
            c if c != "PieceRef" else "RefPiece" for c in FEC_COLONNES
        )
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="5.00")], entete=entete)
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.meta.entete_inconnues == ["RefPiece"]
        assert chargement.ecritures[0].piece_ref == "FAC001"

    def test_r4_ec3_entete_inexploitable(self, tmp_path: Path) -> None:
        """R4 / EC3 — en-tête < 18 colonnes → erreur ENTETE, aucune écriture."""
        fichier = ecrire_fec(
            tmp_path, [ligne_fec()], entete="Colonne1|Colonne2|Colonne3"
        )
        chargement = charger_fec(fichier)

        assert chargement.ecritures == []
        assert chargement.erreurs[0].code == "ENTETE"
        assert chargement.erreurs[0].ligne == 1

    def test_r1_ec12_colonnes_surnumeraires(self, tmp_path: Path) -> None:
        """R1 / EC12 — 19e colonne en en-tête ET données → ignorée, tracée, zéro erreur."""
        entete = "|".join(FEC_COLONNES) + "|Etablissement"
        fichier = ecrire_fec(
            tmp_path,
            [ligne_fec(debit="10.00") + "|SIEGE"],
            entete=entete,
        )
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.meta.colonnes_surnumeraires == ["Etablissement"]
        assert len(chargement.ecritures) == 1

    def test_r1_ec12_ligne_plus_large_que_entete(self, tmp_path: Path) -> None:
        """R1 / EC12 — ligne à 19 champs avec en-tête à 18 → erreur COLONNES."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="10.00") + "|SIEGE"])
        chargement = charger_fec(fichier)

        assert chargement.ecritures == []
        assert chargement.erreurs[0].code == "COLONNES"

    def test_r2_ligne_sans_pipe(self, tmp_path: Path) -> None:
        """R2 — ligne de données sans aucun pipe → erreur SEPARATEUR."""
        fichier = ecrire_fec(tmp_path, ["ceci n'est pas une ligne FEC"])
        chargement = charger_fec(fichier)

        assert chargement.erreurs[0].code == "SEPARATEUR"


class TestMontants:
    """R6 (signés), R7 (0/0), R11 (normalisation par valeur)."""

    def test_r11_ec10_virgule_decimale(self, tmp_path: Path) -> None:
        """R11 / EC10 — montants à virgule → Decimal point, séparateur tracé."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec(num="1", debit="1234,56"),
                ligne_fec(num="1", credit="1234,56"),
            ],
        )
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.ecritures[0].debit == Decimal("1234.56")
        assert chargement.meta.separateur_decimal == ","

    def test_r11_ec11_espaces_milliers(self, tmp_path: Path) -> None:
        """R11 / EC11 — espaces de milliers (espace, insécable, fine) supprimés."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec(num="1", debit="1 234,56"),
                ligne_fec(num="2", debit="1 234,56"),
                ligne_fec(num="3", debit="1 234,56"),
            ],
        )
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert all(e.debit == Decimal("1234.56") for e in chargement.ecritures)

    def test_r11_point_reste_point(self, tmp_path: Path) -> None:
        """R11 — montants à point classiques inchangés, séparateur '.' par défaut."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="1234.56")])
        chargement = charger_fec(fichier)

        assert chargement.ecritures[0].debit == Decimal("1234.56")
        assert chargement.meta.separateur_decimal == "."

    def test_r11_ec20_point_et_virgule_ambigu(self, tmp_path: Path) -> None:
        """R11 / EC20 — valeur mêlant point ET virgule → erreur MONTANT."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="1.234,56")])
        chargement = charger_fec(fichier)

        assert chargement.ecritures == []
        assert chargement.erreurs[0].code == "MONTANT"

    def test_r11_ec6_montant_non_numerique(self, tmp_path: Path) -> None:
        """R11 / EC6 — montant 'abc' → erreur MONTANT typée."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="abc")])
        chargement = charger_fec(fichier)

        assert chargement.erreurs[0].code == "MONTANT"

    def test_r6_ec17_montant_negatif_normalise(self, tmp_path: Path) -> None:
        """R6 / EC17 — Debit négatif → basculé en Credit positif, compté, zéro erreur."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="-100,00")])
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        ecriture = chargement.ecritures[0]
        assert ecriture.debit == Decimal("0")
        assert ecriture.credit == Decimal("100.00")
        assert chargement.meta.nb_montants_negatifs == 1

    def test_r6_credit_negatif_normalise(self, tmp_path: Path) -> None:
        """R6 — Credit négatif → basculé en Debit positif."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(credit="-50.00")])
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.ecritures[0].debit == Decimal("50.00")
        assert chargement.ecritures[0].credit == Decimal("0")

    def test_r7_ec18_ligne_zero_conservee(self, tmp_path: Path) -> None:
        """R7 / EC18 — Debit et Credit vides → ligne conservée à 0/0, comptée."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="", credit="")])
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.ecritures[0].debit == Decimal("0")
        assert chargement.ecritures[0].credit == Decimal("0")
        assert chargement.meta.nb_lignes_zero == 1


class TestDatesEtPieces:
    """R5 — dates YYYYMMDD, ValidDate/PieceDate/PieceRef vides tolérés."""

    def test_r5_ec5_date_invalide(self, tmp_path: Path) -> None:
        """R5 / EC5 — date calendaire impossible → erreur DATE avec colonne."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(date="20251332", debit="1.00")])
        chargement = charger_fec(fichier)

        assert chargement.erreurs[0].code == "DATE"
        assert chargement.erreurs[0].colonne == "EcritureDate"

    def test_r5_ecriture_date_vide_rejetee(self, tmp_path: Path) -> None:
        """R5 — EcritureDate vide → erreur DATE (reste obligatoire)."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(date="", debit="1.00")])
        chargement = charger_fec(fichier)

        assert chargement.erreurs[0].code == "DATE"

    def test_r5_ec13_valid_date_vide(self, tmp_path: Path) -> None:
        """R5 / EC13 — ValidDate vide → écriture parsée avec valid_date=None."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(valid_date="", debit="1.00")])
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.ecritures[0].valid_date is None

    def test_r5_ec19_piece_vides_tolerees(self, tmp_path: Path) -> None:
        """R5 / EC19 — PieceRef et PieceDate vides → tolérés, comptés."""
        fichier = ecrire_fec(
            tmp_path, [ligne_fec(piece_ref="", piece_date="", debit="1.00")]
        )
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.ecritures[0].piece_ref is None
        assert chargement.ecritures[0].piece_date is None
        assert chargement.meta.nb_pieces_incompletes == 1


class TestMetaDivers:
    """R13 (comptes_digits), R14 (fins de ligne), EC7."""

    def test_r13_ec15_comptes_digits_dominant(self, tmp_path: Path) -> None:
        """R13 / EC15 — longueur dominante 8 malgré quelques comptes à 6."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec(num="1", compte="41110000", debit="10.00"),
                ligne_fec(num="2", compte="70600000", credit="10.00"),
                ligne_fec(num="3", compte="512000", debit="5.00"),
            ],
        )
        assert charger_fec(fichier).meta.comptes_digits == 8

    def test_r13_egalite_prend_la_plus_grande(self, tmp_path: Path) -> None:
        """R13 — égalité 6/8 → la plus grande longueur gagne."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec(num="1", compte="512000", debit="5.00"),
                ligne_fec(num="2", compte="41110000", credit="5.00"),
            ],
        )
        assert charger_fec(fichier).meta.comptes_digits == 8

    def test_r13_ec7_aucune_ecriture(self, tmp_path: Path) -> None:
        """R13 / EC7 — en-tête seul → 0 écriture, comptes_digits=None, valide."""
        fichier = ecrire_fec(tmp_path, [])
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.ecritures == []
        assert chargement.meta.comptes_digits is None

    def test_r14_fin_ligne_lf(self, tmp_path: Path) -> None:
        """R14 — LF seul toléré et tracé, jamais une erreur."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="1.00")], fin_ligne="\n")
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.meta.fin_ligne == "LF"

    def test_r14_fin_ligne_crlf(self, tmp_path: Path) -> None:
        """R14 — CRLF détecté."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="1.00")])
        assert charger_fec(fichier).meta.fin_ligne == "CRLF"


class TestSeparateurTab:
    """R2 v2.2 — séparateur tabulation officiel (art. A.47 A-1 VIII, exports Fulll)."""

    def test_r2_ec21_fec_tabule(self, tmp_path: Path) -> None:
        """R2 / EC21 — FEC entièrement tabulé → chargé, séparateur tracé, zéro erreur."""
        entete = "\t".join(FEC_COLONNES)
        ligne = ligne_fec(debit="1234,56").replace("|", "\t")
        fichier = tmp_path / "fec_tab.txt"
        fichier.write_bytes((entete + "\r\n" + ligne + "\r\n").encode("utf-8"))
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.meta.separateur_colonnes == "\t"
        assert chargement.ecritures[0].debit == Decimal("1234.56")
        assert chargement.ecritures[0].compte_num == "41110000"

    def test_r2_ec21_pipe_dans_libelle_tabule(self, tmp_path: Path) -> None:
        """R2 / EC21 — un pipe DANS un libellé d'un fichier tabulé ne casse rien."""
        entete = "\t".join(FEC_COLONNES)
        ligne = (
            "VT\tVentes\t1\t20250314\t41110000\tClients A|B\t\t\tFAC\t20250314\t"
            "Livraison A|B\t100.00\t0\t\t\t20250314\t\t"
        )
        fichier = tmp_path / "fec_tab_pipe.txt"
        fichier.write_bytes((entete + "\r\n" + ligne + "\r\n").encode("utf-8"))
        chargement = charger_fec(fichier)

        assert chargement.erreurs == []
        assert chargement.ecritures[0].compte_lib == "Clients A|B"

    def test_r2_pipe_reste_le_defaut(self, tmp_path: Path) -> None:
        """R2 — fichier pipe classique : séparateur '|' tracé (défaut à égalité)."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="10.00")])
        assert charger_fec(fichier).meta.separateur_colonnes == "|"


class TestRetroCompat:
    """R15 — valider_fec / lire_fec inchangés sur les fichiers valides v1.1."""

    def test_r15_fichier_valide_v1_reste_valide(self, tmp_path: Path) -> None:
        """R15 — fixture v1 (en-tête v1, points, dates remplies) : mêmes valeurs."""
        ligne1 = (
            "VT|Ventes|1|20240314|401100|Clients|C001|Client ABC|FAC001|20240314|"
            "Facture 001|1000.00|0.00||20240314|20240314|0|EUR"
        )
        ligne2 = (
            "VT|Ventes|2|20240314|701100|Ventes marchandises|||FAC001|20240314|"
            "Contrepartie|0.00|1000.00||20240314|20240314|0|EUR"
        )
        fichier = ecrire_fec(tmp_path, [ligne1, ligne2], entete=ENTETE_V1)

        assert valider_fec(fichier) == []
        ecritures = lire_fec(fichier)
        assert len(ecritures) == 2
        assert ecritures[0].compte_aux == "C001"
        assert ecritures[0].debit == Decimal("1000.00")
        assert ecritures[1].valid_date == datetime(2024, 3, 14)

    def test_r15_lire_fec_leve_sur_invalide(self, tmp_path: Path) -> None:
        """R15 / R8 — lire_fec lève ValueError si erreurs (inchangé v1)."""
        fichier = ecrire_fec(tmp_path, [ligne_fec(debit="abc")])

        with pytest.raises(ValueError, match="invalide"):
            lire_fec(fichier)

    def test_variantes_entete_table_exposee(self) -> None:
        """§Constantes — la table des variantes est publique et complète."""
        assert FEC_VARIANTES_ENTETE == {
            "CompteAux": "CompAuxNum",
            "CompteAuxLib": "CompAuxLib",
            "EcrtureLet": "EcritureLet",
        }

    def test_fec_colonnes_officielles(self) -> None:
        """§Constantes — colonnes 7/8 officielles, colonne 14 AVEC i (Légifrance)."""
        assert FEC_COLONNES[6] == "CompAuxNum"
        assert FEC_COLONNES[7] == "CompAuxLib"
        assert FEC_COLONNES[13] == "EcritureLet"
        assert len(FEC_COLONNES) == 18
