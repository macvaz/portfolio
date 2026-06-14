import json
from pathlib import Path

DEFAULT_MAPPING_PATH = Path("data/isin_mapping.json")


def load_isin_mapping(path: Path = DEFAULT_MAPPING_PATH) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_isin_mapping(mapping: dict[str, dict], path: Path = DEFAULT_MAPPING_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2)
        f.write("\n")
