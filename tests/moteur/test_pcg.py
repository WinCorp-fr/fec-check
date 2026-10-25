"""
Tests du module pcg (format des comptes, classe 79 supprimée).
"""

# Fichier généré, ne pas modifier à la main.
# empreinte-source: b8ff1174bc9393554820c4ef9e7444662f5f110ed70aa31b681eb8b9745bee7f

import pytest

from fec_check.pcg import (
    valider_compte,
    compte_supprime,
    ReglePCG,
)


class TestValiderCompte:
    """Tests pour la validation de numéros de compte."""

    def test_compte_valide_minimal(self) -> None:
        """Test compte avec 6 chiffres (minimum)."""
        assert valider_compte("401000") is True

    def test_compte_valide_7_chiffres(self) -> None:
        """Test compte avec 7 chiffres."""
        assert valider_compte("4010001") is True

    def test_compte_valide_bilan(self) -> None:
        """Test comptes de bilan (classe 1-5)."""
        assert valider_compte("101000") is True
        assert valider_compte("211000") is True
        assert valider_compte("310000") is True
        assert valider_compte("411000") is True
        assert valider_compte("512000") is True

    def test_compte_valide_resultat(self) -> None:
        """Test comptes de résultat (classe 6-7)."""
        assert valider_compte("601000") is True
        assert valider_compte("701000") is True

    def test_compte_invalide_moins_6_chiffres(self) -> None:
        """Test compte avec < 6 chiffres (invalide)."""
        assert valider_compte("40100") is False
        assert valider_compte("401") is False

    def test_compte_invalide_non_numerique(self) -> None:
        """Test compte avec caractères non-numériques."""
        assert valider_compte("40100A") is False
        assert valider_compte("401 00") is False
        assert valider_compte("401-00") is False

    def test_compte_supprime_79x(self) -> None:
        """Test rejet strict des comptes 79x (classe supprimée)."""
        assert valider_compte("791000") is False
        assert valider_compte("792000") is False
        assert valider_compte("796000") is False
        assert valider_compte("797000") is False
        assert valider_compte("798000") is False

    def test_compte_invalide_type_non_string(self) -> None:
        """Test compte avec type non-string."""
        assert valider_compte(401000) is False  # type: ignore
        assert valider_compte(None) is False  # type: ignore

    def test_compte_valide_classe_7_non_79(self) -> None:
        """Test comptes classe 7 valides (74x, 75x, 76x, 78x)."""
        assert valider_compte("740000") is True  # 74x valide
        assert valider_compte("750000") is True  # 75x valide
        assert valider_compte("760000") is True  # 76x valide
        assert valider_compte("780000") is True  # 78x valide


class TestCompteSupprime:
    """Tests pour la détection des comptes supprimés."""

    def test_compte_791_supprime(self) -> None:
        """Test compte 791 supprimé."""
        resultat = compte_supprime("791000")
        assert resultat is not None
        assert "7412" in resultat or "7513" in resultat

    def test_compte_796_supprime(self) -> None:
        """Test compte 796 supprimé."""
        resultat = compte_supprime("796000")
        assert resultat is not None

    def test_compte_valide_non_supprime(self) -> None:
        """Test compte valide (pas supprimé)."""
        assert compte_supprime("401000") is None
        assert compte_supprime("701000") is None
        assert compte_supprime("740000") is None

    def test_compte_court_pas_dans_dict(self) -> None:
        """Test compte avec code court (non dans dict)."""
        assert compte_supprime("12") is None

    def test_message_remplacement(self) -> None:
        """Test que le message contient une suggestion."""
        resultat = compte_supprime("791000")
        assert resultat is not None
        assert "→" in resultat or "->" in resultat.lower()


class TestReglePCG:
    """Tests pour les règles PCG constants."""

    def test_classe_79_supprimee(self) -> None:
        """Test que classe 79 est marquée supprimée."""
        assert ReglePCG.CLASSE_79_SUPPRIMEE is True

    def test_classe_bilan(self) -> None:
        """Test les classes de bilan."""
        assert "1" in ReglePCG.CLASSE_BILAN
        assert "2" in ReglePCG.CLASSE_BILAN
        assert "3" in ReglePCG.CLASSE_BILAN
        assert "4" in ReglePCG.CLASSE_BILAN
        assert "5" in ReglePCG.CLASSE_BILAN

    def test_classe_resultat(self) -> None:
        """Test les classes de résultat."""
        assert "6" in ReglePCG.CLASSE_RESULTAT
        assert "7" in ReglePCG.CLASSE_RESULTAT

    def test_est_compte_bilan(self) -> None:
        """Test détection compte de bilan."""
        assert ReglePCG.est_compte_bilan("101000") is True
        assert ReglePCG.est_compte_bilan("401000") is True
        assert ReglePCG.est_compte_bilan("701000") is False

    def test_est_compte_resultat(self) -> None:
        """Test détection compte de résultat."""
        assert ReglePCG.est_compte_resultat("701000") is True
        assert ReglePCG.est_compte_resultat("601000") is True
        assert ReglePCG.est_compte_resultat("401000") is False

    def test_est_compte_bilan_avec_code_vide(self) -> None:
        """Test avec code de compte vide."""
        assert ReglePCG.est_compte_bilan("") is False
        assert ReglePCG.est_compte_resultat("") is False
