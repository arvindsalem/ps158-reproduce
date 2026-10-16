"""Standard errors for the 2025 SCF education wealth gap, following the Fed's MEANIT macro.

Total SE = sqrt((6/5) * imputation variance + sampling variance):
  - imputation variance: variance of the estimate across the 5 implicates
  - sampling variance: variance across 999 bootstrap replicates (first implicate only),
    using replicate weight = wt1b * mm (multiplicity), per the 2025 codebook.
Needs data/p25_rw1.dta from https://www.federalreserve.gov/econres/files/scf2025rw1s.zip
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data"


def wmean(nw, w):
    return (nw * w).sum(axis=0) / w.sum(axis=0)


def wmedian(nw, w):
    o = np.argsort(nw)
    nw, w = nw[o], w[o]
    c = np.cumsum(w, axis=0)
    idx = (c >= 0.5 * c[-1]).argmax(axis=0)
    return nw[idx]


def load():
    d = pd.read_csv(DATA / "scfp2025.csv", usecols=["YY1", "Y1", "WGT", "EDCL", "KIDS", "NETWORTH"])
    d["imp"] = d.Y1 - 10 * d.YY1
    rw = pd.read_stata(DATA / "p25_rw1.dta").set_index("yy1")
    first = d[d.imp == 1].set_index("YY1").join(rw[[c for c in rw.columns if c[:4] in ("wt1b",) or c[:2] == "mm"]])
    wt = first[[f"wt1b{i}" for i in range(1, 1000)]].fillna(0).clip(lower=0).to_numpy()
    mm = first[[f"mm{i}" for i in range(1, 1000)]].fillna(0).clip(lower=0).to_numpy()
    return d, first, wt * mm


def estimate(d, first, rep_w, group, measure, families):
    stat = wmean if measure == "mean" else wmedian

    def member(df):
        m = group(df)
        return m & (df.KIDS > 0) if families == "kids" else m

    # point estimate and imputation spread: one estimate per implicate
    imp_vals = []
    for i in range(1, 6):
        s = d[d.imp == i]
        s = s[member(s)]
        imp_vals.append(stat(s.NETWORTH.to_numpy(), s.WGT.to_numpy()[:, None])[0] if measure == "median"
                        else stat(s.NETWORTH.to_numpy(), s.WGT.to_numpy()))
    imp_vals = np.array(imp_vals)
    # sampling spread: 999 replicates on implicate 1
    m = member(first).to_numpy()
    nw = first.NETWORTH.to_numpy()[m]
    reps = stat(nw[:, None], rep_w[m]) if measure == "mean" else stat(nw, rep_w[m])
    return imp_vals, np.asarray(reps)


def combine(imp_vals, reps):
    imp_var = imp_vals.var(ddof=1)
    samp_var = reps.var(ddof=1)
    return imp_vals.mean(), np.sqrt(1.2 * imp_var + samp_var), np.sqrt(imp_var), np.sqrt(samp_var)


def main():
    d, first, rep_w = load()
    groups = {"BA or more": lambda x: x.EDCL == 4, "HS or less": lambda x: x.EDCL <= 2}
    for families in ("all", "kids"):
        for measure in ("mean", "median"):
            res = {}
            for g, f in groups.items():
                iv, rv = estimate(d, first, rep_w, f, measure, families)
                res[g] = (iv, rv)
                est, se, se_i, se_s = combine(iv, rv)
                print(f"{families:4s} {measure:6s} {g:11s} est ${est/1e3:8,.0f}K  SE ${se/1e3:6,.0f}K  "
                      f"95% CI ${ (est-1.96*se)/1e3:,.0f}K to ${(est+1.96*se)/1e3:,.0f}K  "
                      f"(imputation SE {se_i/1e3:,.1f}K, sampling SE {se_s/1e3:,.1f}K)")
            # ratio BA/HS: compute per implicate and per replicate, then combine
            iv = res["BA or more"][0] / res["HS or less"][0]
            rv = res["BA or more"][1] / res["HS or less"][1]
            est, se, *_ = combine(iv, rv)
            print(f"{families:4s} {measure:6s} ratio BA/HS {est:5.2f}x  SE {se:.2f}  95% CI {est-1.96*se:.1f}x to {est+1.96*se:.1f}x")
        print()


if __name__ == "__main__":
    main()
