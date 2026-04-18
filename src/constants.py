"""Constants, color palette, building definitions, and configuration."""
from __future__ import annotations

import os

# ─── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR: str = os.path.join(PROJECT_ROOT, "assets")
DATA_DIR: str = os.path.join(PROJECT_ROOT, "data")

# ─── Screen & Tile ───────────────────────────────────────────────────────────
SCREEN_W: int = 1600
SCREEN_H: int = 900
FPS: int = 60
TILE_W: int = 64
TILE_H: int = 32
MAP_COLS: int = 30
MAP_ROWS: int = 30
VISTA_PAD: int = 4  # extra tile rows/cols rendered beyond playable area

# ─── Colors — Persona 4 Palette ─────────────────────────────────────────────
C_BG: tuple[int, int, int] = (8, 4, 28)
C_TILE: tuple[int, int, int] = (30, 22, 50)
C_TILE_LINE: tuple[int, int, int] = (55, 40, 90)
C_TILE_HIGHLIGHT: tuple[int, int, int] = (70, 55, 110)
C_GOLD: tuple[int, int, int] = (255, 215, 0)
C_GOLD_DIM: tuple[int, int, int] = (180, 150, 0)
C_PURPLE: tuple[int, int, int] = (100, 40, 160)
C_DEEP_PURPLE: tuple[int, int, int] = (60, 20, 100)
C_TEAL: tuple[int, int, int] = (0, 200, 180)
C_DARK_RED: tuple[int, int, int] = (160, 30, 40)
C_YELLOW: tuple[int, int, int] = (255, 220, 60)
C_WHITE: tuple[int, int, int] = (240, 240, 255)
C_GREY: tuple[int, int, int] = (140, 140, 160)
C_DARK_PANEL: tuple[int, int, int, int] = (10, 6, 30, 220)
C_HUD_BG: tuple[int, int, int, int] = (12, 8, 32, 200)
C_SCANLINE: tuple[int, int, int, int] = (0, 0, 0, 20)
C_RAIN: tuple[int, int, int, int] = (120, 140, 200, 80)
C_PLAYER_BODY: tuple[int, int, int] = (80, 200, 255)
C_PLAYER_OUTLINE: tuple[int, int, int] = (200, 230, 255)
C_NEON_PURPLE: tuple[int, int, int] = (180, 80, 255)
C_NEON_GOLD: tuple[int, int, int] = (255, 230, 100)
C_CYAN: tuple[int, int, int] = (0, 220, 255)
C_PINK: tuple[int, int, int] = (255, 80, 180)
C_EMERALD: tuple[int, int, int] = (0, 200, 100)
C_ORANGE: tuple[int, int, int] = (255, 160, 40)

# ─── Building Definitions (12 interactive) ───────────────────────────────────
BUILDINGS: list[dict] = [
    {"col": 3,  "row": 3,  "color": C_DEEP_PURPLE,    "accent": C_PURPLE,
     "height": 130, "name": "Velvet Tower",       "id": "velvet",      "size": 2},
    {"col": 14, "row": 3,  "color": (160, 140, 20),   "accent": C_GOLD,
     "height": 95,  "name": "Junes Mall",         "id": "junes",       "size": 2},
    {"col": 24, "row": 3,  "color": (0, 90, 120),     "accent": C_CYAN,
     "height": 110, "name": "Connection Hub",     "id": "connection",  "size": 2},
    {"col": 3,  "row": 14, "color": (0, 120, 110),    "accent": C_TEAL,
     "height": 100, "name": "Skill Arcade",       "id": "skill",       "size": 2},
    {"col": 14, "row": 14, "color": (120, 20, 80),    "accent": C_PINK,
     "height": 105, "name": "Inheritance Lab",    "id": "inherit",     "size": 2},
    {"col": 24, "row": 14, "color": (100, 15, 20),    "accent": C_DARK_RED,
     "height": 115, "name": "Shadow Den",         "id": "shadow",      "size": 2},
    {"col": 5,  "row": 24, "color": (10, 80, 50),     "accent": C_EMERALD,
     "height": 90,  "name": "Block Fortress",     "id": "block",       "size": 2},
    {"col": 14, "row": 24, "color": (140, 90, 10),    "accent": C_ORANGE,
     "height": 120, "name": "Persona Archive",    "id": "archive",     "size": 2},
    # ── New district buildings ──
    {"col": 24, "row": 24, "color": (0, 40, 140),     "accent": (0, 150, 255),
     "height": 100, "name": "Fusion Reactor",     "id": "fusion",      "size": 2},
    {"col": 1,  "row": 6,  "color": (55, 55, 80),     "accent": (180, 190, 220),
     "height": 108, "name": "Oracle Spire",       "id": "oracle",      "size": 2},
    {"col": 22, "row": 7,  "color": (130, 75, 10),    "accent": (255, 180, 50),
     "height": 95,  "name": "Fate Compass",       "id": "fate",        "size": 2},
    {"col": 7,  "row": 21, "color": (10, 95, 60),     "accent": (40, 255, 160),
     "height": 112, "name": "Element Shrine",     "id": "shrine",      "size": 2},
]

