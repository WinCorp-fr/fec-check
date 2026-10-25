"""
Tests de lecture et de validation de base d'un FEC.
"""

# Fichier généré, ne pas modifier à la main.
# empreinte-source: 2aa07037bd3521c2094e90f7b457966f7b51d7c9c3234b5c4e169d5c8e705f22

from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from fec_check.fec import (
    FEC_COLONNES,
    charger_fec,
    lire_fec,
    valider_fec,
)


@pytest.fixture
def fec_valide_contenu() -> str:
    """Contenu d'un fichier FEC valide."""
    entete = "|".join(FEC_COLONNES)
    # Format: JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise
    ligne1 = "VT|Ventes|1|20240314|401100|Clients|C001|Client ABC|FAC001|20240314|Facture 001|1000.00|0.00||20240314|20240314|0|EUR"
    ligne2 = "VT|Ventes|2|20240314|701100|Ventes marchandises|||FAC001|20240314|Contrepartie|0.00|1000.00||20240314|20240314|0|EUR"
    return entete + "\r\n" + ligne1 + "\r\n" + ligne2 + "\r\n"


@pytest.fixture
def fec_fichier_valide(fec_valide_contenu: str) -> Path:
    """Crée un fichier FEC valide temporaire."""
    with NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
        newline="",
    ) as f:
        f.write(fec_valide_contenu)
        return Path(f.name)


class TestValiderFEC:
    """Tests pour la validation FEC."""

    def test_fec_fichier_inexistant(self) -> None:
        """Test avec fichier inexistant."""
        erreurs = valider_fec(Path("/tmp/inexistant_xyz_123.txt"))

        assert len(erreurs) > 0
        assert "non trouvé" in erreurs[0].message.lower()

    def test_fec_fichier_vide(self) -> None:
        """Test avec fichier vide."""
        with NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
        ) as f:
            chemin = Path(f.name)

        erreurs = valider_fec(chemin)
        assert len(erreurs) > 0

        chemin.unlink()

    def test_fec_entete_incorrect(self) -> None:
        """Test avec en-tête incorrect."""
        with NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
            newline="",
        ) as f:
            f.write("Colonne1|Colonne2|Colonne3\n")
            chemin = Path(f.name)

        erreurs = valider_fec(chemin)
        assert len(erreurs) > 0
        assert "en-tête" in erreurs[0].message.lower() or "entête" in erreurs[0].message.lower()

        chemin.unlink()

    def test_fec_date_invalide(self) -> None:
        """Test avec date invalide."""
        entete = "|".join(FEC_COLONNES)
        # Date "20240" au lieu de "20240314"
        ligne = "VT|Ventes|1|20240|401100|Clients|||||20240314|Facture|1000|0|||||EUR"

        with NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
            newline="",
        ) as f:
            f.write(entete + "\r\n" + ligne + "\r\n")
            chemin = Path(f.name)

        erreurs = valider_fec(chemin)
        assert len(erreurs) > 0

        chemin.unlink()

    def test_fec_montants_negatifs(self) -> None:
        """R6 v2.1 — montants signés licites (art. A.47 A-1 XII.2°) : normalisés, jamais rejetés.

        Migration : la v1 rejetait ces lignes ; l'audit #1 a établi que les
        valeurs signées sont réglementaires (avoirs, contre-passations).
        """
        entete = "|".join(FEC_COLONNES)
        ligne = (
            "VT|Ventes|1|20240314|401100|Clients|||FAC001|20240314|"
            "Avoir|-1000|0||20240314|20240314|0|EUR"
        )

        with NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
            newline="",
        ) as f:
            f.write(entete + "\r\n" + ligne + "\r\n")
            chemin = Path(f.name)

        erreurs = valider_fec(chemin)
        assert erreurs == []

        ecritures = lire_fec(chemin)
        assert ecritures[0].debit == Decimal("0")
        assert ecritures[0].credit == Decimal("1000")

        chemin.unlink()

    def test_fec_debit_credit_nuls(self) -> None:
        """R7 v2.1 — ligne à débit et crédit nuls CONSERVÉE (ligne technique réelle).

        Migration : la v1 rejetait ces lignes ; l'audit #1 a établi qu'elles
        existent dans les exports réels (TVA à 0, centralisations).
        """
        entete = "|".join(FEC_COLONNES)
        ligne = (
            "VT|Ventes|1|20240314|401100|Clients|||FAC001|20240314|"
            "Ligne technique|0|0||20240314|20240314|0|EUR"
        )

        with NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
            newline="",
        ) as f:
            f.write(entete + "\r\n" + ligne + "\r\n")
            chemin = Path(f.name)

        erreurs = valider_fec(chemin)
        assert erreurs == []

        ecritures = lire_fec(chemin)
        assert len(ecritures) == 1
        assert ecritures[0].debit == Decimal("0")
        assert ecritures[0].credit == Decimal("0")

        chemin.unlink()

    def test_fec_valide(self, fec_fichier_valide: Path) -> None:
        """Test avec FEC valide."""
        erreurs = valider_fec(fec_fichier_valide)

        assert len(erreurs) == 0

        fec_fichier_valide.unlink()

    def test_fec_colonnes_incorrectes(self) -> None:
        """Test avec nombre de colonnes incorrect."""
        entete = "|".join(FEC_COLONNES)
        # Ligne avec colonnes manquantes
        ligne = "VT|Ventes|1|20240314|401100"

        with NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
            newline="",
        ) as f:
            f.write(entete + "\r\n" + ligne + "\r\n")
            chemin = Path(f.name)

        erreurs = valider_fec(chemin)
        assert len(erreurs) > 0

        chemin.unlink()


