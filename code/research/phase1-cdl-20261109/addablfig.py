from pathlib import Path
p=Path('analyze_cdl.py'); s=p.read_text(encoding='utf-8')
needle='    print("WROTE", FIG)'
add='''    # Ablation
    abl = list(csv.DictReader(open(CDL / "cdl_ablation.csv", encoding="utf-8")))
    fig, ax = plt.subplots(figsize=(5.8, 3.2))
    scenes = ["A", "B", "C"]
    width = 0.25
    xs = np.arange(len(scenes))
    for j, (key, label) in enumerate([("assignment", "Assignment only"), ("power", "Power only"), ("joint", "Joint")]):
        vals = [100 * np.mean([(float(r[key]) - float(r["uniform"])) / float(r["uniform"])
                               for r in abl if r["profile"] == p]) for p in scenes]
        ax.bar(xs + (j - 1) * width, vals, width, label=label)
    ax.set_xticks(xs); ax.set_xticklabels([f"CDL-{p}" for p in scenes])
    ax.set_ylabel("Mean gain over uniform (%)")
    ax.set_title("Attribution on CDL")
    ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "cdl_ablation.pdf"); fig.savefig(FIG / "cdl_ablation.png", dpi=200); plt.close(fig)
    print("WROTE", FIG)'''
s=s.replace(needle,add)
p.write_text(s,encoding='utf-8'); print('ok')
