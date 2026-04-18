"""Matplotlib-based 3D chart renderers for all 12 interactive buildings."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

import numpy as np
import pandas as pd
import pygame

CHART_BG: str = "#0a0620"


def _style_3d(ax) -> None:
    """Apply premium dark styling to any 3D axis."""
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors="#9999bb", labelsize=7)
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor("#222244")
    ax.grid(True, alpha=0.2, color="#555588", linestyle="--", linewidth=0.5)


def render_chart_to_surface(fig) -> pygame.Surface:
    """Convert a matplotlib Figure to a pygame Surface."""
    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    buf = canvas.buffer_rgba()
    size = canvas.get_width_height()
    surf = pygame.image.frombuffer(bytes(buf), size, "RGBA")
    plt.close(fig)
    return surf


# ── 1. Velvet Tower — 3D Scatter Cloud: STR × MAG × END by Arcana ───────────
def chart_velvet(data: dict, elev: float = 25, azim: float = 135) -> pygame.Surface | None:
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
def chart_junes(data: dict, elev: float = 20, azim: float = 225) -> pygame.Surface | None:
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
def chart_connection(data: dict, elev: float = 25, azim: float = 140) -> pygame.Surface | None:
    sc = data["skill_connection"].copy()
    personas = data["personas"].copy()
    skills = data["skills"].copy()
    if sc.empty or personas.empty or skills.empty:
        return None

    fig = plt.figure(figsize=(9, 6), facecolor=CHART_BG)
    ax = fig.add_subplot(111, projection="3d")
    _style_3d(ax)

    sc_plot = sc.copy()
    sc_plot["S_lvl"] = pd.to_numeric(sc_plot["S_lvl"], errors="coerce").fillna(1)

    merged = sc_plot.merge(personas[["Name", "Arcana"]],
                           left_on="P_index", right_on=personas.index, how="left")
    arcanas = merged["Arcana"].dropna().unique()
    cmap = matplotlib.colormaps.get_cmap("cool").resampled(max(1, len(arcanas)))
    arcana_map = {a: i for i, a in enumerate(arcanas)}
    colors = [cmap(arcana_map.get(a, 0)) for a in merged["Arcana"].fillna("Unknown")]

    ax.scatter(merged["P_index"], merged["S_index"], merged["S_lvl"],
               c=colors, s=10, alpha=0.7, edgecolors="white",
               linewidths=0.2, depthshade=True)

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
def chart_skill(data: dict, elev: float = 20, azim: float = 140) -> pygame.Surface | None:
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
def chart_inherit(data: dict, elev: float = 22, azim: float = 210) -> pygame.Surface | None:
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
def chart_shadow(data: dict, elev: float = 22, azim: float = 225) -> pygame.Surface | None:
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
def chart_block(data: dict, elev: float = 20, azim: float = 135) -> pygame.Surface | None:
    c_block = data["c_block"].copy()
    c_reflects = data["c_reflects"].copy()
    if c_block.empty and c_reflects.empty:
        return None

    all_elements: set[str] = set()
    block_dict: dict = {}
    reflect_dict: dict = {}

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

    block_vals = [block_dict.get(e, 0) for e in elements]
    xs_b = [0] * len(elements)
    ys_b = list(range(len(elements)))
    ax.bar3d(xs_b, ys_b, [0]*len(elements), 0.6, 0.6, block_vals,
             color="#22DD88", alpha=0.85, edgecolor="#ffffff33",
             label="Block", zsort="average")

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
def chart_archive(data: dict, elev: float = 25, azim: float = 150) -> pygame.Surface | None:
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
def chart_fusion(data: dict, elev: float = 30, azim: float = 60) -> pygame.Surface | None:
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
def chart_oracle(data: dict, elev: float = 25, azim: float = 120) -> pygame.Surface | None:
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
def chart_fate(data: dict, elev: float = 35, azim: float = 230) -> pygame.Surface | None:
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
def chart_shrine(data: dict, elev: float = 25, azim: float = 145) -> pygame.Surface | None:
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
    cats: list[str] = []
    totals: list[int] = []
    colors: list[str] = []
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


# ─── Chart Generator Registry ───────────────────────────────────────────────
CHART_GENERATORS: dict[str, callable] = {
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
