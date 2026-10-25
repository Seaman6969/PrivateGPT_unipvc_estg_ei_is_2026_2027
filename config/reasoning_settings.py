from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from utils.errors import Error

SETTINGS_FILE: Path = Path.home() / ".localgpt" / "rag" / "reasoning.json"
SETTINGS_VERSION: int = 1
ENCODING: str = "utf-8"

@dataclass
class ReasoningSettings:
    use_cot: bool = False
    use_tot: bool = False
    tot_breadth: int = 3
    cot_max_subqueries: int = 4
    reasoning_model: str = "deepseek-r1:7b"
    version: int = SETTINGS_VERSION


def load_reasoning_settings(path: Path = SETTINGS_FILE) -> ReasoningSettings:
    if not path.exists():
        return ReasoningSettings()
    try:
        data = json.loads(path.read_text(encoding=ENCODING))
    except (OSError, json.JSONDecodeError):
        return ReasoningSettings()
    if not isinstance(data, dict):
        return ReasoningSettings()
    known = {f.name for f in fields(ReasoningSettings)}
    try:
        return ReasoningSettings(**{k: v for k, v in data.items() if k in known})
    except TypeError:
        return ReasoningSettings()


def save_reasoning_settings(
    settings: ReasoningSettings, path: Path = SETTINGS_FILE
) -> Error | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(asdict(settings), indent=2), encoding=ENCODING)
    except OSError as exc:
        return Error(message=str(exc))
    return None