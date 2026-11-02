"""Price benchmarks: Medicare rates and the hospital's own price transparency file.

Two sources matter in a negotiation:

1. Medicare's payment for the same code (OPPS for facility outpatient, PFS for
   professional services, CLFS for labs, ASP for drugs). Hospitals accept these
   rates from their largest payer, which makes them the strongest objective anchor.
2. The hospital's machine-readable file (MRF) required by 45 CFR 180. It lists the
   gross charge, the discounted cash price, each payer's negotiated rate, and the
   de-identified minimum and maximum. The cash price and the minimum negotiated
   rate are prices the hospital already accepts for this exact item.

CMS hosts are often unreachable from sandboxed environments, so every loader
accepts a local file path and the module ships illustrative fallback rates.
"""
from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Iterable, Optional

import requests

from .models import Benchmark, Bill

DATA = Path(__file__).parent / "data"


class MedicareRates:
    """Lookup of national Medicare payment by CPT/HCPCS."""

    def __init__(self, rates: dict[str, dict]):
        self.rates = rates

    @classmethod
    def illustrative(cls) -> "MedicareRates":
        payload = json.loads((DATA / "medicare_sample_rates.json").read_text())
        return cls(payload["rates"])

    @classmethod
    def from_opps_addendum_b(cls, path: Path) -> "MedicareRates":
        """Parse a CMS OPPS Addendum B CSV (columns vary by year; we look for HCPCS and Payment Rate)."""
        rates: dict[str, dict] = {}
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cols = {c.lower().strip(): c for c in reader.fieldnames or []}
            code_col = next((cols[c] for c in cols if "hcpcs" in c), None)
            pay_col = next((cols[c] for c in cols if "payment rate" in c), None)
            if not code_col or not pay_col:
                raise ValueError(f"Could not find HCPCS / Payment Rate columns in {path}")
            for row in reader:
                code = (row.get(code_col) or "").strip()
                raw = (row.get(pay_col) or "").replace("$", "").replace(",", "").strip()
                try:
                    amt = float(raw)
                except ValueError:
                    continue
                if code and amt > 0:
                    rates[code] = {"amount": amt, "source": f"OPPS Addendum B ({path.name})"}
        return cls(rates)

    @classmethod
    def from_pfs_national(cls, path: Path) -> "MedicareRates":
        """Parse the CMS PFS national payment amount file (PPRRVU style CSV) for non-facility payment."""
        rates: dict[str, dict] = {}
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cols = {c.lower().strip(): c for c in reader.fieldnames or []}
            code_col = next((cols[c] for c in cols if c in {"hcpcs", "hcpcs code", "cpt"}), None)
            pay_col = next((cols[c] for c in cols if "non-facility" in c and "payment" in c or "nonfacility" in c and "amount" in c), None)
            if not code_col or not pay_col:
                raise ValueError(f"Could not find HCPCS / non-facility payment columns in {path}")
            for row in reader:
                try:
                    amt = float((row.get(pay_col) or "").replace("$", "").replace(",", ""))
                except ValueError:
                    continue
                code = (row.get(code_col) or "").strip()
                if code and amt > 0:
                    rates[code] = {"amount": amt, "source": f"PFS national ({path.name})"}
        return cls(rates)

    def merge(self, other: "MedicareRates") -> "MedicareRates":
        merged = dict(self.rates)
        merged.update(other.rates)
        return MedicareRates(merged)

    def get(self, code: Optional[str]) -> Optional[dict]:
        if not code:
            return None
        return self.rates.get(code.upper())


