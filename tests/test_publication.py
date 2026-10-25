"""
Garde-fou de publication : aucun identifiant réel, aucun nom interne, aucun secret.

Parcourt tous les fichiers texte du dépôt (hors caches). Un seul résultat fait
échouer la CI, donc bloque toute fusion et toute release.
"""

import re
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
EXCLUS = {".git", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
          "build", "dist"}  # fmt: skip
EXTENSIONS = {".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".cfg", ""}
CE_FICHIER = Path(__file__).resolve()

MOTIFS: dict[str, re.Pattern[str]] = {
    "SIREN ou SIRET": re.compile(r"(?<![\w.])\d{3}\s?\d{3}\s?\d{3}(?:\s?\d{5})?(?![\w.])"),
    "IBAN": re.compile(r"\bFR\d{2}(?:\s?[0-9A-Z]{4}){5}"),
    "clé privée": re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
    "jeton GitHub": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    "clé d'API": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "nom interne": re.compile(r"wincorp_common|heimdall|diligences|mimir|spinex|@spec\b", re.I),
}
EMAILS_AUTORISES = {"contact@wincorp.fr"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}")


def _fichiers() -> list[Path]:
    return sorted(
        p
        for p in RACINE.rglob("*")
        if p.is_file()
        and p.resolve() != CE_FICHIER
        and not any(partie in EXCLUS or partie.endswith(".egg-info") for partie in p.parts)
        and p.suffix in EXTENSIONS
    )


@pytest.mark.parametrize("chemin", _fichiers(), ids=lambda p: str(p.relative_to(RACINE)))
def test_aucune_donnee_sensible(chemin: Path) -> None:
    texte = chemin.read_bytes().decode("utf-8", errors="replace")
    for nom, motif in MOTIFS.items():
        trouve = motif.search(texte)
        assert trouve is None, f"{nom} : {trouve.group(0) if trouve else ''}"
    emails = set(EMAIL.findall(texte)) - EMAILS_AUTORISES
    assert not emails, f"adresse e-mail : {sorted(emails)}"
