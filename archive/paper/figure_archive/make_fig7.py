"""Fig. 7: three PC renderer captures in one row, labels under each panel (placeholder layout)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

panels = [("Fig7-1.png", "(a) LoS corridor, residual IDW"),
          ("Fig7-2.png", "(b) NLoS corridor, uncorrected"),
          ("Fig7-3.png", "(c) NLoS corridor, residual IDW")]
fig, axes = plt.subplots(1, 3, figsize=(15, 3.3))
for ax, (path, label) in zip(axes, panels):
    ax.imshow(mpimg.imread(path))
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#94a3b8"); s.set_linewidth(1.2)
    ax.set_xlabel(label, fontsize=13, labelpad=8)
fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.14, wspace=0.04)
fig.savefig("fig7_v3.png", dpi=300, facecolor="white")
