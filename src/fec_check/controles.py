"""
Contrôles déterministes de conformité d'un FEC.

Techniques T1 à T11 (faits du chargement) et comptables C1 à C10 et ECF-1
à ECF-4. Aucun appel réseau, aucun aléa : deux exécutions sur le même
fichier donnent un résultat strictement identique.
"""

# Fichier généré, ne pas modifier à la main.
# empreinte-source: 0d5af6a7fa1c5b75122deef077a2933e076cb87db775c235040b6c8f2e577bbb

import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fec_check.fec import ChargementFEC, EcritureFEC
from fec_check.pcg import compte_supprime
from fec_check.pydantic_types import DecimalStr

Gravite = Literal["bloquant", "avertissement", "info"]

_CENT = Decimal("0.01")
_SEUIL_C1 = Decimal("0.01")
_SEUIL_C2 = Decimal("0.02")
_SEUIL_ECF4 = Decimal("0.02")
_JOURS_DECOUVERT_C10 = 30

# Ordre stable des constats de contrôle — R-A1 (revision y ajoute SIG/BIL).
ORDRE_CODES_CONTROLES: list[str] = [
    *[f"T{i}" for i in range(1, 12)],
    *[f"C{i}" for i in range(1, 11)],
    "ECF-1",
    "ECF-2",
    "ECF-3",
    "ECF-4",
]


def _q(valeur: Decimal) -> Decimal:
    """Quantize 0,01 ROUND_HALF_UP — appliqué à l'EXPOSITION seulement (R-M1)."""
    return valeur.quantize(_CENT, rounding=ROUND_HALF_UP)


class Constat(BaseModel):
    """Constat d'un contrôle — jamais une exception."""

    code: str = Field(..., description="Identifiant stable du contrôle")
    gravite: Gravite = Field(..., description="Mapping skill : bloquant/avertissement/info")
    message: str = Field(..., description="Message FR actionnable")
    occurrences: list[str] = Field(
        default_factory=list, description="Identifiants concernés (format R-M2, triés R-M3)"
    )
    montant_ecart: DecimalStr | None = Field(
        default=None, description="Plus grand écart parmi les occurrences du constat"
    )


class ProfilDossier(BaseModel):
    """Contexte dossier pour les contrôles conditionnels (tous champs optionnels)."""

    model_config = ConfigDict(extra="forbid")

    forme_juridique: str | None = Field(default=None)
    date_debut_exercice: datetime | None = Field(default=None)
    date_fin_exercice: datetime | None = Field(default=None)
    exercice_clos: bool | None = Field(default=None)
    comptes_digits: int | None = Field(default=None)
    journaux_an: list[str] | None = Field(
        default=None, description="Remplace la détection R-AN1 si fourni"
    )


# ---------------------------------------------------------------------------
# Helpers déterminisme
# ---------------------------------------------------------------------------

_RE_OCCURRENCE_LIGNE = re.compile(r"L\d+")


def _trier_occurrences(occurrences: list[str]) -> list[str]:
    """R-M3 — tri numérique pour les L<n>, lexicographique sinon."""
    uniques = list(dict.fromkeys(occurrences))
    if uniques and all(_RE_OCCURRENCE_LIGNE.fullmatch(o) for o in uniques):
        return sorted(uniques, key=lambda o: int(o[1:]))
    return sorted(uniques)


def _cle_ecriture(ecriture: EcritureFEC) -> str:
    """Clé R-M2 d'une écriture : <JournalCode>/<EcritureNum> (comparaison exacte)."""
    return f"{ecriture.journal_code}/{ecriture.ecriture_num}"


def _est_a_nouveau(ecriture: EcritureFEC, profil: ProfilDossier | None) -> bool:
    """R-AN1 — détection des écritures d'à-nouveaux."""
    if profil is not None and profil.journaux_an is not None:
        return ecriture.journal_code in profil.journaux_an
    segments = re.split(r"[^0-9A-Za-z]+", ecriture.journal_code)
    if any(segment.upper() == "AN" for segment in segments):
        return True
    lib = ecriture.journal_lib.lower()
    return "nouveau" in lib or "ouverture" in lib


