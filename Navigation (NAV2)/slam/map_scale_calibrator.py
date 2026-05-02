#!/usr/bin/env python3
"""
Map Scale Calibrator
====================
Opens a PGM map and lets you draw a measurement line over a known real-world
distance.  The tool then computes meters-per-pixel and writes an updated YAML
sidecar so ROS2 / Nav2 can use the corrected resolution.

Usage
-----
    python3 map_scale_calibrator.py [path/to/map.pgm]

Controls (in the image window)
-------------------------------
  Left-click (1st)  → set start of measurement line
  Left-click (2nd)  → set end of measurement line
        R key       → reset line
        S key       → save result to <map>.yaml
        Q / Esc     → quit

"""

import sys
import math
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
from PIL import Image, ImageTk

# ---------------------------------------------------------------------------
# PGM / YAML helpers
# ---------------------------------------------------------------------------

def load_pgm(path: str) -> np.ndarray:
    """Load a PGM (P2 or P5) file and return a uint8 numpy array."""
    img = Image.open(path).convert("L")
    return np.array(img)


def find_yaml(pgm_path: str) -> str | None:
    """Return the matching YAML sidecar path if it exists."""
    base = os.path.splitext(pgm_path)[0]
    for ext in (".yaml", ".yml"):
        candidate = base + ext
        if os.path.exists(candidate):
            return candidate
    return None


def load_yaml_resolution(yaml_path: str) -> float | None:
    """Parse the 'resolution' field from a ROS2 map YAML."""
    try:
        with open(yaml_path) as f:
            for line in f:
                m = re.match(r"\s*resolution\s*:\s*([\d.eE+\-]+)", line)
                if m:
                    return float(m.group(1))
    except Exception:
        pass
    return None


def save_yaml(pgm_path: str, resolution: float, origin: list[float] | None = None):
    """Write / update a ROS2-style map YAML next to the PGM."""
    yaml_path = os.path.splitext(pgm_path)[0] + ".yaml"
    pgm_basename = os.path.basename(pgm_path)

    existing_origin = [0.0, 0.0, 0.0]
    existing_negate = 0
    existing_occ_thresh = 0.65
    existing_free_thresh = 0.196

    # Preserve fields from existing YAML if present
    if os.path.exists(yaml_path):
        try:
            with open(yaml_path) as f:
                content = f.read()
            m = re.search(r"origin\s*:\s*\[([^\]]+)\]", content)
            if m:
                vals = [float(v.strip()) for v in m.group(1).split(",")]
                if len(vals) == 3:
                    existing_origin = vals
            m = re.search(r"negate\s*:\s*(\d)", content)
            if m:
                existing_negate = int(m.group(1))
            m = re.search(r"occupied_thresh\s*:\s*([\d.]+)", content)
            if m:
                existing_occ_thresh = float(m.group(1))
            m = re.search(r"free_thresh\s*:\s*([\d.]+)", content)
            if m:
                existing_free_thresh = float(m.group(1))
        except Exception:
            pass

    if origin is not None:
        existing_origin = origin

    content = (
        f"image: {pgm_basename}\n"
        f"resolution: {resolution:.6f}\n"
        f"origin: [{existing_origin[0]:.4f}, {existing_origin[1]:.4f}, {existing_origin[2]:.4f}]\n"
        f"negate: {existing_negate}\n"
        f"occupied_thresh: {existing_occ_thresh}\n"
        f"free_thresh: {existing_free_thresh}\n"
    )
    with open(yaml_path, "w") as f:
        f.write(content)
    return yaml_path


# ---------------------------------------------------------------------------
# Main GUI
# ---------------------------------------------------------------------------

