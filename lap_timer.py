# -*- coding: utf-8 -*-
"""
RacerLab - Racing Lap Timer for Logitech G29
Pausa con P, pantalla completa con F11.
"""

import pygame
import sys
import time
import json
import os
from dataclasses import dataclass, field
from typing import Optional

# ─── Configuracion ───────────────────────────────────────────────────────────

CONFIG_FILE  = os.path.join(os.path.dirname(__file__), "config.json")
LOGICAL_W    = 800
LOGICAL_H    = 700
FPS          = 60
TITLE        = "RacerLab"

C_BG        = (  8,   8,  18)
C_PANEL     = ( 14,  14,  30)
C_BORDER    = ( 30,  30,  60)
C_TEXT      = (220, 220, 220)
C_DIM       = (100, 100, 130)
C_YELLOW    = (232, 200,  40)
C_PURPLE    = (168,  85, 247)
C_GREEN     = ( 34, 197,  94)
C_RED       = (239,  68,  68)
C_ORANGE    = (251, 146,  60)
C_WHITE     = (255, 255, 255)
C_DARK_RED  = ( 80,  20,  20)
C_DARK_GRN  = ( 15,  50,  25)
C_DARK_PRP  = ( 40,  15,  70)
C_PAUSE_BG  = ( 20,  10,  40)

DEBOUNCE_S  = 0.6


# ─── Estructuras de datos ─────────────────────────────────────────────────────

@dataclass
class Lap:
    number: int
    duration: float
    delta: Optional[float] = None

@dataclass
class Session:
    laps:       list  = field(default_factory=list)
    best_time:  Optional[float] = None
    best_index: int = -1

    def add_lap(self, duration: float) -> "Lap":
        delta = (duration - self.best_time) if self.best_time is not None else None
        lap   = Lap(number=len(self.laps) + 1, duration=duration, delta=delta)
        self.laps.append(lap)
        if self.best_time is None or duration < self.best_time:
            self.best_time  = duration
            self.best_index = len(self.laps) - 1
            for i, l in enumerate(self.laps):
                l.delta = l.duration - self.best_time if i != self.best_index else None
        return lap


# ─── Helpers de formato ───────────────────────────────────────────────────────

def fmt_time(seconds: float) -> str:
    seconds = abs(seconds)
    return f"{int(seconds//60)}:{seconds%60:06.3f}"

def fmt_delta(delta: float) -> str:
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.3f}s"

def delta_color(delta: Optional[float]) -> tuple:
    if delta is None:   return C_PURPLE
    if delta < 0:       return C_GREEN
    if delta < 0.5:     return C_ORANGE
    return C_RED


# ─── Config / deteccion volante ───────────────────────────────────────────────

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def find_g29(joy_count: int) -> Optional[int]:
    for i in range(joy_count):
        j = pygame.joystick.Joystick(i)
        j.init()
        if any(k in j.get_name().lower() for k in ("g29", "g920", "logitech", "wheel")):
            return i
        j.quit()
    return None


# ─── Renderer ─────────────────────────────────────────────────────────────────

class Renderer:
    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.fonts: dict = {}

    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self.fonts:
            try:                self.fonts[key] = pygame.font.SysFont("consolas", size, bold=bold)
            except Exception:   self.fonts[key] = pygame.font.Font(None, size)
        return self.fonts[key]

    def text(self, txt: str, x: int, y: int, size: int = 22,
             color=C_TEXT, bold: bool = False, anchor: str = "topleft"):
        surf = self.font(size, bold).render(txt, True, color)
        rect = surf.get_rect()
        setattr(rect, anchor, (x, y))
        self.surface.blit(surf, rect)
        return rect

    def rect(self, x, y, w, h, color, radius: int = 6, alpha: int = 255):
        if alpha < 255:
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(s, (*color, alpha), (0, 0, w, h), border_radius=radius)
            self.surface.blit(s, (x, y))
        else:
            pygame.draw.rect(self.surface, color, (x, y, w, h), border_radius=radius)

    def border_rect(self, x, y, w, h, color, thick=1, radius=6):
        pygame.draw.rect(self.surface, color, (x, y, w, h), thick, border_radius=radius)

    def hline(self, x, y, w, color, thick=1):
        pygame.draw.line(self.surface, color, (x, y), (x + w, y), thick)