# ---------------------------------------------------------------------------
# Contrôles techniques
# ---------------------------------------------------------------------------


def valider_technique(chargement: ChargementFEC) -> list[Constat]:
    """
    Transcrit les faits du chargement en constats T1-T11 — R-T1 à R-T12.

    Le discriminant est TOUJOURS `ErreurFEC.code` ou la méta, jamais le texte
    des messages (R-T12).

    Args:
        chargement : Résultat de fec.charger_fec.

    Returns:
        list[Constat] : Constats techniques, ordre T1 → T11.
    """
    constats: list[Constat] = []
    meta = chargement.meta
    erreurs_par_code: dict[str, list[int]] = {}
    for erreur in chargement.erreurs:
        erreurs_par_code.setdefault(erreur.code or "", []).append(erreur.ligne)

    lignes_globales = erreurs_par_code.get("FICHIER", []) + erreurs_par_code.get(
        "ENCODAGE", []
    )
    if lignes_globales:
        messages = [
            e.message for e in chargement.erreurs if e.code in ("FICHIER", "ENCODAGE")
        ]
        constats.append(
            Constat(
                code="T1",
                gravite="bloquant",
                message="Fichier illisible : " + " ; ".join(messages),
            )
        )
    elif meta.encodage == "iso-8859-15":
        constats.append(
            Constat(
                code="T1",
                gravite="info",
                message=(
                    "FEC lu en ISO-8859-15 (l'arrêté admet plusieurs jeux de "
                    "caractères) — converti sans perte"
                ),
            )
        )

    if "SEPARATEUR" in erreurs_par_code:
        constats.append(
            Constat(
                code="T2",
                gravite="bloquant",
                message="Lignes sans séparateur pipe — non exploitables",
                occurrences=_trier_occurrences(
                    [f"L{n}" for n in erreurs_par_code["SEPARATEUR"]]
                ),
            )
        )

    lignes_colonnes = erreurs_par_code.get("ENTETE", []) + erreurs_par_code.get(
        "COLONNES", []
    )
    if lignes_colonnes:
        constats.append(
            Constat(
                code="T3",
                gravite="bloquant",
                message="Nombre de colonnes non conforme (18 attendues)",
                occurrences=_trier_occurrences([f"L{n}" for n in lignes_colonnes]),
            )
        )

    if meta.variantes_entete:
        constats.append(
            Constat(
                code="T4",
                gravite="info",
                message="Variantes d'en-tête connues acceptées (noms officiels appliqués)",
                occurrences=_trier_occurrences(list(meta.variantes_entete)),
            )
        )
    if meta.entete_inconnues:
        constats.append(
            Constat(
                code="T4",
                gravite="avertissement",
                message="Noms de colonnes inconnus — traités par position",
                occurrences=_trier_occurrences(meta.entete_inconnues),
            )
        )
    if meta.colonnes_surnumeraires:
        constats.append(
            Constat(
                code="T4",
                gravite="info",
                message="Colonnes surnuméraires ignorées (au-delà des 18 officielles)",
                occurrences=_trier_occurrences(meta.colonnes_surnumeraires),
            )
        )

    if "DATE" in erreurs_par_code:
        constats.append(
            Constat(
                code="T5",
                gravite="bloquant",
                message="Dates invalides (format YYYYMMDD attendu)",
                occurrences=_trier_occurrences(
                    [f"L{n}" for n in erreurs_par_code["DATE"]]
                ),
            )
        )
    if "MONTANT" in erreurs_par_code:
        constats.append(
            Constat(
                code="T6",
                gravite="bloquant",
                message="Montants non convertibles après normalisation",
                occurrences=_trier_occurrences(
                    [f"L{n}" for n in erreurs_par_code["MONTANT"]]
                ),
            )
        )

    comptes_courts = [
        e.compte_num for e in chargement.ecritures if len(e.compte_num) < 6
    ]
    if comptes_courts:
        constats.append(
            Constat(
                code="T7",
                gravite="avertissement",
                message="Numéros de compte de moins de 6 chiffres",
                occurrences=_trier_occurrences(comptes_courts),
            )
        )

    # « inconnu » = fichier non lu ou sans fin de ligne : pas de constat parasite.
    if meta.fin_ligne in ("LF", "mixte"):
        constats.append(
            Constat(
                code="T8",
                gravite="info",
                message=f"Fins de ligne {meta.fin_ligne} (CRLF attendu) — toléré",
            )
        )

    if meta.nb_lignes_zero:
        lignes_zero = [
            f"L{e.ligne_source}"
            for e in chargement.ecritures
            if e.debit == 0 and e.credit == 0 and e.ligne_source is not None
        ]
        constats.append(
            Constat(
                code="T9",
                gravite="info",
                message=f"{meta.nb_lignes_zero} ligne(s) à débit et crédit nuls conservée(s)",
                occurrences=_trier_occurrences(lignes_zero),
            )
        )
    if meta.nb_montants_negatifs:
        constats.append(
            Constat(
                code="T10",
                gravite="info",
                message=(
                    f"{meta.nb_montants_negatifs} montant(s) signé(s) normalisé(s) en "
                    "colonne opposée (valeurs signées licites, art. A.47 A-1 XII.2°)"
                ),
            )
        )
    if meta.nb_pieces_incompletes:
        lignes_pieces = [
            f"L{e.ligne_source}"
            for e in chargement.ecritures
            if (e.piece_ref is None or e.piece_date is None) and e.ligne_source is not None
        ]
        constats.append(
            Constat(
                code="T11",
                gravite="info",
                message=(
                    f"{meta.nb_pieces_incompletes} ligne(s) avec PieceRef ou PieceDate vide"
                ),
                occurrences=_trier_occurrences(lignes_pieces),
            )
        )
    return constats


