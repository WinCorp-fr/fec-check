"""
Rapport de conformité d'un FEC : assemble chargement et contrôles.

Le verdict ne dépend que des constats bloquants. Il est formulé « aucun
bloquant détecté » et jamais « conforme » : l'outil aide à la revue, il ne
remplace pas l'examen d'un professionnel.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from fec_check.controles import (
    ORDRE_CODES_CONTROLES,
    Constat,
    ProfilDossier,
    valider_comptable,
    valider_technique,
)
from fec_check.fec import MetadonneesFEC, charger_fec

Verdict = Literal["AUCUN_BLOQUANT", "BLOQUANTS_DETECTES"]

# Contrôles qui exigent un profil dossier pour être évalués.
CONTROLES_PROFIL: dict[str, str] = {
    "C6": "dates hors exercice (bornes d'exercice)",
    "ECF-1": "compte 108 hors entreprise individuelle (forme juridique)",
    "ECF-2": "compte 455 en entreprise individuelle (forme juridique)",
}


class RapportFEC(BaseModel):
    """Résultat complet d'une vérification, sérialisable en JSON stable."""

    fichier: str = Field(..., description="Nom du fichier vérifié (sans le chemin)")
    verdict: Verdict
    nb_bloquants: int
    nb_avertissements: int
    nb_infos: int
    constats: list[Constat] = Field(default_factory=list)
    meta: MetadonneesFEC
    profil_fourni: bool
    non_evalues: list[str] = Field(
        default_factory=list, description="Contrôles non évalués faute de profil"
    )


def _non_evalues(profil: ProfilDossier | None) -> list[str]:
    manquants: list[str] = []
    if profil is None or profil.date_debut_exercice is None or profil.date_fin_exercice is None:
        manquants.append(f"C6 : {CONTROLES_PROFIL['C6']}")
    if profil is None or profil.forme_juridique is None:
        manquants.append(f"ECF-1 : {CONTROLES_PROFIL['ECF-1']}")
        manquants.append(f"ECF-2 : {CONTROLES_PROFIL['ECF-2']}")
    return manquants


def verifier_fec(chemin: Path, profil: ProfilDossier | None = None) -> RapportFEC:
    """
    Vérifie un FEC et renvoie le rapport. Ne lève jamais sur un fichier dégradé.

    Args:
        chemin : Fichier FEC (tabulation ou pipe, UTF-8 ou ISO-8859-15).
        profil : Contexte dossier facultatif (forme juridique, bornes d'exercice,
            exercice clos) qui active C6, ECF-1 et ECF-2 et durcit ECF-3.

    Returns:
        RapportFEC : verdict, compteurs par gravité, constats, métadonnées.
    """
    chargement = charger_fec(chemin)
    constats = sorted(
        valider_technique(chargement) + valider_comptable(chargement.ecritures, profil),
        key=lambda constat: ORDRE_CODES_CONTROLES.index(constat.code),
    )
    nb_bloquants = sum(1 for c in constats if c.gravite == "bloquant")
    return RapportFEC(
        fichier=chemin.name,
        verdict="BLOQUANTS_DETECTES" if nb_bloquants else "AUCUN_BLOQUANT",
        nb_bloquants=nb_bloquants,
        nb_avertissements=sum(1 for c in constats if c.gravite == "avertissement"),
        nb_infos=sum(1 for c in constats if c.gravite == "info"),
        constats=constats,
        meta=chargement.meta,
        profil_fourni=profil is not None,
        non_evalues=_non_evalues(profil),
    )


def _date(valeur: datetime | None) -> str:
    return valeur.strftime("%d/%m/%Y") if valeur else "?"


def formater_texte(rapport: RapportFEC, max_occurrences: int = 10) -> str:
    """Rapport lisible par un humain, en français."""
    meta = rapport.meta
    sep = "tabulation" if meta.separateur_colonnes == "\t" else "pipe |"
    if rapport.verdict == "AUCUN_BLOQUANT":
        verdict = "aucune anomalie bloquante détectée"
    else:
        verdict = f"{rapport.nb_bloquants} anomalie(s) bloquante(s) détectée(s)"
    lignes = [
        f"FEC : {rapport.fichier}",
        f"Verdict : {verdict}",
        (
            f"{meta.nb_lignes} lignes lues, du {_date(meta.date_min)} au {_date(meta.date_max)}, "
            f"séparateur {sep}, encodage {meta.encodage.upper()}"
        ),
        f"Total débit {meta.total_debit} €, total crédit {meta.total_credit} €",
    ]
    titres = {"bloquant": "BLOQUANT", "avertissement": "AVERTISSEMENT", "info": "INFORMATION"}
    for gravite, titre in titres.items():
        groupe = [c for c in rapport.constats if c.gravite == gravite]
        if not groupe:
            continue
        lignes += ["", f"{titre} ({len(groupe)})"]
        for constat in groupe:
            ecart = f" (écart {constat.montant_ecart} €)" if constat.montant_ecart else ""
            lignes.append(f"  {constat.code:<6}{constat.message}{ecart}")
            if constat.occurrences:
                vues = constat.occurrences[:max_occurrences]
                reste = len(constat.occurrences) - len(vues)
                suite = f" et {reste} autre(s)" if reste > 0 else ""
                lignes.append(f"        concerne : {', '.join(vues)}{suite}")
    if rapport.non_evalues:
        lignes += ["", "Non évalués sans profil dossier (option --profil) :"]
        lignes += [f"  - {item}" for item in rapport.non_evalues]
    lignes += [
        "",
        "Outil d'aide à la revue, fourni sans garantie : il ne remplace pas l'examen",
        "d'un professionnel. fec-check par WinCorp, https://wincorp.fr",
    ]
    return "\n".join(lignes) + "\n"
