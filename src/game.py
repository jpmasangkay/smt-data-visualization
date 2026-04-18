"""Main Game class with all rendering, UI, and interaction logic.

Improvements integrated:
  #1  Animated building neon glow (per-frame rendering)
  #2  Ease-out panel transition + scrim overlay
  #3  Loading splash screen
  #4  Star twinkling animation
  #5  Chart descriptions in panel
  #6  Minimap building labels
  #7  Exploration progress bar
  #8  Camera zoom (mouse wheel)
  #11 Sound effect infrastructure
  #12 Day/night ambient cycle
  #13 FPS counter (F3 toggle)
  #14 Fullscreen toggle (F11)
"""
from __future__ import annotations

import math
import os
import random
import sys
import time
import threading
from typing import Optional

import pygame
import pandas as pd

from .constants import (
    SCREEN_W, SCREEN_H, FPS, TILE_W, TILE_H,
    MAP_COLS, MAP_ROWS, VISTA_PAD, ASSETS_DIR,
    C_BG, C_TILE, C_TILE_LINE, C_TILE_HIGHLIGHT,
    C_GOLD, C_GOLD_DIM, C_PURPLE, C_DEEP_PURPLE,
    C_TEAL, C_DARK_RED, C_YELLOW, C_WHITE, C_GREY,
    C_DARK_PANEL, C_HUD_BG, C_SCANLINE, C_RAIN,
    C_PLAYER_BODY, C_PLAYER_OUTLINE,
    C_NEON_PURPLE, C_NEON_GOLD, C_CYAN, C_PINK, C_EMERALD, C_ORANGE,
    BUILDINGS, LAMP_POSITIONS, PATH_TILES, DEFAULT_VIEWS,
    CHART_DESCRIPTIONS, MINIMAP_LABELS,
)
from .data_loader import load_data
from .world import (
    iso_to_screen, screen_to_iso,
    DECO_BUILDINGS, draw_iso_building,
)
from .renderer import render_scene_fast
from .charts import CHART_GENERATORS
from .scenes import SCENE_GENERATORS
from .entities import (
    RainDrop, GlowParticle, draw_diamond,
    Camera, Player,
)