# ---------------------------------------------------------------------------
# Contrôles comptables
# ---------------------------------------------------------------------------


def _controle_c1(ecritures: list[EcritureFEC]) -> list[Constat]:
    """R-C1 — équilibre global."""
    total_debit = sum((e.debit for e in ecritures), Decimal("0"))
    total_credit = sum((e.credit for e in ecritures), Decimal("0"))
    ecart = abs(total_debit - total_credit)
    if ecart == 0:
        return []
    if ecart <= _SEUIL_C1:
        return [
            Constat(
                code="C1",
                gravite="info",
                message=f"Écart global d'arrondi de {_q(ecart)} € (≤ 0,01 €)",
                montant_ecart=_q(ecart),
            )
        ]
    return [
        Constat(
            code="C1",
            gravite="bloquant",
            message=f"FEC déséquilibré : écart global de {_q(ecart)} € entre débits et crédits",
            montant_ecart=_q(ecart),
        )
    ]


def _controle_c2(ecritures: list[EcritureFEC]) -> list[Constat]:
    """R-C2 — équilibre par écriture, grille 0 / ≤ 0,02 / > 0,02."""
    groupes: dict[tuple[str, str], list[Decimal]] = {}
    for e in ecritures:
        cle = (e.journal_code, e.ecriture_num)
        if cle not in groupes:
            groupes[cle] = [Decimal("0"), Decimal("0")]
        groupes[cle][0] += e.debit
        groupes[cle][1] += e.credit

    avertissements: list[tuple[str, Decimal]] = []
    bloquants: list[tuple[str, Decimal]] = []
    for (journal, num), (debit, credit) in groupes.items():
        ecart = abs(debit - credit)
        if ecart == 0:
            continue
        if ecart <= _SEUIL_C2:
            avertissements.append((f"{journal}/{num}", ecart))
        else:
            bloquants.append((f"{journal}/{num}", ecart))

    constats: list[Constat] = []
    if avertissements:
        constats.append(
            Constat(
                code="C2",
                gravite="avertissement",
                message=(
                    f"{len(avertissements)} écriture(s) avec écart d'arrondi "
                    "inter-systèmes ≤ 0,02 €"
                ),
                occurrences=_trier_occurrences([cle for cle, _ in avertissements]),
                montant_ecart=_q(max(ecart for _, ecart in avertissements)),
            )
        )
    if bloquants:
        constats.append(
            Constat(
                code="C2",
                gravite="bloquant",
                message=f"{len(bloquants)} écriture(s) déséquilibrée(s) (écart > 0,02 €)",
                occurrences=_trier_occurrences([cle for cle, _ in bloquants]),
                montant_ecart=_q(max(ecart for _, ecart in bloquants)),
            )
        )
    return constats


