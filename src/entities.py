"""Game entities: Player, Camera, particle systems, and markers."""
from __future__ import annotations

import math
import os
import random
from typing import Optional

import pygame

from .constants import (
    SCREEN_W, SCREEN_H, TILE_W, TILE_H,
    MAP_COLS, MAP_ROWS, ASSETS_DIR,
    C_PLAYER_BODY, C_PLAYER_OUTLINE, C_GOLD, C_GOLD_DIM,
)
from .world import iso_to_screen


# ─── Particle Systems ───────────────────────────────────────────────────────

class RainDrop:
    """A single animated rain particle."""
    __slots__ = ("x", "y", "speed", "length", "alpha")

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.x: float = random.randint(-100, SCREEN_W + 100)
        self.y: float = random.randint(-SCREEN_H, -10)
        self.speed: float = random.uniform(4, 9)
        self.length: int = random.randint(8, 22)
        self.alpha: int = random.randint(40, 100)

    def update(self) -> None:
        self.x += self.speed * 0.3
        self.y += self.speed
        if self.y > SCREEN_H + 10:
            self.reset()


class GlowParticle:
    """A floating ambient glow particle."""
    __slots__ = ("x", "y", "vx", "vy", "radius", "alpha", "color",
                 "life", "max_life")

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.x: float = random.uniform(-50, SCREEN_W + 50)
        self.y: float = random.uniform(50, SCREEN_H - 50)
        self.vx: float = random.uniform(-0.3, 0.3)
        self.vy: float = random.uniform(-0.5, -0.1)
        self.radius: float = random.uniform(1.5, 4)
        self.max_life: float = random.uniform(3.0, 7.0)
        self.life: float = random.uniform(0, self.max_life)
        self.color: tuple[int, int, int] = random.choice([
            (255, 215, 0), (180, 80, 255), (0, 200, 180), (80, 200, 255)
        ])
        self.alpha: int = 0

    def update(self, dt: float) -> None:
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

def draw_diamond(
    surface: pygame.Surface,
    cx: float, cy: float,
    size: int,
    color: tuple[int, int, int],
    glow_color: tuple[int, int, int],
    t: float,
) -> None:
    """Draw an animated floating diamond marker."""
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


# ─── Camera ──────────────────────────────────────────────────────────────────

