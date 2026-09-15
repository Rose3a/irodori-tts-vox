"""Use the same model/runtime notices as the editor's Help screen."""
import json
from functools import lru_cache
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[2] / "voicevox-editor" / "public"


@lru_cache(maxsize=1)
def dependency_licenses():
    entries = []
    for name in ("licenses.json", "runtime-licenses.json"):
        entries.extend(json.loads((PUBLIC / name).read_text(encoding="utf-8")))
    return entries
