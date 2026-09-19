"""Fig. 4-6 (reverse-only run): uncorrected prediction, residual field, residual-IDW map.

Calibration points are drawn as green squares and test points as white crosses so
that the two roles are distinguishable (reviewer comment on v1).
Grid values come from analysis/reverse_only/processed/grid_predictions.csv, whose
calibration values are the run average (display only; metrics use per-window values).
"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WS = Path("/data/RFVisualizer_Workspace")
RUN = WS / "experiments/0821_lounge_201729"
GRID = RUN / "analysis/reverse_only/processed/grid_predictions.csv"
POINTS = RUN / "processed/sionna_points.csv"
OUT = Path(__file__).resolve().parent
TX = (21.37, 17.83)  # configs/tx_rx.json

rows = list(csv.DictReader(open(GRID)))
r = np.array([int(x["row"]) for x in rows])
c = np.array([int(x["column"]) for x in rows])
xs = np.full(c.max() + 1, np.nan)
ys = np.full(r.max() + 1, np.nan)
xs[c] = [float(x["x"]) for x in rows]
ys[r] = [float(x["y"]) for x in rows]
# ponytail: fill empty grid columns/rows by the constant 0.75 m pitch
xs = xs[np.nanargmin(xs)] + 0.75 * (np.arange(len(xs)) - np.nanargmin(xs))
ys = ys[np.nanargmin(ys)] + 0.75 * (np.arange(len(ys)) - np.nanargmin(ys))


def field(column):
    m = np.full((len(ys), len(xs)), np.nan)
    m[r, c] = [float(x[column]) for x in rows]
    return m


raw = field("raw_sionna_rssi_dbm")
residual_map = field("residual_idw_rssi_dbm")
pts = list(csv.DictReader(open(POINTS)))
cal = np.array([[float(p["x"]), float(p["y"])] for p in pts if p["point_role"] == "calibration"])
test = np.array([[float(p["x"]), float(p["y"])] for p in pts if p["point_role"] == "test"])
assert len(cal) == 4 and len(test) == 10

plt.rcParams.update({"font.size": 20})


def draw(name, matrix, cmap, vmin, vmax, label):
    fig, ax = plt.subplots(figsize=(14.4, 7.2))
    im = ax.pcolormesh(xs, ys, matrix, shading="nearest", cmap=cmap, vmin=vmin, vmax=vmax)
    fig.colorbar(im, ax=ax, label=label, fraction=0.035, pad=0.02)
    ax.scatter(*test.T, marker="x", color="white", s=220, linewidths=4, label="Test point")
    ax.scatter(*cal.T, marker="s", color="#1a9641", edgecolor="white", s=220, linewidths=2,
               label="Calibration point")
    ax.scatter(*TX, marker="*", color="red", edgecolor="white", s=900, linewidths=1.5,
               label="Transmitter")
    ax.set_aspect("equal")
    ax.set_xlabel("X (m)", fontsize=26)
    ax.set_ylabel("Y (m)", fontsize=26)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=16,
              frameon=True, facecolor="0.8", edgecolor="0.8")  # gray so the white cross shows
    ax.set_facecolor("white")
    fig.savefig(OUT / name, dpi=100, bbox_inches="tight")
    plt.close(fig)


draw("fig4_v3.png", raw, "viridis", -95, -20, "Predicted received power (dBm)")
draw("fig5_v3.png", residual_map - raw, "RdBu_r", -20, 20, "Residual (dB)")
draw("fig6_v3.png", residual_map, "viridis", -95, -20, "Estimated RSSI (dBm)")
