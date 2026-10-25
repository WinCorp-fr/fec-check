"""
Chargement tolérant d'un Fichier des Écritures Comptables (FEC).

Format de l'art. A.47 A-1 du livre des procédures fiscales : 18 colonnes,
séparateur tabulation ou pipe, UTF-8 ou ISO-8859-15. Les variantes d'en-tête
des logiciels du marché sont tolérées et tracées. `charger_fec` collecte des
faits (erreurs typées et métadonnées) ; `controles.valider_technique` les
transforme en constats.
"""

# Fichier généré, ne pas modifier à la main.
# empreinte-source: 3f7ae462caa9ea3556749ccd64c23d455c86470e95da5cb069d224f39c9fc504

from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_serializer

from fec_check.pydantic_types import DecimalStr

# 18 colonnes FEC obligatoires — noms OFFICIELS de l'art. A.47 A-1 VII.1°
# (vérifié Légifrance, audit #1 : la colonne 14 officielle est bien
# « EcritureLet » AVEC le i ; seules les colonnes 7/8 changent vs v1).
FEC_COLONNES = [
    "JournalCode",
    "JournalLib",
    "EcritureNum",
    "EcritureDate",
    "CompteNum",
    "CompteLib",
    "CompAuxNum",
    "CompAuxLib",
    "PieceRef",
    "PieceDate",
    "EcritureLib",
    "Debit",
    "Credit",
    "EcritureLet",
    "DateLet",
    "ValidDate",
    "Montantdevise",
    "Idevise",
]

# Variantes d'en-tête tolérées {nom reçu: nom officiel} — R4.
FEC_VARIANTES_ENTETE = {
    "CompteAux": "CompAuxNum",
    "CompteAuxLib": "CompAuxLib",
    "EcrtureLet": "EcritureLet",
}

CodeErreurFEC = Literal[
    "FICHIER", "ENCODAGE", "ENTETE", "SEPARATEUR", "COLONNES", "DATE", "MONTANT"
]

# Espaces utilisés comme séparateurs de milliers dans les montants — R11.
_ESPACES_MILLIERS = (" ", " ", " ")

# Colonnes de date et leur caractère obligatoire — R5.
_COLONNES_DATE_OPTIONNELLES = ("PieceDate", "DateLet", "ValidDate")


class ErreurFEC(BaseModel):
    """Erreur de validation/chargement FEC, typée par un discriminant machine."""

    ligne: int = Field(..., description="Numéro de ligne (0 = global, 1 = en-tête)")
    colonne: str | None = Field(default=None, description="Nom de colonne (si applicable)")
    message: str = Field(..., description="Message d'erreur")
    code: CodeErreurFEC | None = Field(
        default=None, description="Discriminant machine (R-T12 côté revision)"
    )


class EcritureFEC(BaseModel):
    """Modèle d'une écriture FEC."""

    journal_code: str = Field(..., description="Code journal")
    journal_lib: str = Field(..., description="Libellé journal")
    ecriture_num: str = Field(..., description="Numéro écriture")
    ecriture_date: datetime = Field(..., description="Date écriture (YYYYMMDD)")
    compte_num: str = Field(..., description="Numéro de compte")
    compte_lib: str = Field(..., description="Libellé compte")
    compte_aux: str | None = Field(default=None, description="Compte auxiliaire")
    compte_aux_lib: str | None = Field(default=None, description="Libellé auxiliaire")
    piece_ref: str | None = Field(default=None, description="Référence pièce")
    piece_date: datetime | None = Field(default=None, description="Date pièce (YYYYMMDD)")
    ecriture_lib: str = Field(..., description="Libellé écriture")
    debit: DecimalStr = Field(default=Decimal("0"), description="Montant débit")
    credit: DecimalStr = Field(default=Decimal("0"), description="Montant crédit")
    ecriture_let: str | None = Field(default=None, description="Lettre de lettrage")
    date_let: datetime | None = Field(default=None, description="Date lettrage (YYYYMMDD)")
    valid_date: datetime | None = Field(
        default=None, description="Date validation (YYYYMMDD, vide = non validée)"
    )
    montant_devise: str | None = Field(default=None, description="Montant devise")
    devise_id: str | None = Field(default=None, description="Code devise")
    ligne_source: int | None = Field(
        default=None, description="Numéro de ligne fichier (en-tête = 1)"
    )

    @field_serializer(
        "ecriture_date", "piece_date", "date_let", "valid_date", when_used="json"
    )
    def _ser_date_fec(self, v: datetime | None) -> str | None:
        """Format FEC (art. A.47 A-1 LPF) : dates en YYYYMMDD."""
        return v.strftime("%Y%m%d") if v else None


