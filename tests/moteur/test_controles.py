"""
Tests des contrôles T1-T11, C1-C10 et ECF. Fixtures 100 % synthétiques.
Les codes Rx et ECx renvoient aux règles de la spécification interne.
"""

# Fichier généré, ne pas modifier à la main.
# empreinte-source: 7f39407b790b1a236ab10fbfbb2663637557710276babfe00372832ef150305e

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fec_check.fec import FEC_COLONNES, EcritureFEC, charger_fec
from fec_check.controles import (
    Constat,
    ProfilDossier,
    valider_comptable,
    valider_technique,
)


def ecr(
    compte: str,
    debit: str = "0",
    credit: str = "0",
    journal: str = "OD",
    journal_lib: str | None = None,
    num: str = "1",
    date: str = "20250115",
    compte_aux: str | None = None,
    piece_date: str | None = None,
    valid_date: str | None = "20250115",
) -> EcritureFEC:
    """Construit une écriture FEC synthétique en mémoire."""
    return EcritureFEC(
        journal_code=journal,
        journal_lib=journal_lib or f"Journal {journal}",
        ecriture_num=num,
        ecriture_date=datetime.strptime(date, "%Y%m%d"),
        compte_num=compte,
        compte_lib="Compte test",
        compte_aux=compte_aux,
        piece_date=datetime.strptime(piece_date, "%Y%m%d") if piece_date else None,
        ecriture_lib="Ecriture test",
        debit=Decimal(debit),
        credit=Decimal(credit),
        valid_date=datetime.strptime(valid_date, "%Y%m%d") if valid_date else None,
    )


def par_code(constats: list[Constat], code: str) -> list[Constat]:
    """Filtre les constats par code."""
    return [c for c in constats if c.code == code]


def ligne_fec_fichier(
    journal: str = "VT",
    num: str = "1",
    date: str = "20250314",
    compte: str = "41110000",
    debit: str = "0",
    credit: str = "0",
) -> str:
    """Construit une ligne FEC de 18 champs pour fichier."""
    return (
        f"{journal}|Ventes|{num}|{date}|{compte}|Clients|||FAC|{date}|"
        f"Test|{debit}|{credit}|||{date}||"
    )


def ecrire_fec(
    tmp_path: Path,
    lignes: list[str],
    entete: str | None = None,
    encodage: str = "utf-8",
    fin_ligne: str = "\r\n",
) -> Path:
    """Écrit un fichier FEC synthétique."""
    if entete is None:
        entete = "|".join(FEC_COLONNES)
    chemin = tmp_path / "fec.txt"
    chemin.write_bytes((fin_ligne.join([entete, *lignes]) + fin_ligne).encode(encodage))
    return chemin


