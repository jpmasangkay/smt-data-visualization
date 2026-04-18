"""Fast software-rendered 3D scene builders for all 12 interactive buildings."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib

from .renderer import Chart3DScene, _norm
from .constants import (
    C_GOLD, C_CYAN, C_TEAL, C_PINK, C_ORANGE,
)

import matplotlib.pyplot as plt


# ── 1. Velvet Tower ──────────────────────────────────────────────────────────
def scene_velvet(data: dict) -> Chart3DScene | None:
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


# ── 2. Junes Mall ────────────────────────────────────────────────────────────
def scene_junes(data: dict) -> Chart3DScene | None:
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
            x = 1 - 2*i/ns - 0.03 - dx
            z = 1 - 2*j/na - 0.03 - dz
            scene.add_bar(x, 0, z, dx, v/mx*1.3, dz, bar_c[i])
    return scene


# ── 3. Connection Hub ────────────────────────────────────────────────────────
def scene_connection(data: dict) -> Chart3DScene | None:
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


# ── 4. Skill Arcade ──────────────────────────────────────────────────────────
def scene_skill(data: dict) -> Chart3DScene | None:
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
    ys = (df["RN"].values / 2.0) * 1.3
    sizes = 2 + df["Costs"].values * 0.02
    for i in range(len(df)):
        c = ek.get(df.iloc[i]["Elem"], (136,136,136))
        scene.points.append((float(xs[i]),float(ys[i]),float(zs[i]),
                             float(min(5, sizes[i])), c))
    return scene


# ── 5. Inheritance Lab ───────────────────────────────────────────────────────
def scene_inherit(data: dict) -> Chart3DScene | None:
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


# ── 6. Shadow Den ────────────────────────────────────────────────────────────
def scene_shadow(data: dict) -> Chart3DScene | None:
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
            x = 1 - 2*i/nc - 0.05 - dx
            z = 1 - 2*j/np_ - 0.02 - dz
            scene.add_bar(x,0,z, dx, v/mx*1.3, dz, c3)
    return scene


# ── 7. Block Fortress ────────────────────────────────────────────────────────
def scene_block(data: dict) -> Chart3DScene | None:
    """Bars: Block & Reflect by element."""
    cb = data["c_block"]; cref = data["c_reflects"]
    if cb.empty and cref.empty:
        return None
    scene = Chart3DScene("Block Fortress", (34,221,136))
    scene.add_grid()
    elems: set = set()
    bd, rd = {}, {}
    if not cb.empty:
        bc = cb["Block"].value_counts(); bd = bc.to_dict(); elems.update(bc.index)
    if not cref.empty:
        rc2 = cref["Reflects"].value_counts(); rd = rc2.to_dict(); elems.update(rc2.index)
    elems_sorted = sorted(elems)
    ne = max(1, len(elems_sorted))
    vals_b = [bd.get(e, 0) for e in elems_sorted]
    vals_r = [rd.get(e, 0) for e in elems_sorted]
    mx = max(1, max(vals_b + vals_r, default=1))
    for j, e in enumerate(elems_sorted):
        dz = 1.2 / ne
        z = 1 - (2*j + 1) / ne - dz / 2
        scene.add_bar(0.05, 0, z, 0.4, vals_b[j]/mx*1.3, dz, (34,221,136))
        scene.add_bar(-0.45, 0, z, 0.4, vals_r[j]/mx*1.3, dz, (255,102,34))
    return scene


# ── 8. Persona Archive ──────────────────────────────────────────────────────
def scene_archive(data: dict) -> Chart3DScene | None:
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


# ── 9. Fusion Reactor ────────────────────────────────────────────────────────
def scene_fusion(data: dict) -> Chart3DScene | None:
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


# ── 10. Oracle Spire ─────────────────────────────────────────────────────────
def scene_oracle(data: dict) -> Chart3DScene | None:
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


# ── 11. Fate Compass ─────────────────────────────────────────────────────────
def scene_fate(data: dict) -> Chart3DScene | None:
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


# ── 12. Element Shrine ───────────────────────────────────────────────────────
def scene_shrine(data: dict) -> Chart3DScene | None:
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


# ─── Scene Generator Registry ───────────────────────────────────────────────
SCENE_GENERATORS: dict[str, callable] = {
    "velvet": scene_velvet, "junes": scene_junes,
    "connection": scene_connection, "skill": scene_skill,
    "inherit": scene_inherit, "shadow": scene_shadow,
    "block": scene_block, "archive": scene_archive,
    "fusion": scene_fusion, "oracle": scene_oracle,
    "fate": scene_fate, "shrine": scene_shrine,
}