class Camera:
    """Smooth-following isometric camera."""

    def __init__(self) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.target_x: float = 0.0
        self.target_y: float = 0.0
        self.smoothing: float = 3.5

    def update(self, player_col: float, player_row: float, dt: float) -> None:
        px = (player_col - player_row) * (TILE_W // 2) + SCREEN_W // 2
        py = (player_col + player_row) * (TILE_H // 2) + 100
        self.target_x = SCREEN_W // 2 - px
        self.target_y = SCREEN_H // 2 - py
        factor = 1.0 - math.exp(-self.smoothing * dt)
        self.x += (self.target_x - self.x) * factor
        self.y += (self.target_y - self.y) * factor


# ─── Sprite Loading ─────────────────────────────────────────────────────────

def _load_sprite_frames(
    path: str,
    cols: int = 5,
    rows: int = 5,
    scale: float = 0.45,
) -> tuple[list[pygame.Surface], int, int]:
    """Slice a sprite sheet into a flat list of all frames."""
    sheet = pygame.image.load(path).convert_alpha()
    sw, sh = sheet.get_size()
    fw, fh = sw // cols, sh // rows
    frames: list[pygame.Surface] = []
    for r in range(rows):
        for c in range(cols):
            rect = pygame.Rect(c * fw, r * fh, fw, fh)
            frame = sheet.subsurface(rect).copy()
            if scale != 1.0:
                nw, nh = int(fw * scale), int(fh * scale)
                frame = pygame.transform.smoothscale(frame, (nw, nh))
            frames.append(frame)
    return frames, int(fw * scale), int(fh * scale)


# ─── Player ──────────────────────────────────────────────────────────────────

class Player:
    """Animated isometric player character with sprite sheet support."""

    WALK_FPS: int = 12
    IDLE_FPS: int = 6

    def __init__(self, col: float, row: float) -> None:
        self.col: float = float(col)
        self.row: float = float(row)
        self.speed: float = 0.14
        self.trail: list[tuple[int, int]] = []

        self.flip: bool = False
        self.moving: bool = False
        self.anim_time: float = 0.0
        self.frame_idx: int = 0

        idle_path = os.path.join(ASSETS_DIR, "Asahi-idle.png")
        walk_path = os.path.join(ASSETS_DIR, "Asahi-walk.png")

        self._idle_frames, self._fw, self._fh = _load_sprite_frames(idle_path)
        self._walk_frames, _, _ = _load_sprite_frames(walk_path)

    def update(
        self,
        keys: pygame.key.ScancodeWrapper,
        blocked_cells: set[tuple[int, int]],
        dt: float = 0.016,
    ) -> None:
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
                self.flip = False
            elif dx < 0:
                self.flip = True
            else:
                self.flip = (dy > 0)

        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707

        new_col = max(0, min(MAP_COLS - 1, self.col + dx))
        new_row = max(0, min(MAP_ROWS - 1, self.row + dy))
        if (int(new_col), int(new_row)) not in blocked_cells:
            self.col = new_col
            self.row = new_row

        fps = self.WALK_FPS if self.moving else self.IDLE_FPS
        frames = self._walk_frames if self.moving else self._idle_frames
        self.anim_time += dt * fps
        self.frame_idx = int(self.anim_time) % len(frames)

        sx, sy = iso_to_screen(self.col, self.row)
        self.trail.append((sx, sy))
        if len(self.trail) > 16:
            self.trail.pop(0)

    def get_screen_pos(
        self,
        cam_x: float = 0, cam_y: float = 0,
        zoom: float = 1.0,
    ) -> tuple[int, int]:
        return iso_to_screen(self.col, self.row, cam_x, cam_y, zoom)

    def draw(
        self,
        surface: pygame.Surface,
        t: float,
        cam_x: float = 0, cam_y: float = 0,
        zoom: float = 1.0,
    ) -> None:
        sx, sy = self.get_screen_pos(cam_x, cam_y, zoom)

        # Trail
        for i, (tx_raw, ty_raw) in enumerate(self.trail):
            alpha = int(40 * (i / max(1, len(self.trail))))
            r = max(1, int(5 * (i / max(1, len(self.trail)))))
            trail_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*C_PLAYER_BODY, alpha), (r, r), r)
            surface.blit(trail_surf, (tx_raw + int(cam_x) - r,
                                      ty_raw + int(cam_y) - r))

        # Shadow
        shadow_w = int(36 * zoom)
        shadow_h = int(14 * zoom)
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 70), (0, 0, shadow_w, shadow_h))
        surface.blit(shadow_surf, (sx - shadow_w // 2, sy - shadow_h // 2 + 2))

        # Glow
        glow_r = (22 + math.sin(t * 4) * 3) * zoom
        glow_surf = pygame.Surface((int(glow_r * 4), int(glow_r * 4)), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*C_PLAYER_BODY, 18),
                           (int(glow_r * 2), int(glow_r * 2)), int(glow_r * 2))
        surface.blit(glow_surf, (sx - glow_r * 2, sy - glow_r * 2 - self._fh * zoom // 2))

        # Sprite
        frames = self._walk_frames if self.moving else self._idle_frames
        frame = frames[self.frame_idx]
        if self.flip:
            frame = pygame.transform.flip(frame, True, False)

        if zoom != 1.0:
            nw = max(1, int(self._fw * zoom))
            nh = max(1, int(self._fh * zoom))
            frame = pygame.transform.smoothscale(frame, (nw, nh))
            blit_x = sx - nw // 2
            blit_y = sy - nh + int(10 * zoom)
        else:
            blit_x = sx - self._fw // 2
            blit_y = sy - self._fh + 10
        surface.blit(frame, (blit_x, blit_y))

    def near_building(
        self,
        buildings: list[dict],
        threshold: float = 2.5,
    ) -> Optional[dict]:
        for b in buildings:
            center_col = b["col"] + b["size"] / 2
            center_row = b["row"] + b["size"] / 2
            dist = math.sqrt((self.col - center_col) ** 2 +
                             (self.row - center_row) ** 2)
            if dist < threshold:
                return b
        return None