class TestValiderTechnique:
    """R-T1 → R-T12 — transcription des faits du chargement en constats."""

    def test_rt1_info_iso(self, tmp_path: Path) -> None:
        """R-T1 — repli ISO-8859-15 → T1 info."""
        fichier = ecrire_fec(
            tmp_path,
            [ligne_fec_fichier(debit="10.00").replace("Clients", "Clientèle")],
            encodage="iso-8859-15",
        )
        constats = valider_technique(charger_fec(fichier))
        t1 = par_code(constats, "T1")
        assert len(t1) == 1
        assert t1[0].gravite == "info"

    def test_rt1_bloquant_fichier(self, tmp_path: Path) -> None:
        """R-T1 — fichier introuvable → T1 bloquant."""
        constats = valider_technique(charger_fec(tmp_path / "inexistant.txt"))
        t1 = par_code(constats, "T1")
        assert len(t1) == 1
        assert t1[0].gravite == "bloquant"

    def test_rt2_separateur(self, tmp_path: Path) -> None:
        """R-T2 — ligne sans pipe → T2 bloquant, occurrence L<n>."""
        fichier = ecrire_fec(tmp_path, ["pas de pipe ici"])
        constats = valider_technique(charger_fec(fichier))
        t2 = par_code(constats, "T2")
        assert len(t2) == 1
        assert t2[0].gravite == "bloquant"
        assert t2[0].occurrences == ["L2"]

    def test_rt3_colonnes(self, tmp_path: Path) -> None:
        """R-T3 — ligne < 18 champs → T3 bloquant, occurrence L<n>."""
        fichier = ecrire_fec(
            tmp_path, [ligne_fec_fichier(debit="10.00"), "VT|Ventes|2"]
        )
        constats = valider_technique(charger_fec(fichier))
        t3 = par_code(constats, "T3")
        assert len(t3) == 1
        assert t3[0].occurrences == ["L3"]

    def test_rt4_variantes_info_et_inconnues(self, tmp_path: Path) -> None:
        """R-T4 — variantes connues → info ; noms inconnus → avertissement."""
        remplacements: dict[str, str] = {
            "CompAuxNum": "CompteAux",
            "PieceRef": "RefPiece",
        }
        entete_variante = "|".join(remplacements.get(c, c) for c in FEC_COLONNES)
        fichier = ecrire_fec(
            tmp_path, [ligne_fec_fichier(debit="10.00")], entete=entete_variante
        )
        constats = valider_technique(charger_fec(fichier))
        t4 = par_code(constats, "T4")
        gravites = {c.gravite for c in t4}
        assert "info" in gravites  # CompteAux variante connue
        assert "avertissement" in gravites  # RefPiece inconnue
        assert any("CompteAux" in c.occurrences for c in t4)

    def test_rt5_rt6_dates_montants(self, tmp_path: Path) -> None:
        """R-T5/R-T6 — erreurs DATE/MONTANT → constats bloquants localisés."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec_fichier(num="1", date="20259999", debit="10.00"),
                ligne_fec_fichier(num="2", debit="abc"),
            ],
        )
        constats = valider_technique(charger_fec(fichier))
        assert par_code(constats, "T5")[0].occurrences == ["L2"]
        assert par_code(constats, "T6")[0].occurrences == ["L3"]

    def test_rt7_comptes_courts(self, tmp_path: Path) -> None:
        """R-T7 — CompteNum < 6 chiffres → avertissement, occurrences comptes."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec_fichier(num="1", compte="41110", debit="10.00"),
                ligne_fec_fichier(num="1", compte="70600000", credit="10.00"),
            ],
        )
        constats = valider_technique(charger_fec(fichier))
        t7 = par_code(constats, "T7")
        assert len(t7) == 1
        assert t7[0].gravite == "avertissement"
        assert t7[0].occurrences == ["41110"]

    def test_rt8_pas_de_bruit_sur_fichier_non_lu(self, tmp_path: Path) -> None:
        """R-T8 — fichier introuvable : fin_ligne « inconnu » ne produit PAS de T8 parasite."""
        constats = valider_technique(charger_fec(tmp_path / "inexistant.txt"))
        assert par_code(constats, "T8") == []

    def test_rt8_fin_ligne_lf(self, tmp_path: Path) -> None:
        """R-T8 — LF seul → info."""
        fichier = ecrire_fec(tmp_path, [ligne_fec_fichier(debit="10.00")], fin_ligne="\n")
        constats = valider_technique(charger_fec(fichier))
        assert par_code(constats, "T8")[0].gravite == "info"

    def test_rt9_rt10_rt11_qualite_donnees(self, tmp_path: Path) -> None:
        """R-T9/T10/T11 — 0/0, montants signés, pièces vides → infos."""
        lignes = [
            ligne_fec_fichier(num="1", debit="0", credit="0"),
            ligne_fec_fichier(num="2", debit="-50.00"),
            "OD|Divers|3|20250314|62200000|Compte|||||Test|10.00|0|||20250314||",
        ]
        fichier = ecrire_fec(tmp_path, lignes)
        constats = valider_technique(charger_fec(fichier))
        assert par_code(constats, "T9")[0].gravite == "info"
        assert par_code(constats, "T10")[0].gravite == "info"
        assert par_code(constats, "T11")[0].gravite == "info"

    def test_rt4_colonnes_surnumeraires_info(self, tmp_path: Path) -> None:
        """R-T4 — colonnes surnuméraires → T4 info avec les noms en occurrences."""
        entete = "|".join(FEC_COLONNES) + "|Etablissement"
        fichier = ecrire_fec(
            tmp_path, [ligne_fec_fichier(debit="10.00") + "|SIEGE"], entete=entete
        )
        constats = valider_technique(charger_fec(fichier))
        t4 = par_code(constats, "T4")
        assert len(t4) == 1
        assert t4[0].gravite == "info"
        assert t4[0].occurrences == ["Etablissement"]

    def test_rt_fec_propre_aucun_constat(self, tmp_path: Path) -> None:
        """FEC propre (UTF-8, CRLF, en-tête officiel) → aucun constat technique."""
        fichier = ecrire_fec(
            tmp_path,
            [
                ligne_fec_fichier(num="1", debit="10.00"),
                ligne_fec_fichier(num="1", compte="70600000", credit="10.00"),
            ],
        )
        assert valider_technique(charger_fec(fichier)) == []


