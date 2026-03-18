"""
Tower Defense — Tkinter GUI
============================

A graphical frontend for the tower defense engine using only tkinter
(Python standard library). Click buildable cells to place towers,
press "Next Wave" to send enemies.

Run::

    python gui.py
"""

import tkinter as tk
from tkinter import font as tkfont

from engine.enemies import Boss, Enemy, FlyingEnemy, Grunt, Runner, Tank
from engine.events import EventType
from engine.grid import TerrainType
from engine.towers import (
    AntiAirTower,
    ArrowTower,
    CannonTower,
    FrostTower,
    MageTower,
    Tower,
)
from levels import forest_clearing

# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------

CELL_SIZE = 64
FPS = 60
DT = 1.0 / FPS

# Terrain colours
TERRAIN_COLORS = {
    TerrainType.EMPTY: "#2d5a27",      # dark forest green
    TerrainType.PATH: "#c4a661",        # sandy dirt
    TerrainType.BUILDABLE: "#5a8f3c",   # lighter green clearing
    TerrainType.BLOCKED: "#1a3a14",     # very dark trees
}

# Enemy colours by type
ENEMY_COLORS = {
    "Grunt": "#e04040",
    "Runner": "#e8a020",
    "Tank": "#8030a0",
    "Boss": "#d02060",
    "FlyingEnemy": "#40b0e0",
    "Enemy": "#e04040",
}

ENEMY_SIZES = {
    "Grunt": 8,
    "Runner": 6,
    "Tank": 12,
    "Boss": 16,
    "FlyingEnemy": 7,
    "Enemy": 8,
}

# Tower display info: (abbreviation, colour)
TOWER_DISPLAY = {
    "Arrow Tower": ("AR", "#f0e060"),
    "Cannon Tower": ("CA", "#ff8040"),
    "Frost Tower": ("FR", "#60d0f0"),
    "Mage Tower": ("MG", "#c060ff"),
    "Anti-Air Tower": ("AA", "#60ff90"),
}

# Tower shop: class, name, cost
TOWER_SHOP = [
    (ArrowTower, "Arrow", 50),
    (CannonTower, "Cannon", 100),
    (FrostTower, "Frost", 75),
    (MageTower, "Mage", 120),
    (AntiAirTower, "Anti-Air", 90),
]