def _indications_pcg_79(comptes_79: list[str]) -> str:
    """R-C4 — enrichit le message avec les reclassements pcg.compte_supprime."""
    indications = sorted(
        {
            f"{compte[:3]}x : {indication}"
            for compte in comptes_79
            if (indication := compte_supprime(compte)) is not None
        }
    )
    if not indications:
        return ""
    return ". " + " ; ".join(indications)


def _controle_c5(ecritures: list[EcritureFEC]) -> list[Constat]:
    """R-C5 — séquentialité des EcritureNum par journal."""
    sequences: dict[str, list[str]] = {}
    for e in ecritures:
        sequences.setdefault(e.journal_code, [])
        if not sequences[e.journal_code] or sequences[e.journal_code][-1] != e.ecriture_num:
            sequences[e.journal_code].append(e.ecriture_num)

    retours: list[str] = []
    non_applicables: list[str] = []
    for journal, nums in sequences.items():
        if not all(num.isdigit() for num in nums):
            non_applicables.append(journal)
            continue
        for precedent, courant in zip(nums, nums[1:], strict=False):
            if int(courant) < int(precedent):
                retours.append(f"{journal}/{courant}")

    constats: list[Constat] = []
    if retours:
        constats.append(
            Constat(
                code="C5",
                gravite="avertissement",
                message="Retour(s) en arrière dans la numérotation des écritures",
                occurrences=_trier_occurrences(retours),
            )
        )
    if non_applicables:
        constats.append(
            Constat(
                code="C5",
                gravite="info",
                message="Contrôle de séquentialité non applicable (numérotation non numérique)",
                occurrences=_trier_occurrences(non_applicables),
            )
        )
    return constats


def _cumul_glissant(
    ecritures: list[EcritureFEC], racine: str
) -> dict[str, list[tuple[datetime, Decimal]]]:
    """Cumuls glissants (date, solde) par compte d'une racine, tri stable par date."""
    par_compte: dict[str, list[tuple[datetime, Decimal]]] = {}
    for compte in sorted(
        {e.compte_num for e in ecritures if e.compte_num.startswith(racine)}
    ):
        mouvements = [e for e in ecritures if e.compte_num == compte]
        mouvements.sort(key=lambda e: e.ecriture_date)  # tri stable : ordre fichier à date égale
        cumul = Decimal("0")
        serie: list[tuple[datetime, Decimal]] = []
        for e in mouvements:
            cumul += e.debit - e.credit
            serie.append((e.ecriture_date, cumul))
        par_compte[compte] = serie
    return par_compte


def _controle_c9(ecritures: list[EcritureFEC]) -> list[Constat]:
    """R-C9 — caisse créditrice en cumul glissant (impossible physiquement)."""
    constats: list[Constat] = []
    for compte, serie in _cumul_glissant(ecritures, "53").items():
        solde_minimal = Decimal("0")
        date_bascule: datetime | None = None
        for date, cumul in serie:
            if cumul < solde_minimal:
                solde_minimal = cumul
            if cumul < 0 and date_bascule is None:
                date_bascule = date
        if date_bascule is not None:
            constats.append(
                Constat(
                    code="C9",
                    gravite="bloquant",
                    message=(
                        f"Solde de caisse créditeur à partir du "
                        f"{date_bascule.strftime('%Y%m%d')} — impossible physiquement"
                    ),
                    occurrences=[compte],
                    montant_ecart=_q(-solde_minimal),
                )
            )
    return constats


