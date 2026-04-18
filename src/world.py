"""Isometric projection, decorative building generation, and building drawing."""
from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from .constants import (
    BUILDINGS, MAP_COLS, MAP_ROWS, VISTA_PAD,
    TILE_W, TILE_H, SCREEN_W, SCREEN_H,
)


# ─── Isometric Projection ───────────────────────────────────────────────────

def iso_to_screen(
    col: float, row: float,
    cam_x: float = 0, cam_y: float = 0,
    zoom: float = 1.0,
) -> tuple[int, int]:
    """Convert tile (col, row) to screen pixel coordinates with optional zoom."""
    sx = (col - row) * (TILE_W // 2) + SCREEN_W // 2 + cam_x
    sy = (col + row) * (TILE_H // 2) + 100 + cam_y
    if zoom != 1.0:
        sx = SCREEN_W / 2 + (sx - SCREEN_W / 2) * zoom
        sy = SCREEN_H / 2 + (sy - SCREEN_H / 2) * zoom
    return int(sx), int(sy)


def screen_to_iso(
    sx: float, sy: float,
    cam_x: float = 0, cam_y: float = 0,
) -> tuple[float, float]:
    """Convert screen pixel coordinates back to tile (col, row)."""
    sx -= SCREEN_W // 2 + cam_x
    sy -= 100 + cam_y
    col = (sx / (TILE_W // 2) + sy / (TILE_H // 2)) / 2
    row = (sy / (TILE_H // 2) - sx / (TILE_W // 2)) / 2
    return col, row


# ─── Decorative Building Generation ─────────────────────────────────────────

def _deco(c: int, r: int, h: int, seed: int = 0) -> dict:
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


def _generate_deco_buildings() -> list[dict]:
    """Procedurally generate dense decorative buildings throughout the city."""
    deco: list[dict] = []
    rng = random.Random(2024)
    # Occupied tiles from interactive buildings
    occupied: set[tuple[int, int]] = set()
    for b in BUILDINGS:
        for dc in range(b["size"]):
            for dr in range(b["size"]):
                occupied.add((b["col"] + dc, b["row"] + dr))
    # Road tiles
    road_tiles: set[tuple[int, int]] = set()
    for c in range(MAP_COLS):
        for r in range(MAP_ROWS):
            if 9 <= c <= 11 or 18 <= c <= 20 or 9 <= r <= 11 or 18 <= r <= 20:
                road_tiles.add((c, r))
    # Fill the interior densely — skip roads and interactive building footprints
    for c in range(MAP_COLS):
        for r in range(MAP_ROWS):
            if (c, r) in occupied or (c, r) in road_tiles:
                continue
            # Check adjacency to interactive buildings (leave generous buffer)
            too_close = False
            for b in BUILDINGS:
                buf = 3 if b.get("id") == "fusion" else 1
                if (b["col"] - buf <= c <= b["col"] + b["size"] + buf - 1 and
                    b["row"] - buf <= r <= b["row"] + b["size"] + buf - 1):
                    too_close = True
                    break
            if too_close:
                continue
            # Place with ~18% probability
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


DECO_BUILDINGS: list[dict] = _generate_deco_buildings()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _lerp_point(
    p1: tuple[float, float],
    p2: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    """Linear interpolation between two 2D points."""
    return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)


# ─── Isometric Building Drawing (Enhanced) ──────────────────────────────────

def draw_iso_building(
    surface: pygame.Surface,
    col: int, row: int,
    color: tuple, accent: tuple,
    height: int, size: int = 2,
    cam_x: float = 0, cam_y: float = 0,
    neon_pulse: float = 0.0,
    zoom: float = 1.0,
) -> list[tuple[int, int]]:
    """Draw an isometric building with gradient faces, windows, and neon effects."""
    corners = [
        iso_to_screen(col, row, cam_x, cam_y, zoom),
        iso_to_screen(col + size, row, cam_x, cam_y, zoom),
        iso_to_screen(col + size, row + size, cam_x, cam_y, zoom),
        iso_to_screen(col, row + size, cam_x, cam_y, zoom),
    ]
    scaled_height = int(height * zoom)
    top_corners = [(x, y - scaled_height) for x, y in corners]
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

    # ── Ground neon pool ──
    pool_w = int(size * TILE_W * 0.7 * zoom)
    pool_h = int(size * TILE_H * 0.5 * zoom)
    pool_cx = int((corners[0][0] + corners[2][0]) / 2)
    pool_cy = int((corners[0][1] + corners[2][1]) / 2) + 6
    if pool_w > 0 and pool_h > 0:
        pool_surf = pygame.Surface((pool_w * 2, pool_h * 2), pygame.SRCALPHA)
        pool_a = int(10 + neon_pulse * 8)
        pygame.draw.ellipse(pool_surf, (*accent[:3], pool_a),
                            (0, 0, pool_w * 2, pool_h * 2))
        pygame.draw.ellipse(pool_surf, (*accent[:3], pool_a + 5),
                            (pool_w // 2, pool_h // 2, pool_w, pool_h))
        surface.blit(pool_surf, (pool_cx - pool_w, pool_cy - pool_h))

    # ── Right face: 4 gradient bands ──
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

    # ── Left face: 4 gradient bands ──
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

    # ── Top face ──
    top_col = tuple(min(255, c + 8) for c in color[:3])
    pygame.draw.polygon(surface, top_col, top_corners)
    pygame.draw.polygon(surface, accent, top_corners, 1)

    # ── Rooftop structures ──
    if height >= 65:
        tc_cx = sum(p[0] for p in top_corners) / 4
        tc_cy = sum(p[1] for p in top_corners) / 4
        bw = rng.randint(6, 12)
        bh = rng.randint(5, 10)
        roof_col = tuple(min(255, c + 12) for c in color[:3])
        roof_dark = tuple(max(0, c - 10) for c in roof_col)
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

    # ═══ Alpha effects: glow, stripes, windows ═══
    glow = pygame.Surface((bb_w, bb_h), pygame.SRCALPHA)

    # Horizontal accent stripes on right face
    for st in [0.2, 0.4, 0.6, 0.8]:
        p1 = _lerp_point(rf[3], rf[0], st)
        p2 = _lerp_point(rf[2], rf[1], st)
        pygame.draw.line(glow, (*accent[:3], 45),
                         (int(p1[0] - ox), int(p1[1] - oy)),
                         (int(p2[0] - ox), int(p2[1] - oy)), 1)

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

    # Neon edge glow
    top_local = [(int(p[0] - ox), int(p[1] - oy)) for p in top_corners]
    corners_local = [(int(p[0] - ox), int(p[1] - oy)) for p in corners]
    pulse_a = int(20 + neon_pulse * 35)
    for th in [5, 3, 1]:
        a = max(1, pulse_a // th)
        pygame.draw.polygon(glow, (*accent[:3], a), top_local, th)
    for i in range(4):
        for th in [3, 1]:
            a = max(1, pulse_a // (th + 1))
            pygame.draw.line(glow, (*accent[:3], a),
                             corners_local[i], top_local[i], th)

    # Foundation glow
    for i in range(6):
        a = int(55 * (1 - i / 6))
        p1r = (int(corners[1][0] - ox), int(corners[1][1] - oy - i))
        p2r = (int(corners[2][0] - ox), int(corners[2][1] - oy - i))
        pygame.draw.line(glow, (*accent[:3], a), p1r, p2r, 1)
        p1l = (int(corners[2][0] - ox), int(corners[2][1] - oy - i))
        p2l = (int(corners[3][0] - ox), int(corners[3][1] - oy - i))
        pygame.draw.line(glow, (*accent[:3], int(a * 0.7)), p1l, p2l, 1)

    # ── Windows — Right face ──
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
                wcx = sum(p[0] for p in wpts) // 4
                wcy = sum(p[1] for p in wpts) // 4
                gr = max(4, int(height * 0.04))
                pygame.draw.circle(glow, (*wc, 18), (wcx, wcy), gr)
                pygame.draw.polygon(glow, (*wc, 200), wpts)
                mid_top_w = _lerp_point(w_tl, w_tr, 0.5)
                mid_bot_w = _lerp_point(w_bl, w_br, 0.5)
                mid_left_w = _lerp_point(w_tl, w_bl, 0.5)
                mid_right_w = _lerp_point(w_tr, w_br, 0.5)
                pygame.draw.line(glow, (*color[:3], 140),
                                 (int(mid_top_w[0] - ox), int(mid_top_w[1] - oy)),
                                 (int(mid_bot_w[0] - ox), int(mid_bot_w[1] - oy)), 1)
                pygame.draw.line(glow, (*color[:3], 140),
                                 (int(mid_left_w[0] - ox), int(mid_left_w[1] - oy)),
                                 (int(mid_right_w[0] - ox), int(mid_right_w[1] - oy)), 1)
            else:
                pygame.draw.polygon(glow, (8, 6, 18, 170), wpts)
                pygame.draw.polygon(glow, (*accent[:3], 30), wpts, 1)

    # ── Windows — Left face ──
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