class TestLireFEC:
    """Tests pour la lecture FEC."""

    def test_lire_fec_invalide(self) -> None:
        """Test lecture d'un FEC invalide (doit lever erreur)."""
        with NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
            newline="",
        ) as f:
            f.write("Données invalides")
            chemin = Path(f.name)

        with pytest.raises(ValueError, match="invalide"):
            lire_fec(chemin)

        chemin.unlink()

    def test_lire_fec_valide(self, fec_fichier_valide: Path) -> None:
        """Test lecture d'un FEC valide."""
        ecritures = lire_fec(fec_fichier_valide)

        assert len(ecritures) == 2
        assert ecritures[0].journal_code == "VT"
        assert ecritures[0].compte_num == "401100"
        assert ecritures[0].debit.as_tuple().digits == (1, 0, 0, 0, 0, 0) or str(
            ecritures[0].debit
        ) == "1000.00"

        fec_fichier_valide.unlink()

    def test_fec_colonnes_nombre(self) -> None:
        """Test que FEC_COLONNES contient 18 colonnes."""
        assert len(FEC_COLONNES) == 18

    def test_fec_colonnes_noms(self) -> None:
        """Test que les colonnes requises sont présentes."""
        colonnes_attendues = [
            "JournalCode",
            "EcritureDate",
            "CompteNum",
            "Debit",
            "Credit",
            "ValidDate",
        ]
        for col in colonnes_attendues:
            assert col in FEC_COLONNES


class TestEdgeCasesFEC:
    """Tests des edge cases FEC (TODO-1, TODO-2, TODO-3 de fec.spec.md)."""

    def test_fec_encodage_non_utf8(self) -> None:
        """R3 v2.1 — fichier Latin → chargé via repli ISO-8859-15, encodage tracé.

        Migration : la v1 rejetait tout non-UTF-8 ; l'arrêté admet plusieurs
        jeux de caractères (OUT historique levé, GO 03/07).
        """
        entete = "|".join(FEC_COLONNES)
        # Libellé avec caractère non-ASCII encodé en Latin (é = 0xE9)
        ligne = (
            "VT|Ventes|1|20240314|401100|Clients|||FAC001|20240314|"
            "Facturé spécial|1000|0||20240314|20240314|0|EUR"
        )
        contenu = entete + "\r\n" + ligne + "\r\n"

        with NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(contenu.encode("iso-8859-15"))
            chemin = Path(f.name)

        erreurs = valider_fec(chemin)
        assert erreurs == []

        chargement = charger_fec(chemin)
        assert chargement.meta.encodage == "iso-8859-15"
        assert chargement.ecritures[0].ecriture_lib == "Facturé spécial"

        chemin.unlink()

    def test_fec_montant_non_numerique(self) -> None:
        """EC6 / TODO-2 — montant non-numérique (ex: 'abc') → erreur de format."""
        entete = "|".join(FEC_COLONNES)
        # Debit "abc" au lieu d'un nombre
        ligne = (
            "VT|Ventes|1|20240314|401100|Clients|||FAC001|20240314|"
            "Facture|abc|0||20240314|20240314|0|EUR"
        )

        with NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
            newline="",
        ) as f:
            f.write(entete + "\r\n" + ligne + "\r\n")
            chemin = Path(f.name)

        erreurs = valider_fec(chemin)
        assert len(erreurs) > 0

        chemin.unlink()

    def test_fec_entete_seul_sans_lignes(self) -> None:
        """EC7 / TODO-3 — fichier avec en-tête valide et aucune ligne de données → valide."""
        entete = "|".join(FEC_COLONNES)

        with NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            delete=False,
            encoding="utf-8",
            newline="",
        ) as f:
            f.write(entete + "\r\n")
            chemin = Path(f.name)

        erreurs = valider_fec(chemin)
        # Un FEC avec en-tête seul est syntaxiquement valide
        assert len(erreurs) == 0

        # lire_fec retourne une liste vide
        ecritures = lire_fec(chemin)
        assert ecritures == []

        chemin.unlink()