# ─── Blit logico -> display (escala si hay pantalla completa o resize) ────────

def flip_to_display(logical: pygame.Surface):
    display = pygame.display.get_surface()
    dw, dh  = display.get_size()
    if (dw, dh) != (LOGICAL_W, LOGICAL_H):
        display.blit(pygame.transform.smoothscale(logical, (dw, dh)), (0, 0))
    else:
        display.blit(logical, (0, 0))
    pygame.display.flip()


# ─── Pantalla de setup ────────────────────────────────────────────────────────

def run_setup(logical: pygame.Surface, renderer: Renderer,
              joystick: Optional[pygame.joystick.Joystick]) -> dict:
    clock = pygame.time.Clock()
    cfg   = {}
    detected = None
    blink    = 0.0
    cx       = LOGICAL_W // 2

    while detected is None:
        dt    = clock.tick(FPS) / 1000.0
        blink = (blink + dt) % 2.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_SPACE:
                    cfg["button_type"]  = "keyboard"
                    cfg["button_index"] = -1
                    detected = True
            if joystick and event.type == pygame.JOYBUTTONDOWN:
                cfg["button_type"]  = "button"
                cfg["button_index"] = event.button
                detected = True
            if joystick and event.type == pygame.JOYAXISMOTION and event.value > 0.7:
                cfg["button_type"]    = "axis"
                cfg["button_index"]   = event.axis
                cfg["axis_threshold"] = 0.5
                detected = True

        logical.fill(C_BG)
        renderer.text("RacerLab",            cx, 80,  52, C_YELLOW, bold=True, anchor="midtop")
        renderer.text("CONFIGURACION INICIAL", cx, 148, 22, C_DIM,    anchor="midtop")
        renderer.hline(40, 190, LOGICAL_W - 80, C_BORDER)
        if joystick:
            renderer.text(f"Volante detectado: {joystick.get_name()}", cx, 215, 20, C_GREEN, anchor="midtop")
        else:
            renderer.text("No se detecto volante -> solo teclado", cx, 215, 20, C_ORANGE, anchor="midtop")
        renderer.hline(40, 250, LOGICAL_W - 80, C_BORDER)
        if blink < 1.0:
            renderer.text("Pulsa  L2  en el volante", cx, 300, 34, C_WHITE, bold=True, anchor="midtop")
        renderer.text("para detectar el boton automáticamente", cx, 345, 20, C_DIM, anchor="midtop")
        renderer.text("--  o  --", cx, 388, 18, C_DIM, anchor="midtop")
        renderer.text("ESPACIO para usar solo teclado",         cx, 416, 20, C_DIM, anchor="midtop")
        renderer.hline(40, LOGICAL_H - 60, LOGICAL_W - 80, C_BORDER)
        renderer.text("ESC para salir   |   F11 pantalla completa", cx, LOGICAL_H - 44, 16, C_DIM, anchor="midtop")
        flip_to_display(logical)

    if joystick:
        cfg["joystick_name"] = joystick.get_name()
    save_config(cfg)
    return cfg


# ─── App principal ────────────────────────────────────────────────────────────

