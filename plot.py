"""Plot weighted family net worth by education of the SCF reference person, 1989-2025.

Uses the Fed's Summary Extract files as downloaded by get_data.py. Those files
are already in 2025 dollars, so no inflation adjustment is applied here.

    python plot.py                       # mean, families with children (default)
    python plot.py --measure median
    python plot.py --families all
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

DATA = Path(__file__).parent / "data"
YEARS = [1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2013, 2016, 2019, 2022, 2025]
GROUPS = {"BA or more": lambda d: d.EDCL == 4, "HS or less": lambda d: d.EDCL <= 2}


def wmean(s, w):
    return (s * w).sum() / w.sum()


def wmedian(s, w):
    order = s.argsort()
    s, w = s.iloc[order], w.iloc[order]
    c = w.cumsum()
    return s[c >= c.iloc[-1] / 2].iloc[0]


def compute(measure, families):
    stat = wmean if measure == "mean" else wmedian
    rows = []
    for year in YEARS:
        d = pd.read_csv(DATA / f"scfp{year}.csv", usecols=["WGT", "EDCL", "NETWORTH", "KIDS"])
        if families == "kids":
            d = d[d.KIDS > 0]
        # WGT is already original weight / 5, so all five implicates are used as-is.
        for name, sel in GROUPS.items():
            g = d[sel(d)]
            rows.append((year, name, stat(g.NETWORTH.reset_index(drop=True), g.WGT.reset_index(drop=True))))
    return pd.DataFrame(rows, columns=["year", "group", "value"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", choices=["mean", "median"], default="mean")
    ap.add_argument("--families", choices=["kids", "all"], default="kids")
    a = ap.parse_args()

    df = compute(a.measure, a.families)
    df.to_csv(Path(__file__).parent / f"figure_data_{a.measure}_{a.families}.csv", index=False)

    fig, ax = plt.subplots(figsize=(9, 5.8))
    x = {y: i for i, y in enumerate(YEARS)}
    ax.axvspan(x[2013], x[2025] + 0.5, color="#eeeeee", zorder=0)
    ax.text(x[2013] + 0.1, ax.get_ylim()[1], "", va="top")
    colors = {"BA or more": "#1f5fbf", "HS or less": "#d62f2f"}
    for name, g in df.groupby("group"):
        ax.plot(g.year.map(x), g.value, lw=2.5, color=colors[name], label=name)
        last = g.iloc[-1]
        ax.annotate(f"${last.value / 1e3:,.0f}K", (x[2025], last.value), xytext=(8, 0),
                    textcoords="offset points", va="center")
    ax.set_xticks(list(x.values()), [str(y) for y in YEARS])
    ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
    ax.set_ylim(bottom=0)
    ax.set_xlim(-0.3, x[2025] + 1.2)
    ax.grid(axis="y", color="#dddddd")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylabel(f"{a.measure.capitalize()} family net worth (2025 dollars)")
    ax.text(x[2013] + 0.15, ax.get_ylim()[1] * 0.99, "2016-2025: added since\nPutnam (2015)",
            va="top", fontsize=9, color="#555555")
    ax.legend(frameon=False, loc="upper left")
    fams = "Families with children" if a.families == "kids" else "All families"
    ax.set_title(f"Growing wealth gap by education, 1989-2025", loc="left", fontweight="bold")
    fig.text(0.01, 0.01,
             f"{fams} (KIDS > 0 in the SCF extract). Education of the SCF reference person, not both parents.\n"
             "Dollars: Fed extract files are already in 2025 dollars (CPI-U-RS); not re-adjusted. "
             "Weighted by WGT, all 5 implicates.\n"
             "Source: Survey of Consumer Finances, Federal Reserve Board.",
             fontsize=7.5, color="#444444", va="bottom")
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    out = Path(__file__).parent / f"figure_{a.measure}_{a.families}.png"
    fig.savefig(out, dpi=150)
    print("saved", out)
    print(df.pivot(index="year", columns="group", values="value").round(-3))


if __name__ == "__main__":
    main()
