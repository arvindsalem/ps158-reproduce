"""Download the Fed's SCF Summary Extract Public Data (CSV), 1989-2025.

One file per survey year. The Fed re-releases every year's extract in the
latest survey's dollars (2025 dollars), so no further inflation adjustment is
needed downstream.
"""
import io
import zipfile
from pathlib import Path

import urllib.request

BASE = "https://www.federalreserve.gov/econres/files"
YEARS = [1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2013, 2016, 2019, 2022, 2025]
OUT = Path(__file__).parent / "data"


def main():
    OUT.mkdir(exist_ok=True)
    for year in YEARS:
        dest = OUT / f"scfp{year}.csv"
        if dest.exists():
            print(f"{year}: already have {dest.name}")
            continue
        url = f"{BASE}/scfp{year}excel.zip"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            content = r.read()
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            member = next(n for n in z.namelist() if n.lower().endswith(".csv"))
            dest.write_bytes(z.read(member))
        print(f"{year}: saved {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