class TestValiderComptable:
    """R-C1 → R-C10 + R-AN1."""

    def test_rc1_equilibre_global(self) -> None:
        """R-C1 — équilibré → rien ; écart ≤ 0,01 → info ; > 0,01 → bloquant."""
        equilibre = [ecr("512000", debit="10.00"), ecr("706000", credit="10.00")]
        assert par_code(valider_comptable(equilibre), "C1") == []

        petit_ecart = [ecr("512000", debit="10.01"), ecr("706000", credit="10.00")]
        c1 = par_code(valider_comptable(petit_ecart), "C1")
        assert c1[0].gravite == "info"
        assert c1[0].montant_ecart == Decimal("0.01")

        gros_ecart = [ecr("512000", debit="15.00"), ecr("706000", credit="10.00")]
        assert par_code(valider_comptable(gros_ecart), "C1")[0].gravite == "bloquant"

    def test_rc2_ec4_grille_par_ecriture(self) -> None:
        """R-C2 / EC4 — grille 0 / ≤0,02 avertissement / >0,02 bloquant, compensations détectées."""
        ecritures = [
            # écriture VE/1 : écart +0.02 (avertissement)
            ecr("411000", debit="100.02", journal="VE", num="1"),
            ecr("706000", credit="100.00", journal="VE", num="1"),
            # écriture VE/2 : écart −5.00 (bloquant), compense partiellement
            ecr("411000", debit="95.00", journal="VE", num="2"),
            ecr("706000", credit="100.00", journal="VE", num="2"),
        ]
        constats = par_code(valider_comptable(ecritures), "C2")
        avert = [c for c in constats if c.gravite == "avertissement"]
        bloq = [c for c in constats if c.gravite == "bloquant"]
        assert avert[0].occurrences == ["VE/1"]
        assert avert[0].montant_ecart == Decimal("0.02")
        assert bloq[0].occurrences == ["VE/2"]
        assert bloq[0].montant_ecart == Decimal("5.00")

    def test_rc3_debit_et_credit(self) -> None:
        """R-C3 — ligne avec débit ET crédit > 0 → avertissement."""
        ecritures = [
            ecr("512000", debit="10.00", credit="2.00", journal="BQ", num="7"),
            ecr("706000", credit="8.00", journal="BQ", num="7"),
        ]
        c3 = par_code(valider_comptable(ecritures), "C3")
        assert c3[0].gravite == "avertissement"
        assert c3[0].occurrences == ["BQ/7"]

    def test_rc4_ec2_comptes_79(self) -> None:
        """R-C4 / EC2 — toute racine 79 → avertissement, jamais bloquant."""
        ecritures = [
            ecr("791000", credit="10.00"),
            ecr("799000", credit="5.00"),
            ecr("512000", debit="15.00"),
        ]
        c4 = par_code(valider_comptable(ecritures), "C4")
        assert len(c4) == 1
        assert c4[0].gravite == "avertissement"
        assert c4[0].occurrences == ["791000", "799000"]
        # message enrichi par pcg.compte_supprime pour les racines connues
        assert "7412" in c4[0].message

    def test_rc5_ec15_sequentialite(self) -> None:
        """R-C5 / EC15 — retour en arrière numérique → avertissement ; alpha → info."""
        ecritures = [
            ecr("512000", debit="1.00", journal="VE", num="10"),
            ecr("706000", credit="1.00", journal="VE", num="10"),
            ecr("512000", debit="1.00", journal="VE", num="5"),  # retour en arrière
            ecr("706000", credit="1.00", journal="VE", num="5"),
            ecr("512000", debit="1.00", journal="AC", num="X1"),  # alpha
            ecr("706000", credit="1.00", journal="AC", num="X1"),
        ]
        c5 = par_code(valider_comptable(ecritures), "C5")
        avert = [c for c in c5 if c.gravite == "avertissement"]
        infos = [c for c in c5 if c.gravite == "info"]
        assert avert[0].occurrences == ["VE/5"]
        assert len(infos) == 1  # journal AC non applicable

    def test_rc6_ec1_bornes_et_an(self) -> None:
        """R-C6 / EC1 — hors bornes → avertissement ; à-nouveaux exclus ; sans profil → info."""
        ecritures = [
            ecr("512000", debit="1.00", date="20241231", journal="AN", num="1"),
            ecr("101000", credit="1.00", date="20241231", journal="AN", num="1"),
            ecr("512000", debit="1.00", date="20260220", journal="VE", num="2"),
            ecr("706000", credit="1.00", date="20260220", journal="VE", num="2"),
        ]
        profil = ProfilDossier(
            date_debut_exercice=datetime(2025, 1, 1),
            date_fin_exercice=datetime(2025, 12, 31),
        )
        c6 = par_code(valider_comptable(ecritures, profil), "C6")
        assert len(c6) == 1
        assert c6[0].gravite == "avertissement"
        assert c6[0].occurrences == ["VE/2"]  # AN/1 exclu (R-AN1)

        sans_profil = par_code(valider_comptable(ecritures), "C6")
        assert sans_profil[0].gravite == "info"

    def test_ran1_od_an_et_journaux_profil(self) -> None:
        """R-AN1 — OD-AN et lib « ouverture » détectés ; profil.journaux_an prioritaire."""
        ecritures = [
            ecr("512000", debit="1.00", date="20241231", journal="OD-AN", num="1"),
            ecr("101000", credit="1.00", date="20241231", journal="OD-AN", num="1"),
            ecr("512000", debit="1.00", date="20241230", journal="REP", num="2",
                journal_lib="Journal d'ouverture"),
            ecr("101000", credit="1.00", date="20241230", journal="REP", num="2",
                journal_lib="Journal d'ouverture"),
        ]
        profil = ProfilDossier(
            date_debut_exercice=datetime(2025, 1, 1),
            date_fin_exercice=datetime(2025, 12, 31),
        )
        # les deux journaux sont détectés comme à-nouveaux → aucun C6
        assert par_code(valider_comptable(ecritures, profil), "C6") == []

        # profil.journaux_an REMPLACE la détection : seul OD-AN est couvert
        profil_force = ProfilDossier(
            date_debut_exercice=datetime(2025, 1, 1),
            date_fin_exercice=datetime(2025, 12, 31),
            journaux_an=["OD-AN"],
        )
        c6 = par_code(valider_comptable(ecritures, profil_force), "C6")
        assert c6[0].occurrences == ["REP/2"]

    def test_rc7_piece_posterieure(self) -> None:
        """R-C7 — PieceDate > EcritureDate → info ; PieceDate absente → rien."""
        ecritures = [
            ecr("512000", debit="1.00", journal="AC", num="3",
                date="20250110", piece_date="20250120"),
            ecr("401000", credit="1.00", journal="AC", num="3", date="20250110"),
        ]
        c7 = par_code(valider_comptable(ecritures), "C7")
        assert len(c7) == 1
        assert c7[0].gravite == "info"
        assert c7[0].occurrences == ["AC/3"]

    def test_rc8_auxiliaire_manquant(self) -> None:
        """R-C8 — 401/411 sans auxiliaire → avertissement, comptes distincts."""
        ecritures = [
            ecr("401100", credit="10.00", journal="AC", num="1"),
            ecr("606000", debit="10.00", journal="AC", num="1"),
            ecr("411100", debit="20.00", journal="VE", num="2", compte_aux="CLI001"),
            ecr("706000", credit="20.00", journal="VE", num="2"),
        ]
        c8 = par_code(valider_comptable(ecritures), "C8")
        assert len(c8) == 1
        assert c8[0].occurrences == ["401100"]  # 411100 a un auxiliaire

    def test_rc9_ec12_caisse_crediteur_glissant(self) -> None:
        """R-C9 / EC12 — cumul glissant négatif en cours de période → bloquant."""
        ecritures = [
            ecr("530000", debit="100.00", date="20250110", journal="CA", num="1"),
            ecr("706000", credit="100.00", date="20250110", journal="CA", num="1"),
            ecr("530000", credit="300.00", date="20250120", journal="CA", num="2"),
            ecr("606000", debit="300.00", date="20250120", journal="CA", num="2"),
            ecr("530000", debit="500.00", date="20250210", journal="CA", num="3"),
            ecr("706000", credit="500.00", date="20250210", journal="CA", num="3"),
        ]
        c9 = par_code(valider_comptable(ecritures), "C9")
        assert len(c9) == 1
        assert c9[0].gravite == "bloquant"
        assert c9[0].occurrences == ["530000"]
        assert c9[0].montant_ecart == Decimal("200.00")
        assert "20250120" in c9[0].message

    def test_rc9_caisse_saine(self) -> None:
        """R-C9 — caisse toujours positive → aucun constat."""
        ecritures = [
            ecr("530000", debit="100.00", date="20250110"),
            ecr("706000", credit="100.00", date="20250110"),
            ecr("530000", credit="50.00", date="20250120"),
            ecr("606000", debit="50.00", date="20250120"),
        ]
        assert par_code(valider_comptable(ecritures), "C9") == []

    def test_rc10_ec5_decouvert_prolonge(self) -> None:
        """R-C10 / EC5 — 512 créditeur > 30 jours consécutifs → avertissement."""
        ecritures = [
            ecr("512000", credit="1000.00", date="20250101", journal="BQ", num="1"),
            ecr("606000", debit="1000.00", date="20250101", journal="BQ", num="1"),
            ecr("512000", debit="1500.00", date="20250310", journal="BQ", num="2"),
            ecr("706000", credit="1500.00", date="20250310", journal="BQ", num="2"),
        ]
        c10 = par_code(valider_comptable(ecritures), "C10")
        assert len(c10) == 1
        assert c10[0].gravite == "avertissement"
        assert c10[0].occurrences == ["512000"]

    def test_rc10_decouvert_jamais_referme(self) -> None:
        """R-C10 — découvert non refermé : mesuré jusqu'à la dernière date du FEC."""
        ecritures = [
            ecr("512000", credit="1000.00", date="20250101", journal="BQ", num="1"),
            ecr("606000", debit="1000.00", date="20250101", journal="BQ", num="1"),
            # aucune écriture 512 ensuite — la dernière date du FEC borne la période
            ecr("706000", credit="10.00", date="20250315", journal="VE", num="2"),
            ecr("411000", debit="10.00", date="20250315", journal="VE", num="2"),
        ]
        c10 = par_code(valider_comptable(ecritures), "C10")
        assert len(c10) == 1
        assert "73 jours" in c10[0].message  # 01/01 → 15/03

    def test_rc10_decouvert_court(self) -> None:
        """R-C10 — découvert de 14 jours → aucun constat."""
        ecritures = [
            ecr("512000", credit="1000.00", date="20250101", journal="BQ", num="1"),
            ecr("606000", debit="1000.00", date="20250101", journal="BQ", num="1"),
            ecr("512000", debit="1500.00", date="20250115", journal="BQ", num="2"),
            ecr("706000", credit="1500.00", date="20250115", journal="BQ", num="2"),
        ]
        assert par_code(valider_comptable(ecritures), "C10") == []


