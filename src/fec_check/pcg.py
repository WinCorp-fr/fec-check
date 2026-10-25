"""
Plan comptable général (règlement ANC 2022-06) : format des numéros de
compte et comptes supprimés (classe 79).
"""

# Fichier généré, ne pas modifier à la main.
# empreinte-source: f73f46b8cf835eda3adc41ce57b34ecae6c891e31a37cb697c7df750428eb0ad

import re

# Comptes supprimés par la PCG 2022-06
COMPTES_SUPPRIMIS = {
    "791": "Neutralisation de charges exceptionnelles → utiliser 7412 ou 7513",
    "792": "Neutralisation de charges exceptionnelles → utiliser 7412 ou 7513",
    "796": "Neutralisation de charges exceptionnelles → utiliser 7412 ou 7513",
    "797": "Neutralisation de charges exceptionnelles → utiliser 7412 ou 7513",
    "798": "Neutralisation de charges exceptionnelles → utiliser 7412 ou 7513",
}

# Format attendu : 6 à 8 chiffres (compatibilité logiciels comptables comme Fulll)
REGEX_COMPTE = re.compile(r"^\d{6,8}$")


def valider_compte(numero: str) -> bool:
    """
    Valide un numéro de compte selon PCG 2022-06.

    Règles :
    - 6 à 8 chiffres (compatibilité Fulll et autres logiciels comptables)
    - Pas de compte classe 79 (supprimée PCG 2022-06)

    Args:
        numero : Numéro de compte (string)

    Returns:
        bool : True si valide, False sinon

    Example:
        >>> valider_compte("401000")
        True
        >>> valider_compte("791000")
        False
    """
    if not isinstance(numero, str):
        return False

    # Vérifier format de base
    if not REGEX_COMPTE.match(numero):
        return False

    # Vérifier que ce n'est pas un compte supprimé (79x)
    if numero.startswith("79"):
        return False

    return True


def compte_supprime(numero: str) -> str | None:
    """
    Retourne un message si le compte est supprimé par PCG 2022-06.

    Args:
        numero : Numéro de compte

    Returns:
        str | None : Message de remplacement ou None si compte valide

    Example:
        >>> compte_supprime("791000")
        'Neutralisation de charges exceptionnelles → utiliser 7412 ou 7513'
    """
    if len(numero) < 3:
        return None

    prefix = numero[:3]
    return COMPTES_SUPPRIMIS.get(prefix)


class ReglePCG:
    """Règles PCG 2022-06 comme constantes."""

    # Classe 79 supprimée
    CLASSE_79_SUPPRIMEE = True

    # Classe de bilan
    CLASSE_BILAN = frozenset(["1", "2", "3", "4", "5"])

    # Classe de résultat
    CLASSE_RESULTAT = frozenset(["6", "7"])

    # Comptes de neutralisation
    COMPTES_NEUTRALISATION_CHARGES = frozenset(["7412", "7413", "7513"])
    COMPTES_NEUTRALISATION_PRODUITS = frozenset(["7412", "7513", "7514"])

    @staticmethod
    def est_compte_bilan(numero: str) -> bool:
        """Détermine si le compte est un compte de bilan."""
        if len(numero) < 1:
            return False
        return numero[0] in ReglePCG.CLASSE_BILAN

    @staticmethod
    def est_compte_resultat(numero: str) -> bool:
        """Détermine si le compte est un compte de résultat."""
        if len(numero) < 1:
            return False
        return numero[0] in ReglePCG.CLASSE_RESULTAT