class LapTimerApp:
    PAD      = 20
    HEADER_H = 64
    TIMER_H  = 160
    ROW_H    = 38
    MAX_ROWS = 10

    def __init__(self, logical: pygame.Surface, renderer: Renderer,
                 joystick: Optional[pygame.joystick.Joystick], cfg: dict):
        self.logical    = logical
        self.r          = renderer
        self.joy        = joystick
        self.cfg        = cfg
        self.session    = Session()
        self.running    = True
        self.clock      = pygame.time.Clock()
        self.last_press = 0.0

        # Tiempo
        self.lap_start    = time.perf_counter()
        self.paused       = False
        self.pause_start  = 0.0
        self.paused_accum = 0.0   # tiempo pausado en la vuelta actual

        # Fullscreen
        self.fullscreen = False

        # Animaciones
        self.flash_timer  = 0.0
        self.flash_lap: Optional[Lap] = None
        self.anim_scale   = 1.0
        self._pause_blink = 0.0
        self._axis_active = False

    # ── Elapsed corregido ──────────────────────────────────────────────── #

    def _elapsed(self) -> float:
        base = time.perf_counter() - self.lap_start - self.paused_accum
        if self.paused:
            base -= (time.perf_counter() - self.pause_start)
        return max(base, 0.0)

    # ── Pausa ──────────────────────────────────────────────────────────── #

    def toggle_pause(self):
        now = time.perf_counter()
        if not self.paused:
            self.paused      = True
            self.pause_start = now
        else:
            self.paused_accum += now - self.pause_start
            self.paused        = False

    # ── Fullscreen ─────────────────────────────────────────────────────── #

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            pygame.display.set_mode((LOGICAL_W, LOGICAL_H), pygame.RESIZABLE)

    # ── Input ──────────────────────────────────────────────────────────── #

    def _can_record(self) -> bool:
        now = time.perf_counter()
        if now - self.last_press < DEBOUNCE_S:
            return False
        self.last_press = now
        return True

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif event.key == pygame.K_p:
                self.toggle_pause()
            elif event.key == pygame.K_SPACE:
                if not self.paused and self._can_record():
                    self.record_lap()
            elif event.key == pygame.K_r:
                self.reset_session()

        elif self.joy and event.type == pygame.JOYBUTTONDOWN:
            btype = self.cfg.get("button_type")
            bidx  = self.cfg.get("button_index", -1)
            if btype == "button" and event.button == bidx:
                if not self.paused and self._can_record():
                    self.record_lap()

        elif self.joy and event.type == pygame.JOYAXISMOTION:
            btype  = self.cfg.get("button_type")
            bidx   = self.cfg.get("button_index", -1)
            thresh = self.cfg.get("axis_threshold", 0.5)
            if btype == "axis" and event.axis == bidx:
                if event.value > thresh and not self._axis_active:
                    self._axis_active = True
                    if not self.paused and self._can_record():
                        self.record_lap()
                elif event.value <= thresh:
                    self._axis_active = False

    def record_lap(self):
        duration          = self._elapsed()
        now               = time.perf_counter()
        self.lap_start    = now
        self.paused_accum = 0.0
        if self.paused:
            self.pause_start = now
        lap = self.session.add_lap(duration)
        self.flash_lap   = lap
        self.flash_timer = 1.2
        self.anim_scale  = 1.18

    def reset_session(self):
        self.session      = Session()
        self.lap_start    = time.perf_counter()
        self.paused       = False
        self.paused_accum = 0.0
        self.flash_timer  = 0.0
        self.flash_lap    = None
        self.anim_scale   = 1.0

    # ── Dibujo ─────────────────────────────────────────────────────────── #

    def draw_header(self):
        P = self.PAD
        self.r.rect(0, 0, LOGICAL_W, self.HEADER_H, C_PANEL)
        self.r.text("LAP",   P,      self.HEADER_H//2, 30, C_YELLOW, bold=True, anchor="midleft")
        self.r.text("TIMER", P + 62, self.HEADER_H//2, 30, C_WHITE,  bold=True, anchor="midleft")
        if self.paused:
            self.r.text("[ PAUSADO ]", LOGICAL_W//2, self.HEADER_H//2, 20, C_ORANGE, bold=True, anchor="center")
        if self.fullscreen:
            self.r.text("[ PANTALLA COMPLETA   F11 ]", LOGICAL_W//2, self.HEADER_H//2, 14, C_DIM, anchor="midtop")
        label  = f"+ {self.joy.get_name()}" if self.joy else "- Sin volante  (ESPACIO)"
        dot_c  = C_GREEN if self.joy else C_RED
        self.r.text(label, LOGICAL_W - P, self.HEADER_H//2, 15, dot_c, anchor="midright")
        self.r.hline(0, self.HEADER_H, LOGICAL_W, C_BORDER, 2)

    def draw_current_timer(self, dt: float):
        y0  = self.HEADER_H + self.PAD
        h   = self.TIMER_H
        cx  = LOGICAL_W // 2
        P   = self.PAD
        self.r.rect(P, y0, LOGICAL_W - 2*P, h, C_PANEL, radius=10)

        elapsed  = self._elapsed()
        if self.paused:
            timer_color = C_ORANGE
        elif self.session.best_time:
            timer_color = C_GREEN if elapsed < self.session.best_time else C_RED
        else:
            timer_color = C_YELLOW

        if self.anim_scale > 1.0:
            self.anim_scale = max(1.0, self.anim_scale - dt * 3.0)
        self.r.text(fmt_time(elapsed), cx, y0 + 20, int(72 * self.anim_scale),
                    timer_color, bold=True, anchor="midtop")

        dy = y0 + 95
        if self.paused:
            self.r.text("--- CRONOMETRO PAUSADO ---", cx, dy, 20, C_ORANGE, anchor="midtop")
        elif self.session.best_time is not None:
            d    = elapsed - self.session.best_time
            sign = "+" if d >= 0 else ""
            self.r.text(f"D vs mejor  {sign}{d:.3f}s", cx, dy, 22,
                        C_GREEN if d < 0 else C_RED, bold=True, anchor="midtop")
        else:
            self.r.text("Primera vuelta", cx, dy, 22, C_DIM, anchor="midtop")

        iy  = y0 + 125
        self.r.text(f"VUELTA  {len(self.session.laps)+1}", P+16, iy, 17, C_DIM)
        if self.session.best_time:
            self.r.text(f"MEJOR  {fmt_time(self.session.best_time)}", cx, iy, 17, C_PURPLE, anchor="midtop")

        self.r.border_rect(P, y0, LOGICAL_W - 2*P, h, C_BORDER, radius=10)

    def draw_pause_overlay(self, dt: float):
        self._pause_blink = (self._pause_blink + dt) % 1.2
        ov = pygame.Surface((LOGICAL_W, LOGICAL_H), pygame.SRCALPHA)
        ov.fill((*C_PAUSE_BG, 185))
        self.logical.blit(ov, (0, 0))

        cx = LOGICAL_W // 2
        cy = LOGICAL_H // 2
        mw, mh = 440, 136
        mx, my = cx - mw//2, cy - mh//2
        self.r.rect(mx, my, mw, mh, C_PANEL, radius=16)
        self.r.border_rect(mx, my, mw, mh, C_ORANGE, thick=2, radius=16)
        if self._pause_blink < 0.80:
            self.r.text("II  PAUSADO", cx, my + 18, 48, C_ORANGE, bold=True, anchor="midtop")
        self.r.text("P reanudar  |  R reiniciar sesion  |  ESC salir",
                    cx, my + 90, 16, C_DIM, anchor="midtop")

    def draw_lap_flash(self):
        if self.flash_timer <= 0 or not self.flash_lap:
            return
        lap   = self.flash_lap
        alpha = int(min(1.0, self.flash_timer) * 200)
        txt   = fmt_time(lap.duration)
        txt  += f"   {fmt_delta(lap.delta)}" if lap.delta is not None else "   * MEJOR VUELTA"
        surf  = self.r.font(28, bold=True).render(txt, True, delta_color(lap.delta))
        surf.set_alpha(alpha)
        self.logical.blit(surf, surf.get_rect(
            midtop=(LOGICAL_W//2, self.HEADER_H + self.TIMER_H + 36)))

    def draw_lap_table(self):
        P       = self.PAD
        ty      = self.HEADER_H + self.TIMER_H + 2*P + 30
        cx      = LOGICAL_W // 2
        c_lap   = P + 20
        c_time  = P + 100
        c_delt  = P + 260
        c_bar   = P + 370
        bar_max = LOGICAL_W - c_bar - P - 20

        if not self.session.laps:
            self.r.text("Pulsa L2 o ESPACIO para registrar la primera vuelta",
                        cx, ty + 30, 20, C_DIM, anchor="midtop")
            return

        self.r.text("VTA",    c_lap,  ty, 16, C_DIM, bold=True)
        self.r.text("TIEMPO", c_time, ty, 16, C_DIM, bold=True)
        self.r.text("DELTA",  c_delt, ty, 16, C_DIM, bold=True)
        self.r.text("BAR",    c_bar,  ty, 16, C_DIM, bold=True)
        self.r.hline(P, ty + 22, LOGICAL_W - 2*P, C_BORDER)

        shown = list(reversed(self.session.laps))[:self.MAX_ROWS]
        for i, lap in enumerate(shown):
            ry      = ty + 28 + i * self.ROW_H
            is_best = (lap.number - 1 == self.session.best_index)

            if is_best:
                self.r.rect(P, ry-4, LOGICAL_W-2*P, self.ROW_H-2, C_DARK_PRP, radius=6)
            elif lap.delta and lap.delta < 0:
                self.r.rect(P, ry-4, LOGICAL_W-2*P, self.ROW_H-2, C_DARK_GRN, radius=6, alpha=120)
            elif lap.delta and lap.delta > 1.0:
                self.r.rect(P, ry-4, LOGICAL_W-2*P, self.ROW_H-2, C_DARK_RED, radius=6, alpha=80)

            rc = delta_color(lap.delta)
            self.r.text(f"* {lap.number}" if is_best else str(lap.number),
                        c_lap, ry, 19, C_PURPLE if is_best else C_DIM, bold=is_best)
            self.r.text(fmt_time(lap.duration), c_time, ry, 20, C_WHITE if is_best else C_TEXT)

            if is_best:
                self.r.text("MEJOR VUELTA", c_delt, ry, 18, C_PURPLE, bold=True)
            elif lap.delta is not None:
                self.r.text(fmt_delta(lap.delta), c_delt, ry, 19, rc, bold=True)

            if not is_best and lap.delta is not None:
                bw = int(min(abs(lap.delta) / 5.0, 1.0) * bar_max)
                if bw > 2:
                    bc = C_GREEN if lap.delta < 0 else (C_ORANGE if lap.delta < 1.0 else C_RED)
                    self.r.rect(c_bar, ry+4, bw, 14, bc, radius=3)
            elif is_best:
                self.r.rect(c_bar, ry+4, bar_max, 14, C_PURPLE, radius=3, alpha=120)

            if i < len(shown) - 1:
                self.r.hline(P+10, ry+self.ROW_H-4, LOGICAL_W-2*P-20, C_BORDER)

        extra = len(self.session.laps) - self.MAX_ROWS
        if extra > 0:
            self.r.text(f"... y {extra} vuelta{'s' if extra>1 else ''} mas",
                        cx, ty + 28 + self.MAX_ROWS*self.ROW_H + 4, 15, C_DIM, anchor="midtop")

    def draw_footer(self):
        y = LOGICAL_H - 36
        self.r.hline(0, y - 8, LOGICAL_W, C_BORDER)
        hints = "L2/ESPACIO marcar vuelta   |   P pausar/reanudar   |   F11 pantalla completa   |   R reiniciar   |   ESC salir"
        surf  = self.r.font(13).render(hints, True, C_DIM)
        self.logical.blit(surf, surf.get_rect(center=(LOGICAL_W//2, y + 10)))

    # ── Loop ───────────────────────────────────────────────────────────── #

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            if self.flash_timer > 0:
                self.flash_timer -= dt

            self.logical.fill(C_BG)
            self.draw_header()
            self.draw_current_timer(dt)
            self.draw_lap_flash()
            self.draw_lap_table()
            self.draw_footer()
            if self.paused:
                self.draw_pause_overlay(dt)
            else:
                self._pause_blink = 0.0
            flip_to_display(self.logical)


# ─── Punto de entrada ─────────────────────────────────────────────────────────

def main():
    pygame.init()
    pygame.joystick.init()

    pygame.display.set_mode((LOGICAL_W, LOGICAL_H), pygame.RESIZABLE)
    pygame.display.set_caption(TITLE)

    icon = pygame.Surface((32, 32))
    icon.fill(C_BG)
    pygame.draw.circle(icon, C_YELLOW, (16, 16), 14, 3)
    pygame.draw.circle(icon, C_YELLOW, (16, 16), 4)
    pygame.display.set_icon(icon)

    logical  = pygame.Surface((LOGICAL_W, LOGICAL_H))
    renderer = Renderer(logical)

    joy       = None
    joy_count = pygame.joystick.get_count()
    g29_idx   = find_g29(joy_count)
    if g29_idx is not None:
        joy = pygame.joystick.Joystick(g29_idx); joy.init()
    elif joy_count > 0:
        joy = pygame.joystick.Joystick(0); joy.init()

    cfg = load_config()
    if "button_type" not in cfg:
        cfg = run_setup(logical, renderer, joy)

    LapTimerApp(logical, renderer, joy, cfg).run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