def _controle_c10(ecritures: list[EcritureFEC]) -> list[Constat]:
    """R-C10 — banque créditrice sur la plus longue période continue > 30 jours."""
    constats: list[Constat] = []
    if not ecritures:
        return constats
    derniere_date = max(e.ecriture_date for e in ecritures)
    for compte, serie in _cumul_glissant(ecritures, "512").items():
        plus_longue = 0
        debut: datetime | None = None
        for date, cumul in serie:
            if cumul < 0 and debut is None:
                debut = date
            elif cumul >= 0 and debut is not None:
                plus_longue = max(plus_longue, (date - debut).days)
                debut = None
        if debut is not None:
            plus_longue = max(plus_longue, (derniere_date - debut).days)
        if plus_longue > _JOURS_DECOUVERT_C10:
            constats.append(
                Constat(
                    code="C10",
                    gravite="avertissement",
                    message=(
                        f"Compte banque créditeur pendant {plus_longue} jours consécutifs "
                        "(découvert prolongé ou rapprochement manquant)"
                    ),
                    occurrences=[compte],
                )
            )
    return constats


def valider_comptable(
    ecritures: list[EcritureFEC], profil: ProfilDossier | None = None
) -> list[Constat]:
    """
    Contrôles comptables C1-C10 + ECF — R-C1 à R-C10, R-ECF1 à R-ECF4.

    Les anomalies sont des constats, jamais des exceptions ; le moteur agrège
    TOUS les constats (pas d'arrêt au premier bloquant — écart assumé R-A1).

    Args:
        ecritures : Écritures FEC en mémoire (ordre du fichier).
        profil : Contexte dossier optionnel (contrôles conditionnels).

    Returns:
        list[Constat] : Constats, ordre C1 → C10 puis ECF-1 → ECF-4.
    """
    constats: list[Constat] = []
    constats.extend(_controle_c1(ecritures))
    constats.extend(_controle_c2(ecritures))

    # R-C3 — débit ET crédit sur la même ligne.
    doubles = [
        _cle_ecriture(e) for e in ecritures if e.debit > 0 and e.credit > 0
    ]
    if doubles:
        constats.append(
            Constat(
                code="C3",
                gravite="avertissement",
                message="Ligne(s) portant à la fois un débit et un crédit — suspect",
                occurrences=_trier_occurrences(doubles),
            )
        )

    # R-C4 — classe 79 supprimée (PCG 2022-06), JAMAIS bloquant.
    comptes_79 = sorted({e.compte_num for e in ecritures if e.compte_num.startswith("79")})
    if comptes_79:
        constats.append(
            Constat(
                code="C4",
                gravite="avertissement",
                message=(
                    "Comptes de la classe 79 supprimée par le PCG 2022-06 — reclasser "
                    "en 74x/75x/758x (76x/77x selon nature). Le FEC reste valide au sens LPF"
                    + _indications_pcg_79(comptes_79)
                ),
                occurrences=comptes_79,
            )
        )

    constats.extend(_controle_c5(ecritures))

    # R-C6 — dates dans l'exercice (à-nouveaux exclus, R-AN1).
    if profil is None or profil.date_debut_exercice is None or profil.date_fin_exercice is None:
        constats.append(
            Constat(
                code="C6",
                gravite="info",
                message="Bornes d'exercice non fournies — contrôle des dates non évalué",
            )
        )
    else:
        hors_bornes = [
            _cle_ecriture(e)
            for e in ecritures
            if not _est_a_nouveau(e, profil)
            and (
                e.ecriture_date < profil.date_debut_exercice
                or e.ecriture_date > profil.date_fin_exercice
            )
        ]
        if hors_bornes:
            constats.append(
                Constat(
                    code="C6",
                    gravite="avertissement",
                    message="Écriture(s) datée(s) hors des bornes de l'exercice",
                    occurrences=_trier_occurrences(hors_bornes),
                )
            )

    # R-C7 — pièce postérieure à l'écriture.
    pieces_posterieures = [
        _cle_ecriture(e)
        for e in ecritures
        if e.piece_date is not None and e.piece_date > e.ecriture_date
    ]
    if pieces_posterieures:
        constats.append(
            Constat(
                code="C7",
                gravite="info",
                message="Pièce(s) datée(s) après l'écriture",
                occurrences=_trier_occurrences(pieces_posterieures),
            )
        )

    # R-C8 — auxiliaire manquant sur comptes de tiers 401/411.
    sans_auxiliaire = sorted(
        {
            e.compte_num
            for e in ecritures
            if (e.compte_num.startswith("401") or e.compte_num.startswith("411"))
            and not e.compte_aux
        }
    )
    if sans_auxiliaire:
        constats.append(
            Constat(
                code="C8",
                gravite="avertissement",
                message="Compte(s) de tiers 401/411 sans compte auxiliaire",
                occurrences=sans_auxiliaire,
            )
        )

    constats.extend(_controle_c9(ecritures))
    constats.extend(_controle_c10(ecritures))

    # R-ECF1/R-ECF2 — 108/455 vs forme juridique (profil requis).
    if profil is not None and profil.forme_juridique is not None:
        comptes_108 = sorted(
            {e.compte_num for e in ecritures if e.compte_num.startswith("108")}
        )
        if comptes_108 and profil.forme_juridique != "EI":
            constats.append(
                Constat(
                    code="ECF-1",
                    gravite="bloquant",
                    message=(
                        f"Compte de l'exploitant (108) utilisé en "
                        f"{profil.forme_juridique} — réservé à l'entreprise individuelle"
                    ),
                    occurrences=comptes_108,
                )
            )
        comptes_455 = sorted(
            {e.compte_num for e in ecritures if e.compte_num.startswith("455")}
        )
        if comptes_455 and profil.forme_juridique == "EI":
            constats.append(
                Constat(
                    code="ECF-2",
                    gravite="bloquant",
                    message=(
                        "Compte courant d'associé (455) en entreprise individuelle — "
                        "utiliser le compte de l'exploitant (108)"
                    ),
                    occurrences=comptes_455,
                )
            )

    # R-ECF3 — écritures non validées (ordre d'évaluation : None D'ABORD).
    non_validees: list[str] = []
    for e in ecritures:
        if e.valid_date is None or (
            profil is not None
            and profil.date_fin_exercice is not None
            and e.valid_date > profil.date_fin_exercice
        ):
            non_validees.append(_cle_ecriture(e))
    if non_validees:
        gravite_ecf3: Gravite = (
            "bloquant" if profil is not None and profil.exercice_clos else "avertissement"
        )
        constats.append(
            Constat(
                code="ECF-3",
                gravite=gravite_ecf3,
                message=(
                    "Écriture(s) non validée(s) à la clôture — FEC non transmissible en l'état"
                ),
                occurrences=_trier_occurrences(non_validees),
            )
        )

    # R-ECF4 — à-nouveaux déséquilibrés.
    ecritures_an = [e for e in ecritures if _est_a_nouveau(e, profil)]
    if ecritures_an:
        ecart_an = abs(
            sum((e.debit for e in ecritures_an), Decimal("0"))
            - sum((e.credit for e in ecritures_an), Decimal("0"))
        )
        if ecart_an > _SEUIL_ECF4:
            constats.append(
                Constat(
                    code="ECF-4",
                    gravite="bloquant",
                    message=(
                        f"À-nouveaux déséquilibrés de {_q(ecart_an)} € — "
                        "erreur de reprise du bilan N-1"
                    ),
                    occurrences=_trier_occurrences(
                        [e.journal_code for e in ecritures_an]
                    ),
                    montant_ecart=_q(ecart_an),
                )
            )
    return constats