class MetadonneesFEC(BaseModel):
    """Faits observés au chargement d'un FEC (jamais de gravité métier ici)."""

    encodage: Literal["utf-8", "iso-8859-15"] = Field(default="utf-8")
    bom: bool = Field(default=False, description="BOM UTF-8 présent")
    separateur_colonnes: Literal["|", "\t"] = Field(
        default="|", description="Séparateur détecté sur l'en-tête (R2 — tab et pipe officiels)"
    )
    separateur_decimal: Literal[".", ","] = Field(default=".")
    fin_ligne: Literal["CRLF", "LF", "mixte", "inconnu"] = Field(default="inconnu")
    variantes_entete: dict[str, str] = Field(
        default_factory=dict, description="{nom reçu: nom officiel}"
    )
    colonnes_surnumeraires: list[str] = Field(default_factory=list)
    entete_inconnues: list[str] = Field(
        default_factory=list, description="Noms inconnus traités par position"
    )
    comptes_digits: int | None = Field(
        default=None, description="Longueur dominante des CompteNum"
    )
    date_min: datetime | None = Field(default=None)
    date_max: datetime | None = Field(default=None)
    nb_lignes: int = Field(default=0, description="Lignes de données non vides lues")
    nb_lignes_zero: int = Field(default=0, description="Lignes à débit ET crédit nuls")
    nb_montants_negatifs: int = Field(
        default=0, description="Valeurs signées normalisées en colonne opposée"
    )
    nb_pieces_incompletes: int = Field(
        default=0, description="Lignes avec PieceRef ou PieceDate vide"
    )
    total_debit: DecimalStr = Field(default=Decimal("0"))
    total_credit: DecimalStr = Field(default=Decimal("0"))


class ChargementFEC(BaseModel):
    """Résultat du chargement tolérant : écritures + erreurs typées + métadonnées."""

    ecritures: list[EcritureFEC] = Field(
        default_factory=list, description="Écritures parsées, ordre du fichier (R12)"
    )
    erreurs: list[ErreurFEC] = Field(default_factory=list)
    meta: MetadonneesFEC = Field(default_factory=MetadonneesFEC)


def _detecter_fin_ligne(contenu: str) -> Literal["CRLF", "LF", "mixte", "inconnu"]:
    """Détecte le style de fins de ligne du fichier — R14."""
    nb_crlf = contenu.count("\r\n")
    nb_lf_seuls = contenu.count("\n") - nb_crlf
    if nb_crlf and nb_lf_seuls:
        return "mixte"
    if nb_crlf:
        return "CRLF"
    if nb_lf_seuls:
        return "LF"
    return "inconnu"


def _normaliser_montant(brut: str) -> tuple[Decimal, bool]:
    """
    Normalise un montant FEC — R11.

    Suppression des espaces de milliers, virgule décimale remplacée par un
    point quand la valeur ne contient aucun point, champ vide traité comme 0.

    Args:
        brut : Valeur brute de la colonne Debit ou Credit.

    Returns:
        tuple[Decimal, bool] : (montant, une virgule a été normalisée).

    Raises:
        InvalidOperation: Valeur non convertible ou ambiguë (point ET virgule).
    """
    valeur = brut.strip()
    for espace in _ESPACES_MILLIERS:
        valeur = valeur.replace(espace, "")
    if not valeur:
        return Decimal("0"), False
    virgule = False
    if "," in valeur:
        if "." in valeur:
            raise InvalidOperation(
                f"montant ambigu (point et virgule) : {brut!r}"
            )
        valeur = valeur.replace(",", ".")
        virgule = True
    return Decimal(valeur), virgule


def _parser_date(
    valeur: str, colonne: str, num_ligne: int, erreurs: list[ErreurFEC]
) -> datetime | None:
    """Parse une date YYYYMMDD ; enregistre une erreur DATE localisée si invalide."""
    if not valeur:
        if colonne in _COLONNES_DATE_OPTIONNELLES:
            return None
        erreurs.append(
            ErreurFEC(
                ligne=num_ligne,
                colonne=colonne,
                message="Date invalide '' (format YYYYMMDD attendu)",
                code="DATE",
            )
        )
        return None
    if len(valeur) != 8:
        erreurs.append(
            ErreurFEC(
                ligne=num_ligne,
                colonne=colonne,
                message=f"Date invalide '{valeur}' (format YYYYMMDD attendu)",
                code="DATE",
            )
        )
        return None
    try:
        return datetime.strptime(valeur, "%Y%m%d")
    except ValueError:
        erreurs.append(
            ErreurFEC(
                ligne=num_ligne,
                colonne=colonne,
                message=f"Date invalide '{valeur}' (date calendaire incorrecte)",
                code="DATE",
            )
        )
        return None


