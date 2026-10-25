"""Charge scripts/generer_fec_fictifs.py comme module (les scripts ne sont pas un paquet)."""

import importlib.util
from pathlib import Path

_CHEMIN = Path(__file__).resolve().parent.parent / "scripts" / "generer_fec_fictifs.py"
_SPEC = importlib.util.spec_from_file_location("generer_fec_fictifs", _CHEMIN)
assert _SPEC is not None and _SPEC.loader is not None
generateur = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(generateur)