class HospitalMRF:
    """Reader for CMS hospital price transparency machine-readable files (v2.0+ JSON or CSV 'tall' layout)."""

    def __init__(self, items: list[dict], source: str):
        self.items = items
        self.source = source
        self._by_code: dict[str, list[dict]] = {}
        for it in items:
            for code in it.get("codes", []):
                self._by_code.setdefault(code, []).append(it)

    @staticmethod
    def discover_url(hospital_homepage: str, timeout: int = 15) -> Optional[str]:
        """Hospitals must post cms-hpt.txt at their web root listing the MRF URL (45 CFR 180.50(d))."""
        base = hospital_homepage.rstrip("/")
        try:
            r = requests.get(f"{base}/cms-hpt.txt", timeout=timeout)
            if r.ok:
                for line in r.text.splitlines():
                    if line.lower().startswith("mrf-url"):
                        return line.split(":", 1)[1].strip()
        except requests.RequestException:
            return None
        return None

    @classmethod
    def from_json(cls, path: Path) -> "HospitalMRF":
        payload = json.loads(Path(path).read_text())
        items = []
        for sc in payload.get("standard_charge_information", []):
            codes = [c.get("code", "").upper() for c in sc.get("code_information", []) if c.get("type", "").upper() in {"CPT", "HCPCS", "MS-DRG", "NDC", "RC"}]
            for charge in sc.get("standard_charges", []):
                negotiated = []
                for p in charge.get("payers_information", []):
                    amt = p.get("standard_charge_dollar")
                    if amt is not None:
                        negotiated.append(float(amt))
                items.append({
                    "description": sc.get("description"),
                    "codes": codes,
                    "setting": charge.get("setting"),
                    "gross": charge.get("gross_charge"),
                    "cash": charge.get("discounted_cash"),
                    "min": charge.get("minimum"),
                    "max": charge.get("maximum"),
                    "negotiated": negotiated,
                })
        return cls(items, source=str(path))

    @classmethod
    def from_csv_tall(cls, path: Path) -> "HospitalMRF":
        items: dict[tuple, dict] = {}
        with open(path, newline="", encoding="utf-8-sig") as f:
            # CMS CSV templates carry two metadata rows before the header
            rows = list(csv.reader(f))
        header_idx = next(i for i, r in enumerate(rows) if any("description" == c.strip().lower() for c in r))
        header = [c.strip().lower() for c in rows[header_idx]]
        for r in rows[header_idx + 1:]:
            row = dict(zip(header, r))
            codes = [row[k].upper() for k in header if k.startswith("code|") and not k.endswith("|type") and row.get(k)]
            key = (row.get("description"), tuple(codes), row.get("setting"))
            it = items.setdefault(key, {"description": row.get("description"), "codes": codes, "setting": row.get("setting"),
                                        "gross": _f(row.get("standard_charge|gross")), "cash": _f(row.get("standard_charge|discounted_cash")),
                                        "min": _f(row.get("standard_charge|min")), "max": _f(row.get("standard_charge|max")), "negotiated": []})
            neg = _f(row.get("standard_charge|negotiated_dollar"))
            if neg is not None:
                it["negotiated"].append(neg)
        return cls(list(items.values()), source=str(path))

    def lookup(self, code: Optional[str], setting: Optional[str] = None) -> Optional[dict]:
        if not code:
            return None
        hits = self._by_code.get(code.upper(), [])
        if setting:
            pref = [h for h in hits if (h.get("setting") or "").lower().startswith(setting.lower())]
            hits = pref or hits
        if not hits:
            return None
        neg = [n for h in hits for n in h["negotiated"]]
        cash = [h["cash"] for h in hits if h.get("cash") is not None]
        mins = [h["min"] for h in hits if h.get("min") is not None]
        return {
            "cash": min(cash) if cash else None,
            "min_negotiated": min(mins) if mins else (min(neg) if neg else None),
            "median_negotiated": statistics.median(neg) if neg else None,
            "gross": hits[0].get("gross"),
        }


def _f(v: Optional[str]) -> Optional[float]:
    try:
        return float(str(v).replace("$", "").replace(",", "")) if v not in (None, "") else None
    except ValueError:
        return None


def benchmark_bill(bill: Bill, medicare: Optional[MedicareRates] = None, mrf: Optional[HospitalMRF] = None) -> list[Benchmark]:
    medicare = medicare or MedicareRates.illustrative()
    out = []
    setting = "outpatient" if bill.setting in {"emergency", "observation", "outpatient"} else ("inpatient" if bill.setting == "inpatient" else None)
    for line in bill.lines:
        b = Benchmark(line_id=line.line_id, cpt_hcpcs=line.cpt_hcpcs, billed=line.total_charge)
        m = medicare.get(line.cpt_hcpcs)
        if m:
            b.medicare_rate = round(m["amount"] * max(line.units, 1), 2)
            b.medicare_source = m["source"]
            if b.medicare_rate:
                b.markup_vs_medicare = round(line.total_charge / b.medicare_rate, 1)
        if mrf:
            h = mrf.lookup(line.cpt_hcpcs, setting)
            if h:
                b.hospital_cash_price = h["cash"]
                b.payer_min_negotiated = h["min_negotiated"]
                b.payer_median_negotiated = h["median_negotiated"]
                b.mrf_source = mrf.source
        out.append(b)
    return out


def summarize(benchmarks: Iterable[Benchmark]) -> dict:
    bl = list(benchmarks)
    med = [b for b in bl if b.medicare_rate]
    cash = [b for b in bl if b.hospital_cash_price]
    return {
        "lines": len(bl),
        "lines_with_medicare": len(med),
        "billed_on_benchmarked_lines": round(sum(b.billed for b in med), 2),
        "medicare_on_benchmarked_lines": round(sum(b.medicare_rate for b in med), 2),
        "median_markup_vs_medicare": statistics.median([b.markup_vs_medicare for b in med]) if med else None,
        "lines_with_cash_price": len(cash),
        "cash_price_total": round(sum(b.hospital_cash_price for b in cash), 2) if cash else None,
        "coverage_note": "Medicare and MRF totals cover only matched lines; extrapolate with care." if med and len(med) < len(bl) else "",
    }