def _lire_contenu(
    filepath: Path, meta: MetadonneesFEC, erreurs: list[ErreurFEC]
) -> str | None:
    """Lit le fichier en UTF-8 (BOM toléré) avec repli ISO-8859-15 — R3."""
    if not filepath.exists():
        erreurs.append(
            ErreurFEC(
                ligne=0,
                message=f"Fichier non trouvé : {filepath}",
                code="FICHIER",
            )
        )
        return None

    brut = filepath.read_bytes()
    if brut.startswith(b"\xef\xbb\xbf"):
        meta.bom = True
        brut = brut[3:]
    try:
        return brut.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        contenu = brut.decode("iso-8859-15")
    except UnicodeDecodeError as exc:  # pragma: no cover — 8859-15 décode tout octet
        erreurs.append(
            ErreurFEC(ligne=0, message=f"Erreur d'encodage : {exc}", code="ENCODAGE")
        )
        return None
    meta.encodage = "iso-8859-15"
    return contenu


def _analyser_entete(
    champs: list[str], meta: MetadonneesFEC, erreurs: list[ErreurFEC]
) -> bool:
    """Analyse l'en-tête reçu : variantes tolérées, inconnus par position — R4."""
    if len(champs) < len(FEC_COLONNES):
        erreurs.append(
            ErreurFEC(
                ligne=1,
                message=(
                    f"En-tête incorrect : {len(champs)} colonnes reçues, "
                    f"{len(FEC_COLONNES)} attendues"
                ),
                code="ENTETE",
            )
        )
        return False

    # strict=False : champs peut être plus long (colonnes surnuméraires, R1)
    for recu, officiel in zip(champs, FEC_COLONNES, strict=False):
        if recu == officiel:
            continue
        if FEC_VARIANTES_ENTETE.get(recu) == officiel:
            meta.variantes_entete[recu] = officiel
        else:
            meta.entete_inconnues.append(recu)
    meta.colonnes_surnumeraires = list(champs[len(FEC_COLONNES) :])
    return True


