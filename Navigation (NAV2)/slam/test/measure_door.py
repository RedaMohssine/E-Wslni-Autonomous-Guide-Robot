#!/usr/bin/env python3
"""
Map Resolution Calibrator (matplotlib version)
================================================
Click on two points that represent a known real-world distance (default: 0.80 m door).

Usage:
    python3 measure_door.py [path_to_pgm] [real_world_meters]

Example:
    python3 measure_door.py src/robot_simulation/Floor-Plan.pgm 0.80

Controls:
    - Left-click : place points (2 total)
    - Right-click / middle-click : reset
    - Close window : exit
"""

import sys
import math
import numpy as np

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: pip3 install Pillow")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use('TkAgg')          # most reliable backend on Ubuntu
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.lines import Line2D
except ImportError:
    print("ERROR: matplotlib not installed. Run: pip3 install matplotlib")
    sys.exit(1)

# ── Arguments ──────────────────────────────────────────────────────────────────
pgm_path    = sys.argv[1] if len(sys.argv) > 1 else "src/robot_simulation/Floor-Plan.pgm"
real_meters = float(sys.argv[2]) if len(sys.argv) > 2 else 0.80

# ── Load image ────────────────────────────────────────────────────────────────
img = Image.open(pgm_path).convert('L')
w, h = img.size
arr = np.array(img)

print(f"\nImage loaded: {w} x {h} px")
print(f"Real-world reference: {real_meters} m\n")
print("Instructions:")
print("  1. Use the scroll wheel or toolbar to zoom into a door")
print("  2. Left-click one door jamb, then the other")
print("  3. The resolution is printed here + shown on the image")
print("  Right-click = reset points\n")

# ── State ─────────────────────────────────────────────────────────────────────
points = []
artists = []   # matplotlib artists to remove on reset

fig, ax = plt.subplots(figsize=(14, 10))
ax.imshow(arr, cmap='gray', origin='upper')
ax.set_title(f'Click 2 door edges  |  Reference = {real_meters} m  |  Right-click = reset',
             fontsize=11)
ax.set_xlabel('pixel x')
ax.set_ylabel('pixel y')
plt.tight_layout()

def redraw():
    for a in artists:
        try:
            a.remove()
        except Exception:
            pass
    artists.clear()

    for i, (px, py) in enumerate(points):
        dot = ax.plot(px, py, 'o', color='#ff4444', markersize=10,
                      markeredgecolor='white', markeredgewidth=1.5)[0]
        lbl = ax.text(px + 15, py - 15, f'P{i+1}', color='#ff4444',
                      fontsize=10, fontweight='bold',
                      bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.6))
        artists.extend([dot, lbl])

    if len(points) == 2:
        p1, p2 = points
        pix_dist = math.dist(p1, p2)
        res      = real_meters / pix_dist
        img_w_m  = w * res
        img_h_m  = h * res

        line = ax.add_line(Line2D([p1[0], p2[0]], [p1[1], p2[1]],
                                   color='#00e676', linewidth=2))
        mid  = ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2)
        txt  = ax.text(mid[0]+15, mid[1]-15,
                       f'{pix_dist:.1f} px  →  {res:.5f} m/px',
                       color='#00e676', fontsize=10, fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', fc='black', alpha=0.7))
        artists.extend([line, txt])

        result = (
            f"\n{'='*55}\n"
            f"  Pixel distance : {pix_dist:.2f} px\n"
            f"  Real reference : {real_meters} m\n"
            f"  RESOLUTION     : {res:.5f} m/px  (use {res:.4f})\n"
            f"  Map real size  : {img_w_m:.1f} m  x  {img_h_m:.1f} m\n"
            f"  Suggested origin: [{-img_w_m/2:.2f}, {-img_h_m/2:.2f}, 0]\n"
            f"{'='*55}\n"
            f"\nPaste into map.yaml:\n"
            f"  resolution: {res:.4f}\n"
            f"  origin: [{-img_w_m/2:.2f}, {-img_h_m/2:.2f}, 0]\n"
        )
        print(result)
        fig.canvas.set_window_title(f"resolution = {res:.5f} m/px  |  {img_w_m:.1f} x {img_h_m:.1f} m")

    fig.canvas.draw_idle()

def on_click(event):
    if event.inaxes != ax:
        return
    if event.button == 1:       # left click → add point
        if len(points) < 2:
            points.append((event.xdata, event.ydata))
            print(f"  Point {len(points)}: pixel ({event.xdata:.1f}, {event.ydata:.1f})")
            redraw()
    else:                        # right / middle click → reset
        points.clear()
        redraw()
        print("  Points reset.")

fig.canvas.mpl_connect('button_press_event', on_click)
plt.show()
print("Done.")