# Street lamp positions for atmospheric lighting
LAMP_POSITIONS: list[tuple[int, int]] = [
    (10, 3), (10, 6), (10, 14), (10, 24), (10, 27),
    (19, 3), (19, 6), (19, 14), (19, 24), (19, 27),
    (3, 10), (6, 10), (14, 10), (24, 10), (27, 10),
    (3, 19), (6, 19), (14, 19), (24, 19), (27, 19),
    (10, 10), (10, 19), (19, 10), (19, 19),
    # Near new district buildings
    (8, 6), (8, 7), (22, 8), (23, 8), (4, 22), (3, 21), (26, 24), (26, 26),
]

# Walkway path tiles connecting roads to interactive buildings
PATH_TILES: set[tuple[int, int]] = {
    # Velvet Tower (3,3) → road col 9
    (5, 3), (6, 3), (7, 3), (8, 3),
    # Junes Mall (14,3) → road row 9
    (14, 5), (14, 6), (14, 7), (14, 8),
    # Connection Hub (24,3) → road row 9
    (24, 5), (24, 6), (24, 7), (24, 8),
    # Skill Arcade (3,14) → road col 9
    (5, 14), (6, 14), (7, 14), (8, 14),
    # Shadow Den (24,14) → road col 18
    (21, 14), (22, 14), (23, 14),
    # Block Fortress (5,24) → road row 18
    (5, 21), (5, 22), (6, 21), (6, 22),
    # Persona Archive (14,24) → road row 18
    (14, 21), (14, 22), (15, 21), (15, 22),
    # Fusion Reactor (24,24) → road col 18
    (22, 24), (23, 24), (21, 24),
    # Oracle Spire (1,6) → road col 9
    (3, 6), (4, 6), (5, 6), (6, 6), (7, 6), (8, 6),
    # Fate Compass (22,7) → road col 20
    (21, 7), (21, 8),
    # Element Shrine (7,21) borders road row 20
    (7, 20), (8, 20),
}

# Default 3D view angles per chart
DEFAULT_VIEWS: dict[str, dict[str, int]] = {
    "velvet":     {"elev": 25, "azim": 135},
    "junes":      {"elev": 20, "azim": 225},
    "connection": {"elev": 25, "azim": 140},
    "skill":      {"elev": 20, "azim": 140},
    "inherit":    {"elev": 22, "azim": 210},
    "shadow":     {"elev": 22, "azim": 225},
    "block":      {"elev": 20, "azim": 135},
    "archive":    {"elev": 25, "azim": 150},
    "fusion":     {"elev": 30, "azim": 60},
    "oracle":     {"elev": 25, "azim": 120},
    "fate":       {"elev": 35, "azim": 230},
    "shrine":     {"elev": 25, "azim": 145},
}

# ─── Chart Descriptions (#5 improvement) ────────────────────────────────────
CHART_DESCRIPTIONS: dict[str, str] = {
    "velvet":     "3D scatter cloud mapping Strength × Magic × Endurance for each Persona, colored by Arcana. Larger points indicate higher base levels.",
    "junes":      "Grouped 3D bars showing average stats (STR, MAG, END, AGI, LCK) for the top 10 Arcanas by total average.",
    "connection": "Network scatter visualizing Persona × Skill connections. Each point is a skill learned, positioned by persona index, skill index, and learn level.",
    "skill":      "Scatter plot of skill costs by resource type and element. Point size scales with cost value.",
    "inherit":    "3D bar chart of inheritance type distribution across the top 8 Arcanas.",
    "shadow":     "Grouped bars comparing Weakness, Resistance, and Absorption counts for the top 20 elementally complex Personas.",
    "block":      "Side-by-side 3D bars comparing Block and Reflect counts across all elements.",
    "archive":    "Surface heatmap of average stat values across level tiers, revealing stat growth curves over progression.",
    "fusion":     "Layered 3D radar polygons showing stat profiles of the 6 strongest Personas by total stats.",
    "oracle":     "Stem plot of skill costs for the first 50 skills, colored by elemental affinity.",
    "fate":       "Density surface mapping the relationship between base level and total stats across all Personas.",
    "shrine":     "Bar overview of total affinity counts: Weak, Resist, Reflect, Absorb, and Block across all Personas.",
}

# ─── Minimap Abbreviations (#6 improvement) ─────────────────────────────────
MINIMAP_LABELS: dict[str, str] = {
    "velvet":     "VLV",
    "junes":      "JUN",
    "connection": "CON",
    "skill":      "SKL",
    "inherit":    "INH",
    "shadow":     "SHD",
    "block":      "BLK",
    "archive":    "ARC",
    "fusion":     "FUS",
    "oracle":     "ORC",
    "fate":       "FAT",
    "shrine":     "ELM",
}
