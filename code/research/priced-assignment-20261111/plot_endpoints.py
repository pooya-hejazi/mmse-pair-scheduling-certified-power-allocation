"""Render publication axes for the frozen endpoint estimates and block primitives."""
import argparse
import csv
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR",str(HERE/"matplotlib-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir",type=Path,default=HERE/"analysis")
    parser.add_argument("--output-dir",type=Path)
    options = parser.parse_args()
    input_dir = options.analysis_dir
    target = options.output_dir or input_dir/"figures"
    report = json.loads((input_dir/"results.json").read_text())
    if report["status"] != "COMPLETE":
        raise ValueError("The frozen analysis must have completed")
    with (input_dir/"block_effects.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    block_ids = np.asarray([int(row["block"]) for row in rows])
    if list(block_ids) != list(range(20)):
        raise ValueError("Expected one effect from each of 20 blocks")
    differences = np.asarray([float(row["mean_new_minus_best"]) for row in rows])
    ratios = np.exp([float(row["mean_log_time_ratio"]) for row in rows])
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8,
                         "axes.spines.top":False,"axes.spines.right":False,"pdf.fonttype":42})
    fig, axes = plt.subplots(1,3,figsize=(7.05,3.35),sharey=True)
    panels = (
        ("Primary rate, 95% interval", differences, report["primary_rate"],1000.,
         report["primary_margin_bpshz"],"SE difference\n($10^{-3}$ bit/s/Hz)"),
        ("Secondary rate, 97.5%",differences,report["secondary_rate"],1000.,
         report["secondary_floor_bpshz"],"SE difference\n($10^{-3}$ bit/s/Hz)"),
        ("Secondary time, 97.5%",ratios,report["geometric_time_ratio"],1.,
         report["secondary_time_ratio_threshold"],"Time ratio to\nfastest control"))
    for ax,(title,values,estimate,scale,margin,label) in zip(axes,panels):
        ax.axvline(margin*scale,color="#af4642",ls="--",lw=1.15,zorder=0)
        ax.scatter(values*scale,block_ids,c="#397b99",s=13,zorder=2)
        ax.axhline(20.3,color="#b7b7b7",lw=.55,zorder=0)
        ax.plot([estimate["low"]*scale,estimate["high"]*scale],[22,22],color="#172932",lw=2.3)
        ax.vlines([estimate["low"]*scale,estimate["high"]*scale],21.75,22.25,color="#172932",lw=.8)
        ax.scatter(estimate["mean"]*scale,22,color="#172932",s=14,marker="D",zorder=3)
        ax.set_title(title,fontsize=8.5,pad=6)
        ax.set_xlabel(label)
        ax.set_ylim(-1,23.6)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4,steps=[1,2,2.5,5,10]))
        if title.startswith("Secondary rate"):
            ax.set_xticks([-1,0,5,10])
        if label.startswith("Time ratio"):
            ax.set_xlim(left=0)
            ax.set_xticks([0,.5,1,1.5])
        ax.tick_params(labelsize=7)
    axes[0].set_yticks([0,5,10,15,19,22],["0","5","10","15","19","Mean"])
    axes[0].set_ylabel("Replicate block")
    legend = [Line2D([],[],marker="o",ls="none",color="#397b99",markersize=4,label="Block effect"),
              Line2D([],[],marker="D",color="#172932",lw=1.7,ms=4,label="Mean and bootstrap interval"),
              Line2D([],[],ls="--",color="#af4642",lw=1.1,label="Decision margin")]
    fig.legend(handles=legend,loc="lower center",ncol=3,frameon=False,fontsize=7.3)
    fig.subplots_adjust(left=.09,right=.985,bottom=.275,top=.90,wspace=.24)
    target.mkdir(parents=True,exist_ok=True)
    for suffix in ("pdf","png"):
        fig.savefig(target/("priced_cdl_endpoints."+suffix),dpi=240,bbox_inches="tight",pad_inches=.025)
    plt.close(fig)


if __name__ == "__main__":
    main()
