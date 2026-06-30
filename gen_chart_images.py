"""
gen_chart_images.py — render brand-styled chart PNGs for the PPTX decks.

Native PPTX scatter charts render unreliably in LibreOffice/PowerPoint, so the
predicted-vs-actual scatter is embedded as an image instead (bar/line charts are
kept native in the deck). Brand palette, transparent background.

Run:  python3 gen_chart_images.py   ->  img_scatter.png
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COB = "#306CB8"; INK3 = "#666D74"; LINE = "#D8DBDF"; INK4 = "#9399A0"

ME = json.load(open("model_eval.json"))
a = np.array(ME["scatter"]["actual"]) / 1000
p = np.array(ME["scatter"]["pred"]) / 1000
rng = np.random.default_rng(0)
idx = rng.choice(len(a), 700, replace=False)
a, p = a[idx], p[idx]

fig, ax = plt.subplots(figsize=(5.15, 3.45), dpi=200)
fig.patch.set_alpha(0)
ax.set_facecolor("none")
ax.plot([0, 1800], [0, 1800], ls=(0, (5, 4)), color=INK4, lw=1.2, zorder=1)
ax.scatter(a, p, s=9, color=COB, alpha=0.33, edgecolors="none", zorder=2)
ax.set_xlim(0, 1800); ax.set_ylim(0, 1800)
ax.set_xticks([0, 600, 1200, 1800]); ax.set_yticks([0, 600, 1200, 1800])
ax.set_xticklabels([f"${v}k" for v in [0, 600, 1200, 1800]], fontsize=8.5, color=INK3)
ax.set_yticklabels([f"${v}k" for v in [0, 600, 1200, 1800]], fontsize=8.5, color=INK3)
ax.set_xlabel("actual max loan ($k)", fontsize=9, color=INK3)
ax.set_ylabel("predicted ($k)", fontsize=9, color=INK3)
ax.grid(True, color=LINE, lw=0.6)
for sp in ["top", "right"]:
    ax.spines[sp].set_visible(False)
for sp in ["left", "bottom"]:
    ax.spines[sp].set_color(LINE)
ax.tick_params(length=0)
fig.tight_layout(pad=0.4)
fig.savefig("img_scatter.png", transparent=True)
print("wrote img_scatter.png")
