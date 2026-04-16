import sys
import math
import random
import os
import threading

import pygame
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# ─── Constants ───────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1600, 900
FPS = 60
TILE_W, TILE_H = 64, 32
MAP_COLS, MAP_ROWS = 30, 30
VISTA_PAD = 4  # extra tile rows/cols rendered beyond playable area

# Colors — Persona 4 palette
C_BG = (8, 4, 28)
C_TILE = (30, 22, 50)
C_TILE_LINE = (55, 40, 90)
C_TILE_HIGHLIGHT = (70, 55, 110)
C_GOLD = (255, 215, 0)
C_GOLD_DIM = (180, 150, 0)
C_PURPLE = (100, 40, 160)
C_DEEP_PURPLE = (60, 20, 100)
C_TEAL = (0, 200, 180)
C_DARK_RED = (160, 30, 40)
C_YELLOW = (255, 220, 60)
C_WHITE = (240, 240, 255)
C_GREY = (140, 140, 160)
C_DARK_PANEL = (10, 6, 30, 220)
C_HUD_BG = (12, 8, 32, 200)
C_SCANLINE = (0, 0, 0, 20)
C_RAIN = (120, 140, 200, 80)
C_PLAYER_BODY = (80, 200, 255)
C_PLAYER_OUTLINE = (200, 230, 255)
C_NEON_PURPLE = (180, 80, 255)
C_NEON_GOLD = (255, 230, 100)
C_CYAN = (0, 220, 255)
C_PINK = (255, 80, 180)
C_EMERALD = (0, 200, 100)
C_ORANGE = (255, 160, 40)