def charger_fec(filepath: Path) -> ChargementFEC:
    """
    Charge un fichier FEC de manière TOLÉRANTE — R12.

    Ne lève jamais sur un fichier dégradé : chaque ligne rejetée produit une
    `ErreurFEC` typée et localisée, les lignes valides sont parsées dans
    l'ordre du fichier (chaque écriture porte son `ligne_source`).

    Args:
        filepath : Chemin du fichier FEC.

    Returns:
        ChargementFEC : Écritures + erreurs + métadonnées d'observation.

    Example:
        >>> chargement = charger_fec(Path("fec_2025.txt"))
        >>> if not chargement.erreurs:
        ...     print(f"{len(chargement.ecritures)} écritures")
    """
    meta = MetadonneesFEC()
    erreurs: list[ErreurFEC] = []
    ecritures: list[EcritureFEC] = []

    contenu = _lire_contenu(filepath, meta, erreurs)
    if contenu is None:
        return ChargementFEC(ecritures=ecritures, erreurs=erreurs, meta=meta)

    meta.fin_ligne = _detecter_fin_ligne(contenu)
    lignes = contenu.splitlines()
    if not lignes:
        erreurs.append(ErreurFEC(ligne=0, message="Fichier vide", code="FICHIER"))
        return ChargementFEC(ecritures=ecritures, erreurs=erreurs, meta=meta)

    # R2 — tab et pipe sont tous deux officiels (art. A.47 A-1 VIII) :
    # le séparateur le plus fréquent sur l'en-tête gagne, pipe à égalité.
    separateur: Literal["|", "\t"] = (
        "\t" if lignes[0].count("\t") > lignes[0].count("|") else "|"
    )
    meta.separateur_colonnes = separateur
    champs_entete = lignes[0].split(separateur)
    if not _analyser_entete(champs_entete, meta, erreurs):
        return ChargementFEC(ecritures=ecritures, erreurs=erreurs, meta=meta)
    nb_champs_attendu = len(champs_entete)

    virgule_detectee = False
    longueurs_comptes: Counter[int] = Counter()
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for num_ligne, ligne in enumerate(lignes[1:], start=2):
        if not ligne.strip():
            continue  # R9 — lignes vides ignorées
        meta.nb_lignes += 1

        champs = ligne.split(separateur)
        if len(champs) == 1:
            erreurs.append(
                ErreurFEC(
                    ligne=num_ligne,
                    message="Séparateur de colonnes absent",
                    code="SEPARATEUR",
                )
            )
            continue
        if len(champs) != nb_champs_attendu:
            erreurs.append(
                ErreurFEC(
                    ligne=num_ligne,
                    message=(
                        f"Nombre de colonnes incorrect : {len(champs)}, "
                        f"attendu {nb_champs_attendu}"
                    ),
                    code="COLONNES",
                )
            )
            continue

        data = {
            colonne: champs[i].strip() for i, colonne in enumerate(FEC_COLONNES)
        }
        erreurs_ligne: list[ErreurFEC] = []

        ecriture_date = _parser_date(
            data["EcritureDate"], "EcritureDate", num_ligne, erreurs_ligne
        )
        piece_date = _parser_date(data["PieceDate"], "PieceDate", num_ligne, erreurs_ligne)
        date_let = _parser_date(data["DateLet"], "DateLet", num_ligne, erreurs_ligne)
        valid_date = _parser_date(data["ValidDate"], "ValidDate", num_ligne, erreurs_ligne)

        debit = Decimal("0")
        credit = Decimal("0")
        negatifs_ligne = 0
        try:
            debit, virgule_d = _normaliser_montant(data["Debit"])
            credit, virgule_c = _normaliser_montant(data["Credit"])
            virgule_detectee = virgule_detectee or virgule_d or virgule_c
            # R6 — montants signés licites (art. A.47 A-1 XII.2°) : bascule
            # de la valeur absolue dans la colonne opposée, jamais un rejet.
            if debit < 0:
                credit += -debit
                debit = Decimal("0")
                negatifs_ligne += 1
            if credit < 0:
                debit += -credit
                credit = Decimal("0")
                negatifs_ligne += 1
        except (InvalidOperation, ValueError) as exc:
            erreurs_ligne.append(
                ErreurFEC(
                    ligne=num_ligne,
                    message=f"Format montant invalide : {exc}",
                    code="MONTANT",
                )
            )

        if erreurs_ligne:
            erreurs.extend(erreurs_ligne)
            continue

        assert ecriture_date is not None  # garanti : erreur DATE sinon
        meta.nb_montants_negatifs += negatifs_ligne
        if debit == 0 and credit == 0:
            meta.nb_lignes_zero += 1  # R7 — conservée
        if not data["PieceRef"] or not data["PieceDate"]:
            meta.nb_pieces_incompletes += 1

        ecritures.append(
            EcritureFEC(
                journal_code=data["JournalCode"],
                journal_lib=data["JournalLib"],
                ecriture_num=data["EcritureNum"],
                ecriture_date=ecriture_date,
                compte_num=data["CompteNum"],
                compte_lib=data["CompteLib"],
                compte_aux=data["CompAuxNum"] or None,
                compte_aux_lib=data["CompAuxLib"] or None,
                piece_ref=data["PieceRef"] or None,
                piece_date=piece_date,
                ecriture_lib=data["EcritureLib"],
                debit=debit,
                credit=credit,
                ecriture_let=data["EcritureLet"] or None,
                date_let=date_let,
                valid_date=valid_date,
                montant_devise=data["Montantdevise"] or None,
                devise_id=data["Idevise"] or None,
                ligne_source=num_ligne,
            )
        )
        longueurs_comptes[len(data["CompteNum"])] += 1
        total_debit += debit
        total_credit += credit
        if meta.date_min is None or ecriture_date < meta.date_min:
            meta.date_min = ecriture_date
        if meta.date_max is None or ecriture_date > meta.date_max:
            meta.date_max = ecriture_date

    if virgule_detectee:
        meta.separateur_decimal = ","
    if longueurs_comptes:
        # R13 — longueur dominante ; égalité → la plus grande gagne.
        frequence_max = max(longueurs_comptes.values())
        meta.comptes_digits = max(
            longueur
            for longueur, nb in longueurs_comptes.items()
            if nb == frequence_max
        )
    meta.total_debit = total_debit
    meta.total_credit = total_credit
    return ChargementFEC(ecritures=ecritures, erreurs=erreurs, meta=meta)


def valider_fec(filepath: Path) -> list[ErreurFEC]:
    """
    Valide un fichier FEC — interface sacrée v1 (R15).

    Args:
        filepath : Chemin du fichier FEC.

    Returns:
        list[ErreurFEC] : Liste des erreurs (vide si valide).

    Example:
        >>> erreurs = valider_fec(Path("fec_2024.txt"))
        >>> if not erreurs:
        ...     print("FEC valide")
    """
    return charger_fec(filepath).erreurs


def lire_fec(filepath: Path) -> list[EcritureFEC]:
    """
    Lit un fichier FEC et retourne les écritures — interface sacrée v1 (R15).

    Args:
        filepath : Chemin du fichier FEC.

    Returns:
        list[EcritureFEC] : Écritures extraites, ordre du fichier.

    Raises:
        ValueError: Si le fichier n'est pas valide (R8).

    Example:
        >>> ecritures = lire_fec(Path("fec_2024.txt"))
        >>> print(f"Lues {len(ecritures)} écritures")
    """
    chargement = charger_fec(filepath)
    if chargement.erreurs:
        raise ValueError(
            f"Fichier FEC invalide : {len(chargement.erreurs)} erreur(s)"
        )
    return chargement.ecritures
