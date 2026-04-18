"""CSV data loading for Persona 4 datasets."""
from __future__ import annotations

import os

import pandas as pd

from .constants import DATA_DIR


def load_data() -> dict[str, pd.DataFrame]:
    """Load all 10 CSV files into DataFrames."""
    data: dict[str, pd.DataFrame] = {}
    csv_map: dict[str, str] = {
        "personas": "personas.csv",
        "skills": "skills.csv",
        "skill_connection": "skill_connection.csv",
        "c_weak": "c_weak.csv",
        "c_resists": "c_resists.csv",
        "c_absorbs": "c_absorbs.csv",
        "c_block": "c_block.csv",
        "c_reflects": "c_reflects.csv",
        "c_inherit": "c_inherit.csv",
        "persona4": "persona4.csv",
    }
    for key, filename in csv_map.items():
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            data[key] = pd.read_csv(path)
        else:
            data[key] = pd.DataFrame()
    return data