class ScaleCalibratorApp:
    DISPLAY_MAX = 900   # max dimension for the display canvas

    def __init__(self, root: tk.Tk, pgm_path: str):
        self.root = root
        self.root.title("Map Scale Calibrator")
        self.root.configure(bg="#1a1a2e")

        self.pgm_path = pgm_path
        self.arr = load_pgm(pgm_path)
        self.h, self.w = self.arr.shape

        # Compute display scale so the map fits on screen
        scale = min(self.DISPLAY_MAX / self.w, self.DISPLAY_MAX / self.h)
        self.disp_w = int(self.w * scale)
        self.disp_h = int(self.h * scale)
        self.scale = scale  # display pixels per image pixel

        # State
        self.points: list[tuple[int, int]] = []   # image-space coords
        self.line_id = None
        self.dot_ids: list[int] = []
        self.resolution_m_per_px: float | None = None

        # Try to load existing resolution from YAML
        yaml_path = find_yaml(pgm_path)
        self.existing_resolution: float | None = None
        if yaml_path:
            self.existing_resolution = load_yaml_resolution(yaml_path)

        self._build_ui()
        self._render_map()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = self.root
        DARK   = "#1a1a2e"
        PANEL  = "#16213e"
        ACCENT = "#e94560"
        TEXT   = "#eaeaea"
        MUTED  = "#8892b0"
        CARD   = "#0f3460"

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame",       background=PANEL)
        style.configure("TLabel",       background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Header.TLabel",background=PANEL, foreground=ACCENT,
                        font=("Segoe UI", 13, "bold"))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("TEntry",       fieldbackground=CARD, foreground=TEXT,
                        insertcolor=TEXT, font=("Segoe UI", 10))
        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                        font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Accent.TButton",
                  background=[("active", "#c73652"), ("pressed", "#a02840")])
        style.configure("Reset.TButton", background="#2d3561", foreground=TEXT,
                        font=("Segoe UI", 10), borderwidth=0)
        style.map("Reset.TButton", background=[("active", "#3d4571")])

        # ── Top toolbar ────────────────────────────────────────────────
        toolbar = ttk.Frame(root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 4))

        ttk.Label(toolbar, text="🗺  Map Scale Calibrator", style="Header.TLabel").pack(side=tk.LEFT)

        btn_open = ttk.Button(toolbar, text="📂 Open different map",
                              command=self._open_map, style="Reset.TButton")
        btn_open.pack(side=tk.RIGHT, padx=4)

        # ── Main layout ────────────────────────────────────────────────
        main = ttk.Frame(root)
        main.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Canvas
        canvas_frame = tk.Frame(main, bg=DARK, bd=2, relief=tk.FLAT,
                                highlightbackground=ACCENT, highlightthickness=1)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, width=self.disp_w, height=self.disp_h,
                                bg=DARK, cursor="crosshair",
                                highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>",   self._on_motion)
        root.bind("<r>", lambda e: self._reset())
        root.bind("<R>", lambda e: self._reset())
        root.bind("<s>", lambda e: self._save())
        root.bind("<S>", lambda e: self._save())
        root.bind("<Escape>", lambda e: root.quit())
        root.bind("<q>",      lambda e: root.quit())

        # Side panel
        panel = ttk.Frame(main, width=260)
        panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        panel.pack_propagate(False)

        # Map info card
        self._section(panel, "Map Info")
        fn = os.path.basename(self.pgm_path)
        ttk.Label(panel, text=f"File: {fn}", style="Muted.TLabel").pack(anchor=tk.W, padx=8)
        ttk.Label(panel, text=f"Size: {self.w} × {self.h} px", style="Muted.TLabel").pack(anchor=tk.W, padx=8)
        if self.existing_resolution:
            ttk.Label(panel, text=f"Current resolution: {self.existing_resolution:.5f} m/px",
                      style="Muted.TLabel").pack(anchor=tk.W, padx=8)

        # Instructions card
        self._section(panel, "How to use")
        instructions = (
            "1. Click to place the START of your\n"
            "   measurement line.\n\n"
            "2. Click again to place the END.\n\n"
            "3. Enter the real-world distance\n"
            "   that this line represents.\n\n"
            "4. Press  [Calculate]  to get the\n"
            "   resolution (m/px).\n\n"
            "5. Press  [Save YAML]  to write the\n"
            "   result to the map sidecar file.\n\n"
            "  R  → reset line\n"
            "  S  → save YAML\n"
            "  Q / Esc → quit"
        )
        ttk.Label(panel, text=instructions, style="Muted.TLabel",
                  justify=tk.LEFT).pack(anchor=tk.W, padx=8, pady=4)

        # Measurement card
        self._section(panel, "Measurement")

        row1 = ttk.Frame(panel)
        row1.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(row1, text="Pixel length:").pack(side=tk.LEFT)
        self.lbl_pixels = ttk.Label(row1, text="—", foreground=ACCENT,
                                    background=PANEL, font=("Segoe UI", 10, "bold"))
        self.lbl_pixels.pack(side=tk.RIGHT)

        row2 = ttk.Frame(panel)
        row2.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(row2, text="Real distance (m):").pack(side=tk.LEFT)
        self.entry_dist = ttk.Entry(row2, width=8)
        self.entry_dist.pack(side=tk.RIGHT)
        self.entry_dist.insert(0, "1.0")

        btn_calc = ttk.Button(panel, text="⚙  Calculate resolution",
                              command=self._calculate, style="Accent.TButton")
        btn_calc.pack(fill=tk.X, padx=8, pady=(6, 2))

        # Results card
        self._section(panel, "Results")

        row3 = ttk.Frame(panel)
        row3.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(row3, text="Resolution (m/px):").pack(side=tk.LEFT)
        self.lbl_res = ttk.Label(row3, text="—", foreground=ACCENT,
                                  background=PANEL, font=("Segoe UI", 10, "bold"))
        self.lbl_res.pack(side=tk.RIGHT)

        row4 = ttk.Frame(panel)
        row4.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(row4, text="Map size (m):").pack(side=tk.LEFT)
        self.lbl_size_m = ttk.Label(row4, text="—", foreground=ACCENT,
                                     background=PANEL, font=("Segoe UI", 10, "bold"))
        self.lbl_size_m.pack(side=tk.RIGHT)

        row5 = ttk.Frame(panel)
        row5.pack(fill=tk.X, padx=8, pady=2)
        ttk.Label(row5, text="Old → New res:").pack(side=tk.LEFT)
        self.lbl_delta = ttk.Label(row5, text="—", foreground=ACCENT,
                                    background=PANEL, font=("Segoe UI", 10, "bold"))
        self.lbl_delta.pack(side=tk.RIGHT)

        btn_save = ttk.Button(panel, text="💾  Save YAML",
                              command=self._save, style="Accent.TButton")
        btn_save.pack(fill=tk.X, padx=8, pady=(6, 2))

        btn_reset = ttk.Button(panel, text="↺  Reset line",
                               command=self._reset, style="Reset.TButton")
        btn_reset.pack(fill=tk.X, padx=8, pady=2)

        # Status bar
        self.status_var = tk.StringVar(value="Click on the map to place the first point of your line.")
        status_bar = tk.Label(root, textvariable=self.status_var,
                              bg="#0f0f1a", fg=MUTED, anchor=tk.W,
                              font=("Segoe UI", 9), pady=4, padx=8)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Cursor guide line (drawn before committing 2nd point)
        self.guide_id = None

    def _section(self, parent, title: str):
        ACCENT = "#e94560"
        PANEL  = "#16213e"
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, padx=4, pady=(10, 2))
        ttk.Label(f, text=title.upper(), foreground=ACCENT,
                  background=PANEL,
                  font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        tk.Frame(f, bg=ACCENT, height=1).pack(side=tk.LEFT, fill=tk.X,
                                               expand=True, padx=4)

    # ------------------------------------------------------------------
    # Map rendering
    # ------------------------------------------------------------------

    def _render_map(self):
        pil = Image.fromarray(self.arr).convert("RGB").resize(
            (self.disp_w, self.disp_h), Image.NEAREST)
        self._tk_img = ImageTk.PhotoImage(pil)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self._tk_img)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _img_to_disp(self, ix, iy):
        return ix * self.scale, iy * self.scale

    def _disp_to_img(self, dx, dy):
        return int(dx / self.scale), int(dy / self.scale)

    def _on_click(self, event):
        ix, iy = self._disp_to_img(event.x, event.y)
        # Clamp
        ix = max(0, min(ix, self.w - 1))
        iy = max(0, min(iy, self.h - 1))

        if len(self.points) >= 2:
            self._reset()

        self.points.append((ix, iy))
        dx, dy = self._img_to_disp(ix, iy)
        dot = self.canvas.create_oval(dx - 5, dy - 5, dx + 5, dy + 5,
                                      fill="#e94560", outline="white", width=1)
        self.dot_ids.append(dot)

        if len(self.points) == 2:
            self._draw_line()
            px_len = math.dist(self.points[0], self.points[1])
            self.lbl_pixels.config(text=f"{px_len:.1f} px")
            self.status_var.set(
                f"Line defined: {px_len:.1f} px  |  Enter real-world distance and click [Calculate]."
            )
            if self.guide_id:
                self.canvas.delete(self.guide_id)
                self.guide_id = None
        else:
            self.status_var.set("First point set. Click to place the end of the line.")

    def _on_motion(self, event):
        if len(self.points) == 1:
            x0, y0 = self._img_to_disp(*self.points[0])
            if self.guide_id:
                self.canvas.coords(self.guide_id, x0, y0, event.x, event.y)
            else:
                self.guide_id = self.canvas.create_line(
                    x0, y0, event.x, event.y,
                    fill="#e94560", dash=(6, 4), width=2)

    def _draw_line(self):
        if self.line_id:
            self.canvas.delete(self.line_id)
        (x0, y0), (x1, y1) = [self._img_to_disp(*p) for p in self.points]
        self.line_id = self.canvas.create_line(
            x0, y0, x1, y1, fill="#e94560", width=2)
        # Annotate pixel distance
        mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
        px_len = math.dist(self.points[0], self.points[1])
        self.canvas.create_text(mid_x, mid_y - 12,
                                text=f"{px_len:.1f} px",
                                fill="white", font=("Segoe UI", 9, "bold"),
                                tags="annotation")

    def _reset(self):
        self.points.clear()
        for d in self.dot_ids:
            self.canvas.delete(d)
        self.dot_ids.clear()
        if self.line_id:
            self.canvas.delete(self.line_id)
            self.line_id = None
        if self.guide_id:
            self.canvas.delete(self.guide_id)
            self.guide_id = None
        self.canvas.delete("annotation")
        self.lbl_pixels.config(text="—")
        self.resolution_m_per_px = None
        self.lbl_res.config(text="—")
        self.lbl_size_m.config(text="—")
        self.lbl_delta.config(text="—")
        self.status_var.set("Line reset. Click on the map to start a new measurement.")

    # ------------------------------------------------------------------
    # Calculation
    # ------------------------------------------------------------------

    def _calculate(self):
        if len(self.points) < 2:
            messagebox.showwarning("No line", "Please draw a measurement line first.")
            return
        try:
            real_dist = float(self.entry_dist.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Enter a valid number for the real-world distance.")
            return
        if real_dist <= 0:
            messagebox.showerror("Invalid input", "Distance must be positive.")
            return

        px_len = math.dist(self.points[0], self.points[1])
        if px_len < 1:
            messagebox.showerror("Too short", "The line is too short. Draw a longer line.")
            return

        self.resolution_m_per_px = real_dist / px_len

        size_w_m = self.w * self.resolution_m_per_px
        size_h_m = self.h * self.resolution_m_per_px

        self.lbl_res.config(text=f"{self.resolution_m_per_px:.6f}")
        self.lbl_size_m.config(text=f"{size_w_m:.2f} × {size_h_m:.2f} m")

        if self.existing_resolution:
            ratio = self.resolution_m_per_px / self.existing_resolution
            self.lbl_delta.config(
                text=f"{self.existing_resolution:.5f} → {self.resolution_m_per_px:.5f}"
            )
        else:
            self.lbl_delta.config(text="(no previous YAML)")

        self.status_var.set(
            f"Resolution = {self.resolution_m_per_px:.6f} m/px  |  "
            f"Map = {size_w_m:.2f} × {size_h_m:.2f} m  |  "
            f"Press [Save YAML] to write."
        )

        # Annotate the line with the real distance
        self.canvas.delete("dist_annotation")
        (x0, y0), (x1, y1) = [self._img_to_disp(*p) for p in self.points]
        mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
        self.canvas.create_text(mid_x, mid_y + 12,
                                text=f"{real_dist:.3f} m",
                                fill="#64ffda", font=("Segoe UI", 9, "bold"),
                                tags="dist_annotation")

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save(self):
        if self.resolution_m_per_px is None:
            messagebox.showwarning("Not calculated", "Please calculate the resolution first.")
            return
        yaml_path = save_yaml(self.pgm_path, self.resolution_m_per_px)
        messagebox.showinfo(
            "Saved",
            f"YAML written to:\n{yaml_path}\n\n"
            f"resolution: {self.resolution_m_per_px:.6f} m/px\n"
            f"Map size: {self.w * self.resolution_m_per_px:.3f} × "
            f"{self.h * self.resolution_m_per_px:.3f} m"
        )
        self.status_var.set(f"✔ Saved → {yaml_path}")

    # ------------------------------------------------------------------
    # Open different map
    # ------------------------------------------------------------------

    def _open_map(self):
        path = filedialog.askopenfilename(
            title="Open PGM map",
            filetypes=[("PGM files", "*.pgm"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.pgm_path)
        )
        if not path:
            return
        self.pgm_path = path
        self.arr = load_pgm(path)
        self.h, self.w = self.arr.shape
        scale = min(self.DISPLAY_MAX / self.w, self.DISPLAY_MAX / self.h)
        self.disp_w = int(self.w * scale)
        self.disp_h = int(self.h * scale)
        self.scale = scale
        self.canvas.config(width=self.disp_w, height=self.disp_h)
        self._reset()
        self._render_map()

        yaml_path = find_yaml(path)
        self.existing_resolution = load_yaml_resolution(yaml_path) if yaml_path else None
        self.root.title(f"Map Scale Calibrator — {os.path.basename(path)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    default_map = "/home/utilisateur/slam/test/map2mapping7.pgm"

    pgm_path = sys.argv[1] if len(sys.argv) > 1 else default_map

    if not os.path.exists(pgm_path):
        # fall back to file picker
        root_tmp = tk.Tk()
        root_tmp.withdraw()
        pgm_path = filedialog.askopenfilename(
            title="Open PGM map",
            filetypes=[("PGM files", "*.pgm"), ("All files", "*.*")]
        )
        root_tmp.destroy()
        if not pgm_path:
            print("No file selected. Exiting.")
            sys.exit(1)

    root = tk.Tk()
    root.resizable(True, True)
    app = ScaleCalibratorApp(root, pgm_path)
    root.mainloop()


if __name__ == "__main__":
    main()