class Game:
    """Main game loop with all rendering, UI, and interaction."""

    def __init__(self) -> None:
        pygame.init()
        self._sounds: dict[str, Optional[pygame.mixer.Sound]] = {}
        self._sound_enabled = False

        # (#14) Fullscreen state
        self._fullscreen = False
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(
            "THE MIDNIGHT CHANNEL — Persona 4 Data Explorer")
        self.clock = pygame.time.Clock()

        # (#3) Show loading splash before heavy init
        self._show_loading_screen("Entering the Midnight Channel...", 0.0, min_time=1.5)

        # (#11) Initialize sound AFTER display is created
        try:
            pygame.mixer.quit()  # Reset any auto-init from pygame.init()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self._sound_enabled = True
        except Exception:
            self._sound_enabled = False

        # Generate sounds if missing, then load UI sounds
        self._ensure_sounds_exist()
        self._load_sounds()

        # Fonts
        self.font_title = pygame.font.SysFont("Segoe UI", 30, bold=True)
        self.font_hud = pygame.font.SysFont("Segoe UI", 18)
        self.font_prompt = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.font_panel_title = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.font_panel_hint = pygame.font.SysFont("Segoe UI", 14)
        self.font_minimap = pygame.font.SysFont("Segoe UI", 11)
        self.font_stat = pygame.font.SysFont("Segoe UI", 14)
        self.font_zone = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.font_desc = pygame.font.SysFont("Segoe UI", 16)     # (#5) chart descriptions
        self.font_fps = pygame.font.SysFont("Consolas", 14)     # (#13) FPS counter

        # (#3) Progress update
        self._show_loading_screen("Loading Persona data...", 0.15, min_time=0.6)

        # Data
        self.data = load_data()

        self._show_loading_screen("Preparing city assets...", 0.35, min_time=0.5)

        # Extra building sprites
        try:
            _eb = pygame.image.load(os.path.join(ASSETS_DIR, "Extra_Buildings.png")).convert_alpha()
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
                os.path.join(ASSETS_DIR, "Lamps.png")).convert_alpha()
        except Exception:
            self.lamp_sprite = None

        # Distant city background image
        try:
            _dcb = pygame.image.load(
                os.path.join(ASSETS_DIR, "Distant_City_Background.png")).convert_alpha()
            _scale = SCREEN_W / _dcb.get_width()
            _dh = int(_dcb.get_height() * _scale)
            self.city_bg_sprite = pygame.transform.smoothscale(_dcb, (SCREEN_W, _dh))
        except Exception:
            self.city_bg_sprite = None

        # Building sprites — keyed by building "id"
        _SPRITE_MAP = {
            "velvet": "Velvet_Tower.png", "junes": "Junes.png",
            "connection": "Connection_Hub.png", "skill": "Skill_Arcade.png",
            "inherit": "Inheritance_Lab.png", "shadow": "Shadow_Den.png",
            "block": "Block_Fortress.png", "archive": "Persona_Archive.png",
            "fusion": "Fusion_Reactor.png", "oracle": "Oracle_Spire.png",
            "fate": "Fate_Compass.png", "shrine": "Element_Shrine.png",
        }
        self.building_sprites: dict[str, pygame.Surface] = {}
        for bid, fname in _SPRITE_MAP.items():
            path = os.path.join(ASSETS_DIR, fname)
            try:
                img = pygame.image.load(path).convert_alpha()
                self.building_sprites[bid] = img
            except Exception:
                pass

        self._show_loading_screen("Constructing the Midnight District...", 0.55, min_time=0.5)

        # Camera & Player
        self.camera = Camera()
        self.player = Player(10.0, 10.0)

        # Precompute blocked cells
        self._blocked_cells: set[tuple[int, int]] = set()
        for b in BUILDINGS + DECO_BUILDINGS:
            for dc in range(b["size"]):
                for dr in range(b["size"]):
                    self._blocked_cells.add((b["col"] + dc, b["row"] + dr))

        # Particles
        self.rain = [RainDrop() for _ in range(200)]
        self.glow_particles = [GlowParticle() for _ in range(50)]

        self._show_loading_screen("Rendering distant skyline...", 0.65, min_time=0.5)

        # Pre-render backdrop (and save bright star positions for #4 twinkling)
        self._bright_stars: list[tuple[int, int, int, tuple[int, int, int]]] = []
        self.backdrop = self._build_backdrop()

        self._show_loading_screen("Building city tilemap...", 0.80, min_time=0.5)

        # Pre-render city cache
        self._build_city_cache()

        # ── UI PNG assets ──
        self._vignette_png = None
        self._hud_png = None
        self._prompt_bubble_png = None

        _mapf = self._load_ui_asset("Map_Frame.png")
        if _mapf:
            c_color = _mapf.get_at((_mapf.get_width() // 2, _mapf.get_height() // 2))
            _mapf.set_colorkey(c_color)
            self._map_frame_png = _mapf
        else:
            self._map_frame_png = None

        self._vignette = self._build_vignette()

        # Scanline overlay
        self.scanline_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for y in range(0, SCREEN_H, 3):
            pygame.draw.line(self.scanline_surf, C_SCANLINE, (0, y), (SCREEN_W, y))

        # Fog
        self.fog_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for i in range(200):
            alpha = int(55 * (i / 200))
            pygame.draw.line(self.fog_surf, (18, 10, 45, alpha),
                             (0, SCREEN_H - i), (SCREEN_W, SCREEN_H - i))
        for i in range(90):
            alpha = int(22 * (1 - i / 90))
            pygame.draw.line(self.fog_surf, (20, 12, 48, alpha), (0, i), (SCREEN_W, i))

        self._show_loading_screen("Initializing data systems...", 0.95, min_time=0.5)

        # Final loading screen before entering
        self._show_loading_screen("Welcome to the Midnight Channel.", 1.0, min_time=1.2)

        # Chart panel state
        self.panel_open = False
        self.panel_slide = 0.0
        self.panel_target = 0.0
        self.current_chart_surface: Optional[pygame.Surface] = None
        self.current_building_name = ""
        self.current_building_accent = C_GOLD
        self.current_building_id = ""

        # 3D Chart rotation state
        self.chart_azim = 0.0
        self.chart_elev = 0.0
        self.chart_rotate_speed = 80.0
        self.chart_scene = None
        self.scene_cache: dict = {}

        # Chart cache
        self.chart_cache: dict = {}

        # Rotation key hold tracking
        self.rotating_left = False
        self.rotating_right = False
        self.rotating_up = False
        self.rotating_down = False

        # Background chart rendering
        self._bg_thread: Optional[threading.Thread] = None
        self._bg_result = None
        self._bg_lock = threading.Lock()

        # (#8) Camera zoom
        self.zoom: float = 1.0
        self.target_zoom: float = 1.0
        self._zoom_min: float = 0.6
        self._zoom_max: float = 1.8

        # (#13) FPS counter
        self._show_fps: bool = False

        # Time
        self.t: float = 0.0
        self.running: bool = True

        # Stats
        self.total_personas = len(self.data.get("personas", pd.DataFrame()))
        self.total_skills = len(self.data.get("skills", pd.DataFrame()))
        self.buildings_visited: set[str] = set()

        # (#11) Play SMT4 Tokyo OST background music
        if self._sound_enabled:
            _music = os.path.join(ASSETS_DIR, "sounds", "smt4_tokyo.wav")
            if os.path.exists(_music):
                try:
                    pygame.mixer.music.load(_music)
                    pygame.mixer.music.set_volume(0.35)
                    pygame.mixer.music.play(loops=-1)
                except Exception:
                    pass

    # ── Sound Infrastructure (#11) ────────────────────────────────────────────

    def _ensure_sounds_exist(self) -> None:
        """Generate procedural audio files if they don't exist."""
        sounds_dir = os.path.join(ASSETS_DIR, "sounds")
        ambient_path = os.path.join(sounds_dir, "ambient.wav")
        if not os.path.exists(ambient_path):
            try:
                from .sound_gen import generate_all_sounds
                self._show_loading_screen("Generating ambient soundtrack...", 0.08, min_time=0.3)
                generate_all_sounds(sounds_dir)
            except Exception as e:
                print(f"Warning: Could not generate sounds: {e}")

    def _load_sounds(self) -> None:
        """Load sound effects from assets, silently skip missing files."""
        if not self._sound_enabled:
            return
        sound_map = {
            "ambient": "ambient.wav",
            "interact": "interact.wav",
            "panel_open": "panel_open.wav",
            "panel_close": "panel_close.wav",
        }
        for key, fname in sound_map.items():
            path = os.path.join(ASSETS_DIR, "sounds", fname)
            try:
                if os.path.exists(path):
                    self._sounds[key] = pygame.mixer.Sound(path)
                else:
                    self._sounds[key] = None
            except Exception:
                self._sounds[key] = None

    def _play_sound(
        self, name: str, loops: int = 0, volume: float = 1.0,
    ) -> None:
        """Play a named sound if it exists."""
        snd = self._sounds.get(name)
        if snd is not None:
            snd.set_volume(volume)
            snd.play(loops=loops)

    # ── Loading Screen (#3) ──────────────────────────────────────────────────

    def _show_loading_screen(self, message: str, progress: float, min_time: float = 0.0) -> None:
        """Display a loading splash with message and progress bar.

        Args:
            min_time: Minimum seconds this screen stays visible.
        """
        _start = time.monotonic()
        self.screen.fill((8, 4, 28))

        # Animated TV static
        static_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        static_rng = random.Random(42 + int(progress * 100))
        for _ in range(800):
            sx = static_rng.randint(0, SCREEN_W)
            sy = static_rng.randint(0, SCREEN_H)
            a = static_rng.randint(3, 12)
            sz = static_rng.randint(1, 3)
            pygame.draw.rect(static_surf, (255, 255, 255, a), (sx, sy, sz, sz))
        self.screen.blit(static_surf, (0, 0))

        # Title
        font_big = pygame.font.SysFont("Segoe UI", 42, bold=True)
        font_sub = pygame.font.SysFont("Segoe UI", 18)
        font_msg = pygame.font.SysFont("Segoe UI", 16)

        title = font_big.render("T H E   M I D N I G H T   C H A N N E L", True, C_GOLD)
        tr = title.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 80))
        # Title glow
        glow = pygame.Surface((tr.width + 40, tr.height + 20), pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 215, 0, 12), glow.get_rect(), border_radius=10)
        self.screen.blit(glow, (tr.x - 20, tr.y - 10))
        self.screen.blit(title, tr)

        sub = font_sub.render("Persona 4 Golden — Data Explorer", True, (150, 140, 180))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 40)))

        # Progress bar
        bar_w, bar_h = 400, 6
        bar_x = SCREEN_W // 2 - bar_w // 2
        bar_y = SCREEN_H // 2 + 20
        # Background
        pygame.draw.rect(self.screen, (30, 20, 60), (bar_x, bar_y, bar_w, bar_h),
                         border_radius=3)
        # Fill
        fill_w = int(bar_w * min(1.0, progress))
        if fill_w > 0:
            # Gradient fill from gold to warm orange
            for px in range(fill_w):
                t = px / max(1, bar_w)
                r = int(255 * (1 - t * 0.3))
                g = int(215 * (1 - t * 0.4))
                b = int(0 + t * 60)
                pygame.draw.line(self.screen, (r, g, b),
                                 (bar_x + px, bar_y), (bar_x + px, bar_y + bar_h - 1))
        # Border
        pygame.draw.rect(self.screen, (255, 215, 0, 80), (bar_x, bar_y, bar_w, bar_h),
                         1, border_radius=3)

        # Message
        msg = font_msg.render(message, True, (120, 110, 150))
        self.screen.blit(msg, msg.get_rect(center=(SCREEN_W // 2, bar_y + 28)))

        # Percentage
        pct = font_msg.render(f"{int(progress * 100)}%", True, C_GOLD)
        self.screen.blit(pct, pct.get_rect(center=(SCREEN_W // 2, bar_y + 50)))

        pygame.display.flip()

        # Enforce minimum display time
        if min_time > 0:
            elapsed = time.monotonic() - _start
            remaining = min_time - elapsed
            if remaining > 0:
                pygame.time.wait(int(remaining * 1000))

    # ── UI Asset Loading ─────────────────────────────────────────────────────

    def _load_ui_asset(
        self, fname: str, crop: bool = True,
    ) -> Optional[pygame.Surface]:
        path = os.path.join(ASSETS_DIR, fname)
        if not os.path.exists(path):
            return None
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

    # ── Angle step for cache rounding ─────────────────────────────────────────
    _ANGLE_STEP: int = 10

    def _get_cache_key(self) -> tuple:
        s = self._ANGLE_STEP
        e = round(self.chart_elev / s) * s
        a = round(self.chart_azim / s) * s % 360
        return (self.current_building_id, e, a)

    def _render_current_chart(self) -> None:
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

    def _find_nearest_cached(self) -> Optional[pygame.Surface]:
        s = self._ANGLE_STEP
        e = round(self.chart_elev / s) * s
        a_cur = round(self.chart_azim / s) * s % 360
        bid = self.current_building_id
        exact = (bid, e, a_cur)
        if exact in self.chart_cache:
            return self.chart_cache[exact]
        for offset in range(s, 60, s):
            for sign in (1, -1):
                test_a = (a_cur + sign * offset) % 360
                key = (bid, e, test_a)
                if key in self.chart_cache:
                    return self.chart_cache[key]
        return None

    def _show_nearest_cached(self) -> None:
        key = self._get_cache_key()
        if key in self.chart_cache:
            self.current_chart_surface = self.chart_cache[key]
            return
        nearest = self._find_nearest_cached()
        if nearest is not None:
            self.current_chart_surface = nearest

    def _request_chart_render_async(self) -> None:
        key = self._get_cache_key()
        if key in self.chart_cache:
            self.current_chart_surface = self.chart_cache[key]
            return
        if self._bg_thread is not None and self._bg_thread.is_alive():
            return
        gen = CHART_GENERATORS.get(self.current_building_id)
        if gen:
            _, e, a = key
            self._bg_thread = threading.Thread(
                target=self._bg_render_chart,
                args=(gen, e, a, key), daemon=True)
            self._bg_thread.start()

    def _bg_render_chart(self, gen, elev, azim, cache_key) -> None:
        try:
            surf = gen(self.data, elev=elev, azim=azim)
        except Exception:
            surf = None
        with self._bg_lock:
            self._bg_result = (cache_key, surf)

    def _collect_bg_render(self) -> None:
        with self._bg_lock:
            if self._bg_result is None:
                return
            key, surf = self._bg_result
            self._bg_result = None
        if surf is not None:
            self._cache_put(key, surf)
            if key[0] == self.current_building_id:
                self.current_chart_surface = surf

    def _cache_put(self, key: tuple, surf: pygame.Surface) -> None:
        if len(self.chart_cache) > 200:
            evict = list(self.chart_cache.keys())[:100]
            for k in evict:
                del self.chart_cache[k]
        self.chart_cache[key] = surf

    # ── Event Handling ───────────────────────────────────────────────────────

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.panel_open:
                        self.panel_target = 0.0
                        self.panel_open = False
                        self.rotating_left = self.rotating_right = False
                        self.rotating_up = self.rotating_down = False
                        self._play_sound("panel_close", volume=0.5)
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

                            defaults = DEFAULT_VIEWS.get(
                                nearby["id"], {"elev": 25, "azim": 135})
                            self.chart_elev = defaults["elev"]
                            self.chart_azim = defaults["azim"]

                            with self._bg_lock:
                                self._bg_result = None

                            bid = nearby["id"]
                            if bid not in self.scene_cache:
                                sg = SCENE_GENERATORS.get(bid)
                                if sg:
                                    self.scene_cache[bid] = sg(self.data)
                            self.chart_scene = self.scene_cache.get(bid)

                            if self.chart_scene is not None:
                                self.current_chart_surface = render_scene_fast(
                                    self.chart_scene, self.chart_elev,
                                    self.chart_azim, 900, 600,
                                    self.font_panel_title)
                            else:
                                self.current_chart_surface = None

                            self._request_chart_render_async()
                            self.panel_open = True
                            self.panel_target = 1.0
                            self._play_sound("panel_open", volume=0.5)

                # (#13) FPS counter toggle
                elif event.key == pygame.K_F3:
                    self._show_fps = not self._show_fps

                # (#14) Fullscreen toggle
                elif event.key == pygame.K_F11:
                    self._fullscreen = not self._fullscreen
                    if self._fullscreen:
                        self.screen = pygame.display.set_mode(
                            (SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
                    else:
                        self.screen = pygame.display.set_mode(
                            (SCREEN_W, SCREEN_H))

                # Chart rotation keys
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

            # (#8) Mouse wheel zoom
            elif event.type == pygame.MOUSEWHEEL:
                if not self.panel_open:
                    self.target_zoom += event.y * 0.1
                    self.target_zoom = max(self._zoom_min,
                                           min(self._zoom_max, self.target_zoom))

    # ── Update ───────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self.t += dt
        self.camera.update(self.player.col, self.player.row, dt)

        if not self.panel_open:
            keys = pygame.key.get_pressed()
            self.player.update(keys, self._blocked_cells, dt)

        # Chart rotation
        if self.panel_open:
            rotated = False
            if self.rotating_left:
                self.chart_azim += self.chart_rotate_speed * dt
                rotated = True
            if self.rotating_right:
                self.chart_azim -= self.chart_rotate_speed * dt
                rotated = True
            if self.rotating_up:
                self.chart_elev = min(60, self.chart_elev + self.chart_rotate_speed * dt * 0.5)
                rotated = True
            if self.rotating_down:
                self.chart_elev = max(5, self.chart_elev - self.chart_rotate_speed * dt * 0.5)
                rotated = True

            if rotated:
                self.chart_azim %= 360
                if self.chart_scene is not None:
                    self.current_chart_surface = render_scene_fast(
                        self.chart_scene, self.chart_elev, self.chart_azim,
                        900, 600, self.font_panel_title)
                else:
                    self._show_nearest_cached()

            self._collect_bg_render()

        # Rain
        for drop in self.rain:
            drop.update()

        # Glow particles
        for p in self.glow_particles:
            p.update(dt)

        # (#2) Ease-out panel slide (exponential decay)
        diff = self.panel_target - self.panel_slide
        self.panel_slide += diff * min(1.0, 8.0 * dt)
        if abs(diff) < 0.002:
            self.panel_slide = self.panel_target

        # (#8) Smooth zoom interpolation
        zoom_diff = self.target_zoom - self.zoom
        self.zoom += zoom_diff * min(1.0, 6.0 * dt)
        if abs(zoom_diff) < 0.002:
            self.zoom = self.target_zoom

    # ── Backdrop (sky, stars, mountains) ─────────────────────────────────────

    def _build_backdrop(self) -> pygame.Surface:
        bg = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        # Gradient sky
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            r = int(8 + t * 12)
            g = int(4 + t * 14)
            b = int(28 + t * 30)
            pygame.draw.line(bg, (r, g, b), (0, y), (SCREEN_W, y))
        # Stars (#4 — track bright ones for twinkling)
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
                # (#4) Save bright star positions for twinkling
                self._bright_stars.append((sx, sy, size, tint))

        # Aurora bands
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

        # Mountain layers
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
            pygame.draw.polygon(mtn_surf, (col_val, col_val - 2, col_b, alpha), pts)
            bg.blit(mtn_surf, (0, 0))

        # Distant city background image
        if self.city_bg_sprite is not None:
            _cw, _ch = self.city_bg_sprite.get_size()
            _cy = int(SCREEN_H * 0.60) - _ch
            _tinted = self.city_bg_sprite.copy()
            _tinted.fill((20, 10, 50, 60), special_flags=pygame.BLEND_RGBA_ADD)
            bg.blit(_tinted, (0, _cy))
        else:
            sil_rng = random.Random(777)
            sil_y = int(SCREEN_H * 0.55)
            for sx in range(0, SCREEN_W, 12):
                bh = sil_rng.randint(8, 65)
                bw = sil_rng.randint(6, 14)
                col_v = sil_rng.randint(14, 28)
                pygame.draw.rect(bg, (col_v, col_v - 2, col_v + 18, 150),
                                 (sx, sil_y - bh, bw, bh))
        return bg

    # ── City Cache ───────────────────────────────────────────────────────────

    def _build_city_cache(self) -> None:
        """Pre-render the city (tiles + buildings) to a cached surface.

        (#1) Interactive buildings are excluded from cache so they can
        be drawn per-frame with animated neon glow.
        """
        c_min, c_max = -VISTA_PAD, MAP_COLS + VISTA_PAD
        r_min, r_max = -VISTA_PAD, MAP_ROWS + VISTA_PAD

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
        y1 = min(ys) - TILE_H - 240
        y2 = max(ys) + TILE_H + 40

        surf_w = int(x2 - x1)
        surf_h = int(y2 - y1)
        self._cache_ox = int(x1)
        self._cache_oy = int(y1)

        ccx = -self._cache_ox
        ccy = -self._cache_oy

        cache = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

        # ── Tiles ──
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

                if is_isect:
                    cw_s = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    for si in range(4):
                        t_s = 0.2 + si * 0.2
                        lp1 = (int(TILE_W * 0.3), int(TILE_H * t_s))
                        lp2 = (int(TILE_W * 0.7), int(TILE_H * t_s))
                        pygame.draw.line(cw_s, (190, 185, 220, 40), lp1, lp2, 2)
                    cache.blit(cw_s, (sx - TILE_W // 2, sy - TILE_H // 2))

                if is_road and not is_isect and rng.random() < 0.035:
                    mh_s = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
                    pygame.draw.circle(mh_s, (38, 32, 58, 90),
                                       (TILE_W // 2, TILE_H // 2), 5)
                    pygame.draw.circle(mh_s, (58, 52, 82, 70),
                                       (TILE_W // 2, TILE_H // 2), 5, 1)
                    pygame.draw.circle(mh_s, (48, 42, 72, 50),
                                       (TILE_W // 2, TILE_H // 2), 3)
                    cache.blit(mh_s, (sx - TILE_W // 2, sy - TILE_H // 2))

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
                    cx_c = TILE_W // 2 + crack_rng.randint(-8, 8)
                    cy_c = TILE_H // 2 + crack_rng.randint(-3, 3)
                    for _ in range(crack_rng.randint(2, 4)):
                        ddx = crack_rng.randint(-7, 7)
                        ddy = crack_rng.randint(-3, 3)
                        pygame.draw.line(cs, (18, 12, 35, 80),
                                         (cx_c, cy_c), (cx_c + ddx, cy_c + ddy), 1)
                        cx_c += ddx; cy_c += ddy
                    cache.blit(cs, (sx - TILE_W // 2, sy - TILE_H // 2))

        # ── Buildings (depth-sorted) ──
        # (#1) Only DECO buildings go in cache; interactive buildings rendered per-frame
        all_b: list[dict] = list(DECO_BUILDINGS)
        all_b.sort(key=lambda b: b["col"] + b["row"])

        for b in all_b:
            bid = b.get("id", "")
            sprite = self.building_sprites.get(bid)
            if sprite is not None:
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

    # ── Per-frame interactive building rendering (#1) ─────────────────────────

    def _draw_interactive_buildings(self) -> None:
        """Draw interactive buildings per-frame with animated neon glow.

        Render order per building: ground neon pool → sprite → neon tint overlay.
        This creates a breathing, living effect on data buildings.
        """
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        neon_pulse = 0.5 + 0.5 * math.sin(self.t * 2.0)
        fast_pulse = 0.5 + 0.5 * math.sin(self.t * 4.0)

        # Depth-sort buildings
        sorted_buildings = sorted(BUILDINGS, key=lambda b: b["col"] + b["row"])

        for b in sorted_buildings:
            bid = b.get("id", "")
            size = b["size"]
            accent = b["accent"]

            # Compute footprint corners
            tl = iso_to_screen(b["col"],        b["row"],        cam_x, cam_y, self.zoom)
            tr = iso_to_screen(b["col"] + size, b["row"],        cam_x, cam_y, self.zoom)
            bl = iso_to_screen(b["col"],        b["row"] + size, cam_x, cam_y, self.zoom)
            br = iso_to_screen(b["col"] + size, b["row"] + size, cam_x, cam_y, self.zoom)
            foot_cx = (tl[0] + br[0]) / 2
            foot_cy = max(tl[1], tr[1], bl[1], br[1])
            center_x = sum(p[0] for p in [tl, tr, bl, br]) / 4
            center_y = sum(p[1] for p in [tl, tr, bl, br]) / 4

            # Skip off-screen buildings
            if center_x < -300 or center_x > SCREEN_W + 300:
                continue
            if center_y < -300 or center_y > SCREEN_H + 300:
                continue

            # ── 1) Building sprite ──
            sprite = self.building_sprites.get(bid)
            if sprite is not None:
                foot_w = int(abs(tr[0] - tl[0]) + abs(bl[0] - br[0]))
                scale_f = foot_w / sprite.get_width() * 1.6
                new_w = max(1, int(sprite.get_width() * scale_f))
                new_h = max(1, int(sprite.get_height() * scale_f))
                scaled = pygame.transform.smoothscale(sprite, (new_w, new_h))
                blit_x = int(foot_cx - new_w / 2)
                blit_y = int(foot_cy - new_h)
                self.screen.blit(scaled, (blit_x, blit_y))
            else:
                # Fallback procedural building with animated pulse
                draw_iso_building(
                    self.screen, b["col"], b["row"],
                    b["color"], b["accent"], b["height"], b["size"],
                    cam_x, cam_y, neon_pulse, self.zoom)

            # ── 2) Neon glow outline at building base (drawn AFTER sprite) ──
            # Thin pulsing isometric diamond outline at ground level
            iso_pts = [
                (int(tl[0]), int(tl[1])),
                (int(tr[0]), int(tr[1])),
                (int(br[0]), int(br[1])),
                (int(bl[0]), int(bl[1])),
            ]
            # Outer glow (thicker, more transparent)
            glow_a = int(40 + neon_pulse * 60)
            glow_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            pygame.draw.polygon(glow_surf, (*accent[:3], glow_a // 3), iso_pts, 4)
            pygame.draw.polygon(glow_surf, (*accent[:3], glow_a), iso_pts, 2)
            self.screen.blit(glow_surf, (0, 0))

            # Small glow dot at the center base
            dot_r = int(6 * self.zoom)
            if dot_r > 1:
                dot_surf = pygame.Surface((dot_r * 6, dot_r * 4), pygame.SRCALPHA)
                dot_a = int(30 + neon_pulse * 50)
                pygame.draw.ellipse(dot_surf, (*accent[:3], dot_a),
                                    (0, 0, dot_r * 6, dot_r * 4))
                self.screen.blit(dot_surf,
                                 (int(foot_cx) - dot_r * 3,
                                  int(foot_cy) - dot_r * 2))

    # ── Drawing Helpers ──────────────────────────────────────────────────────

    def _draw_building_markers(self) -> None:
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        for b in BUILDINGS:
            size = b["size"]
            corners = [
                iso_to_screen(b["col"], b["row"], cam_x, cam_y, self.zoom),
                iso_to_screen(b["col"] + size, b["row"], cam_x, cam_y, self.zoom),
                iso_to_screen(b["col"] + size, b["row"] + size, cam_x, cam_y, self.zoom),
                iso_to_screen(b["col"], b["row"] + size, cam_x, cam_y, self.zoom),
            ]
            scaled_h = int(b["height"] * self.zoom)
            top = [(x, y - scaled_h) for x, y in corners]
            cx = sum(p[0] for p in top) / 4
            cy = min(p[1] for p in top) - 20
            if cx < -120 or cx > SCREEN_W + 120 or cy < -120 or cy > SCREEN_H + 120:
                continue

            draw_diamond(self.screen, cx, cy, 10, C_GOLD, C_GOLD_DIM, self.t)

            ns = self.font_prompt.render(b["name"], True, b["accent"])
            nr = ns.get_rect(center=(cx, cy - 22))
            bg = pygame.Surface((nr.width + 16, nr.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, 160), bg.get_rect(), border_radius=5)
            pygame.draw.rect(bg, (*b["accent"][:3], 80),
                             bg.get_rect(), 1, border_radius=5)
            self.screen.blit(bg, (nr.x - 8, nr.y - 4))
            self.screen.blit(ns, nr)

    def draw_rain(self) -> None:
        rain_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for drop in self.rain:
            ex = drop.x + drop.length * 0.3
            ey = drop.y + drop.length
            pygame.draw.line(rain_surf, (*C_RAIN[:3], drop.alpha),
                             (int(drop.x), int(drop.y)),
                             (int(ex), int(ey)), 1)
        self.screen.blit(rain_surf, (0, 0))

    def draw_glow_particles(self) -> None:
        for p in self.glow_particles:
            if p.alpha <= 0:
                continue
            r = max(1, int(p.radius))
            s = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p.color, p.alpha // 3), (r * 3, r * 3), r * 3)
            pygame.draw.circle(s, (*p.color, min(255, p.alpha)), (r * 3, r * 3), r)
            self.screen.blit(s, (int(p.x) - r * 3, int(p.y) - r * 3))

    def draw_fog(self) -> None:
        self.screen.blit(self.fog_surf, (0, 0))

    def draw_street_lamps(self) -> None:
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        for lcol, lrow in LAMP_POSITIONS:
            sx, sy = iso_to_screen(lcol, lrow, cam_x, cam_y, self.zoom)
            if sx < -60 or sx > SCREEN_W + 60 or sy < -80 or sy > SCREEN_H + 60:
                continue

            pulse = 0.8 + 0.2 * math.sin(self.t * 1.5 + lcol * 0.7 + lrow)

            # Ground light pool
            pw, ph = int(44 * self.zoom), int(18 * self.zoom)
            ps = pygame.Surface((pw, ph), pygame.SRCALPHA)
            pool_a = int(18 * pulse)
            pygame.draw.ellipse(ps, (255, 220, 140, pool_a), (0, 0, pw, ph))
            pygame.draw.ellipse(ps, (255, 230, 160, pool_a + 6),
                                (pw // 4, ph // 4, pw // 2, ph // 2))
            self.screen.blit(ps, (sx - pw // 2, sy - ph // 2 + 2))

            # Lamp sprite
            lamp_h = int(52 * self.zoom)
            if self.lamp_sprite is not None:
                _lw = self.lamp_sprite.get_width()
                _lh = self.lamp_sprite.get_height()
                _sc = lamp_h / _lh
                _nw = max(1, int(_lw * _sc))
                _nh = lamp_h
                _scaled = pygame.transform.smoothscale(self.lamp_sprite, (_nw, _nh))
                self.screen.blit(_scaled, (sx - _nw // 2, sy - _nh))
                head_y = sy - _nh + int(_nh * 0.18)
            else:
                post_col = (55, 45, 75)
                pygame.draw.line(self.screen, post_col, (sx, sy), (sx, sy - lamp_h), 2)
                pygame.draw.circle(self.screen, (75, 65, 95), (sx, sy - lamp_h), 4)
                head_y = sy - lamp_h

            # Warm glow
            glow_r = int(30 * pulse * self.zoom)
            if glow_r > 0:
                gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(gs, (255, 220, 120, int(28 * pulse)),
                                   (glow_r, glow_r), glow_r)
                pygame.draw.circle(gs, (255, 235, 150, int(55 * pulse)),
                                   (glow_r, glow_r), int(glow_r * 0.55))
                pygame.draw.circle(gs, (255, 245, 200, int(90 * pulse)),
                                   (glow_r, glow_r), int(glow_r * 0.25))
                self.screen.blit(gs, (sx - glow_r, head_y - glow_r))

    def draw_proximity_prompt(self) -> None:
        nearby = self.player.near_building(BUILDINGS)
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        if nearby and not self.panel_open:
            px, py = self.player.get_screen_pos(cam_x, cam_y, self.zoom)
            text = "[ Press E to Investigate ]"
            surf = self.font_prompt.render(text, True, C_GOLD)
            rect = surf.get_rect(center=(px, py - 36))
            pulse = int(180 + math.sin(self.t * 4) * 30)

            bg = pygame.Surface((rect.width + 20, rect.height + 10), pygame.SRCALPHA)
            pygame.draw.rect(bg, (0, 0, 0, pulse), bg.get_rect(), border_radius=8)
            pygame.draw.rect(bg, (*C_GOLD, 120), bg.get_rect(), 1, border_radius=8)
            self.screen.blit(bg, (rect.x - 10, rect.y - 5))
            self.screen.blit(surf, rect)

    def _hud_text_shadow(self, hud, font, text, color, x, y) -> None:
        shadow = font.render(text, True, (0, 0, 0))
        hud.blit(shadow, (x + 1, y + 1))
        hud.blit(shadow, (x + 2, y + 2))
        main = font.render(text, True, color)
        hud.blit(main, (x, y))

    def draw_hud(self) -> None:
        hud_h = 56
        hud = pygame.Surface((SCREEN_W, hud_h), pygame.SRCALPHA)

        pygame.draw.rect(hud, (8, 4, 24, 230), (0, 0, SCREEN_W, hud_h))
        pygame.draw.line(hud, (*C_GOLD, 140), (0, 0), (SCREEN_W, 0), 2)
        pygame.draw.line(hud, (255, 255, 255, 30), (0, 2), (SCREEN_W, 2), 1)

        nearby = self.player.near_building(BUILDINGS)
        zone_name = nearby["name"] if nearby else "Midnight District"
        zone_color = nearby["accent"] if nearby else C_GOLD

        # Diamond icon
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

        self._hud_text_shadow(hud, self.font_zone, zone_name, zone_color,
                              diamond_x + diamond_size + 10, hud_h // 2 - 13)

        explored = len(self.buildings_visited)
        total_buildings = len(BUILDINGS)
        stats = (f"Personas: {self.total_personas}  |  "
                 f"Skills: {self.total_skills}  |  "
                 f"Explored: {explored}/{total_buildings}")
        self._hud_text_shadow(hud, self.font_stat, stats, (180, 180, 200),
                              SCREEN_W // 2 - self.font_stat.size(stats)[0] // 2, 4)

        # (#7) Exploration progress bar
        bar_w = 160
        bar_h = 4
        bar_x = SCREEN_W // 2 - bar_w // 2
        bar_y = 22
        pygame.draw.rect(hud, (40, 30, 70, 180), (bar_x, bar_y, bar_w, bar_h),
                         border_radius=2)
        fill_w = int(bar_w * explored / max(1, total_buildings))
        if fill_w > 0:
            # Gold gradient fill
            for px in range(fill_w):
                t_p = px / max(1, bar_w)
                r = int(255 - t_p * 40)
                g = int(215 - t_p * 30)
                b = int(0 + t_p * 80)
                pygame.draw.line(hud, (r, g, b),
                                 (bar_x + px, bar_y), (bar_x + px, bar_y + bar_h - 1))
        pygame.draw.rect(hud, (*C_GOLD, 60), (bar_x, bar_y, bar_w, bar_h),
                         1, border_radius=2)

        # Flash gold when all explored
        if explored >= total_buildings:
            flash_a = int(15 + 10 * math.sin(self.t * 3))
            flash_s = pygame.Surface((bar_w + 10, bar_h + 10), pygame.SRCALPHA)
            pygame.draw.rect(flash_s, (*C_GOLD, flash_a),
                             (0, 0, bar_w + 10, bar_h + 10), border_radius=4)
            hud.blit(flash_s, (bar_x - 5, bar_y - 5))

        ctrl = "WASD: Move  |  E: Investigate  |  ESC: Close/Quit  |  Scroll: Zoom"
        self._hud_text_shadow(hud, self.font_stat, ctrl, (120, 120, 145),
                              SCREEN_W // 2 - self.font_stat.size(ctrl)[0] // 2, 30)

        self.screen.blit(hud, (0, SCREEN_H - hud_h))

    def draw_minimap(self) -> None:
        mm_w, mm_h = 220, 220
        mm_x = SCREEN_W - mm_w - 18
        mm_y = 18

        if self._map_frame_png is not None:
            pad = 16
            frame_w = mm_w + pad * 2
            frame_h = mm_h + pad * 2
            frame = pygame.transform.smoothscale(self._map_frame_png, (frame_w, frame_h))
            self.screen.blit(frame, (mm_x - pad, mm_y - pad))

        mm = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
        pygame.draw.rect(mm, (8, 4, 28, 255), (0, 0, mm_w, mm_h), border_radius=6)
        pygame.draw.rect(mm, (255, 255, 255, 15), (0, 0, mm_w, mm_h), border_radius=6)

        title = self.font_minimap.render("MIDNIGHT MAP", True, C_GOLD)
        mm.blit(title, (mm_w // 2 - title.get_width() // 2, 5))

        sx_scale = (mm_w - 24) / MAP_COLS
        sy_scale = (mm_h - 32) / MAP_ROWS
        ox, oy = 12, 24

        for r in range(0, MAP_ROWS, 2):
            for c in range(0, MAP_COLS, 2):
                px = int(ox + c * sx_scale + sx_scale / 2)
                py = int(oy + r * sy_scale + sy_scale / 2)
                pygame.draw.circle(mm, (40, 30, 60), (px, py), 1)

        for b in BUILDINGS:
            bx = int(ox + b["col"] * sx_scale)
            by = int(oy + b["row"] * sy_scale)
            bw = max(4, int(b["size"] * sx_scale))
            bh = max(4, int(b["size"] * sy_scale))
            col = b["accent"]
            if b["id"] in self.buildings_visited:
                gs = pygame.Surface((bw + 4, bh + 4), pygame.SRCALPHA)
                pygame.draw.rect(gs, (*col[:3], 40), (0, 0, bw + 4, bh + 4),
                                 border_radius=2)
                mm.blit(gs, (bx - 2, by - 2))
            pygame.draw.rect(mm, col, (bx, by, bw, bh))
            pygame.draw.rect(mm, (255, 255, 255, 60), (bx, by, bw, bh), 1)

            # (#6) Minimap building labels
            label = MINIMAP_LABELS.get(b["id"], "")
            if label:
                lbl_surf = self.font_minimap.render(label, True, (*col[:3],))
                lbl_x = bx + bw + 2
                lbl_y = by + bh // 2 - lbl_surf.get_height() // 2
                # Clamp to minimap bounds
                if lbl_x + lbl_surf.get_width() > mm_w - 4:
                    lbl_x = bx - lbl_surf.get_width() - 2
                mm.blit(lbl_surf, (lbl_x, lbl_y))

        for b in DECO_BUILDINGS:
            bx = int(ox + b["col"] * sx_scale)
            by = int(oy + b["row"] * sy_scale)
            bw = max(2, int(b.get("size", 1) * sx_scale))
            bh = max(2, int(b.get("size", 1) * sy_scale))
            pygame.draw.rect(mm, (40, 30, 60), (bx, by, bw, bh))

        # Player dot
        ppx = int(ox + self.player.col * sx_scale + sx_scale / 2)
        ppy = int(oy + self.player.row * sy_scale + sy_scale / 2)
        pulse = int(4 + math.sin(self.t * 5) * 2)
        pygame.draw.circle(mm, (80, 200, 255, 50), (ppx, ppy), pulse + 3)
        pygame.draw.circle(mm, C_PLAYER_BODY, (ppx, ppy), 3)
        pygame.draw.circle(mm, (255, 255, 255), (ppx, ppy), 3, 1)

        self.screen.blit(mm, (mm_x, mm_y))

    def draw_title(self) -> None:
        text = "T H E   M I D N I G H T   C H A N N E L"
        surf = self.font_title.render(text, True, C_GOLD)
        rect = surf.get_rect(center=(SCREEN_W // 2, 32))
        bg = pygame.Surface((rect.width + 40, rect.height + 14), pygame.SRCALPHA)
        pygame.draw.rect(bg, (255, 215, 0, 10), bg.get_rect(), border_radius=8)
        self.screen.blit(bg, (rect.x - 20, rect.y - 7))
        self.screen.blit(surf, rect)

        sub = self.font_hud.render(
            "Persona 4 Golden — Data Explorer", True, (150, 140, 180))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, 58)))

    def draw_chart_panel(self) -> None:
        if self.panel_slide <= 0.01:
            return

        panel_w = int(SCREEN_W * 0.72)
        slide_off = int(panel_w * (1.0 - self.panel_slide))
        panel_x = SCREEN_W - panel_w + slide_off

        # (#2) Scrim overlay — darken world behind panel
        scrim_alpha = int(120 * self.panel_slide)
        scrim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        pygame.draw.rect(scrim, (0, 0, 0, scrim_alpha), (0, 0, SCREEN_W, SCREEN_H))
        self.screen.blit(scrim, (0, 0))

        panel = pygame.Surface((panel_w, SCREEN_H), pygame.SRCALPHA)

        # Glassmorphism
        pygame.draw.rect(panel, (10, 6, 30, 200), (0, 0, panel_w, SCREEN_H))
        pygame.draw.rect(panel, (255, 255, 255, 8), (0, 0, panel_w, SCREEN_H))

        accent = self.current_building_accent
        # Left accent strip
        strip_w = 32
        for i in range(strip_w):
            a = int(80 * (1 - i / strip_w))
            pygame.draw.line(panel, (*accent[:3], a), (i, 0), (i, SCREEN_H))

        # Vertical building name
        title = self.font_panel_title.render(self.current_building_name, True, accent)
        title_rot = pygame.transform.rotate(title, 90)
        tr = title_rot.get_rect(center=(strip_w // 2 + 2, SCREEN_H // 2))
        tbg = pygame.Surface((tr.width + 8, tr.height + 16), pygame.SRCALPHA)
        pygame.draw.rect(tbg, (*accent[:3], 20), tbg.get_rect(), border_radius=6)
        panel.blit(tbg, (tr.x - 4, tr.y - 8))
        panel.blit(title_rot, tr)

        content_x = strip_w + 10
        content_w = panel_w - content_x - 10

        # Chart
        if self.current_chart_surface:
            chart = self.current_chart_surface
            avail_w = content_w
            avail_h = SCREEN_H - 140  # Leave room for description
            cw, ch = chart.get_size()
            scale = min(avail_w / cw, avail_h / ch)
            nw = int(cw * scale)
            nh = int(ch * scale)
            scaled = pygame.transform.smoothscale(chart, (nw, nh))
            cx = content_x + (content_w - nw) // 2
            cy = 20

            container = pygame.Surface((nw + 8, nh + 8), pygame.SRCALPHA)
            pygame.draw.rect(container, (255, 255, 255, 8),
                             (0, 0, nw + 8, nh + 8), border_radius=6)
            pygame.draw.rect(container, (*accent[:3], 40),
                             (0, 0, nw + 8, nh + 8), 1, border_radius=6)
            panel.blit(container, (cx - 4, cy - 4))
            panel.blit(scaled, (cx, cy))

            # (#5) Chart description — made prominent and readable
            desc = CHART_DESCRIPTIONS.get(self.current_building_id, "")
            if desc:
                desc_y = cy + nh + 12
                # Word wrap at content width using larger font
                words = desc.split()
                lines: list[str] = []
                current_line = ""
                for word in words:
                    test = current_line + (" " if current_line else "") + word
                    if self.font_desc.size(test)[0] > content_w - 40:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                    else:
                        current_line = test
                if current_line:
                    lines.append(current_line)
                # Background pill for readability
                line_h = 22
                total_h = len(lines[:3]) * line_h + 18
                desc_bg = pygame.Surface((content_w - 10, total_h), pygame.SRCALPHA)
                pygame.draw.rect(desc_bg, (0, 0, 0, 140),
                                 desc_bg.get_rect(), border_radius=6)
                pygame.draw.rect(desc_bg, (*accent[:3], 80),
                                 desc_bg.get_rect(), 1, border_radius=6)
                panel.blit(desc_bg, (content_x + 5, desc_y - 4))
                for i_l, line in enumerate(lines[:3]):
                    # Shadow for readability
                    ls_shadow = self.font_desc.render(line, True, (0, 0, 0))
                    panel.blit(ls_shadow, (content_x + 17, desc_y + 6 + i_l * line_h))
                    ls = self.font_desc.render(line, True, (255, 250, 240))
                    panel.blit(ls, (content_x + 16, desc_y + 5 + i_l * line_h))

        # Rotation indicator
        content_center = content_x + content_w // 2
        rot_text = f"Azim: {int(self.chart_azim)}°  Elev: {int(self.chart_elev)}°"
        rot_surf = self.font_stat.render(rot_text, True, (120, 120, 150))
        panel.blit(rot_surf, (content_center - rot_surf.get_width() // 2, SCREEN_H - 60))

        # Controls hint
        hint = "← → Rotate   ↑ ↓ Tilt   ESC Close"
        h_surf = self.font_panel_hint.render(hint, True, C_GREY)
        hr = h_surf.get_rect(center=(content_center, SCREEN_H - 28))
        pill = pygame.Surface((hr.width + 24, hr.height + 10), pygame.SRCALPHA)
        pygame.draw.rect(pill, (255, 255, 255, 12), pill.get_rect(), border_radius=12)
        pygame.draw.rect(pill, (255, 255, 255, 30), pill.get_rect(), 1, border_radius=12)
        panel.blit(pill, (hr.x - 12, hr.y - 5))
        panel.blit(h_surf, hr)

        self.screen.blit(panel, (panel_x, 0))

    def _build_vignette(self) -> pygame.Surface:
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
                             (SCREEN_W - 1 - i, 0), (SCREEN_W - 1 - i, SCREEN_H))
        return vig

    def draw_vignette(self) -> None:
        if self._vignette_png is not None:
            self.screen.blit(self._vignette_png, (0, 0))
        else:
            self.screen.blit(self._vignette, (0, 0))

    # ── (#4) Star Twinkling ──────────────────────────────────────────────────

    def _draw_twinkling_stars(self) -> None:
        """Animate ~20 bright stars with pulsing alpha glow."""
        if not self._bright_stars:
            return
        twinkle_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for sx, sy, size, tint in self._bright_stars:
            # Each star has its own phase offset based on position
            phase = self.t * 2.5 + sx * 0.013 + sy * 0.017
            pulse = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(phase))
            glow_r = int((6 + size * 3) * pulse)
            glow_a = int(35 * pulse)
            if glow_r > 0:
                pygame.draw.circle(twinkle_surf, (*tint, glow_a),
                                   (sx, sy), glow_r)
                # Inner bright core
                core_a = int(80 * pulse)
                pygame.draw.circle(twinkle_surf, (*tint, core_a),
                                   (sx, sy), max(1, glow_r // 3))
        self.screen.blit(twinkle_surf, (0, 0))

    # ── (#12) Day/Night Ambient Cycle ────────────────────────────────────────

    def _draw_day_night_cycle(self) -> None:
        """Apply a visible ambient color tint that shifts between warm twilight and cool deep-night."""
        cycle_t = (self.t * 0.025) % 1.0  # Full cycle ~40 seconds (more noticeable)
        twilight = 0.5 + 0.5 * math.sin(cycle_t * 2 * math.pi)
        deep_night = 1.0 - twilight

        # Twilight phase: warm amber-purple tint
        # Deep night phase: cold blue-purple tint
        tint_r = int(35 * twilight + 5 * deep_night)
        tint_g = int(10 * twilight + 8 * deep_night)
        tint_b = int(15 * twilight + 45 * deep_night)
        alpha = int(25 + 20 * deep_night)  # Darker at deep night

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((tint_r, tint_g, tint_b, alpha))
        self.screen.blit(overlay, (0, 0))

        # Additional: subtle ambient light shift on the horizon during twilight
        if twilight > 0.6:
            horizon_glow = pygame.Surface((SCREEN_W, 120), pygame.SRCALPHA)
            glow_a = int(12 * (twilight - 0.6) / 0.4)
            for hy in range(120):
                hy_fade = 1.0 - hy / 120.0
                pygame.draw.line(horizon_glow, (80, 40, 20, int(glow_a * hy_fade)),
                                 (0, hy), (SCREEN_W, hy))
            self.screen.blit(horizon_glow, (0, int(SCREEN_H * 0.45)))

    # ── Main Draw ────────────────────────────────────────────────────────────

    def draw(self) -> None:
        # Backdrop
        self.screen.blit(self.backdrop, (0, 0))

        # (#4) Twinkling stars
        self._draw_twinkling_stars()

        # (#12) Day/night cycle overlay — applied early so it tints the whole scene
        self._draw_day_night_cycle()

        # (#8) Zoomed city cache blit (deco buildings + tiles only)
        cam_x, cam_y = int(self.camera.x), int(self.camera.y)
        if self.zoom != 1.0:
            cache_w, cache_h = self._city_cache.get_size()
            new_w = max(1, int(cache_w * self.zoom))
            new_h = max(1, int(cache_h * self.zoom))
            scaled_cache = pygame.transform.scale(self._city_cache, (new_w, new_h))
            base_x = self._cache_ox + cam_x
            base_y = self._cache_oy + cam_y
            zoom_x = SCREEN_W / 2 + (base_x - SCREEN_W / 2) * self.zoom
            zoom_y = SCREEN_H / 2 + (base_y - SCREEN_H / 2) * self.zoom
            self.screen.blit(scaled_cache, (int(zoom_x), int(zoom_y)))
        else:
            self.screen.blit(self._city_cache,
                             (self._cache_ox + cam_x, self._cache_oy + cam_y))

        # (#1) Interactive buildings — per-frame with neon glow + sprite + tint
        self._draw_interactive_buildings()

        # Per-frame overlays
        self._draw_building_markers()
        self.draw_street_lamps()
        self.player.draw(self.screen, self.t, cam_x, cam_y, self.zoom)
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

        # (#13) FPS counter
        if self._show_fps:
            fps_val = int(self.clock.get_fps())
            fps_text = self.font_fps.render(
                f"FPS: {fps_val}  Zoom: {self.zoom:.1f}x", True, C_GOLD)
            fps_bg = pygame.Surface(
                (fps_text.get_width() + 12, fps_text.get_height() + 6),
                pygame.SRCALPHA)
            pygame.draw.rect(fps_bg, (0, 0, 0, 160), fps_bg.get_rect(),
                             border_radius=4)
            self.screen.blit(fps_bg, (8, 8))
            self.screen.blit(fps_text, (14, 11))

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()
        sys.exit()
