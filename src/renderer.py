"""Fast software 3D renderer — bypasses matplotlib for real-time chart rotation."""
from __future__ import annotations

import math

import numpy as np
import pygame

from .constants import C_GOLD


class Chart3DScene:
    """Pre-computed 3D geometry for a chart. Built once, rendered every frame."""
    __slots__ = ("faces", "points", "grid_lines", "title", "title_color", "bg")

    def __init__(
        self,
        title: str = "",
        title_color: tuple[int, int, int] = C_GOLD,
        bg: tuple[int, int, int] = (10, 6, 32),
    ) -> None:
        self.faces: list[tuple] = []       # (verts_Nx3, fill_rgb, edge_rgb|None)
        self.points: list[tuple] = []      # (x, y, z, radius, color_rgb)
        self.grid_lines: list[tuple] = []  # (verts_Nx3, color_rgb)
        self.title = title
        self.title_color = title_color
        self.bg = bg

    def add_bar(
        self,
        x: float, y: float, z: float,
        dx: float, dy: float, dz: float,
        color: tuple[int, int, int],
    ) -> None:
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

    def add_surface_quad(
        self,
        v0: tuple, v1: tuple, v2: tuple, v3: tuple,
        color: tuple[int, int, int],
    ) -> None:
        """Single quad of a 3D surface mesh."""
        self.faces.append((
            np.array([v0, v1, v2, v3], dtype=np.float32),
            color[:3], tuple(min(255, c + 30) for c in color[:3])
        ))

    def add_grid(self, n: int = 5, color: tuple[int, int, int] = (55, 50, 85)) -> None:
        """Ground-plane grid + axis lines."""
        for i in range(n + 1):
            t = -1 + 2 * i / n
            self.grid_lines.append((np.array([(-1, 0, t), (1, 0, t)], dtype=np.float32), color))
            self.grid_lines.append((np.array([(t, 0, -1), (t, 0, 1)], dtype=np.float32), color))
        ax_c = (90, 85, 130)
        self.grid_lines.append((np.array([(-1.1,0,0),(1.1,0,0)], dtype=np.float32), ax_c))
        self.grid_lines.append((np.array([(0,0,-1.1),(0,0,1.1)], dtype=np.float32), ax_c))
        self.grid_lines.append((np.array([(0,0,0),(0,1.4,0)], dtype=np.float32), ax_c))


def _rot_matrix(elev: float, azim: float) -> np.ndarray:
    """Rotation matrix matching matplotlib's view_init, mapped to Y-up data."""
    a = math.radians(azim - 90)
    e = math.radians(elev)
    ca, sa = math.cos(a), math.sin(a)
    ce, se = math.cos(e), math.sin(e)
    return np.array([
        [ ca,        0,     sa],
        [-se * sa,   ce,    se * ca],
        [ ce * sa,   se,   -ce * ca],
    ], dtype=np.float32)


def render_scene_fast(
    scene: Chart3DScene,
    elev: float, azim: float,
    w: int, h: int,
    font: pygame.font.Font | None = None,
) -> pygame.Surface:
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
    items: list[tuple] = []
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
            if r >= 2:
                gs = pygame.Surface((int(r*4), int(r*4)), pygame.SRCALPHA)
                pygame.draw.circle(gs, (*col[:3], 35), (int(r*2), int(r*2)), int(r*2))
                surf.blit(gs, (int(pos[0] - r*2), int(pos[1] - r*2)))

    # Title
    if font and scene.title:
        ts = font.render(scene.title, True, scene.title_color)
        surf.blit(ts, (w // 2 - ts.get_width() // 2, 12))

    return surf


def _norm(vals: np.ndarray, lo: float = -1.0, hi: float = 1.0) -> np.ndarray:
    """Normalize array to [lo, hi]."""
    mn, mx = float(np.nanmin(vals)), float(np.nanmax(vals))
    if mx <= mn:
        return np.full_like(vals, (lo + hi) / 2, dtype=float)
    return lo + (np.asarray(vals, dtype=float) - mn) / (mx - mn) * (hi - lo)
