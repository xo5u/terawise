import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

DATA_FILES = {
    "rain": "rain_monthly.json",
    "ph": "ph_soil.json",
    "temperature": "temperature_monthly_estimate.json",
}


def load_dataset(name: str):
    filename = DATA_FILES.get(name)
    if filename is None:
        raise KeyError(name)
    path = BACKEND_DIR / filename
    with path.open(encoding="utf-8-sig") as file:
        return json.load(file)


def load_all():
    return {name: load_dataset(name) for name in DATA_FILES}