class TestECF:
    """R-ECF1 → R-ECF4."""

    def test_recf1_ec11_108_hors_ei(self) -> None:
        """R-ECF1 / EC11 — 108 en SAS → bloquant ; sans profil → rien."""
        ecritures = [
            ecr("108000", credit="100.00"),
            ecr("512000", debit="100.00"),
        ]
        avec_profil = valider_comptable(ecritures, ProfilDossier(forme_juridique="SAS"))
        ecf1 = par_code(avec_profil, "ECF-1")
        assert ecf1[0].gravite == "bloquant"
        assert ecf1[0].occurrences == ["108000"]

        assert par_code(valider_comptable(ecritures), "ECF-1") == []

    def test_recf2_455_en_ei(self) -> None:
        """R-ECF2 — 455 en EI → bloquant ; en SARL → rien."""
        ecritures = [
            ecr("455000", credit="100.00"),
            ecr("512000", debit="100.00"),
        ]
        en_ei = valider_comptable(ecritures, ProfilDossier(forme_juridique="EI"))
        assert par_code(en_ei, "ECF-2")[0].gravite == "bloquant"

        en_sarl = valider_comptable(ecritures, ProfilDossier(forme_juridique="SARL"))
        assert par_code(en_sarl, "ECF-2") == []

    def test_recf3_non_validees(self) -> None:
        """R-ECF3 — valid_date None → avertissement ; exercice clos → bloquant."""
        ecritures = [
            ecr("512000", debit="10.00", journal="VE", num="9", valid_date=None),
            ecr("706000", credit="10.00", journal="VE", num="9"),
        ]
        defaut = par_code(valider_comptable(ecritures), "ECF-3")
        assert defaut[0].gravite == "avertissement"
        assert defaut[0].occurrences == ["VE/9"]

        clos = valider_comptable(ecritures, ProfilDossier(exercice_clos=True))
        assert par_code(clos, "ECF-3")[0].gravite == "bloquant"

    def test_recf3_validee_apres_cloture(self) -> None:
        """R-ECF3 — valid_date postérieure à la clôture → constat (jamais de comparaison sur None)."""
        ecritures = [
            ecr("512000", debit="10.00", journal="VE", num="4", valid_date="20260315"),
            ecr("706000", credit="10.00", journal="VE", num="4", valid_date="20251215"),
        ]
        profil = ProfilDossier(date_fin_exercice=datetime(2025, 12, 31))
        ecf3 = par_code(valider_comptable(ecritures, profil), "ECF-3")
        assert len(ecf3) == 1
        assert ecf3[0].occurrences == ["VE/4"]

    def test_recf4_an_desequilibres(self) -> None:
        """R-ECF4 — à-nouveaux déséquilibrés > 0,02 → bloquant."""
        ecritures = [
            ecr("512000", debit="100.00", journal="AN", num="1"),
            ecr("101000", credit="90.00", journal="AN", num="1"),
            ecr("512000", debit="1.00", journal="VE", num="2"),
            ecr("706000", credit="11.00", journal="VE", num="2"),
        ]
        ecf4 = par_code(valider_comptable(ecritures), "ECF-4")
        assert ecf4[0].gravite == "bloquant"
        assert ecf4[0].montant_ecart == Decimal("10.00")

    def test_recf4_sans_an(self) -> None:
        """R-ECF4 — aucun à-nouveau → aucun constat."""
        ecritures = [ecr("512000", debit="10.00"), ecr("706000", credit="10.00")]
        assert par_code(valider_comptable(ecritures), "ECF-4") == []