# ─── Building Definitions (12 interactive) ───────────────────────────────────
BUILDINGS = [
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

# Ambient buildings (decorative) — dense city fill across the interior
def _deco(c, r, h, seed=0):
    """Generate a decorative building dict with seeded color variation."""
    rng = random.Random(hash((c, r, seed)) + 99)
    base_r = rng.randint(18, 32)
    base_g = rng.randint(12, 24)
    base_b = rng.randint(36, 55)
    acc_r = min(255, base_r + rng.randint(22, 32))
    acc_g = min(255, base_g + rng.randint(16, 28))
    acc_b = min(255, base_b + rng.randint(28, 40))
    return {"col": c, "row": r, "color": (base_r, base_g, base_b),
            "accent": (acc_r, acc_g, acc_b), "height": h, "size": 1}


def _generate_deco_buildings():
    """Procedurally generate dense decorative buildings throughout the city."""
    deco = []
    rng = random.Random(2024)
    # Occupied tiles from interactive buildings
    occupied = set()
    for b in BUILDINGS:
        for dc in range(b["size"]):
            for dr in range(b["size"]):
                occupied.add((b["col"] + dc, b["row"] + dr))
    # Road tiles
    road_tiles = set()
    for c in range(MAP_COLS):
        for r in range(MAP_ROWS):
            if 9 <= c <= 11 or 18 <= c <= 20 or 9 <= r <= 11 or 18 <= r <= 20:
                road_tiles.add((c, r))
    # Fill the interior densely — skip roads and interactive building footprints
    for c in range(MAP_COLS):
        for r in range(MAP_ROWS):
            if (c, r) in occupied or (c, r) in road_tiles:
                continue
            # Check adjacency to interactive buildings (leave generous buffer around huge sprites)
            too_close = False
            for b in BUILDINGS:
                buf = 3 if b.get("id") == "fusion" else 1
                if (b["col"] - buf <= c <= b["col"] + b["size"] + buf - 1 and
                    b["row"] - buf <= r <= b["row"] + b["size"] + buf - 1):
                    too_close = True
                    break
            if too_close:
                continue
            # Place with ~18% probability — less clutter, main buildings stand out
            if rng.random() < 0.18:
                h = rng.randint(30, 95)
                deco.append(_deco(c, r, h))
    # Distant horizon buildings beyond the playable area
    for c in range(-VISTA_PAD, MAP_COLS + VISTA_PAD):
        for r in range(-VISTA_PAD, MAP_ROWS + VISTA_PAD):
            if 0 <= c < MAP_COLS and 0 <= r < MAP_ROWS:
                continue  # inside main area — already handled
            if rng.random() < 0.35:
                h = rng.randint(25, 100)
                deco.append(_deco(c, r, h, seed=1))
    return deco


DECO_BUILDINGS = _generate_deco_buildings()

# Street lamp positions for atmospheric lighting
LAMP_POSITIONS = [
    (10, 3), (10, 6), (10, 14), (10, 24), (10, 27),
    (19, 3), (19, 6), (19, 14), (19, 24), (19, 27),
    (3, 10), (6, 10), (14, 10), (24, 10), (27, 10),
    (3, 19), (6, 19), (14, 19), (24, 19), (27, 19),
    (10, 10), (10, 19), (19, 10), (19, 19),
    # Near new district buildings
    (8, 6), (8, 7), (22, 8), (23, 8), (4, 22), (3, 21), (26, 24), (26, 26),
]

# Walkway path tiles connecting roads to interactive buildings
PATH_TILES = {
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
DEFAULT_VIEWS = {
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


# ─── Isometric Projection ───────────────────────────────────────────────────
def iso_to_screen(col, row, cam_x=0, cam_y=0):
    sx = (col - row) * (TILE_W // 2) + SCREEN_W // 2 + cam_x
    sy = (col + row) * (TILE_H // 2) + 100 + cam_y
    return sx, sy


def screen_to_iso(sx, sy, cam_x=0, cam_y=0):
    sx -= SCREEN_W // 2 + cam_x
    sy -= 100 + cam_y
    col = (sx / (TILE_W // 2) + sy / (TILE_H // 2)) / 2
    row = (sy / (TILE_H // 2) - sx / (TILE_W // 2)) / 2
    return col, row


# ─── Data Loading ────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_data():
    """Load all 10 CSV files into DataFrames."""
    data = {}
    csv_map = {
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


# ─── Chart Renderers (ALL 3D with rotation support) ─────────────────────────
CHART_BG = "#0a0620"


def _style_3d(ax):
    """Apply premium dark styling to any 3D axis."""
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors="#9999bb", labelsize=7)
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor("#222244")
    ax.grid(True, alpha=0.2, color="#555588", linestyle="--", linewidth=0.5)


def render_chart_to_surface(fig):
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    buf = canvas.buffer_rgba()
    size = canvas.get_width_height()
    surf = pygame.image.frombuffer(bytes(buf), size, "RGBA")
    plt.close(fig)
    return surf


# ── 1. Velvet Tower — 3D Scatter Cloud: STR × MAG × END by Arcana ───────────
def chart_velvet(data, elev=25, azim=135):
    df = data["personas"].copy()
    if df.empty:
        return None
    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    arcanas = df["Arcana"].unique()
    cmap = matplotlib.colormaps.get_cmap("plasma").resampled(len(arcanas))
    arcana_map = {a: i for i, a in enumerate(arcanas)}
    colors = [cmap(arcana_map[a]) for a in df["Arcana"]]
    sizes = 20 + (df["Base level"] / df["Base level"].max()) * 80

    ax.scatter(df["Strength"], df["Magic"], df["Endurance"],
               c=colors, s=sizes, alpha=0.85, edgecolors="white",
               linewidths=0.4, depthshade=True)

    # Connect personas within same arcana with faint lines
    for arcana in list(arcanas)[:5]:
        sub = df[df["Arcana"] == arcana].sort_values("Base level")
        if len(sub) >= 2:
            ax.plot(sub["Strength"], sub["Magic"], sub["Endurance"],
                    color=cmap(arcana_map[arcana]), alpha=0.3, linewidth=0.8)

    ax.set_xlabel("Strength", color="#FFD700", fontsize=10, labelpad=10)
    ax.set_ylabel("Magic", color="#FFD700", fontsize=10, labelpad=10)
    ax.set_zlabel("Endurance", color="#FFD700", fontsize=10, labelpad=10)
    ax.set_title("< The Velvet Room -- Persona Stats Cloud >",
                 color="#FFD700", fontsize=13, pad=15, fontweight="bold")
    ax.view_init(elev=elev, azim=azim)

    # Legend
    unique_display = list(arcanas)[:8]
    legend_elems = [Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=cmap(arcana_map[a]), markersize=7, label=a)
                   for a in unique_display]
    ax.legend(handles=legend_elems, loc="upper left", fontsize=6,
              facecolor=CHART_BG, edgecolor="#444466", labelcolor="#ccccee",
              title="Arcana", title_fontsize=7, framealpha=0.9)

    fig.tight_layout(pad=1.5)
    return render_chart_to_surface(fig)


# ── 2. Junes Mall — 3D Bar: Average stats per Arcana ────────────────────────
def chart_junes(data, elev=20, azim=225):
    df = data["personas"].copy()
    if df.empty:
        return None
    stats = ["Strength", "Magic", "Endurance", "Agility", "Luck"]
    grouped = df.groupby("Arcana")[stats].mean()
    grouped["total"] = grouped.sum(axis=1)
    grouped = grouped.nlargest(10, "total").drop(columns=["total"])

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    arcanas = grouped.index.tolist()
    bar_colors = ["#FFD700", "#9B59B6", "#1ABC9C", "#E74C3C", "#3498DB"]

    for i, stat in enumerate(stats):
        xs = [i] * len(arcanas)
        ys = list(range(len(arcanas)))
        zs = [0] * len(arcanas)
        dz = grouped[stat].values
        ax.bar3d(xs, ys, zs, 0.55, 0.55, dz, color=bar_colors[i],
                 alpha=0.85, edgecolor="#ffffff33", label=stat, zsort="average")

    ax.set_xticks(range(len(stats)))
    ax.set_xticklabels(stats, fontsize=7, color="#FFD700", rotation=20)
    ax.set_yticks(range(len(arcanas)))
    ax.set_yticklabels(arcanas, fontsize=6, color="#ccccee")
    ax.set_zlabel("Average", color="#FFD700", fontsize=10, labelpad=10)
    ax.set_title("[ Junes Special ] -- Avg Stats per Arcana (Top 10)",
                 color="#FFD700", fontsize=12, pad=15, fontweight="bold")
    ax.view_init(elev=elev, azim=azim)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.05)
    return render_chart_to_surface(fig)


# ── 3. Connection Hub — 3D Skill Network Scatter ────────────────────────────
def chart_connection(data, elev=25, azim=140):
    sc = data["skill_connection"].copy()
    personas = data["personas"].copy()
    skills = data["skills"].copy()
    if sc.empty or personas.empty or skills.empty:
        return None

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    # Each skill connection as a point in 3D: (P_index, S_index, S_lvl)
    sc_plot = sc.copy()
    sc_plot["S_lvl"] = pd.to_numeric(sc_plot["S_lvl"], errors="coerce").fillna(1)

    # Color by persona arcana
    merged = sc_plot.merge(personas[["Name", "Arcana"]],
                           left_on="P_index", right_on=personas.index, how="left")
    arcanas = merged["Arcana"].dropna().unique()
    cmap = matplotlib.colormaps.get_cmap("cool").resampled(max(1, len(arcanas)))
    arcana_map = {a: i for i, a in enumerate(arcanas)}
    colors = [cmap(arcana_map.get(a, 0)) for a in merged["Arcana"].fillna("Unknown")]

    ax.scatter(merged["P_index"], merged["S_index"], merged["S_lvl"],
               c=colors, s=10, alpha=0.7, edgecolors="white",
               linewidths=0.2, depthshade=True)

    # Draw connection lines for top 5 most-connected personas
    top_personas = sc_plot["P_index"].value_counts().head(5).index
    for p_idx in top_personas:
        sub = sc_plot[sc_plot["P_index"] == p_idx].sort_values("S_lvl")
        if len(sub) >= 2:
            ax.plot(sub["P_index"], sub["S_index"], sub["S_lvl"],
                    alpha=0.4, linewidth=1.0, color="#00DDFF")

    ax.set_xlabel("Persona Idx", color="#00DDFF", fontsize=10, labelpad=10)
    ax.set_ylabel("Skill Idx", color="#00DDFF", fontsize=10, labelpad=10)
    ax.set_zlabel("Learn Level", color="#00DDFF", fontsize=10, labelpad=10)
    ax.set_title(">> Connection Hub -- Persona x Skill Network",
                 color="#00DDFF", fontsize=12, pad=15, fontweight="bold")
    ax.view_init(elev=elev, azim=azim)
    fig.tight_layout(pad=1.5)
    return render_chart_to_surface(fig)


# ── 4. Skill Arcade — 3D Scatter: Cost × Resource × Element ─────────────────
def chart_skill(data, elev=20, azim=140):
    df = data["skills"].copy()
    if df.empty:
        return None
    df["Costs"] = pd.to_numeric(df["Costs"], errors="coerce")
    df = df.dropna(subset=["Costs"])
    df = df[df["Costs"] > 0].copy()

    element_keywords = {
        "Fire": "#FF4500", "Ice": "#00BFFF", "Elec": "#FFFF00",
        "Wind": "#00FF7F", "Light": "#FFFFEE", "Dark": "#CC44FF",
        "Almighty": "#FF69B4", "Phys": "#FF8C00",
    }

    def get_element(effect):
        if not isinstance(effect, str):
            return "Other"
        for kw in element_keywords:
            if kw.lower() in effect.lower():
                return kw
        return "Other"

    df["Element"] = df["Effect"].apply(get_element)
    resource_map = {"% HP": 0, "SP": 1, "Passive": 2}
    df["ResNum"] = df["Resource"].map(resource_map).fillna(3)
    colors = [element_keywords.get(e, "#888888") for e in df["Element"]]
    sizes = 15 + df["Costs"] * 0.5

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    ax.scatter(df.index, df["Costs"], df["ResNum"],
               c=colors, s=sizes, alpha=0.85, edgecolors="white",
               linewidths=0.3, depthshade=True)

    ax.set_xlabel("Skill Index", color="#00E5CC", fontsize=10, labelpad=10)
    ax.set_ylabel("Cost", color="#00E5CC", fontsize=10, labelpad=10)
    ax.set_zlabel("Resource", color="#00E5CC", fontsize=10, labelpad=10)
    ax.set_zticks([0, 1, 2])
    ax.set_zticklabels(["% HP", "SP", "Passive"], fontsize=7, color="#ccccee")
    ax.set_title(":: Skill Arcade -- Cost x Resource x Element",
                 color="#00E5CC", fontsize=12, pad=15, fontweight="bold")
    ax.view_init(elev=elev, azim=azim)

    legend_elems = [Line2D([0], [0], marker="o", color="w",
                   markerfacecolor=c, markersize=7, label=k)
                   for k, c in element_keywords.items()]
    ax.legend(handles=legend_elems, loc="upper left", fontsize=6,
              facecolor=CHART_BG, edgecolor="#444466", labelcolor="#ccccee",
              framealpha=0.9)
    fig.tight_layout(pad=1.5)
    return render_chart_to_surface(fig)


# ── 5. Inheritance Lab — 3D Bar: Inherit types per Arcana ────────────────────
def chart_inherit(data, elev=22, azim=210):
    c_inherit = data["c_inherit"].copy()
    personas = data["personas"].copy()
    if c_inherit.empty or personas.empty:
        return None

    merged = c_inherit.merge(personas[["Name", "Arcana"]],
                             left_on="P_index", right_on=personas.index, how="left")

    top_arcanas = merged["Arcana"].value_counts().head(8).index.tolist()
    filtered = merged[merged["Arcana"].isin(top_arcanas)]
    cross = pd.crosstab(filtered["Arcana"], filtered["Inherit"])
    cross = cross.reindex(top_arcanas)
    inherit_types = cross.columns.tolist()

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    cmap_stack = plt.cm.magma(np.linspace(0.15, 0.85, len(inherit_types)))

    for i, itype in enumerate(inherit_types):
        xs = [i] * len(top_arcanas)
        ys = list(range(len(top_arcanas)))
        zs = [0] * len(top_arcanas)
        dz = cross[itype].values
        ax.bar3d(xs, ys, zs, 0.55, 0.55, dz,
                 color=cmap_stack[i], alpha=0.85,
                 edgecolor="#ffffff22", label=itype, zsort="average")

    ax.set_xticks(range(len(inherit_types)))
    ax.set_xticklabels(inherit_types, fontsize=6, color="#FF88CC", rotation=30)
    ax.set_yticks(range(len(top_arcanas)))
    ax.set_yticklabels(top_arcanas, fontsize=7, color="#ccccee")
    ax.set_zlabel("Count", color="#FF55BB", fontsize=10, labelpad=10)
    ax.set_title("++ Inheritance Lab -- Inherit Types per Arcana",
                 color="#FF55BB", fontsize=12, pad=15, fontweight="bold")
    ax.view_init(elev=elev, azim=azim)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.05)
    return render_chart_to_surface(fig)


# ── 6. Shadow Den — 3D Grouped Bar: Weak / Resist / Absorb ──────────────────
def chart_shadow(data, elev=22, azim=225):
    personas = data["personas"].copy()
    c_weak = data["c_weak"].copy()
    c_resists = data["c_resists"].copy()
    c_absorbs = data["c_absorbs"].copy()
    if personas.empty:
        return None

    weak_counts = c_weak.groupby("P_index").size().rename("Weaknesses") if not c_weak.empty else pd.Series(dtype=int, name="Weaknesses")
    resist_counts = c_resists.groupby("P_index").size().rename("Resistances") if not c_resists.empty else pd.Series(dtype=int, name="Resistances")
    absorb_counts = c_absorbs.groupby("P_index").size().rename("Absorbs") if not c_absorbs.empty else pd.Series(dtype=int, name="Absorbs")

    combined = pd.concat([weak_counts, resist_counts, absorb_counts], axis=1).fillna(0)
    combined["Total"] = combined.sum(axis=1)
    combined = combined.nlargest(20, "Total")

    idx_to_name = dict(zip(personas.iloc[:, 0], personas["Name"]))
    combined["Name"] = [idx_to_name.get(i, f"#{i}") for i in combined.index]

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    names = combined["Name"].tolist()
    categories = ["Weaknesses", "Resistances", "Absorbs"]
    cat_colors = ["#FF4444", "#44AAFF", "#44FF88"]

    for i, cat in enumerate(categories):
        xs = [i] * len(names)
        ys = list(range(len(names)))
        zs = [0] * len(names)
        dz = combined[cat].values
        ax.bar3d(xs, ys, zs, 0.55, 0.55, dz, color=cat_colors[i],
                 alpha=0.85, edgecolor="#ffffff22", label=cat, zsort="average")

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, fontsize=7, color="#FF6666", rotation=10)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=5, color="#ccccee")
    ax.set_zlabel("Count", color="#FF6666", fontsize=10, labelpad=10)
    ax.set_title("<< Shadow Den >> -- Weak / Resist / Absorb (Top 20)",
                 color="#FF6666", fontsize=12, pad=15, fontweight="bold")
    ax.view_init(elev=elev, azim=azim)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.05)
    return render_chart_to_surface(fig)


# ── 7. Block Fortress — 3D Bar: Block & Reflect element counts ──────────────
def chart_block(data, elev=20, azim=135):
    c_block = data["c_block"].copy()
    c_reflects = data["c_reflects"].copy()
    if c_block.empty and c_reflects.empty:
        return None

    # Combine block and reflect into a single 3D viz
    all_elements = set()
    block_dict = {}
    reflect_dict = {}

    if not c_block.empty:
        block_counts = c_block["Block"].value_counts()
        block_dict = block_counts.to_dict()
        all_elements.update(block_counts.index)
    if not c_reflects.empty:
        reflect_counts = c_reflects["Reflects"].value_counts()
        reflect_dict = reflect_counts.to_dict()
        all_elements.update(reflect_counts.index)

    elements = sorted(all_elements)

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    # Block bars (category 0)
    block_vals = [block_dict.get(e, 0) for e in elements]
    xs_b = [0] * len(elements)
    ys_b = list(range(len(elements)))
    ax.bar3d(xs_b, ys_b, [0]*len(elements), 0.6, 0.6, block_vals,
             color="#22DD88", alpha=0.85, edgecolor="#ffffff33",
             label="Block", zsort="average")

    # Reflect bars (category 1)
    reflect_vals = [reflect_dict.get(e, 0) for e in elements]
    xs_r = [1] * len(elements)
    ax.bar3d(xs_r, ys_b, [0]*len(elements), 0.6, 0.6, reflect_vals,
             color="#FF6622", alpha=0.85, edgecolor="#ffffff33",
             label="Reflect", zsort="average")

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Block", "Reflect"], fontsize=9, color="#88FFAA")
    ax.set_yticks(range(len(elements)))
    ax.set_yticklabels(elements, fontsize=7, color="#ccccee")
    ax.set_zlabel("Count", color="#22DD88", fontsize=10, labelpad=10)
    ax.set_title("|| Block Fortress -- Block & Reflect by Element",
                 color="#22DD88", fontsize=12, pad=15, fontweight="bold")
    ax.legend(fontsize=8, facecolor=CHART_BG, edgecolor="#444466",
              labelcolor="#ccccee", loc="upper right")
    ax.view_init(elev=elev, azim=azim)
    fig.tight_layout(pad=1.5)
    return render_chart_to_surface(fig)


# ── 8. Persona Archive — 3D Surface: Level × Stat heatmap ───────────────────
def chart_archive(data, elev=25, azim=150):
    p4 = data["persona4"].copy()
    personas = data["personas"].copy()
    df = p4 if not p4.empty else personas
    if df.empty:
        return None

    stat_cols = ["Strength", "Magic", "Endurance", "Agility", "Luck"]
    available = [s for s in stat_cols if s in df.columns]
    if not available or "Base level" not in df.columns:
        return None

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    # Bin personas by level into groups & compute average stats
    df_sorted = df.sort_values("Base level")
    n_bins = 12
    df_sorted["LevelBin"] = pd.cut(df_sorted["Base level"], bins=n_bins,
                                    labels=False)
    binned = df_sorted.groupby("LevelBin")[available].mean().dropna()

    X = np.arange(len(available))
    Y = np.arange(len(binned))
    X, Y = np.meshgrid(X, Y)
    Z = binned.values

    surf = ax.plot_surface(X, Y, Z, cmap="inferno", alpha=0.85,
                           edgecolor="#ffffff15", linewidth=0.5,
                           antialiased=True)

    # Add wireframe for depth
    ax.plot_wireframe(X, Y, Z, color="#ffffff", alpha=0.08, linewidth=0.3)

    ax.set_xticks(range(len(available)))
    ax.set_xticklabels(available, fontsize=7, color="#FF9900", rotation=20)
    ax.set_ylabel("Level Tier", color="#FF9900", fontsize=10, labelpad=10)
    ax.set_zlabel("Stat Value", color="#FF9900", fontsize=10, labelpad=10)
    ax.set_title("// Persona Archive -- Stat Surface by Level",
                 color="#FF9900", fontsize=12, pad=15, fontweight="bold")

    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, pad=0.08,
                 label="Stat Value")

    ax.view_init(elev=elev, azim=azim)
    fig.tight_layout(pad=1.5)
    return render_chart_to_surface(fig)



# ── 9. Fusion Reactor — 3D Radar Polygon: Top Persona Stat Profiles ─────────
def chart_fusion(data, elev=30, azim=60):
    df = data["personas"].copy()
    if df.empty:
        return None
    stats = ["Strength", "Magic", "Endurance", "Agility", "Luck"]
    df["Total"] = df[stats].sum(axis=1)
    top = df.nlargest(6, "Total")

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    n = len(stats)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    max_v = max(1, df[stats].values.max())
    rc = ["#00AAFF", "#FF44AA", "#44FF88", "#FFD700", "#FF6633", "#AA44FF"]

    for i, (_, p) in enumerate(top.iterrows()):
        vals = np.array([p[s] for s in stats], dtype=float) / max_v
        vals_c = np.append(vals, vals[0])
        ang_c = np.append(angles, angles[0])
        x = np.cos(ang_c) * vals_c
        y = np.sin(ang_c) * vals_c
        z = np.full_like(x, i * 0.7)
        c = rc[i % len(rc)]
        ax.plot(x, y, z, color=c, linewidth=2.0, alpha=0.9,
                label=str(p["Name"])[:12])
        poly = Poly3DCollection([list(zip(x, y, z))],
                                alpha=0.15, facecolor=c, edgecolor=c)
        ax.add_collection3d(poly)
        ax.scatter(x[:-1], y[:-1], z[:-1], color=c, s=18, alpha=0.9,
                   edgecolors="white", linewidths=0.3)

    for j, stat in enumerate(stats):
        ax.text(np.cos(angles[j]) * 1.2, np.sin(angles[j]) * 1.2, -0.3,
                stat[:3], color="#9999bb", fontsize=8, ha="center")

    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-1.3, 1.3)
    ax.set_title("Fusion Reactor -- Top Persona Profiles",
                 color="#00AAFF", fontsize=12, pad=15, fontweight="bold")
    ax.legend(fontsize=6, facecolor=CHART_BG, edgecolor="#444466",
              labelcolor="#ccccee", loc="upper left")
    ax.view_init(elev=elev, azim=azim)
    fig.tight_layout(pad=1.5)
    return render_chart_to_surface(fig)


# ── 10. Oracle Spire — 3D Stem/Lollipop: Skill Costs by Element ─────────────
def chart_oracle(data, elev=25, azim=120):
    df = data["skills"].copy()
    if df.empty:
        return None
    df["Costs"] = pd.to_numeric(df["Costs"], errors="coerce")
    df = df.dropna(subset=["Costs"])
    df = df[df["Costs"] > 0].head(50)
    if df.empty:
        return None

    ek = {"Fire": "#FF4500", "Ice": "#00BFFF", "Elec": "#FFFF00",
          "Wind": "#00FF7F", "Light": "#FFFFAA", "Dark": "#CC44FF",
          "Almighty": "#FF69B4", "Phys": "#FF8C00"}

    def _el(eff):
        if not isinstance(eff, str):
            return "Other"
        for kw in ek:
            if kw.lower() in eff.lower():
                return kw
        return "Other"

    df = df.copy()
    df["Element"] = df["Effect"].apply(_el)
    colors = [ek.get(e, "#888888") for e in df["Element"]]

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    xs = np.arange(len(df))
    zs = np.zeros(len(df))
    dz = df["Costs"].values
    ax.bar3d(xs, zs, zs, 0.3, 0.3, dz, color=colors, alpha=0.75,
             edgecolor="#ffffff11", zsort="average")
    ax.scatter(xs + 0.15, zs + 0.15, dz, c=colors, s=28, alpha=1.0,
               edgecolors="white", linewidths=0.5, depthshade=True)

    ax.set_xlabel("Skill #", color="#B0C0E0", fontsize=10, labelpad=10)
    ax.set_zlabel("Cost", color="#B0C0E0", fontsize=10, labelpad=10)
    ax.set_title("Oracle Spire -- Skill Cost Stems",
                 color="#B0C0E0", fontsize=12, pad=15, fontweight="bold")
    legend_e = [Line2D([0], [0], marker="o", color="w",
                markerfacecolor=c, markersize=7, label=k) for k, c in ek.items()]
    ax.legend(handles=legend_e, loc="upper left", fontsize=5,
              facecolor=CHART_BG, edgecolor="#444466", labelcolor="#ccccee",
              framealpha=0.9)
    ax.view_init(elev=elev, azim=azim)
    fig.tight_layout(pad=1.5)
    return render_chart_to_surface(fig)


# ── 11. Fate Compass — 3D Density Surface: Level × Total Stats ──────────────
def chart_fate(data, elev=35, azim=230):
    df = data["personas"].copy()
    if df.empty:
        return None
    stats = ["Strength", "Magic", "Endurance", "Agility", "Luck"]
    avail = [s for s in stats if s in df.columns]
    if not avail or "Base level" not in df.columns:
        return None
    df["Total"] = df[avail].sum(axis=1)

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    lvl = df["Base level"].values.astype(float)
    total = df["Total"].values.astype(float)
    n_bins = 14
    xe = np.linspace(lvl.min(), lvl.max(), n_bins)
    ye = np.linspace(total.min(), total.max(), n_bins)
    H, xe, ye = np.histogram2d(lvl, total, bins=[xe, ye])
    xc = (xe[:-1] + xe[1:]) / 2
    yc = (ye[:-1] + ye[1:]) / 2
    X, Y = np.meshgrid(xc, yc)
    Z = H.T

    ax.plot_surface(X, Y, Z, cmap="magma", alpha=0.85,
                    edgecolor="#ffffff10", linewidth=0.3, antialiased=True)
    ax.contour(X, Y, Z, zdir="z", offset=-0.5, cmap="magma", alpha=0.3,
               levels=6)

    ax.set_xlabel("Base Level", color="#FFB040", fontsize=10, labelpad=10)
    ax.set_ylabel("Total Stats", color="#FFB040", fontsize=10, labelpad=10)
    ax.set_zlabel("Density", color="#FFB040", fontsize=10, labelpad=10)
    ax.set_title("Fate Compass -- Level x Stats Density",
                 color="#FFB040", fontsize=12, pad=15, fontweight="bold")
    ax.view_init(elev=elev, azim=azim)
    fig.tight_layout(pad=1.5)
    return render_chart_to_surface(fig)


# ── 12. Element Shrine — 3D Scatter: Element Affinity Overview ────────────
def chart_shrine(data, elev=25, azim=145):
    df = data["personas"].copy()
    if df.empty:
        return None

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    tables = {
        "Weak": ("c_weak", "#FF4444"),
        "Resists": ("c_resists", "#4488FF"),
        "Reflects": ("c_reflects", "#FFAA22"),
        "Absorbs": ("c_absorbs", "#44FF88"),
        "Block": ("c_block", "#22DD88"),
    }
    cats = []
    totals = []
    colors = []
    for cat_name, (key, color) in tables.items():
        tbl = data[key]
        if tbl.empty:
            continue
        elem_col = [c for c in tbl.columns if c != "P_index"]
        if not elem_col:
            continue
        cats.append(cat_name)
        totals.append(len(tbl))
        colors.append(color)

    if not cats:
        plt.close(fig)
        return None

    xs = list(range(len(cats)))
    ys = [0] * len(cats)
    zs = [0] * len(cats)
    ax.bar3d(xs, ys, zs, 0.7, 0.7, totals, color=colors,
             alpha=0.88, edgecolor="#ffffff33", zsort="average")

    ax.set_xticks(xs)
    ax.set_xticklabels(cats, fontsize=7, color="#44FFA0", rotation=15)
    ax.set_zlabel("Count", color="#44FFA0", fontsize=10, labelpad=10)
    ax.set_title("Element Shrine -- Affinity Totals",
                 color="#44FFA0", fontsize=12, pad=15, fontweight="bold")
    ax.view_init(elev=elev, azim=azim)
    fig.tight_layout(pad=1.5)
    return render_chart_to_surface(fig)


CHART_GENERATORS = {
    "velvet": chart_velvet,
    "junes": chart_junes,
    "connection": chart_connection,
    "skill": chart_skill,
    "inherit": chart_inherit,
    "shadow": chart_shadow,
    "block": chart_block,
    "archive": chart_archive,
    "fusion": chart_fusion,
    "oracle": chart_oracle,
    "fate": chart_fate,
    "shrine": chart_shrine,
}


# ─── Fast Software 3D Renderer (bypasses matplotlib for rotation) ────────────
# Uses numpy for 3D→2D projection and pygame for polygon drawing.
# Renders a full chart in ~2-5 ms → smooth 60 fps rotation.

class Chart3DScene:
    """Pre-computed 3D geometry for a chart. Built once, rendered every frame."""
    __slots__ = ("faces", "points", "grid_lines", "title", "title_color", "bg")

    def __init__(self, title="", title_color=C_GOLD, bg=(10, 6, 32)):
        self.faces = []         # list of (verts_Nx3 ndarray, fill_rgb, edge_rgb|None)
        self.points = []        # list of (x, y, z, radius, color_rgb)
        self.grid_lines = []    # list of (verts_Nx3 ndarray, color_rgb)
        self.title = title
        self.title_color = title_color
        self.bg = bg

    def add_bar(self, x, y, z, dx, dy, dz, color):
        """Axis-aligned box with shaded faces."""
        c = color[:3]
        top   = tuple(min(255, v + 18) for v in c)
        front = c
        right = tuple(max(0, v - 22) for v in c)
        back  = tuple(max(0, v - 35) for v in c)
        left  = tuple(max(0, v - 42) for v in c)
        edge  = tuple(min(255, v + 55) for v in c)
        x1, y1, z1 = x + dx, y + dy, z + dz
        self.faces.extend([
            (np.array([(x,y1,z),(x1,y1,z),(x1,y1,z1),(x,y1,z1)], dtype=np.float32), top, edge),
            (np.array([(x,y,z1),(x1,y,z1),(x1,y1,z1),(x,y1,z1)], dtype=np.float32), front, edge),
            (np.array([(x1,y,z),(x1,y,z1),(x1,y1,z1),(x1,y1,z)], dtype=np.float32), right, edge),
            (np.array([(x,y,z),(x1,y,z),(x1,y1,z),(x,y1,z)], dtype=np.float32), back, None),
            (np.array([(x,y,z),(x,y,z1),(x,y1,z1),(x,y1,z)], dtype=np.float32), left, None),
        ])

    def add_surface_quad(self, v0, v1, v2, v3, color):
        """Single quad of a 3D surface mesh."""
        self.faces.append((
            np.array([v0, v1, v2, v3], dtype=np.float32),
            color[:3], tuple(min(255, c + 30) for c in color[:3])
        ))

    def add_grid(self, n=5, color=(55, 50, 85)):
        """Ground-plane grid + axis lines."""
        for i in range(n + 1):
            t = -1 + 2 * i / n
            self.grid_lines.append((np.array([(-1, 0, t), (1, 0, t)], dtype=np.float32), color))
            self.grid_lines.append((np.array([(t, 0, -1), (t, 0, 1)], dtype=np.float32), color))
        ax_c = (90, 85, 130)
        self.grid_lines.append((np.array([(-1.1,0,0),(1.1,0,0)], dtype=np.float32), ax_c))
        self.grid_lines.append((np.array([(0,0,-1.1),(0,0,1.1)], dtype=np.float32), ax_c))
        self.grid_lines.append((np.array([(0,0,0),(0,1.4,0)], dtype=np.float32), ax_c))


def _rot_matrix(elev, azim):
    """Exact rotation matching matplotlib's view_init, mapped to Y-up data.

    Matplotlib uses a counterclockwise azimuth convention.  We negate azim
    so that the custom renderer's screen-space matches matplotlib exactly,
    preventing the horizontal mirror / inversion that occurred before.

    Mapping:  data (X, Y-up, Z) → matplotlib axes (Xm=X, Ym=Z, Zm=Y)
        screen_x =  cos(a)*Xm + sin(a)*Ym   →  cos(a)*X + sin(a)*Z
        screen_y = -sin(a)*ce*Xm + cos(a)*ce*Ym + se*Zm
                 = -sin(a)*ce*X  + cos(a)*ce*Z  + se*Y
    """
    a = math.radians(azim - 90)          # offset → match matplotlib rotational direction
    e = math.radians(elev)
    ca, sa = math.cos(a), math.sin(a)
    ce, se = math.cos(e), math.sin(e)
    return np.array([
        [ ca,        0,     sa],
        [-se * sa,   ce,    se * ca],
        [ ce * sa,   se,   -ce * ca],
    ], dtype=np.float32)


def render_scene_fast(scene, elev, azim, w, h, font=None):
    """Render Chart3DScene → pygame Surface.  Typically 2-5 ms."""
    surf = pygame.Surface((w, h))
    surf.fill(scene.bg)
    R = _rot_matrix(elev, azim)
    sc = min(w, h) * 0.33
    cx, cy = w // 2, h // 2 + 20

    # ── Grid lines (always behind everything) ──
    for verts, color in scene.grid_lines:
        rv = verts @ R.T
        pts = [(int(cx + v[0] * sc), int(cy - v[1] * sc)) for v in rv]
        if len(pts) >= 2:
            pygame.draw.lines(surf, color, False, pts, 1)

    # ── Collect faces + points for depth sort ──
    items = []
    for verts, color, edge in scene.faces:
        rv = verts @ R.T
        depth = float(rv[:, 2].mean())
        pts = [(cx + v[0] * sc, cy - v[1] * sc) for v in rv]
        items.append((depth, 0, pts, color, edge))   # 0 = face
    for x, y, z, r, color in scene.points:
        rv = np.array([x, y, z], dtype=np.float32) @ R.T
        items.append((float(rv[2]), 1, (cx + rv[0] * sc, cy - rv[1] * sc), color, r))

    # Painter's algorithm — draw far objects first
    items.sort(key=lambda it: it[0])

    for it in items:
        if it[1] == 0:      # face
            pts, col, edge = it[2], it[3], it[4]
            ipts = [(int(x), int(y)) for x, y in pts]
            if len(ipts) >= 3:
                pygame.draw.polygon(surf, col, ipts)
                if edge:
                    pygame.draw.polygon(surf, edge, ipts, 1)
        else:               # point
            pos, col, r = it[2], it[3], it[4]
            pygame.draw.circle(surf, col, (int(pos[0]), int(pos[1])), max(1, int(r)))
            # Tiny glow
            if r >= 2:
                gs = pygame.Surface((int(r*4), int(r*4)), pygame.SRCALPHA)
                pygame.draw.circle(gs, (*col[:3], 35), (int(r*2), int(r*2)), int(r*2))
                surf.blit(gs, (int(pos[0] - r*2), int(pos[1] - r*2)))

    # Title
    if font and scene.title:
        ts = font.render(scene.title, True, scene.title_color)
        surf.blit(ts, (w // 2 - ts.get_width() // 2, 12))

    return surf


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _norm(vals, lo=-1.0, hi=1.0):
    """Normalize array to [lo, hi]."""
    mn, mx = float(np.nanmin(vals)), float(np.nanmax(vals))
    if mx <= mn:
        return np.full_like(vals, (lo + hi) / 2, dtype=float)
    return lo + (np.asarray(vals, dtype=float) - mn) / (mx - mn) * (hi - lo)


# ─── Scene Builders (one per chart type) ─────────────────────────────────────

def scene_velvet(data):
    """Scatter: STR × MAG × END by Arcana."""
    df = data["personas"]
    if df.empty:
        return None
    scene = Chart3DScene("Velvet Room \u2014 Persona Stats", C_GOLD)
    scene.add_grid()
    arcanas = df["Arcana"].unique()
    cmap = matplotlib.colormaps.get_cmap("plasma").resampled(len(arcanas))
    amap = {a: i for i, a in enumerate(arcanas)}
    xs = -_norm(df["Strength"].values)
    ys = _norm(df["Endurance"].values, 0, 1.3)
    zs = -_norm(df["Magic"].values)
    sizes = 2 + (df["Base level"].values / max(1, df["Base level"].max())) * 4
    for i in range(len(df)):
        c = cmap(amap[df.iloc[i]["Arcana"]])
        scene.points.append((float(xs[i]), float(ys[i]), float(zs[i]),
                             float(sizes[i]),
                             (int(c[0]*255), int(c[1]*255), int(c[2]*255))))
    return scene


def scene_junes(data):
    """Bars: Avg stats per Arcana (top 10)."""
    df = data["personas"]
    if df.empty:
        return None
    scene = Chart3DScene("Junes \u2014 Avg Stats / Arcana", C_GOLD)
    scene.add_grid()
    stats = ["Strength", "Magic", "Endurance", "Agility", "Luck"]
    grp = df.groupby("Arcana")[stats].mean()
    grp["t"] = grp.sum(axis=1)
    grp = grp.nlargest(10, "t").drop(columns=["t"])
    bar_c = [(255,215,0),(155,89,182),(26,188,156),(231,76,60),(52,152,219)]
    mx = max(1, grp.values.max())
    ns, na = len(stats), len(grp)
    for i, s in enumerate(stats):
        for j, arc in enumerate(grp.index):
            v = grp.loc[arc, s]
            dx = 1.8/ns*0.85
            dz = 1.8/na*0.85
            x = 1 - 2*i/ns - 0.03 - dx   # stat group → data X
            z = 1 - 2*j/na - 0.03 - dz   # arcana item → data Z
            scene.add_bar(x, 0, z, dx, v/mx*1.3, dz, bar_c[i])
    return scene


def scene_connection(data):
    """Scatter: Persona × Skill network."""
    sc = data["skill_connection"]
    personas = data["personas"]
    if sc.empty or personas.empty:
        return None
    scene = Chart3DScene("Connection Hub \u2014 P\u00d7S Network", C_CYAN)
    scene.add_grid()
    sc2 = sc.copy()
    sc2["S_lvl"] = pd.to_numeric(sc2["S_lvl"], errors="coerce").fillna(1)
    merged = sc2.merge(personas[["Name", "Arcana"]],
                       left_on="P_index", right_on=personas.index, how="left")
    arcanas = merged["Arcana"].dropna().unique()
    cmap = matplotlib.colormaps.get_cmap("cool").resampled(max(1, len(arcanas)))
    amap = {a: i for i, a in enumerate(arcanas)}
    xs = -_norm(merged["P_index"].values)
    ys = _norm(merged["S_lvl"].values, 0, 1.3)
    zs = -_norm(merged["S_index"].values)
    for i in range(len(merged)):
        a = merged.iloc[i]["Arcana"]
        c = cmap(amap.get(a, 0))
        scene.points.append((float(xs[i]), float(ys[i]), float(zs[i]), 1.5,
                             (int(c[0]*255), int(c[1]*255), int(c[2]*255))))
    return scene


def scene_skill(data):
    """Scatter: Cost × Resource × Element."""
    df = data["skills"].copy()
    if df.empty:
        return None
    df["Costs"] = pd.to_numeric(df["Costs"], errors="coerce")
    df = df.dropna(subset=["Costs"])
    df = df[df["Costs"] > 0].copy()
    if df.empty:
        return None
    scene = Chart3DScene("Skill Arcade \u2014 Cost\u00d7Resource", C_TEAL)
    scene.add_grid()
    ek = {"Fire":(255,69,0),"Ice":(0,191,255),"Elec":(255,255,0),
          "Wind":(0,255,127),"Light":(255,255,200),"Dark":(204,68,255),
          "Almighty":(255,105,180),"Phys":(255,140,0)}
    def _el(e):
        if not isinstance(e, str): return "Other"
        for kw in ek:
            if kw.lower() in e.lower(): return kw
        return "Other"
    df["Elem"] = df["Effect"].apply(_el)
    rm = {"% HP":0,"SP":1,"Passive":2}
    df["RN"] = df["Resource"].map(rm).fillna(3)
    xs = -_norm(df.index.values.astype(float))
    zs = -_norm(df["Costs"].values)
    # Don't force min/max to perfectly hit the roof. RN goes 0, 1, 2. If no passives, max is 1.
    ys = (df["RN"].values / 2.0) * 1.3
    sizes = 2 + df["Costs"].values * 0.02
    for i in range(len(df)):
        c = ek.get(df.iloc[i]["Elem"], (136,136,136))
        scene.points.append((float(xs[i]),float(ys[i]),float(zs[i]),
                             float(min(5, sizes[i])), c))
    return scene


def scene_inherit(data):
    """Bars: Inherit types per Arcana."""
    ci = data["c_inherit"]
    personas = data["personas"]
    if ci.empty or personas.empty:
        return None
    scene = Chart3DScene("Inheritance Lab", C_PINK)
    scene.add_grid()
    merged = ci.merge(personas[["Name","Arcana"]],
                      left_on="P_index", right_on=personas.index, how="left")
    top_a = merged["Arcana"].value_counts().head(8).index.tolist()
    filt = merged[merged["Arcana"].isin(top_a)]
    cross = pd.crosstab(filt["Arcana"], filt["Inherit"]).reindex(top_a)
    itypes = cross.columns.tolist()
    cmap_s = plt.cm.magma(np.linspace(0.15, 0.85, max(1, len(itypes))))
    mx = max(1, cross.values.max())
    ni, na = len(itypes), len(top_a)
    dx = 1.8/ni*0.85
    dz = 1.8/na*0.85
    for i, it in enumerate(itypes):
        c3 = (int(cmap_s[i][0]*255), int(cmap_s[i][1]*255), int(cmap_s[i][2]*255))
        for j in range(na):
            v = cross.iloc[j][it] if it in cross.columns else 0
            x = 1 - 2*i/ni - 0.03 - dx
            z = 1 - 2*j/na - 0.03 - dz
            scene.add_bar(x,0,z, dx, v/mx*1.3, dz, c3)
    return scene


def scene_shadow(data):
    """Bars: Weak / Resist / Absorb (top 20)."""
    personas = data["personas"]
    if personas.empty:
        return None
    scene = Chart3DScene("Shadow Den \u2014 W/R/A", (255,100,100))
    scene.add_grid()
    cw = data["c_weak"]; cr = data["c_resists"]; ca = data["c_absorbs"]
    wc = cw.groupby("P_index").size() if not cw.empty else pd.Series(dtype=int)
    rc = cr.groupby("P_index").size() if not cr.empty else pd.Series(dtype=int)
    ac = ca.groupby("P_index").size() if not ca.empty else pd.Series(dtype=int)
    combined = pd.concat([wc.rename("W"),rc.rename("R"),ac.rename("A")],axis=1).fillna(0)
    combined["T"] = combined.sum(axis=1)
    combined = combined.nlargest(20, "T")
    cats = [("W",(255,68,68)),("R",(68,170,255)),("A",(68,255,136))]
    mx = max(1, combined[["W","R","A"]].values.max())
    nc, np_ = len(cats), len(combined)
    dx = 1.8/nc * 0.8
    dz = 1.8/np_ * 0.85
    for i,(col,c3) in enumerate(cats):
        for j in range(np_):
            v = combined.iloc[j][col]
            x = 1 - 2*i/nc - 0.05 - dx  # mirrored Category axis
            z = 1 - 2*j/np_ - 0.02 - dz # mirrored Persona axis
            scene.add_bar(x,0,z, dx, v/mx*1.3, dz, c3)
    return scene


def scene_block(data):
    """Bars: Block & Reflect by element."""
    cb = data["c_block"]; cref = data["c_reflects"]
    if cb.empty and cref.empty:
        return None
    scene = Chart3DScene("Block Fortress", (34,221,136))
    scene.add_grid()
    elems = set()
    bd, rd = {}, {}
    if not cb.empty:
        bc = cb["Block"].value_counts(); bd = bc.to_dict(); elems.update(bc.index)
    if not cref.empty:
        rc2 = cref["Reflects"].value_counts(); rd = rc2.to_dict(); elems.update(rc2.index)
    elems = sorted(elems)
    ne = max(1, len(elems))
    vals_b = [bd.get(e, 0) for e in elems]
    vals_r = [rd.get(e, 0) for e in elems]
    mx = max(1, max(vals_b + vals_r, default=1))
    for j, e in enumerate(elems):
        dz = 1.2 / ne
        z = 1 - (2*j + 1) / ne - dz / 2
        scene.add_bar(0.05, 0, z, 0.4, vals_b[j]/mx*1.3, dz, (34,221,136))
        scene.add_bar(-0.45, 0, z, 0.4, vals_r[j]/mx*1.3, dz, (255,102,34))
    return scene


def scene_archive(data):
    """Surface: Level × Stat heatmap."""
    p4 = data["persona4"]; personas = data["personas"]
    df = p4 if not p4.empty else personas
    if df.empty:
        return None
    stats = [s for s in ["Strength","Magic","Endurance","Agility","Luck"] if s in df.columns]
    if not stats or "Base level" not in df.columns:
        return None
    scene = Chart3DScene("Persona Archive \u2014 Stat Surface", C_ORANGE)
    scene.add_grid()
    ds = df.sort_values("Base level")
    nb = 12
    ds["LB"] = pd.cut(ds["Base level"], bins=nb, labels=False)
    binned = ds.groupby("LB")[stats].mean().dropna()
    if binned.empty:
        return None
    Z = binned.values
    nr, nc2 = Z.shape
    mx = max(1, Z.max())
    cmap_s = matplotlib.colormaps.get_cmap("inferno")
    for r in range(nr - 1):
        for c2 in range(nc2 - 1):
            v00 = Z[r, c2] / mx;     v10 = Z[r+1, c2] / mx
            v01 = Z[r, c2+1] / mx;   v11 = Z[r+1, c2+1] / mx
            x0 = 1 - 2*c2/(nc2-1);   x1 = 1 - 2*(c2+1)/(nc2-1)
            z0 = 1 - 2*r/(nr-1);     z1 = 1 - 2*(r+1)/(nr-1)
            avg_v = (v00+v10+v01+v11)/4
            c_rgba = cmap_s(avg_v)
            c3 = (int(c_rgba[0]*255), int(c_rgba[1]*255), int(c_rgba[2]*255))
            scene.add_surface_quad(
                (x0, v00*1.3, z0), (x1, v10*1.3, z0),
                (x1, v11*1.3, z1), (x0, v01*1.3, z1), c3)
    return scene


def scene_fusion(data):
    """Polygon: Top Persona stat profiles (radar in 3D)."""
    df = data["personas"]
    if df.empty:
        return None
    scene = Chart3DScene("Fusion Reactor \u2014 Profiles", (0,170,255))
    scene.add_grid()
    stats = ["Strength","Magic","Endurance","Agility","Luck"]
    df2 = df.copy()
    df2["Total"] = df2[stats].sum(axis=1)
    top = df2.nlargest(6, "Total")
    n = len(stats)
    angles = np.linspace(0, 2*np.pi, n, endpoint=False)
    mx = max(1, df[stats].values.max())
    rc = [(0,170,255),(255,68,170),(68,255,136),(255,215,0),(255,102,51),(170,68,255)]
    for i, (_, p) in enumerate(top.iterrows()):
        vals = np.array([p[s] for s in stats], dtype=float) / mx
        vals_c = np.append(vals, vals[0])
        ang_c = np.append(angles, angles[0])
        x_pts = -np.cos(ang_c) * vals_c
        z_pts = -np.sin(ang_c) * vals_c
        y_base = i * 0.35
        verts = [(float(x_pts[j]),y_base,float(z_pts[j])) for j in range(len(x_pts))]
        scene.grid_lines.append((np.array(verts, dtype=np.float32), rc[i % len(rc)]))
        # Fill polygon
        for j in range(n):
            j1 = (j+1) % (n+1)
            scene.faces.append((
                np.array([(0,y_base,0),
                          (float(x_pts[j]),y_base,float(z_pts[j])),
                          (float(x_pts[j1]),y_base,float(z_pts[j1]))], dtype=np.float32),
                (*rc[i%len(rc)][:3],), None
            ))
        for j in range(n):
            scene.points.append((float(x_pts[j]),y_base,float(z_pts[j]),
                                 2.5, rc[i%len(rc)]))
    return scene


def scene_oracle(data):
    """Bars + points: Skill costs by element."""
    df = data["skills"].copy()
    if df.empty:
        return None
    df["Costs"] = pd.to_numeric(df["Costs"], errors="coerce")
    df = df.dropna(subset=["Costs"])
    df = df[df["Costs"] > 0].head(50)
    if df.empty:
        return None
    scene = Chart3DScene("Oracle Spire \u2014 Skill Costs", (176,192,224))
    scene.add_grid()
    ek = {"Fire":(255,69,0),"Ice":(0,191,255),"Elec":(255,255,0),
          "Wind":(0,255,127),"Light":(255,255,170),"Dark":(204,68,255),
          "Almighty":(255,105,180),"Phys":(255,140,0)}
    def _el(e):
        if not isinstance(e,str): return "Other"
        for k in ek:
            if k.lower() in e.lower(): return k
        return "Other"
    df = df.copy()
    df["Elem"] = df["Effect"].apply(_el)
    mx = max(1, df["Costs"].max())
    n = len(df)
    for i in range(n):
        c3 = ek.get(df.iloc[i]["Elem"], (136,136,136))
        dx = 1.8/n*0.85
        x = 1 - 2*i/n - 0.01 - dx
        v = df.iloc[i]["Costs"]
        old_x = -1 + 2*i/n + 0.01
        scene.add_bar(x, 0, -0.2, dx, v/mx*1.3, 0.3, c3)
        scene.points.append((-old_x - 0.9/n, v/mx*1.3, -0.05, 2.5, c3))
    return scene


def scene_fate(data):
    """Surface: Level × Total Stats density."""
    df = data["personas"]
    if df.empty:
        return None
    stats = [s for s in ["Strength","Magic","Endurance","Agility","Luck"] if s in df.columns]
    if not stats or "Base level" not in df.columns:
        return None
    scene = Chart3DScene("Fate Compass \u2014 Density", (255,176,64))
    scene.add_grid()
    df2 = df.copy()
    df2["Total"] = df2[stats].sum(axis=1)
    lvl = df2["Base level"].values.astype(float)
    total = df2["Total"].values.astype(float)
    nb = 14
    xe = np.linspace(lvl.min(), lvl.max(), nb)
    ye = np.linspace(total.min(), total.max(), nb)
    H, xe, ye = np.histogram2d(lvl, total, bins=[xe, ye])
    mx = max(1, H.max())
    cmap_s = matplotlib.colormaps.get_cmap("magma")
    nr, nc2 = H.shape
    for r in range(nr - 1):
        for c2 in range(nc2 - 1):
            v00 = H[r,c2]/mx; v10 = H[r+1,c2]/mx
            v01 = H[r,c2+1]/mx; v11 = H[r+1,c2+1]/mx
            avg = (v00+v10+v01+v11)/4
            c_rgba = cmap_s(avg)
            c3 = (int(c_rgba[0]*255), int(c_rgba[1]*255), int(c_rgba[2]*255))
            z0 = 1 - 2*c2/(nc2-1); z1 = 1 - 2*(c2+1)/(nc2-1)
            x0 = 1 - 2*r/(nr-1);   x1 = 1 - 2*(r+1)/(nr-1)
            scene.add_surface_quad(
                (x0,v00*1.3,z0),(x1,v10*1.3,z0),
                (x1,v11*1.3,z1),(x0,v01*1.3,z1), c3)
    return scene


def scene_shrine(data):
    """Simple bars: 5 affinity totals."""
    scene = Chart3DScene("Element Shrine \u2014 Affinity", (68,255,160))
    scene.add_grid()
    tables = {"Weak":("c_weak",(255,68,68)), "Resists":("c_resists",(68,136,255)),
              "Reflects":("c_reflects",(255,170,34)), "Absorbs":("c_absorbs",(68,255,136)),
              "Block":("c_block",(34,221,136))}
    cats = []; totals = []; colors = []
    for cat,(key,c3) in tables.items():
        t = data[key]
        if t.empty: continue
        cats.append(cat)
        totals.append(len(t))
        colors.append(c3)
    if not cats: return None
    mx = max(1, max(totals))
    n = len(cats)
    for i in range(n):
        dx = 1.6/n
        x = 1 - 2*i/n - 0.05 - dx
        scene.add_bar(x, 0, -0.3, dx, totals[i]/mx*1.3, 0.6, colors[i])
    return scene


SCENE_GENERATORS = {
    "velvet": scene_velvet, "junes": scene_junes,
    "connection": scene_connection, "skill": scene_skill,
    "inherit": scene_inherit, "shadow": scene_shadow,
    "block": scene_block, "archive": scene_archive,
    "fusion": scene_fusion, "oracle": scene_oracle,
    "fate": scene_fate, "shrine": scene_shrine,
}


# ─── Particle Systems ───────────────────────────────────────────────────────
class RainDrop:
    __slots__ = ("x", "y", "speed", "length", "alpha")

    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.randint(-100, SCREEN_W + 100)
        self.y = random.randint(-SCREEN_H, -10)
        self.speed = random.uniform(4, 9)
        self.length = random.randint(8, 22)
        self.alpha = random.randint(40, 100)

    def update(self):
        self.x += self.speed * 0.3
        self.y += self.speed
        if self.y > SCREEN_H + 10:
            self.reset()


class GlowParticle:
    __slots__ = ("x", "y", "vx", "vy", "radius", "alpha", "color",
                 "life", "max_life")

    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.uniform(-50, SCREEN_W + 50)
        self.y = random.uniform(50, SCREEN_H - 50)
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-0.5, -0.1)
        self.radius = random.uniform(1.5, 4)
        self.max_life = random.uniform(3.0, 7.0)
        self.life = random.uniform(0, self.max_life)
        self.color = random.choice([
            (255, 215, 0), (180, 80, 255), (0, 200, 180), (80, 200, 255)
        ])
        self.alpha = 0

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy
        self.life += dt
        progress = self.life / self.max_life
        if progress < 0.3:
            self.alpha = int(60 * (progress / 0.3))
        elif progress > 0.7:
            self.alpha = int(60 * (1.0 - (progress - 0.7) / 0.3))
        else:
            self.alpha = 60
        if self.life >= self.max_life:
            self.reset()


# ─── Floating Diamond Marker ────────────────────────────────────────────────
def draw_diamond(surface, cx, cy, size, color, glow_color, t):
    bob = math.sin(t * 2.5) * 4
    cy_anim = cy + bob
    glow_size = size + 6 + math.sin(t * 3) * 2
    glow_surf = pygame.Surface((int(glow_size * 3), int(glow_size * 3)),
                               pygame.SRCALPHA)
    pygame.draw.polygon(glow_surf, (*glow_color, 40), [
        (glow_size * 1.5, glow_size * 0.5),
        (glow_size * 2.2, glow_size * 1.5),
        (glow_size * 1.5, glow_size * 2.5),
        (glow_size * 0.8, glow_size * 1.5),
    ])
    surface.blit(glow_surf, (cx - glow_size * 1.5, cy_anim - glow_size * 1.5))
    pts = [
        (cx, cy_anim - size),
        (cx + size * 0.7, cy_anim),
        (cx, cy_anim + size),
        (cx - size * 0.7, cy_anim),
    ]
    pygame.draw.polygon(surface, color, pts)
    pygame.draw.polygon(surface, (255, 255, 255, 180), pts, 2)


# ─── Helpers ────────────────────────────────────────────────────────────────
def _lerp_point(p1, p2, t):
    """Linear interpolation between two 2D points."""
    return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)


# ─── Isometric Building Drawing (Enhanced) ──────────────────────────────────
def draw_iso_building(surface, col, row, color, accent, height, size=2,
                      cam_x=0, cam_y=0, neon_pulse=0.0):
    corners = [
        iso_to_screen(col, row, cam_x, cam_y),
        iso_to_screen(col + size, row, cam_x, cam_y),
        iso_to_screen(col + size, row + size, cam_x, cam_y),
        iso_to_screen(col, row + size, cam_x, cam_y),
    ]
    top_corners = [(x, y - height) for x, y in corners]
    rng = random.Random(hash((col, row)) + 42)

    # Bounding box for localized alpha surface
    all_pts = corners + top_corners
    pad = 30
    surf_w, surf_h = surface.get_size()
    bb_x1 = max(0, int(min(p[0] for p in all_pts)) - pad)
    bb_y1 = max(0, int(min(p[1] for p in all_pts)) - pad)
    bb_x2 = min(surf_w, int(max(p[0] for p in all_pts)) + pad)
    bb_y2 = min(surf_h, int(max(p[1] for p in all_pts)) + pad)
    bb_w = max(1, bb_x2 - bb_x1)
    bb_h = max(1, bb_y2 - bb_y1)
    ox, oy = bb_x1, bb_y1

    # Face definitions
    rf = [corners[1], corners[2], top_corners[2], top_corners[1]]
    lf = [corners[2], corners[3], top_corners[3], top_corners[2]]

    # ── Ground neon pool (drawn BEFORE faces so building sits on top) ──
    pool_w = int(size * TILE_W * 0.7)
    pool_h = int(size * TILE_H * 0.5)
    pool_cx = int((corners[0][0] + corners[2][0]) / 2)
    pool_cy = int((corners[0][1] + corners[2][1]) / 2) + 6
    pool_surf = pygame.Surface((pool_w * 2, pool_h * 2), pygame.SRCALPHA)
    pool_a = int(10 + neon_pulse * 8)
    pygame.draw.ellipse(pool_surf, (*accent[:3], pool_a),
                        (0, 0, pool_w * 2, pool_h * 2))
    pygame.draw.ellipse(pool_surf, (*accent[:3], pool_a + 5),
                        (pool_w // 2, pool_h // 2, pool_w, pool_h))
    surface.blit(pool_surf, (pool_cx - pool_w, pool_cy - pool_h))

    # ── Right face: 4 gradient bands (opaque) ──
    n_bands = 4
    for bi in range(n_bands):
        t0, t1 = bi / n_bands, (bi + 1) / n_bands
        dark = 25 + int(45 * t0)
        bc = tuple(max(0, c - dark) for c in color[:3])
        band_pts = [
            _lerp_point(rf[3], rf[0], t0), _lerp_point(rf[2], rf[1], t0),
            _lerp_point(rf[2], rf[1], t1), _lerp_point(rf[3], rf[0], t1),
        ]
        pygame.draw.polygon(surface, bc, band_pts)
    pygame.draw.polygon(surface, accent, rf, 1)

    # ── Left face: 4 gradient bands (opaque) ──
    for bi in range(n_bands):
        t0, t1 = bi / n_bands, (bi + 1) / n_bands
        dark = 45 + int(40 * t0)
        bc = tuple(max(0, c - dark) for c in color[:3])
        band_pts = [
            _lerp_point(lf[3], lf[0], t0), _lerp_point(lf[2], lf[1], t0),
            _lerp_point(lf[2], lf[1], t1), _lerp_point(lf[3], lf[0], t1),
        ]
        pygame.draw.polygon(surface, bc, band_pts)
    pygame.draw.polygon(surface, accent, lf, 1)

    # ── Top face with slight highlight ──
    top_col = tuple(min(255, c + 8) for c in color[:3])
    pygame.draw.polygon(surface, top_col, top_corners)
    pygame.draw.polygon(surface, accent, top_corners, 1)

    # ── Rooftop structures (opaque) ──
    if height >= 65:
        tc_cx = sum(p[0] for p in top_corners) / 4
        tc_cy = sum(p[1] for p in top_corners) / 4
        bw = rng.randint(6, 12)
        bh = rng.randint(5, 10)
        roof_col = tuple(min(255, c + 12) for c in color[:3])
        roof_dark = tuple(max(0, c - 10) for c in roof_col)
        # Small equipment box
        roof_box = [
            (tc_cx - bw / 2, tc_cy - bh),
            (tc_cx + bw / 2, tc_cy - bh),
            (tc_cx + bw / 2, tc_cy),
            (tc_cx - bw / 2, tc_cy),
        ]
        pygame.draw.polygon(surface, roof_dark, roof_box)
        pygame.draw.polygon(surface, accent, roof_box, 1)
        # Antenna
        if rng.random() < 0.6:
            ax = int(tc_cx + rng.randint(-3, 3))
            ay = int(tc_cy - bh)
            ah = rng.randint(6, 16)
            pygame.draw.line(surface, accent, (ax, ay), (ax, ay - ah), 1)
            if neon_pulse > 0.5:
                pygame.draw.circle(surface, (255, 50, 50), (ax, ay - ah), 2)
            else:
                pygame.draw.circle(surface, (120, 20, 20), (ax, ay - ah), 1)
        # Second smaller box for larger buildings
        if height >= 100 and rng.random() < 0.7:
            bw2 = rng.randint(4, 7)
            bh2 = rng.randint(3, 6)
            off_x = rng.choice([-1, 1]) * rng.randint(6, 12)
            box2 = [
                (tc_cx + off_x - bw2 / 2, tc_cy - bh2),
                (tc_cx + off_x + bw2 / 2, tc_cy - bh2),
                (tc_cx + off_x + bw2 / 2, tc_cy),
                (tc_cx + off_x - bw2 / 2, tc_cy),
            ]
            pygame.draw.polygon(surface, roof_col, box2)
            pygame.draw.polygon(surface, accent, box2, 1)

    # ═══ Alpha effects: glow, stripes, windows (one localized surface) ═══
    glow = pygame.Surface((bb_w, bb_h), pygame.SRCALPHA)

    # Horizontal accent stripes on right face
    for st in [0.2, 0.4, 0.6, 0.8]:
        p1 = _lerp_point(rf[3], rf[0], st)
        p2 = _lerp_point(rf[2], rf[1], st)
        pygame.draw.line(glow, (*accent[:3], 45),
                         (int(p1[0] - ox), int(p1[1] - oy)),
                         (int(p2[0] - ox), int(p2[1] - oy)), 1)

    # Horizontal accent stripes on left face
    for st in [0.25, 0.5, 0.75]:
        p1 = _lerp_point(lf[3], lf[0], st)
        p2 = _lerp_point(lf[2], lf[1], st)
        pygame.draw.line(glow, (*accent[:3], 35),
                         (int(p1[0] - ox), int(p1[1] - oy)),
                         (int(p2[0] - ox), int(p2[1] - oy)), 1)

    # Vertical neon accent strip on right face center
    mid_top = _lerp_point(rf[3], rf[2], 0.5)
    mid_bot = _lerp_point(rf[0], rf[1], 0.5)
    for w in range(3):
        a = [45, 28, 12][w]
        pygame.draw.line(glow, (*accent[:3], a),
                         (int(mid_top[0] - ox + w - 1), int(mid_top[1] - oy)),
                         (int(mid_bot[0] - ox + w - 1), int(mid_bot[1] - oy)), 1)

    # Neon edge glow — bloom with multiple passes
    top_local = [(int(p[0] - ox), int(p[1] - oy)) for p in top_corners]
    corners_local = [(int(p[0] - ox), int(p[1] - oy)) for p in corners]
    pulse_a = int(20 + neon_pulse * 35)
    for th in [5, 3, 1]:
        a = max(1, pulse_a // th)
        pygame.draw.polygon(glow, (*accent[:3], a), top_local, th)
    # Vertical edge glow on corners
    for i in range(4):
        for th in [3, 1]:
            a = max(1, pulse_a // (th + 1))
            pygame.draw.line(glow, (*accent[:3], a),
                             corners_local[i], top_local[i], th)

    # Foundation glow at building base
    for i in range(6):
        a = int(55 * (1 - i / 6))
        p1r = (int(corners[1][0] - ox), int(corners[1][1] - oy - i))
        p2r = (int(corners[2][0] - ox), int(corners[2][1] - oy - i))
        pygame.draw.line(glow, (*accent[:3], a), p1r, p2r, 1)
        p1l = (int(corners[2][0] - ox), int(corners[2][1] - oy - i))
        p2l = (int(corners[3][0] - ox), int(corners[3][1] - oy - i))
        pygame.draw.line(glow, (*accent[:3], int(a * 0.7)), p1l, p2l, 1)

    # ── Windows with glow — Right face (face-local projection) ──
    win_rows_r = max(1, int(height / 16))
    win_cols_r = max(1, int(size * 3))
    for wr in range(win_rows_r):
        t_y0 = 0.08 + (wr / win_rows_r) * 0.84
        t_y1 = t_y0 + 0.6 / win_rows_r
        for wc_i in range(win_cols_r):
            if rng.random() < 0.25:
                continue
            t_x0 = 0.10 + (wc_i / win_cols_r) * 0.80
            t_x1 = t_x0 + 0.55 / win_cols_r
            # Compute window quad on the face via bilinear lerp
            top_l = _lerp_point(rf[3], rf[0], t_y0)
            top_r = _lerp_point(rf[2], rf[1], t_y0)
            bot_l = _lerp_point(rf[3], rf[0], t_y1)
            bot_r = _lerp_point(rf[2], rf[1], t_y1)
            w_tl = _lerp_point(top_l, top_r, t_x0)
            w_tr = _lerp_point(top_l, top_r, t_x1)
            w_bl = _lerp_point(bot_l, bot_r, t_x0)
            w_br = _lerp_point(bot_l, bot_r, t_x1)
            wpts = [
                (int(w_tl[0] - ox), int(w_tl[1] - oy)),
                (int(w_tr[0] - ox), int(w_tr[1] - oy)),
                (int(w_br[0] - ox), int(w_br[1] - oy)),
                (int(w_bl[0] - ox), int(w_bl[1] - oy)),
            ]
            lit = rng.random() < 0.80
            if lit:
                warmth = rng.randint(0, 2)
                wc = [(255, 235, 170), (190, 215, 255), (255, 195, 140)][warmth]
                # Glow halo behind window
                wcx = sum(p[0] for p in wpts) // 4
                wcy = sum(p[1] for p in wpts) // 4
                gr = max(4, int(height * 0.04))
                pygame.draw.circle(glow, (*wc, 18), (wcx, wcy), gr)
                pygame.draw.polygon(glow, (*wc, 200), wpts)
                # Window cross dividers
                mid_top = _lerp_point(w_tl, w_tr, 0.5)
                mid_bot = _lerp_point(w_bl, w_br, 0.5)
                mid_left = _lerp_point(w_tl, w_bl, 0.5)
                mid_right = _lerp_point(w_tr, w_br, 0.5)
                pygame.draw.line(glow, (*color[:3], 140),
                                 (int(mid_top[0] - ox), int(mid_top[1] - oy)),
                                 (int(mid_bot[0] - ox), int(mid_bot[1] - oy)), 1)
                pygame.draw.line(glow, (*color[:3], 140),
                                 (int(mid_left[0] - ox), int(mid_left[1] - oy)),
                                 (int(mid_right[0] - ox), int(mid_right[1] - oy)), 1)
            else:
                pygame.draw.polygon(glow, (8, 6, 18, 170), wpts)
                pygame.draw.polygon(glow, (*accent[:3], 30), wpts, 1)

    # ── Windows with glow — Left face (face-local projection) ──
    win_rows_l = max(1, int(height / 18))
    win_cols_l = max(1, int(size * 3))
    for wr in range(win_rows_l):
        t_y0 = 0.08 + (wr / win_rows_l) * 0.84
        t_y1 = t_y0 + 0.55 / win_rows_l
        for wc_i in range(win_cols_l):
            if rng.random() < 0.35:
                continue
            t_x0 = 0.10 + (wc_i / win_cols_l) * 0.80
            t_x1 = t_x0 + 0.50 / win_cols_l
            top_l = _lerp_point(lf[3], lf[0], t_y0)
            top_r = _lerp_point(lf[2], lf[1], t_y0)
            bot_l = _lerp_point(lf[3], lf[0], t_y1)
            bot_r = _lerp_point(lf[2], lf[1], t_y1)
            w_tl = _lerp_point(top_l, top_r, t_x0)
            w_tr = _lerp_point(top_l, top_r, t_x1)
            w_bl = _lerp_point(bot_l, bot_r, t_x0)
            w_br = _lerp_point(bot_l, bot_r, t_x1)
            wpts = [
                (int(w_tl[0] - ox), int(w_tl[1] - oy)),
                (int(w_tr[0] - ox), int(w_tr[1] - oy)),
                (int(w_br[0] - ox), int(w_br[1] - oy)),
                (int(w_bl[0] - ox), int(w_bl[1] - oy)),
            ]
            lit = rng.random() < 0.70
            if lit:
                warmth = rng.randint(0, 2)
                wc = [(220, 205, 150), (170, 195, 235), (215, 175, 130)][warmth]
                wcx = sum(p[0] for p in wpts) // 4
                wcy = sum(p[1] for p in wpts) // 4
                gr = max(3, int(height * 0.035))
                pygame.draw.circle(glow, (*wc, 14), (wcx, wcy), gr)
                pygame.draw.polygon(glow, (*wc, 170), wpts)
            else:
                pygame.draw.polygon(glow, (8, 6, 18, 140), wpts)

    # ── Neon sign / billboard panels on building faces ──
    if height >= 50 and rng.random() < 0.55:
        sign_colors = [
            (255, 50, 80), (50, 200, 255), (255, 200, 50),
            (100, 255, 100), (255, 100, 255), (255, 150, 50),
        ]
        sign_col = sign_colors[rng.randint(0, len(sign_colors) - 1)]
        # Position on right face
        st_top = rng.uniform(0.15, 0.35)
        st_bot = st_top + rng.uniform(0.12, 0.22)
        sl_left = rng.uniform(0.15, 0.3)
        sl_right = sl_left + rng.uniform(0.25, 0.5)
        top_edge_l = _lerp_point(rf[3], rf[0], st_top)
        top_edge_r = _lerp_point(rf[2], rf[1], st_top)
        bot_edge_l = _lerp_point(rf[3], rf[0], st_bot)
        bot_edge_r = _lerp_point(rf[2], rf[1], st_bot)
        s_tl = _lerp_point(top_edge_l, top_edge_r, sl_left)
        s_tr = _lerp_point(top_edge_l, top_edge_r, sl_right)
        s_br = _lerp_point(bot_edge_l, bot_edge_r, sl_right)
        s_bl = _lerp_point(bot_edge_l, bot_edge_r, sl_left)
        sign_pts = [
            (int(s_tl[0] - ox), int(s_tl[1] - oy)),
            (int(s_tr[0] - ox), int(s_tr[1] - oy)),
            (int(s_br[0] - ox), int(s_br[1] - oy)),
            (int(s_bl[0] - ox), int(s_bl[1] - oy)),
        ]
        # Glow halo behind sign
        for expand in [4, 2]:
            exp_pts = []
            cx_s = sum(p[0] for p in sign_pts) / 4
            cy_s = sum(p[1] for p in sign_pts) / 4
            for p in sign_pts:
                dx = p[0] - cx_s
                dy = p[1] - cy_s
                d = max(1, (dx*dx + dy*dy) ** 0.5)
                exp_pts.append((int(p[0] + dx/d*expand),
                                int(p[1] + dy/d*expand)))
            pygame.draw.polygon(glow, (*sign_col, 20), exp_pts)
        # Sign face
        pygame.draw.polygon(glow, (*sign_col, 140), sign_pts)
        pygame.draw.polygon(glow, (255, 255, 255, 60), sign_pts, 1)

    # Second sign on left face for taller buildings
    if height >= 80 and rng.random() < 0.4:
        sign_colors2 = [
            (255, 80, 50), (80, 220, 255), (255, 220, 80),
            (80, 255, 120), (200, 80, 255),
        ]
        sc2 = sign_colors2[rng.randint(0, len(sign_colors2) - 1)]
        st2 = rng.uniform(0.3, 0.5)
        sb2 = st2 + rng.uniform(0.1, 0.18)
        sl2 = rng.uniform(0.2, 0.35)
        sr2 = sl2 + rng.uniform(0.2, 0.4)
        te_l2 = _lerp_point(lf[3], lf[0], st2)
        te_r2 = _lerp_point(lf[2], lf[1], st2)
        be_l2 = _lerp_point(lf[3], lf[0], sb2)
        be_r2 = _lerp_point(lf[2], lf[1], sb2)
        sp2 = [
            (int(_lerp_point(te_l2, te_r2, sl2)[0] - ox),
             int(_lerp_point(te_l2, te_r2, sl2)[1] - oy)),
            (int(_lerp_point(te_l2, te_r2, sr2)[0] - ox),
             int(_lerp_point(te_l2, te_r2, sr2)[1] - oy)),
            (int(_lerp_point(be_l2, be_r2, sr2)[0] - ox),
             int(_lerp_point(be_l2, be_r2, sr2)[1] - oy)),
            (int(_lerp_point(be_l2, be_r2, sl2)[0] - ox),
             int(_lerp_point(be_l2, be_r2, sl2)[1] - oy)),
        ]
        pygame.draw.polygon(glow, (*sc2, 120), sp2)
        pygame.draw.polygon(glow, (255, 255, 255, 50), sp2, 1)

    surface.blit(glow, (bb_x1, bb_y1))
    return top_corners


# ─── Camera ──────────────────────────────────────────────────────────────────
class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.smoothing = 3.5

    def update(self, player_col, player_row, dt):
        px = (player_col - player_row) * (TILE_W // 2) + SCREEN_W // 2
        py = (player_col + player_row) * (TILE_H // 2) + 100
        self.target_x = SCREEN_W // 2 - px
        self.target_y = SCREEN_H // 2 - py
        factor = 1.0 - math.exp(-self.smoothing * dt)
        self.x += (self.target_x - self.x) * factor
        self.y += (self.target_y - self.y) * factor


# ─── Player ──────────────────────────────────────────────────────────────────
def _load_sprite_frames(path, cols=5, rows=5, scale=0.45):
    """Slice a sprite sheet into a flat list of all frames, left-to-right top-to-bottom."""
    sheet = pygame.image.load(path).convert_alpha()
    sw, sh = sheet.get_size()
    fw, fh = sw // cols, sh // rows
    frames = []
    for r in range(rows):
        for c in range(cols):
            rect = pygame.Rect(c * fw, r * fh, fw, fh)
            frame = sheet.subsurface(rect).copy()
            if scale != 1.0:
                nw, nh = int(fw * scale), int(fh * scale)
                frame = pygame.transform.smoothscale(frame, (nw, nh))
            frames.append(frame)
    return frames, int(fw * scale), int(fh * scale)


class Player:
    # Both sprite sheets only face RIGHT.
    # We horizontally flip the sprite to get left-facing.
    #
    # Flip logic (isometric):
    #   dx > 0  (right key)  → face right, no flip
    #   dx < 0  (left key)   → face left,  flip
    #   dy < 0  (up key)     → moving away from camera, face right (no flip)
    #   dy > 0  (down key)   → moving toward camera, face left  (flip)

    WALK_FPS = 12
    IDLE_FPS = 6

    def __init__(self, col, row):
        self.col = float(col)
        self.row = float(row)
        self.speed = 0.14
        self.trail = []

        self.flip      = False
        self.moving    = False
        self.anim_time = 0.0
        self.frame_idx = 0

        base = os.path.dirname(os.path.abspath(__file__))
        idle_path = os.path.join(base, "assets", "Asahi-idle.png")
        walk_path = os.path.join(base, "assets", "Asahi-walk.png")

        self._idle_frames, self._fw, self._fh = _load_sprite_frames(idle_path)
        self._walk_frames, _,  _              = _load_sprite_frames(walk_path)

    def update(self, keys, blocked_cells, dt=0.016):
        dx, dy = 0.0, 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy = self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx = self.speed

        self.moving = (dx != 0 or dy != 0)

        if self.moving:
            if dx > 0:
                self.flip = False      # right → face right
            elif dx < 0:
                self.flip = True       # left  → flip to face left
            else:
                # Pure vertical: up moves away (right shoulder forward), down moves toward (flip)
                self.flip = (dy > 0)

        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707

        new_col = max(0, min(MAP_COLS - 1, self.col + dx))
        new_row = max(0, min(MAP_ROWS - 1, self.row + dy))
        if (int(new_col), int(new_row)) not in blocked_cells:
            self.col = new_col
            self.row = new_row

        fps            = self.WALK_FPS if self.moving else self.IDLE_FPS
        frames         = self._walk_frames if self.moving else self._idle_frames
        self.anim_time += dt * fps
        self.frame_idx  = int(self.anim_time) % len(frames)

        sx, sy = iso_to_screen(self.col, self.row)
        self.trail.append((sx, sy))
        if len(self.trail) > 16:
            self.trail.pop(0)

    def get_screen_pos(self, cam_x=0, cam_y=0):
        return iso_to_screen(self.col, self.row, cam_x, cam_y)

    def draw(self, surface, t, cam_x=0, cam_y=0):
        sx, sy = self.get_screen_pos(cam_x, cam_y)

        for i, (tx_raw, ty_raw) in enumerate(self.trail):
            alpha = int(40 * (i / max(1, len(self.trail))))
            r = max(1, int(5 * (i / max(1, len(self.trail)))))
            trail_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*C_PLAYER_BODY, alpha), (r, r), r)
            surface.blit(trail_surf, (tx_raw + int(cam_x) - r,
                                      ty_raw + int(cam_y) - r))

        shadow_surf = pygame.Surface((36, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 70), (0, 0, 36, 14))
        surface.blit(shadow_surf, (sx - 18, sy - 2))

        glow_r = 22 + math.sin(t * 4) * 3
        glow_surf = pygame.Surface((int(glow_r * 4), int(glow_r * 4)), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*C_PLAYER_BODY, 18),
                           (int(glow_r * 2), int(glow_r * 2)), int(glow_r * 2))
        surface.blit(glow_surf, (sx - glow_r * 2, sy - glow_r * 2 - self._fh // 2))

        frames = self._walk_frames if self.moving else self._idle_frames
        frame  = frames[self.frame_idx]
        if self.flip:
            frame = pygame.transform.flip(frame, True, False)

        blit_x = sx - self._fw // 2
        blit_y = sy - self._fh + 10
        surface.blit(frame, (blit_x, blit_y))

    def near_building(self, buildings, threshold=2.5):
        for b in buildings:
            center_col = b["col"] + b["size"] / 2
            center_row = b["row"] + b["size"] / 2
            dist = math.sqrt((self.col - center_col) ** 2 +
                             (self.row - center_row) ** 2)
            if dist < threshold:
                return b
        return None


# ─── Main Game ───────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(
            "THE MIDNIGHT CHANNEL — Persona 4 Data Explorer")
        self.clock = pygame.time.Clock()

        # Fonts — sized for readability
        self.font_title = pygame.font.SysFont("Segoe UI", 30, bold=True)
        self.font_hud = pygame.font.SysFont("Segoe UI", 18)
        self.font_prompt = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.font_panel_title = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.font_panel_hint = pygame.font.SysFont("Segoe UI", 14)
        self.font_minimap = pygame.font.SysFont("Segoe UI", 11)
        self.font_stat = pygame.font.SysFont("Segoe UI", 14)
        self.font_zone = pygame.font.SysFont("Segoe UI", 22, bold=True)

        # Data
        self.data = load_data()

        # Extra building sprites — 6 variants sliced from sheet (3 cols × 2 rows)
        try:
            _eb = pygame.image.load(os.path.join("assets", "Extra_Buildings.png")).convert_alpha()
            _ew, _eh = _eb.get_size()
            _cw, _rh = _ew // 3, _eh // 2
            self.extra_building_sprites = [
                _eb.subsurface((_cw * c, _rh * r, _cw, _rh))
                for r in range(2) for c in range(3)
            ]
        except Exception:
            self.extra_building_sprites = []

        # Lamp sprite
        try:
            self.lamp_sprite = pygame.image.load(
                os.path.join("assets", "Lamps.png")).convert_alpha()
        except Exception:
            self.lamp_sprite = None

        # Distant city background image
        try:
            _dcb = pygame.image.load(
                os.path.join("assets", "Distant_City_Background.png")).convert_alpha()
            # Scale to fill screen width, anchor to lower 40% of screen
            _scale = SCREEN_W / _dcb.get_width()
            _dh = int(_dcb.get_height() * _scale)
            self.city_bg_sprite = pygame.transform.smoothscale(_dcb, (SCREEN_W, _dh))
        except Exception:
            self.city_bg_sprite = None

        # Building sprites — keyed by building "id"
        _SPRITE_MAP = {
            "velvet":     "Velvet_Tower.png",
            "junes":      "Junes.png",
            "connection": "Connection_Hub.png",
            "skill":      "Skill_Arcade.png",
            "inherit":    "Inheritance_Lab.png",
            "shadow":     "Shadow_Den.png",
            "block":      "Block_Fortress.png",
            "archive":    "Persona_Archive.png",
            "fusion":     "Fusion_Reactor.png",
            "oracle":     "Oracle_Spire.png",
            "fate":       "Fate_Compass.png",
            "shrine":     "Element_Shrine.png",
        }
        self.building_sprites = {}
        for bid, fname in _SPRITE_MAP.items():
            path = os.path.join("assets", fname)
            try:
                img = pygame.image.load(path).convert_alpha()
                self.building_sprites[bid] = img
            except Exception:
                pass

        # Camera & Player
        self.camera = Camera()
        self.player = Player(10.0, 10.0)

        # Precompute blocked cells for O(1) collision
        self._blocked_cells = set()
        for b in BUILDINGS + DECO_BUILDINGS:
            for dc in range(b["size"]):
                for dr in range(b["size"]):
                    self._blocked_cells.add((b["col"] + dc, b["row"] + dr))

        # Particles
        self.rain = [RainDrop() for _ in range(200)]
        self.glow_particles = [GlowParticle() for _ in range(50)]

        # Pre-render distant backdrop
        self.backdrop = self._build_backdrop()

        # Pre-render entire city to cached surface (tiles + buildings)
        self._build_city_cache()

        # ── UI PNG assets ──────────────────────────────────────────────────────
        def load_ui_asset(fname, crop=True):
            path = os.path.join("assets", fname)
            if not os.path.exists(path): return None
            try:
                img = pygame.image.load(path).convert_alpha()
                if crop:
                    mask = pygame.mask.from_surface(img)
                    rects = mask.get_bounding_rects()
                    if rects:
                        r_u = rects[0]
                        for r in rects[1:]:
                            r_u.union_ip(r)
                        if r_u.width > 0 and r_u.height > 0:
                            img = img.subsurface(r_u).copy()
                return img
            except Exception:
                return None

        self._vignette_png = None
        self._hud_png = None
        self._prompt_bubble_png = None

        # Map Frame 
        _mapf = load_ui_asset("Map_Frame.png")
        if _mapf:
            c_color = _mapf.get_at((_mapf.get_width() // 2, _mapf.get_height() // 2))
            _mapf.set_colorkey(c_color)
            self._map_frame_png = _mapf
        else:
            self._map_frame_png = None

        # Pre-render vignette overlay (fallback programmatic)
        self._vignette = self._build_vignette()

        # Scanline overlay
        self.scanline_surf = pygame.Surface(
            (SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for y in range(0, SCREEN_H, 3):
            pygame.draw.line(self.scanline_surf, C_SCANLINE,
                             (0, y), (SCREEN_W, y))

        # Fog — thick bottom haze + subtle top haze
        self.fog_surf = pygame.Surface(
            (SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for i in range(200):
            alpha = int(55 * (i / 200))
            pygame.draw.line(self.fog_surf, (18, 10, 45, alpha),
                             (0, SCREEN_H - i), (SCREEN_W, SCREEN_H - i))
        # Top atmospheric haze
        for i in range(90):
            alpha = int(22 * (1 - i / 90))
            pygame.draw.line(self.fog_surf, (20, 12, 48, alpha),
                             (0, i), (SCREEN_W, i))

        # Chart panel state
        self.panel_open = False
        self.panel_slide = 0.0
        self.panel_target = 0.0
        self.current_chart_surface = None
        self.current_building_name = ""
        self.current_building_accent = C_GOLD
        self.current_building_id = ""

        # 3D Chart rotation state
        self.chart_azim = 0.0
        self.chart_elev = 0.0
        self.chart_rotate_speed = 80.0   # degrees per second when holding key
        self.chart_scene = None          # Chart3DScene for fast rotation rendering
        self.scene_cache = {}            # building_id → Chart3DScene

        # Chart cache: keyed by (building_id, elev_rounded, azim_rounded)
        self.chart_cache = {}

        # Rotation key hold tracking
        self.rotating_left = False
        self.rotating_right = False
        self.rotating_up = False
        self.rotating_down = False

        # Background chart rendering (avoids blocking game loop)
        self._bg_thread = None
        self._bg_result = None   # (cache_key, surface) when render completes
        self._bg_lock = threading.Lock()

        # Time
        self.t = 0.0
        self.running = True

        # Stats
        self.total_personas = len(self.data.get("personas", pd.DataFrame()))
        self.total_skills = len(self.data.get("skills", pd.DataFrame()))
        self.buildings_visited = set()

    # ── Angle step for cache rounding (10° = 36 frames per full rotation) ──
    _ANGLE_STEP = 10

    def _get_cache_key(self):
        """Cache key rounded to nearest _ANGLE_STEP degrees."""
        s = self._ANGLE_STEP
        e = round(self.chart_elev / s) * s
        a = round(self.chart_azim / s) * s % 360
        return (self.current_building_id, e, a)

    def _render_current_chart(self):
        """Synchronous chart render (used only for initial panel open)."""
        key = self._get_cache_key()
        if key in self.chart_cache:
            self.current_chart_surface = self.chart_cache[key]
            return
        gen = CHART_GENERATORS.get(self.current_building_id)
        if gen:
            _, e, a = key
            surf = gen(self.data, elev=e, azim=a)
            if surf is not None:
                self._cache_put(key, surf)
                self.current_chart_surface = surf

    def _find_nearest_cached(self):
        """Find the closest cached surface to the current angle (instant)."""
        s = self._ANGLE_STEP
        e = round(self.chart_elev / s) * s
        a_cur = round(self.chart_azim / s) * s % 360
        bid = self.current_building_id
        # Try exact match first
        exact = (bid, e, a_cur)
        if exact in self.chart_cache:
            return self.chart_cache[exact]
        # Expand outward in 10° steps up to ±50°
        for offset in range(s, 60, s):
            for sign in (1, -1):
                test_a = (a_cur + sign * offset) % 360
                key = (bid, e, test_a)
                if key in self.chart_cache:
                    return self.chart_cache[key]
        return None

    def _show_nearest_cached(self):
        """Instantly display the closest cached angle (zero overhead)."""
        key = self._get_cache_key()
        if key in self.chart_cache:
            self.current_chart_surface = self.chart_cache[key]
            return
        nearest = self._find_nearest_cached()
        if nearest is not None:
            self.current_chart_surface = nearest

    def _request_chart_render_async(self):
        """Queue a single bg render for current angle (called on key release)."""
        key = self._get_cache_key()
        if key in self.chart_cache:
            self.current_chart_surface = self.chart_cache[key]
            return
        # Don't pile up threads
        if self._bg_thread is not None and self._bg_thread.is_alive():
            return
        gen = CHART_GENERATORS.get(self.current_building_id)
        if gen:
            _, e, a = key
            self._bg_thread = threading.Thread(
                target=self._bg_render_chart,
                args=(gen, e, a, key),
                daemon=True,
            )
            self._bg_thread.start()

    def _bg_render_chart(self, gen, elev, azim, cache_key):
        """Background thread: render one chart frame."""
        try:
            surf = gen(self.data, elev=elev, azim=azim)
        except Exception:
            surf = None
        with self._bg_lock:
            self._bg_result = (cache_key, surf)

    def _collect_bg_render(self):
        """Main-thread: pick up completed bg render if it matches current building."""
        with self._bg_lock:
            if self._bg_result is None:
                return
            key, surf = self._bg_result
            self._bg_result = None
        if surf is not None:
            self._cache_put(key, surf)
            # Only display if this result is for the CURRENT building
            if key[0] == self.current_building_id:
                self.current_chart_surface = surf

    def _cache_put(self, key, surf):
        """Store surface in chart cache with eviction."""
        if len(self.chart_cache) > 200:
            evict = list(self.chart_cache.keys())[:100]
            for k in evict:
                del self.chart_cache[k]
        self.chart_cache[key] = surf

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.panel_open:
                        self.panel_target = 0.0
                        self.panel_open = False
                        self.rotating_left = False
                        self.rotating_right = False
                        self.rotating_up = False
                        self.rotating_down = False
                    else:
                        self.running = False

                elif event.key in (pygame.K_e, pygame.K_RETURN):
                    if not self.panel_open:
                        nearby = self.player.near_building(BUILDINGS)
                        if nearby:
                            self.current_building_name = nearby["name"]
                            self.current_building_accent = nearby["accent"]
                            self.current_building_id = nearby["id"]
                            self.buildings_visited.add(nearby["id"])

                            # Reset rotation to default for this chart
                            defaults = DEFAULT_VIEWS.get(nearby["id"],
                                                         {"elev": 25, "azim": 135})
                            self.chart_elev = defaults["elev"]
                            self.chart_azim = defaults["azim"]

                            # Discard any stale bg render from previous building
                            with self._bg_lock:
                                self._bg_result = None

                            # Build fast 3D scene (cached per building)
                            bid = nearby["id"]
                            if bid not in self.scene_cache:
                                sg = SCENE_GENERATORS.get(bid)
                                if sg:
                                    self.scene_cache[bid] = sg(self.data)
                            self.chart_scene = self.scene_cache.get(bid)

                            # Show fast 3D scene INSTANTLY (no matplotlib blocking)
                            if self.chart_scene is not None:
                                self.current_chart_surface = render_scene_fast(
                                    self.chart_scene, self.chart_elev,
                                    self.chart_azim, 900, 600,
                                    self.font_panel_title)
                            else:
                                self.current_chart_surface = None

                            # Queue high-quality matplotlib render in background
                            self._request_chart_render_async()
                            self.panel_open = True
                            self.panel_target = 1.0

                # Chart rotation keys (hold to rotate)
                if self.panel_open:
                    if event.key == pygame.K_LEFT:
                        self.rotating_left = True
                    elif event.key == pygame.K_RIGHT:
                        self.rotating_right = True
                    elif event.key == pygame.K_UP:
                        self.rotating_up = True
                    elif event.key == pygame.K_DOWN:
                        self.rotating_down = True

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    self.rotating_left = False
                    if self.panel_open:
                        self._request_chart_render_async()
                elif event.key == pygame.K_RIGHT:
                    self.rotating_right = False
                    if self.panel_open:
                        self._request_chart_render_async()
                elif event.key == pygame.K_UP:
                    self.rotating_up = False
                    if self.panel_open:
                        self._request_chart_render_async()
                elif event.key == pygame.K_DOWN:
                    self.rotating_down = False
                    if self.panel_open:
                        self._request_chart_render_async()

    def update(self, dt):
        self.t += dt
        self.camera.update(self.player.col, self.player.row, dt)

        if not self.panel_open:
            keys = pygame.key.get_pressed()
            self.player.update(keys, self._blocked_cells, dt)

        # Handle smooth chart rotation (non-blocking)
        if self.panel_open:
            rotated = False
            if self.rotating_left:
                self.chart_azim += self.chart_rotate_speed * dt   # LEFT → rotate left
                rotated = True
            if self.rotating_right:
                self.chart_azim -= self.chart_rotate_speed * dt   # RIGHT → rotate right
                rotated = True
            if self.rotating_up:
                self.chart_elev = min(60, self.chart_elev + self.chart_rotate_speed * dt * 0.5)  # UP → tilt up
                rotated = True
            if self.rotating_down:
                self.chart_elev = max(5, self.chart_elev - self.chart_rotate_speed * dt * 0.5)   # DOWN → tilt down
                rotated = True

            if rotated:
                self.chart_azim %= 360
                # Render with fast 3D engine (~2-5ms, no matplotlib)
                if self.chart_scene is not None:
                    self.current_chart_surface = render_scene_fast(
                        self.chart_scene, self.chart_elev, self.chart_azim,
                        900, 600, self.font_panel_title)
                else:
                    self._show_nearest_cached()

            # Collect any finished background renders
            self._collect_bg_render()

        # Rain
        for drop in self.rain:
            drop.update()

        # Glow particles
        for p in self.glow_particles:
            p.update(dt)

        # Panel slide
        slide_speed = 5.0 * dt
        if self.panel_slide < self.panel_target:
            self.panel_slide = min(self.panel_target,
                                   self.panel_slide + slide_speed)
        elif self.panel_slide > self.panel_target:
            self.panel_slide = max(self.panel_target,
                                   self.panel_slide - slide_speed)

    def _build_backdrop(self):
        """Pre-render the distant landscape backdrop (mountains, stars, city silhouette)."""
        bg = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        # ── Gradient sky ──
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            r = int(8 + t * 12)
            g = int(4 + t * 14)
            b = int(28 + t * 30)
            pygame.draw.line(bg, (r, g, b), (0, y), (SCREEN_W, y))
        # ── Stars ──
        star_rng = random.Random(42)
        for _ in range(220):
            sx = star_rng.randint(0, SCREEN_W)
            sy = star_rng.randint(0, int(SCREEN_H * 0.65))
            brightness = star_rng.randint(80, 220)
            size = star_rng.choice([1, 1, 1, 2])
            tint = star_rng.choice([
                (brightness, brightness, int(brightness * 0.9)),
                (int(brightness * 0.85), brightness, brightness),
                (brightness, int(brightness * 0.8), brightness),
            ])
            pygame.draw.circle(bg, tint, (sx, sy), size)
            if brightness > 160 and size >= 2:
                gs = pygame.Surface((12, 12), pygame.SRCALPHA)
                pygame.draw.circle(gs, (*tint, 25), (6, 6), 6)
                bg.blit(gs, (sx - 6, sy - 6))
        # ── Subtle aurora bands ──
        aurora_rng = random.Random(333)
        for _ in range(5):
            ay1 = aurora_rng.randint(int(SCREEN_H * 0.08), int(SCREEN_H * 0.38))
            aw = aurora_rng.randint(200, 600)
            ah = aurora_rng.randint(40, 100)
            ax_pos = aurora_rng.randint(0, SCREEN_W - aw)
            aurora_s = pygame.Surface((aw, ah), pygame.SRCALPHA)
            ac = aurora_rng.choice([
                (80, 200, 120, 8), (100, 150, 255, 6),
                (180, 100, 255, 5), (0, 200, 220, 7),
            ])
            for ayi in range(ah):
                t_a = 1.0 - abs(2 * ayi / ah - 1)
                a_v = int(ac[3] * t_a * t_a)
                pygame.draw.line(aurora_s, (*ac[:3], a_v), (0, ayi), (aw, ayi))
            bg.blit(aurora_s, (ax_pos, ay1))
        # ── Distant mountain layers ──
        for layer in range(3):
            y_base = int(SCREEN_H * (0.35 + layer * 0.12))
            col_val = 12 + layer * 6
            alpha = 100 + layer * 40
            pts = [(0, SCREEN_H)]
            mtn_rng = random.Random(100 + layer)
            x = 0
            while x <= SCREEN_W:
                peak_h = mtn_rng.randint(30, 120 - layer * 25)
                pts.append((x, y_base - peak_h))
                x += mtn_rng.randint(40, 120)
            pts.append((SCREEN_W, y_base))
            pts.append((SCREEN_W, SCREEN_H))
            mtn_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            col_b = min(255, col_val + 25 + layer * 8)
            pygame.draw.polygon(mtn_surf,
                                (col_val, col_val - 2, col_b, alpha), pts)
            bg.blit(mtn_surf, (0, 0))
        # ── Distant city background image ──
        if self.city_bg_sprite is not None:
            _cw, _ch = self.city_bg_sprite.get_size()
            # Anchor bottom of image to ~60% screen height
            _cy = int(SCREEN_H * 0.60) - _ch
            # Tint to match night palette
            _tinted = self.city_bg_sprite.copy()
            _tinted.fill((20, 10, 50, 60), special_flags=pygame.BLEND_RGBA_ADD)
            bg.blit(_tinted, (0, _cy))
        else:
            # Fallback procedural silhouette
            sil_rng = random.Random(777)
            sil_y = int(SCREEN_H * 0.55)
            for sx in range(0, SCREEN_W, 12):
                bh = sil_rng.randint(8, 65)
                bw = sil_rng.randint(6, 14)
                col_v = sil_rng.randint(14, 28)
                pygame.draw.rect(bg, (col_v, col_v - 2, col_v + 18, 150),
                                 (sx, sil_y - bh, bw, bh))
        return bg

    def _build_city_cache(self):
        """Pre-render the entire city (tiles + all buildings) to a single
        cached surface.  Only called once at startup."""
        c_min, c_max = -VISTA_PAD, MAP_COLS + VISTA_PAD
        r_min, r_max = -VISTA_PAD, MAP_ROWS + VISTA_PAD

        # Compute isometric bounding box (world-space with cam=0)
        xs, ys = [], []
        for c in range(c_min, c_max):
            for r in (r_min, r_max - 1):
                sx, sy = iso_to_screen(c, r, 0, 0)
                xs.append(sx); ys.append(sy)
        for r in range(r_min, r_max):
            for c in (c_min, c_max - 1):
                sx, sy = iso_to_screen(c, r, 0, 0)
                xs.append(sx); ys.append(sy)

        x1 = min(xs) - TILE_W - 20
        x2 = max(xs) + TILE_W + 20
        y1 = min(ys) - TILE_H - 240   # headroom for tallest buildings
        y2 = max(ys) + TILE_H + 40

        surf_w = int(x2 - x1)
        surf_h = int(y2 - y1)
        self._cache_ox = int(x1)
        self._cache_oy = int(y1)

        # cam offsets that map world coords → cache-local coords
        ccx = -self._cache_ox
        ccy = -self._cache_oy

        cache = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

        # ────────────────────── tiles ──────────────────────
        rng = random.Random(7)
        puddle_rng = random.Random(123)
        crack_rng = random.Random(456)

        for row in range(r_min, r_max):
            for col in range(c_min, c_max):
                sx, sy = iso_to_screen(col, row, ccx, ccy)
                pts = [
                    (sx, sy - TILE_H // 2),
                    (sx + TILE_W // 2, sy),
                    (sx, sy + TILE_H // 2),
                    (sx - TILE_W // 2, sy),
                ]
                in_bounds = 0 <= col < MAP_COLS and 0 <= row < MAP_ROWS

                if not in_bounds:
                    dist = max(0, max(-col, col - MAP_COLS + 1,
                                      -row, row - MAP_ROWS + 1))
                    fade = max(0, 1.0 - dist / (VISTA_PAD + 1))
                    v = int(22 * fade)
                    pygame.draw.polygon(cache, (v, int(v * 0.8), int(v * 1.6)), pts)
                    if fade > 0.25:
                        ec = (int(35 * fade), int(28 * fade), int(60 * fade))
                        pygame.draw.polygon(cache, ec, pts, 1)
                    continue

                is_path = (col, row) in PATH_TILES
                is_road = (is_path or 9 <= col <= 11 or 18 <= col <= 20
                           or 9 <= row <= 11 or 18 <= row <= 20)
                is_isect = (is_road
                            and (9 <= col <= 11 or 18 <= col <= 20)
                            and (9 <= row <= 11 or 18 <= row <= 20))

                brightness = rng.randint(0, 10) if (col + row) % 3 == 0 else 0
                if is_isect:
                    base = (52, 48, 78); edge_col = (85, 75, 130)
                elif is_road:
                    base = (45, 40, 68); edge_col = (72, 62, 110)
                else:
                    vary = rng.randint(-3, 3)
                    base = tuple(max(0, c + vary) for c in C_TILE)
                    edge_col = C_TILE_LINE
                tile_col = tuple(min(255, c + brightness) for c in base)

                pygame.draw.polygon(cache, tile_col, pts)
                pygame.draw.polygon(cache, edge_col, pts, 1)

                if is_road:
                    rg = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    ga = 18 if is_isect else 12
                    pygame.draw.polygon(rg, (100, 120, 200, ga), [
                        (TILE_W // 2, 0), (TILE_W, TILE_H // 2),
                        (TILE_W // 2, TILE_H), (0, TILE_H // 2)])
                    pygame.draw.polygon(rg, (140, 160, 240, ga // 2), [
                        (TILE_W // 2, TILE_H // 4),
                        (TILE_W * 3 // 4, TILE_H // 2),
                        (TILE_W // 2, TILE_H * 3 // 4),
                        (TILE_W // 4, TILE_H // 2)])
                    cache.blit(rg, (sx - TILE_W // 2, sy - TILE_H // 2))

                if is_road and not is_isect and (col + row) % 2 == 0:
                    ds = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    pygame.draw.line(ds, (110, 100, 160, 65),
                                     (TILE_W // 2 - 6, TILE_H // 2),
                                     (TILE_W // 2 + 6, TILE_H // 2), 1)
                    cache.blit(ds, (sx - TILE_W // 2, sy - TILE_H // 2))

                # Crosswalk pattern at intersections
                if is_isect:
                    cw_s = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    for si in range(4):
                        t_s = 0.2 + si * 0.2
                        lp1 = (int(TILE_W * 0.3), int(TILE_H * t_s))
                        lp2 = (int(TILE_W * 0.7), int(TILE_H * t_s))
                        pygame.draw.line(cw_s, (190, 185, 220, 40), lp1, lp2, 2)
                    cache.blit(cw_s, (sx - TILE_W // 2, sy - TILE_H // 2))

                # Manhole covers on sparse road tiles
                if is_road and not is_isect and rng.random() < 0.035:
                    mh_s = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    pygame.draw.circle(mh_s, (38, 32, 58, 90),
                                       (TILE_W // 2, TILE_H // 2), 5)
                    pygame.draw.circle(mh_s, (58, 52, 82, 70),
                                       (TILE_W // 2, TILE_H // 2), 5, 1)
                    pygame.draw.circle(mh_s, (48, 42, 72, 50),
                                       (TILE_W // 2, TILE_H // 2), 3)
                    cache.blit(mh_s, (sx - TILE_W // 2, sy - TILE_H // 2))

                # Curb highlights where road meets sidewalk
                if is_road and not is_isect:
                    adj_non_road = False
                    for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nc, nr = col + dc, row + dr
                        if 0 <= nc < MAP_COLS and 0 <= nr < MAP_ROWS:
                            is_adj_road = (9 <= nc <= 11 or 18 <= nc <= 20
                                           or 9 <= nr <= 11 or 18 <= nr <= 20)
                            if not is_adj_road:
                                adj_non_road = True
                                break
                    if adj_non_road:
                        cb_s = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                        pygame.draw.polygon(cb_s, (100, 90, 150, 25), [
                            (TILE_W // 2, 1), (TILE_W - 2, TILE_H // 2),
                            (TILE_W // 2, TILE_H - 1), (2, TILE_H // 2)], 1)
                        cache.blit(cb_s, (sx - TILE_W // 2, sy - TILE_H // 2))

                if puddle_rng.random() < 0.06:
                    pw = puddle_rng.randint(10, 22)
                    ph = puddle_rng.randint(4, 8)
                    pcx = TILE_W // 2 + puddle_rng.randint(-6, 6)
                    pcy = TILE_H // 2 + puddle_rng.randint(-2, 2)
                    ps = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    pygame.draw.ellipse(ps, (40, 35, 70, 40),
                                        (pcx - pw // 2, pcy - ph // 2, pw, ph))
                    pygame.draw.ellipse(ps, (80, 90, 140, 22),
                                        (pcx - pw // 3, pcy - ph // 3,
                                         pw // 2, ph // 2))
                    cache.blit(ps, (sx - TILE_W // 2, sy - TILE_H // 2))

                if (col + row) % 5 == 0:
                    hl = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    pygame.draw.polygon(hl, (80, 70, 120, 15), [
                        (TILE_W // 2, 0), (TILE_W, TILE_H // 2),
                        (TILE_W // 2, TILE_H), (0, TILE_H // 2)])
                    cache.blit(hl, (sx - TILE_W // 2, sy - TILE_H // 2))

                if crack_rng.random() < 0.03:
                    cs = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    cx = TILE_W // 2 + crack_rng.randint(-8, 8)
                    cy = TILE_H // 2 + crack_rng.randint(-3, 3)
                    for _ in range(crack_rng.randint(2, 4)):
                        ddx = crack_rng.randint(-7, 7)
                        ddy = crack_rng.randint(-3, 3)
                        pygame.draw.line(cs, (18, 12, 35, 80),
                                         (cx, cy), (cx + ddx, cy + ddy), 1)
                        cx += ddx; cy += ddy
                    cache.blit(cs, (sx - TILE_W // 2, sy - TILE_H // 2))

        # ────────────────────── buildings (depth-sorted) ──────────────────────
        all_b = []
        for b in DECO_BUILDINGS:
            all_b.append(b)
        for b in BUILDINGS:
            all_b.append(b)
        all_b.sort(key=lambda b: b["col"] + b["row"])

        for b in all_b:
            bid = b.get("id", "")
            sprite = self.building_sprites.get(bid)
            if sprite is not None:
                # Sprite-based rendering for main buildings
                size  = b["size"]
                tl = iso_to_screen(b["col"],        b["row"],        ccx, ccy)
                tr = iso_to_screen(b["col"] + size, b["row"],        ccx, ccy)
                bl = iso_to_screen(b["col"],        b["row"] + size, ccx, ccy)
                br = iso_to_screen(b["col"] + size, b["row"] + size, ccx, ccy)
                foot_cx = (tl[0] + br[0]) / 2
                foot_cy = max(tl[1], tr[1], bl[1], br[1])
                foot_w  = int(abs(tr[0] - tl[0]) + abs(bl[0] - br[0]))
                scale_f = foot_w / sprite.get_width() * 1.6
                new_w   = max(1, int(sprite.get_width()  * scale_f))
                new_h   = max(1, int(sprite.get_height() * scale_f))
                scaled  = pygame.transform.smoothscale(sprite, (new_w, new_h))
                blit_x = int(foot_cx - new_w / 2)
                blit_y = int(foot_cy  - new_h)
                cache.blit(scaled, (blit_x, blit_y))
            elif self.extra_building_sprites and b.get("size", 1) == 1:
                # Extra building sprite chosen deterministically per tile
                _idx = hash((b["col"], b["row"])) % len(self.extra_building_sprites)
                _spr = self.extra_building_sprites[_idx]
                _size = b.get("size", 1)
                _tl = iso_to_screen(b["col"],          b["row"],          ccx, ccy)
                _tr = iso_to_screen(b["col"] + _size,  b["row"],          ccx, ccy)
                _bl = iso_to_screen(b["col"],           b["row"] + _size, ccx, ccy)
                _br = iso_to_screen(b["col"] + _size,  b["row"] + _size, ccx, ccy)
                _foot_cx = (_tl[0] + _br[0]) / 2
                _foot_cy = max(_tl[1], _tr[1], _bl[1], _br[1])
                _foot_w  = int(abs(_tr[0] - _tl[0]) + abs(_bl[0] - _br[0]))
                _sc = _foot_w / _spr.get_width() * 1.5
                _nw = max(1, int(_spr.get_width()  * _sc))
                _nh = max(1, int(_spr.get_height() * _sc))
                _scaled = pygame.transform.smoothscale(_spr, (_nw, _nh))
                cache.blit(_scaled, (int(_foot_cx - _nw / 2), int(_foot_cy - _nh)))
            else:
                draw_iso_building(
                    cache, b["col"], b["row"],
                    b["color"], b["accent"], b["height"], b["size"],
                    ccx, ccy, 0.5)

        self._city_cache = cache

    def _draw_building_markers(self):
        """Draw interactive building overlays (diamonds + name labels) per frame."""
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        for b in BUILDINGS:
            size = b["size"]
            corners = [
                iso_to_screen(b["col"], b["row"], cam_x, cam_y),
                iso_to_screen(b["col"] + size, b["row"], cam_x, cam_y),
                iso_to_screen(b["col"] + size, b["row"] + size, cam_x, cam_y),
                iso_to_screen(b["col"], b["row"] + size, cam_x, cam_y),
            ]
            top = [(x, y - b["height"]) for x, y in corners]
            cx = sum(p[0] for p in top) / 4
            cy = min(p[1] for p in top) - 20
            if cx < -120 or cx > SCREEN_W + 120 or cy < -120 or cy > SCREEN_H + 120:
                continue

            draw_diamond(self.screen, cx, cy, 10, C_GOLD, C_GOLD_DIM, self.t)

            ns = self.font_prompt.render(b["name"], True, b["accent"])
            nr = ns.get_rect(center=(cx, cy - 22))
            bg = pygame.Surface(
                (nr.width + 16, nr.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 160),
                             bg.get_rect(), border_radius=5)
            pygame.draw.rect(bg, (*b["accent"][:3], 80),
                             bg.get_rect(), 1, border_radius=5)
            self.screen.blit(bg, (nr.x - 8, nr.y - 4))
            self.screen.blit(ns, nr)

    def draw_rain(self):
        rain_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for drop in self.rain:
            ex = drop.x + drop.length * 0.3
            ey = drop.y + drop.length
            pygame.draw.line(rain_surf, (*C_RAIN[:3], drop.alpha),
                             (int(drop.x), int(drop.y)),
                             (int(ex), int(ey)), 1)
        self.screen.blit(rain_surf, (0, 0))

    def draw_glow_particles(self):
        for p in self.glow_particles:
            if p.alpha <= 0:
                continue
            r = max(1, int(p.radius))
            s = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p.color, p.alpha // 3),
                               (r * 3, r * 3), r * 3)
            pygame.draw.circle(s, (*p.color, min(255, p.alpha)),
                               (r * 3, r * 3), r)
            self.screen.blit(s, (int(p.x) - r * 3, int(p.y) - r * 3))

    def draw_fog(self):
        self.screen.blit(self.fog_surf, (0, 0))

    def draw_street_lamps(self):
        """Draw atmospheric street lamps using sprite + glow effect."""
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        for lcol, lrow in LAMP_POSITIONS:
            sx, sy = iso_to_screen(lcol, lrow, cam_x, cam_y)
            if sx < -60 or sx > SCREEN_W + 60:
                continue
            if sy < -80 or sy > SCREEN_H + 60:
                continue

            pulse = 0.8 + 0.2 * math.sin(self.t * 1.5 + lcol * 0.7 + lrow)

            # ── Ground light pool ──
            pw, ph = 44, 18
            ps = pygame.Surface((pw, ph), pygame.SRCALPHA)
            pool_a = int(18 * pulse)
            pygame.draw.ellipse(ps, (255, 220, 140, pool_a), (0, 0, pw, ph))
            pygame.draw.ellipse(ps, (255, 230, 160, pool_a + 6),
                                (pw // 4, ph // 4, pw // 2, ph // 2))
            self.screen.blit(ps, (sx - pw // 2, sy - ph // 2 + 2))

            # ── Lamp sprite ──
            lamp_h = 52   # display height of the sprite on screen
            if self.lamp_sprite is not None:
                _lw = self.lamp_sprite.get_width()
                _lh = self.lamp_sprite.get_height()
                _sc = lamp_h / _lh
                _nw = max(1, int(_lw * _sc))
                _nh = lamp_h
                _scaled = pygame.transform.smoothscale(self.lamp_sprite, (_nw, _nh))
                self.screen.blit(_scaled, (sx - _nw // 2, sy - _nh))
                head_y = sy - _nh + int(_nh * 0.18)   # top portion = lamp head
            else:
                # Fallback: simple procedural lamp
                post_col = (55, 45, 75)
                pygame.draw.line(self.screen, post_col, (sx, sy), (sx, sy - lamp_h), 2)
                pygame.draw.circle(self.screen, (75, 65, 95), (sx, sy - lamp_h), 4)
                head_y = sy - lamp_h

            # ── Warm glow around lamp head ──
            glow_r = int(30 * pulse)
            gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 220, 120, int(28 * pulse)),
                               (glow_r, glow_r), glow_r)
            pygame.draw.circle(gs, (255, 235, 150, int(55 * pulse)),
                               (glow_r, glow_r), int(glow_r * 0.55))
            pygame.draw.circle(gs, (255, 245, 200, int(90 * pulse)),
                               (glow_r, glow_r), int(glow_r * 0.25))
            self.screen.blit(gs, (sx - glow_r, head_y - glow_r))

    def draw_proximity_prompt(self):
        nearby = self.player.near_building(BUILDINGS)
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        if nearby and not self.panel_open:
            px, py = self.player.get_screen_pos(cam_x, cam_y)
            text = "[ Press E to Investigate ]"
            surf = self.font_prompt.render(text, True, C_GOLD)
            rect = surf.get_rect(center=(px, py - 36))
            pulse = int(180 + math.sin(self.t * 4) * 30)

            if self._prompt_bubble_png is not None:
                # Scale bubble to fit text with padding
                bw = rect.width + 48
                bh = rect.height + 24
                bubble = pygame.transform.smoothscale(
                    self._prompt_bubble_png, (bw, bh))
                # Apply pulse alpha
                bubble.set_alpha(pulse)
                bx = rect.centerx - bw // 2
                # Position bubble above player; tail points down so offset up
                by = rect.centery - int(bh * 0.72)
                self.screen.blit(bubble, (bx, by))
                # Draw text centred in bubble interior (above tail)
                tx = bx + bw // 2 - surf.get_width() // 2
                ty = by + (bh - rect.height) // 2 - 6
                self.screen.blit(surf, (tx, ty))
            else:
                bg = pygame.Surface(
                    (rect.width + 20, rect.height + 10), pygame.SRCALPHA)
                pygame.draw.rect(bg, (0, 0, 0, pulse),
                                 bg.get_rect(), border_radius=8)
                pygame.draw.rect(bg, (*C_GOLD, 120),
                                 bg.get_rect(), 1, border_radius=8)
                self.screen.blit(bg, (rect.x - 10, rect.y - 5))
                self.screen.blit(surf, rect)

    def _hud_text_shadow(self, hud, font, text, color, x, y):
        """Render text with a dark shadow for improved readability."""
        shadow = font.render(text, True, (0, 0, 0))
        hud.blit(shadow, (x + 1, y + 1))
        hud.blit(shadow, (x + 2, y + 2))
        main = font.render(text, True, color)
        hud.blit(main, (x, y))

    def draw_hud(self):
        # Use HUD PNG height if available, else default
        if self._hud_png is not None:
            hud_h = self._hud_png.get_height()
        else:
            hud_h = 56
        hud = pygame.Surface((SCREEN_W, hud_h), pygame.SRCALPHA)
        # PNG background or fallback solid bar
        if self._hud_png is not None:
            hud.blit(self._hud_png, (0, 0))
        else:
            pygame.draw.rect(hud, (8, 4, 24, 230), (0, 0, SCREEN_W, hud_h))
            pygame.draw.line(hud, (*C_GOLD, 140), (0, 0), (SCREEN_W, 0), 2)
            pygame.draw.line(hud, (255, 255, 255, 30), (0, 2), (SCREEN_W, 2), 1)

        nearby = self.player.near_building(BUILDINGS)
        zone_name = nearby["name"] if nearby else "Midnight District"
        zone_color = nearby["accent"] if nearby else C_GOLD

        # Draw a small gold diamond icon instead of emoji (which renders as a box)
        diamond_x, diamond_y = 22, hud_h // 2
        diamond_size = 6
        diamond_pts = [
            (diamond_x, diamond_y - diamond_size),
            (diamond_x + diamond_size, diamond_y),
            (diamond_x, diamond_y + diamond_size),
            (diamond_x - diamond_size, diamond_y),
        ]
        pygame.draw.polygon(hud, zone_color, diamond_pts)
        pygame.draw.polygon(hud, (255, 255, 255, 160), diamond_pts, 1)

        # Zone name with shadow for readability
        self._hud_text_shadow(hud, self.font_zone, zone_name, zone_color,
                              diamond_x + diamond_size + 10, hud_h // 2 - 13)

        stats = (f"Personas: {self.total_personas}  |  "
                 f"Skills: {self.total_skills}  |  "
                 f"Explored: {len(self.buildings_visited)}/{len(BUILDINGS)}")
        self._hud_text_shadow(hud, self.font_stat, stats, (180, 180, 200),
                              SCREEN_W // 2 - self.font_stat.size(stats)[0] // 2, 6)

        ctrl = "WASD: Move  |  E: Investigate  |  ESC: Close/Quit"
        self._hud_text_shadow(hud, self.font_stat, ctrl, (120, 120, 145),
                              SCREEN_W // 2 - self.font_stat.size(ctrl)[0] // 2, 30)

        self.screen.blit(hud, (0, SCREEN_H - hud_h))

    def draw_minimap(self):
        mm_w, mm_h = 220, 220
        mm_x = SCREEN_W - mm_w - 18
        mm_y = 18

        # Map_Frame PNG drawn underneath first as a background frame!
        if self._map_frame_png is not None:
            pad = 16  # extra pixels around minimap
            frame_w = mm_w + pad * 2
            frame_h = mm_h + pad * 2
            frame = pygame.transform.smoothscale(
                self._map_frame_png, (frame_w, frame_h))
            self.screen.blit(frame, (mm_x - pad, mm_y - pad))

        mm = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)

        pygame.draw.rect(mm, (8, 4, 28, 255), (0, 0, mm_w, mm_h),
                         border_radius=6)
        pygame.draw.rect(mm, (255, 255, 255, 15), (0, 0, mm_w, mm_h),
                         border_radius=6)

        title = self.font_minimap.render("MIDNIGHT MAP", True, C_GOLD)
        mm.blit(title, (mm_w // 2 - title.get_width() // 2, 5))

        sx = (mm_w - 24) / MAP_COLS
        sy = (mm_h - 32) / MAP_ROWS
        ox, oy = 12, 24

        for r in range(0, MAP_ROWS, 2):
            for c in range(0, MAP_COLS, 2):
                px = int(ox + c * sx + sx / 2)
                py = int(oy + r * sy + sy / 2)
                pygame.draw.circle(mm, (40, 30, 60), (px, py), 1)

        for b in BUILDINGS:
            bx = int(ox + b["col"] * sx)
            by = int(oy + b["row"] * sy)
            bw = max(4, int(b["size"] * sx))
            bh = max(4, int(b["size"] * sy))
            col = b["accent"]
            if b["id"] in self.buildings_visited:
                gs = pygame.Surface((bw + 4, bh + 4), pygame.SRCALPHA)
                pygame.draw.rect(gs, (*col[:3], 40), (0, 0, bw + 4, bh + 4),
                                 border_radius=2)
                mm.blit(gs, (bx - 2, by - 2))
            pygame.draw.rect(mm, col, (bx, by, bw, bh))
            pygame.draw.rect(mm, (255, 255, 255, 60), (bx, by, bw, bh), 1)

        for b in DECO_BUILDINGS:
            bx = int(ox + b["col"] * sx)
            by = int(oy + b["row"] * sy)
            bw = max(2, int(b.get("size", 1) * sx))
            bh = max(2, int(b.get("size", 1) * sy))
            pygame.draw.rect(mm, (40, 30, 60), (bx, by, bw, bh))

        ppx = int(ox + self.player.col * sx + sx / 2)
        ppy = int(oy + self.player.row * sy + sy / 2)
        pulse = int(4 + math.sin(self.t * 5) * 2)
        pygame.draw.circle(mm, (80, 200, 255, 50), (ppx, ppy), pulse + 3)
        pygame.draw.circle(mm, C_PLAYER_BODY, (ppx, ppy), 3)
        pygame.draw.circle(mm, (255, 255, 255), (ppx, ppy), 3, 1)

        self.screen.blit(mm, (mm_x, mm_y))

    def draw_title(self):
        text = "T H E   M I D N I G H T   C H A N N E L"
        surf = self.font_title.render(text, True, C_GOLD)
        rect = surf.get_rect(center=(SCREEN_W // 2, 32))
        bg = pygame.Surface(
            (rect.width + 40, rect.height + 14), pygame.SRCALPHA)
        pygame.draw.rect(bg, (255, 215, 0, 10), bg.get_rect(),
                         border_radius=8)
        self.screen.blit(bg, (rect.x - 20, rect.y - 7))
        self.screen.blit(surf, rect)

        sub = self.font_hud.render(
            "Persona 4 Golden — Data Explorer", True, (150, 140, 180))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, 58)))

    def draw_chart_panel(self):
        if self.panel_slide <= 0.01:
            return

        panel_w = int(SCREEN_W * 0.72)
        slide_off = int(panel_w * (1.0 - self.panel_slide))
        panel_x = SCREEN_W - panel_w + slide_off

        panel = pygame.Surface((panel_w, SCREEN_H), pygame.SRCALPHA)

        # Glassmorphism
        pygame.draw.rect(panel, (10, 6, 30, 200), (0, 0, panel_w, SCREEN_H))
        pygame.draw.rect(panel, (255, 255, 255, 8),
                         (0, 0, panel_w, SCREEN_H))

        accent = self.current_building_accent
        # Left accent strip (wider for vertical title)
        strip_w = 32
        for i in range(strip_w):
            a = int(80 * (1 - i / strip_w))
            pygame.draw.line(panel, (*accent[:3], a), (i, 0), (i, SCREEN_H))

        # Vertical building name along left strip
        title = self.font_panel_title.render(self.current_building_name,
                                             True, accent)
        title_rot = pygame.transform.rotate(title, 90)
        tr = title_rot.get_rect(
            center=(strip_w // 2 + 2, SCREEN_H // 2))
        # Background pill for vertical title
        tbg = pygame.Surface(
            (tr.width + 8, tr.height + 16), pygame.SRCALPHA)
        pygame.draw.rect(tbg, (*accent[:3], 20), tbg.get_rect(),
                         border_radius=6)
        panel.blit(tbg, (tr.x - 4, tr.y - 8))
        panel.blit(title_rot, tr)

        # Content area starts after the strip
        content_x = strip_w + 10
        content_w = panel_w - content_x - 10

        # Chart
        if self.current_chart_surface:
            chart = self.current_chart_surface
            avail_w = content_w
            avail_h = SCREEN_H - 100
            cw, ch = chart.get_size()
            scale = min(avail_w / cw, avail_h / ch)
            nw = int(cw * scale)
            nh = int(ch * scale)
            scaled = pygame.transform.smoothscale(chart, (nw, nh))
            cx = content_x + (content_w - nw) // 2
            cy = 20

            container = pygame.Surface(
                (nw + 8, nh + 8), pygame.SRCALPHA)
            pygame.draw.rect(container, (255, 255, 255, 8),
                             (0, 0, nw + 8, nh + 8), border_radius=6)
            pygame.draw.rect(container, (*accent[:3], 40),
                             (0, 0, nw + 8, nh + 8), 1, border_radius=6)
            panel.blit(container, (cx - 4, cy - 4))
            panel.blit(scaled, (cx, cy))

        # Rotation indicator with angle display
        content_center = content_x + content_w // 2
        rot_text = f"Azim: {int(self.chart_azim)}°  Elev: {int(self.chart_elev)}°"
        rot_surf = self.font_stat.render(rot_text, True, (120, 120, 150))
        panel.blit(rot_surf,
                   (content_center - rot_surf.get_width() // 2, SCREEN_H - 60))

        # Controls hint
        hint = "← → Rotate   ↑ ↓ Tilt   ESC Close"
        h_surf = self.font_panel_hint.render(hint, True, C_GREY)
        hr = h_surf.get_rect(center=(content_center, SCREEN_H - 28))
        pill = pygame.Surface(
            (hr.width + 24, hr.height + 10), pygame.SRCALPHA)
        pygame.draw.rect(pill, (255, 255, 255, 12),
                         pill.get_rect(), border_radius=12)
        pygame.draw.rect(pill, (255, 255, 255, 30),
                         pill.get_rect(), 1, border_radius=12)
        panel.blit(pill, (hr.x - 12, hr.y - 5))
        panel.blit(h_surf, hr)

        self.screen.blit(panel, (panel_x, 0))

    def _build_vignette(self):
        vig = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for i in range(70):
            a = int(90 * (1 - i / 70))
            pygame.draw.line(vig, (0, 0, 0, a), (0, i), (SCREEN_W, i))
            pygame.draw.line(vig, (0, 0, 0, a),
                             (0, SCREEN_H - 1 - i), (SCREEN_W, SCREEN_H - 1 - i))
        for i in range(50):
            a = int(60 * (1 - i / 50))
            pygame.draw.line(vig, (0, 0, 0, a), (i, 0), (i, SCREEN_H))
            pygame.draw.line(vig, (0, 0, 0, a),
                             (SCREEN_W - 1 - i, 0),
                             (SCREEN_W - 1 - i, SCREEN_H))
        return vig

    def draw_vignette(self):
        if self._vignette_png is not None:
            self.screen.blit(self._vignette_png, (0, 0))
        else:
            self.screen.blit(self._vignette, (0, 0))

    def draw(self):
        # Distant landscape backdrop
        self.screen.blit(self.backdrop, (0, 0))

        # Blit pre-rendered city cache (tiles + buildings) with camera offset
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        self.screen.blit(self._city_cache,
                         (self._cache_ox + cam_x, self._cache_oy + cam_y))

        # Per-frame overlays
        self._draw_building_markers()
        self.draw_street_lamps()
        self.player.draw(self.screen, self.t, cam_x, cam_y)
        self.draw_rain()
        self.draw_glow_particles()
        self.draw_fog()
        self.draw_proximity_prompt()

        self.screen.blit(self.scanline_surf, (0, 0))
        self.draw_vignette()

        self.draw_title()
        self.draw_hud()
        self.draw_minimap()
        self.draw_chart_panel()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