class GameGUI:
    def __init__(self) -> None:
        # --- Engine setup ---
        self.state, self.event_bus = forest_clearing.create()
        self.grid = self.state.grid
        self.wave_active = False
        self.selected_tower_class: type | None = None
        self.game_result: str | None = None

        # Subscribe to events
        self.event_bus.subscribe(EventType.WAVE_COMPLETE, self._on_wave_complete)
        self.event_bus.subscribe(EventType.GAME_OVER, self._on_game_over)

        # --- Tkinter setup ---
        self.root = tk.Tk()
        self.root.title("Tower Defense")
        self.root.resizable(False, False)

        canvas_w = self.grid.cols * CELL_SIZE
        canvas_h = self.grid.rows * CELL_SIZE

        # Main frame
        main_frame = tk.Frame(self.root, bg="#1a1a2e")
        main_frame.pack()

        # HUD bar (top)
        self.hud_frame = tk.Frame(main_frame, bg="#1a1a2e", height=50)
        self.hud_frame.pack(fill=tk.X, padx=8, pady=(8, 0))

        hud_font = tkfont.Font(family="Helvetica", size=14, weight="bold")

        self.lives_var = tk.StringVar()
        self.gold_var = tk.StringVar()
        self.wave_var = tk.StringVar()
        self.score_var = tk.StringVar()

        tk.Label(self.hud_frame, textvariable=self.lives_var, font=hud_font,
                 fg="#ff6060", bg="#1a1a2e").pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(self.hud_frame, textvariable=self.gold_var, font=hud_font,
                 fg="#ffd700", bg="#1a1a2e").pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(self.hud_frame, textvariable=self.wave_var, font=hud_font,
                 fg="#80c0ff", bg="#1a1a2e").pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(self.hud_frame, textvariable=self.score_var, font=hud_font,
                 fg="#c0c0c0", bg="#1a1a2e").pack(side=tk.LEFT)

        # Canvas (game field)
        self.canvas = tk.Canvas(main_frame, width=canvas_w, height=canvas_h,
                                bg="#2d5a27", highlightthickness=0)
        self.canvas.pack(padx=8, pady=8)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Motion>", self._on_canvas_hover)

        # Bottom panel (shop + controls)
        bottom = tk.Frame(main_frame, bg="#1a1a2e")
        bottom.pack(fill=tk.X, padx=8, pady=(0, 8))

        # Tower shop buttons
        shop_frame = tk.Frame(bottom, bg="#1a1a2e")
        shop_frame.pack(side=tk.LEFT)

        shop_label = tk.Label(shop_frame, text="Build:", font=("Helvetica", 11),
                              fg="#aaaaaa", bg="#1a1a2e")
        shop_label.pack(side=tk.LEFT, padx=(0, 6))

        self.shop_buttons: list[tk.Button] = []
        for tower_cls, name, cost in TOWER_SHOP:
            _, color = TOWER_DISPLAY.get(f"{name} Tower", (name[:2], "#ffffff"))
            if name == "Anti-Air":
                _, color = TOWER_DISPLAY["Anti-Air Tower"]
            btn = tk.Button(
                shop_frame, text=f"{name}\n{cost}g",
                width=7, height=2, font=("Helvetica", 9),
                bg="#2a2a4a", fg=color, activebackground="#3a3a6a",
                relief=tk.RAISED, bd=2,
                command=lambda c=tower_cls: self._select_tower(c),
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.shop_buttons.append(btn)

        # Deselect button
        self.deselect_btn = tk.Button(
            shop_frame, text="X", width=3, height=2, font=("Helvetica", 9, "bold"),
            bg="#4a2a2a", fg="#ff6060", activebackground="#6a3a3a",
            relief=tk.RAISED, bd=2, command=self._deselect_tower,
        )
        self.deselect_btn.pack(side=tk.LEFT, padx=(6, 0))

        # Right side controls
        ctrl_frame = tk.Frame(bottom, bg="#1a1a2e")
        ctrl_frame.pack(side=tk.RIGHT)

        self.sell_btn = tk.Button(
            ctrl_frame, text="Sell\nTower", width=7, height=2, font=("Helvetica", 9),
            bg="#4a2a2a", fg="#ff8060", activebackground="#6a3a3a",
            relief=tk.RAISED, bd=2, command=self._enter_sell_mode,
        )
        self.sell_btn.pack(side=tk.LEFT, padx=2)

        self.wave_btn = tk.Button(
            ctrl_frame, text="Next\nWave", width=7, height=2,
            font=("Helvetica", 10, "bold"),
            bg="#2a4a2a", fg="#60ff60", activebackground="#3a6a3a",
            relief=tk.RAISED, bd=2, command=self._start_wave,
        )
        self.wave_btn.pack(side=tk.LEFT, padx=(2, 0))

        # Status bar
        self.status_var = tk.StringVar(value="Select a tower to build, then click a green cell.")
        status_bar = tk.Label(main_frame, textvariable=self.status_var,
                              font=("Helvetica", 10), fg="#888888", bg="#1a1a2e",
                              anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=8, pady=(0, 6))

        # State for hover
        self.hover_cell: tuple[int, int] | None = None
        self.sell_mode = False

        # Draw static terrain once
        self._draw_terrain()
        self._update_hud()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_wave_complete(self, data: dict) -> None:
        self.wave_active = False
        total = len(self.state.wave_manager.waves)
        current = data["wave_number"]
        if current >= total:
            self.game_result = "victory"
        self.status_var.set(f"Wave {current} complete! Place towers and start the next wave.")

    def _on_game_over(self, data: dict) -> None:
        self.game_result = "defeat"

    def _select_tower(self, tower_cls: type) -> None:
        self.selected_tower_class = tower_cls
        self.sell_mode = False
        t = tower_cls()
        self.status_var.set(f"Placing {t.name} ({t.cost}g) — click a green cell. "
                            f"Range: {t.range_:.1f}  Dmg: {t.damage:.0f}")

    def _deselect_tower(self) -> None:
        self.selected_tower_class = None
        self.sell_mode = False
        self.status_var.set("Selection cleared.")

    def _enter_sell_mode(self) -> None:
        self.sell_mode = not self.sell_mode
        self.selected_tower_class = None
        if self.sell_mode:
            self.status_var.set("Sell mode — click a tower to sell it for 70% of its cost.")
        else:
            self.status_var.set("Sell mode cancelled.")

    def _on_canvas_click(self, event: tk.Event) -> None:
        col = event.x // CELL_SIZE
        row = event.y // CELL_SIZE

        if self.game_result:
            return

        if self.sell_mode:
            self._try_sell(row, col)
            return

        if self.selected_tower_class is None:
            return

        tower = self.selected_tower_class()
        if self.state.gold < tower.cost:
            self.status_var.set(f"Not enough gold! Need {tower.cost}g, have {self.state.gold}g.")
            return

        if self.state.place_tower(tower, (row, col)):
            self.status_var.set(f"Placed {tower.name} at ({row}, {col}). "
                                f"Gold: {self.state.gold}")
        else:
            self.status_var.set("Can't build there.")

    def _try_sell(self, row: int, col: int) -> None:
        for tower in self.state.towers:
            tx, ty = tower.position  # (col_f, row_f)
            if int(ty) == row and int(tx) == col:
                refund = tower.sell_value()
                self.state.sell_tower(tower)
                self.sell_mode = False
                self.status_var.set(f"Sold {tower.name} for {refund}g.")
                return
        self.status_var.set("No tower at that cell.")

    def _on_canvas_hover(self, event: tk.Event) -> None:
        col = event.x // CELL_SIZE
        row = event.y // CELL_SIZE
        if 0 <= row < self.grid.rows and 0 <= col < self.grid.cols:
            self.hover_cell = (row, col)
        else:
            self.hover_cell = None

    def _start_wave(self) -> None:
        if self.wave_active or self.game_result:
            return
        if self.state.start_wave():
            self.wave_active = True
            self.status_var.set(f"Wave {self.state.current_wave} incoming!")
        else:
            self.status_var.set("No more waves — you survived!")

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _draw_terrain(self) -> None:
        """Draw the static grid terrain onto the canvas."""
        self.canvas.delete("terrain")
        for r in range(self.grid.rows):
            for c in range(self.grid.cols):
                x0 = c * CELL_SIZE
                y0 = r * CELL_SIZE
                terrain = self.grid.get_cell(r, c)
                color = TERRAIN_COLORS.get(terrain, "#333333")
                self.canvas.create_rectangle(
                    x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE,
                    fill=color, outline="#1a3a14", width=1, tags="terrain",
                )

                # Draw small grass tufts on empty and buildable cells
                if terrain == TerrainType.BUILDABLE:
                    # Dotted border to show buildable
                    pad = 3
                    self.canvas.create_rectangle(
                        x0 + pad, y0 + pad, x0 + CELL_SIZE - pad, y0 + CELL_SIZE - pad,
                        outline="#7ab856", width=1, dash=(4, 4), tags="terrain",
                    )

                # Mark spawn and exit
                if terrain == TerrainType.BLOCKED:
                    if r == 0 and c == 0:
                        self.canvas.create_text(
                            x0 + CELL_SIZE // 2, y0 + CELL_SIZE // 2,
                            text="SPAWN", fill="#ff8080", font=("Helvetica", 9, "bold"),
                            tags="terrain",
                        )
                    elif r == self.grid.rows - 2 and c == self.grid.cols - 1:
                        self.canvas.create_text(
                            x0 + CELL_SIZE // 2, y0 + CELL_SIZE // 2,
                            text="EXIT", fill="#ff8080", font=("Helvetica", 9, "bold"),
                            tags="terrain",
                        )

        # Draw path direction arrows
        path = self.state.track.get_path()
        for i in range(len(path) - 1):
            ax = path[i].x * CELL_SIZE + CELL_SIZE // 2
            ay = path[i].y * CELL_SIZE + CELL_SIZE // 2
            bx = path[i + 1].x * CELL_SIZE + CELL_SIZE // 2
            by = path[i + 1].y * CELL_SIZE + CELL_SIZE // 2
            self.canvas.create_line(
                ax, ay, bx, by, fill="#a08850", width=2,
                arrow=tk.LAST, arrowshape=(6, 8, 4), tags="terrain",
            )

    def _draw_frame(self) -> None:
        """Draw all dynamic elements (towers, enemies, projectiles, hover)."""
        self.canvas.delete("dynamic")

        # Hover highlight
        if self.hover_cell and self.selected_tower_class:
            hr, hc = self.hover_cell
            x0 = hc * CELL_SIZE
            y0 = hr * CELL_SIZE
            buildable = self.grid.is_buildable(hr, hc)
            color = "#60ff6040" if buildable else "#ff404040"
            self.canvas.create_rectangle(
                x0 + 2, y0 + 2, x0 + CELL_SIZE - 2, y0 + CELL_SIZE - 2,
                fill=color, outline="#ffffff", width=2, tags="dynamic",
            )
            # Show range preview
            if buildable:
                tower = self.selected_tower_class()
                cx = x0 + CELL_SIZE // 2
                cy = y0 + CELL_SIZE // 2
                r_px = tower.range_ * CELL_SIZE
                self.canvas.create_oval(
                    cx - r_px, cy - r_px, cx + r_px, cy + r_px,
                    outline="#ffffff", width=1, dash=(3, 3), tags="dynamic",
                )

        # Towers — small centered square with label
        tower_half = CELL_SIZE // 4  # smaller square (half the cell quarter)
        for tower in self.state.towers:
            tx, ty = tower.position  # (x=col, y=row)
            cx = tx * CELL_SIZE + CELL_SIZE // 2
            cy = ty * CELL_SIZE + CELL_SIZE // 2
            abbr, color = TOWER_DISPLAY.get(tower.name, ("??", "#ffffff"))

            # Tower body — small square
            self.canvas.create_rectangle(
                cx - tower_half, cy - tower_half,
                cx + tower_half, cy + tower_half,
                fill="#2a2a2a", outline=color, width=2, tags="dynamic",
            )
            self.canvas.create_text(
                cx, cy, text=abbr, fill=color,
                font=("Helvetica", 8, "bold"), tags="dynamic",
            )

            # Range circle (subtle)
            r_px = tower.range_ * CELL_SIZE
            self.canvas.create_oval(
                cx - r_px, cy - r_px, cx + r_px, cy + r_px,
                outline=color, width=1, dash=(2, 4),
                stipple="gray25", tags="dynamic",
            )

        # Enemies — small squares with health bars
        for enemy in self.state.active_enemies:
            if not enemy.alive:
                continue
            ex, ey = enemy.position  # (x=col, y=row) in world coords
            px = ex * CELL_SIZE + CELL_SIZE // 2
            py = ey * CELL_SIZE + CELL_SIZE // 2

            class_name = type(enemy).__name__
            color = ENEMY_COLORS.get(class_name, "#e04040")
            size = ENEMY_SIZES.get(class_name, 8)

            # All enemies as small squares; flying get a white border
            outline = "#ffffff" if enemy.is_flying else "#000000"
            self.canvas.create_rectangle(
                px - size, py - size, px + size, py + size,
                fill=color, outline=outline, width=1, tags="dynamic",
            )

            # Health bar
            bar_w = size * 2 + 4
            bar_h = 3
            bar_x = px - bar_w // 2
            bar_y = py - size - 6
            hp_frac = enemy.health / enemy.max_health if enemy.max_health > 0 else 0
            # Background
            self.canvas.create_rectangle(
                bar_x, bar_y, bar_x + bar_w, bar_y + bar_h,
                fill="#400000", outline="", tags="dynamic",
            )
            # Fill
            hp_color = "#00ff00" if hp_frac > 0.5 else ("#ffff00" if hp_frac > 0.25 else "#ff0000")
            self.canvas.create_rectangle(
                bar_x, bar_y, bar_x + bar_w * hp_frac, bar_y + bar_h,
                fill=hp_color, outline="", tags="dynamic",
            )

        # Projectiles — tiny squares
        for proj in self.state.projectile_mgr.projectiles:
            if not proj.alive:
                continue
            px_pos = proj.position[0] * CELL_SIZE + CELL_SIZE // 2
            py_pos = proj.position[1] * CELL_SIZE + CELL_SIZE // 2
            r = 3 if proj.splash_radius == 0 else 5
            self.canvas.create_rectangle(
                px_pos - r, py_pos - r, px_pos + r, py_pos + r,
                fill="#ffffff", outline="#ffff80", width=1, tags="dynamic",
            )

    def _update_hud(self) -> None:
        """Update the HUD labels."""
        total_waves = len(self.state.wave_manager.waves)
        wave_num = max(self.state.current_wave, 1)
        self.lives_var.set(f"Lives: {self.state.lives}")
        self.gold_var.set(f"Gold: {self.state.gold}")
        self.wave_var.set(f"Wave: {wave_num}/{total_waves}")
        self.score_var.set(f"Score: {self.state.score}")

    def _draw_overlay(self) -> None:
        """Draw victory/defeat overlay."""
        if not self.game_result:
            return
        self.canvas.delete("overlay")
        cw = self.grid.cols * CELL_SIZE
        ch = self.grid.rows * CELL_SIZE

        # Semi-transparent overlay (simulated with stipple)
        self.canvas.create_rectangle(
            0, 0, cw, ch, fill="#000000", stipple="gray50", tags="overlay",
        )

        if self.game_result == "defeat":
            text = "GAME OVER"
            color = "#ff4040"
        else:
            text = "VICTORY!"
            color = "#40ff40"

        self.canvas.create_text(
            cw // 2, ch // 2 - 20, text=text, fill=color,
            font=("Helvetica", 36, "bold"), tags="overlay",
        )
        self.canvas.create_text(
            cw // 2, ch // 2 + 25,
            text=f"Score: {self.state.score}",
            fill="#ffffff", font=("Helvetica", 18), tags="overlay",
        )

    # ------------------------------------------------------------------
    # Game loop
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """One frame: update engine, redraw, schedule next frame."""
        if self.wave_active and not self.game_result:
            self.state.update(DT)

        self._draw_frame()
        self._update_hud()

        if self.game_result:
            self._draw_overlay()
        else:
            self.root.after(1000 // FPS, self._tick)
            return

        # If game ended, stop looping but keep window open
        self.root.after(1000 // FPS, self._tick_idle)

    def _tick_idle(self) -> None:
        """Keep the window responsive after game over."""
        pass  # Tkinter mainloop handles events; no need to schedule more

    def run(self) -> None:
        """Start the game."""
        self.root.after(100, self._tick)
        self.root.mainloop()


if __name__ == "__main__":
    GameGUI().run()
