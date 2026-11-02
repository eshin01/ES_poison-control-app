"""Deterministic audit rules for itemized bills.

Each rule returns Finding objects. The rules need no network or model access, so they
run the same way every time and can be unit tested. The LLM layer sits on top and
explains findings or hunts for things the rules miss.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Iterable, Optional

from .models import EOB, Bill, Finding, LineItem, Severity

DATA = Path(__file__).parent / "data"

ED_FACILITY_LEVELS = ["99281", "99282", "99283", "99284", "99285"]
CRITICAL_CARE = {"99291", "99292"}
OBSERVATION_HOURLY = {"G0378"}
ROOM_BOARD_REV = {"0100", "0110", "0111", "0112", "0113", "0114", "0115", "0116", "0117", "0118", "0119",
                  "0120", "0121", "0122", "0123", "0124", "0125", "0126", "0127", "0128", "0129",
                  "0130", "0140", "0150", "0160", "0200", "0201", "0202", "0203", "0204", "0206", "0207", "0208", "0209",
                  "0210", "0211", "0212", "0213", "0214", "0219"}
PHARMACY_REV = {"0250", "0251", "0252", "0254", "0255", "0257", "0258", "0259", "0636", "0637"}


def _load_ptp(path: Optional[Path] = None) -> dict[tuple[str, str], dict]:
    path = path or DATA / "ncci_ptp_sample.csv"
    pairs: dict[tuple[str, str], dict] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            pairs[(row["column1"].strip(), row["column2"].strip())] = row
    return pairs


def _load_mue(path: Optional[Path] = None) -> dict[str, dict]:
    path = path or DATA / "mue_sample.csv"
    with open(path, newline="") as f:
        return {row["cpt_hcpcs"].strip(): row for row in csv.DictReader(f)}


def _load_supplies() -> dict:
    return json.loads((DATA / "routine_supplies.json").read_text())


def _norm(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# --------------------------------------------------------------------------- rules


def rule_duplicates(bill: Bill) -> list[Finding]:
    """Same code (or same description when no code), same date, billed more than once."""
    groups: dict[tuple, list[LineItem]] = defaultdict(list)
    for line in bill.lines:
        key = (line.service_date, line.cpt_hcpcs or _norm(line.description), round(line.total_charge / max(line.units, 1), 2))
        groups[key].append(line)
    out = []
    for key, lines in groups.items():
        if len(lines) < 2:
            continue
        code = key[1]
        # a legitimately repeated drug dose or hourly observation is not a duplicate
        if code and (code.startswith("J") or code in OBSERVATION_HOURLY):
            continue
        dup_amount = sum(l.total_charge for l in lines[1:])
        out.append(Finding(
            rule="duplicate_charge",
            severity=Severity.high,
            line_ids=[l.line_id for l in lines],
            title=f"Possible duplicate: '{lines[0].description}' billed {len(lines)} times on {key[0] or 'same date'}",
            explanation="Identical code, date, and unit price appear on multiple rows. Hospitals' own audit literature lists duplicate charges as the most common itemized-bill error. Ask the provider to produce the medical record entries supporting each instance or remove the extras.",
            disputed_amount=round(dup_amount, 2),
            evidence=["Medliminal Health Solutions hospital bill audit (duplicate charges most common error)", "Request medical record under 45 CFR 164.524 to confirm"],
            confidence="deduction",
            requires_records=True,
        ))
    return out


def rule_mue(bill: Bill, mue: Optional[dict] = None) -> list[Finding]:
    """Units per day exceed the Medically Unlikely Edit ceiling."""
    mue = mue or _load_mue()
    per_day: dict[tuple, list[LineItem]] = defaultdict(list)
    for line in bill.lines:
        if line.cpt_hcpcs and line.cpt_hcpcs in mue:
            per_day[(line.service_date, line.cpt_hcpcs)].append(line)
    out = []
    for (day, code), lines in per_day.items():
        units = sum(l.units for l in lines)
        cap = float(mue[code]["mue"])
        if units > cap:
            unit_price = lines[0].total_charge / max(lines[0].units, 1)
            excess = units - cap
            out.append(Finding(
                rule="mue_exceeded",
                severity=Severity.high,
                line_ids=[l.line_id for l in lines],
                title=f"{code} billed {units:g} units on {day or 'one date'}; Medicare's unit ceiling is {cap:g}",
                explanation=f"CMS Medically Unlikely Edits cap {code} at {cap:g} unit(s) per day ({mue[code]['rationale']}). Units above the cap are presumptively billing errors unless the record documents a separate, distinct service.",
                disputed_amount=round(excess * unit_price, 2),
                evidence=["CMS NCCI Medically Unlikely Edits (practitioner and facility outpatient tables)"],
                confidence="deduction",
                requires_records=True,
            ))
    return out


def rule_unbundling(bill: Bill, ptp: Optional[dict] = None) -> list[Finding]:
    """Column-2 code billed alongside its column-1 comprehensive code on the same date."""
    ptp = ptp or _load_ptp()
    by_day: dict = defaultdict(list)
    for line in bill.lines:
        if line.cpt_hcpcs:
            by_day[line.service_date].append(line)
    out = []
    for day, lines in by_day.items():
        codes = {l.cpt_hcpcs: l for l in lines}
        for (c1, c2), row in ptp.items():
            if c1 in codes and c2 in codes:
                comp = codes[c2]
                mod_ok = row["modifier_indicator"] == "1" and any(m in {"59", "XE", "XS", "XP", "XU", "25"} for m in comp.modifiers)
                if mod_ok:
                    continue
                out.append(Finding(
                    rule="unbundling",
                    severity=Severity.high,
                    line_ids=[codes[c1].line_id, comp.line_id],
                    title=f"{c2} ('{comp.description}') is a component of {c1} and should not be billed separately",
                    explanation=f"{row['rationale']}. CMS National Correct Coding Initiative procedure-to-procedure edits treat {c2} as included in {c1} when both are reported on the same date"
                                + (" unless an appropriate modifier documents a distinct service; none is present." if row["modifier_indicator"] == "1" else "; no modifier can override this pair."),
                    disputed_amount=round(comp.total_charge, 2),
                    evidence=[f"CMS NCCI PTP edit {c1}/{c2}, modifier indicator {row['modifier_indicator']}"],
                    confidence="fact" if row["modifier_indicator"] == "0" else "deduction",
                ))
    return out


def rule_ed_level(bill: Bill) -> list[Finding]:
    """Flag a level 4 or 5 ED facility charge that lacks supporting intensity, and any ED visit billed with both facility and critical care."""
    out = []
    levels = [l for l in bill.lines if l.cpt_hcpcs in ED_FACILITY_LEVELS]
    if not levels:
        return out
    codes = {l.cpt_hcpcs for l in bill.lines if l.cpt_hcpcs}
    intensity_markers = {"70450", "70460", "70470", "74176", "74177", "74178", "71250", "71260", "96365", "96374", "96360", "99291", "99292"}
    has_intensity = bool(codes & intensity_markers)
    for lvl in levels:
        if lvl.cpt_hcpcs in {"99284", "99285"} and not has_intensity:
            out.append(Finding(
                rule="ed_level_support",
                severity=Severity.medium,
                line_ids=[lvl.line_id],
                title=f"Emergency department level {lvl.cpt_hcpcs[-1]} facility charge with no imaging, infusion, or critical care on the bill",
                explanation="Facility ED levels are set by the hospital's own intensity criteria. A level 4 or 5 charge without CT, infusion, or critical care on the same bill is worth challenging: ask for the hospital's written leveling criteria and the nursing interventions documented for this visit. If unsupported, request reassignment to the level the record supports.",
                disputed_amount=round(lvl.total_charge * 0.4, 2),
                evidence=["CMS OPPS: facilities must apply their own documented ED leveling guidelines consistently (65 FR 18451; annual OPPS rule preamble)"],
                confidence="speculation",
                requires_records=True,
            ))
        if CRITICAL_CARE & codes:
            cc = [l for l in bill.lines if l.cpt_hcpcs in CRITICAL_CARE]
            out.append(Finding(
                rule="ed_level_plus_critical_care",
                severity=Severity.high,
                line_ids=[lvl.line_id] + [c.line_id for c in cc],
                title="Both an ED visit level and critical care (99291) are billed by the facility for the same date",
                explanation="Under OPPS a facility reports critical care 99291 instead of, not in addition to, an ED visit level for the same encounter. One of these charges should come off.",
                disputed_amount=round(lvl.total_charge, 2),
                evidence=["CMS OPPS critical care facility billing guidance (Medicare Claims Processing Manual ch. 4 section 160.1)"],
                confidence="deduction",
            ))
    return out


def rule_routine_supplies(bill: Bill, supplies: Optional[dict] = None) -> list[Finding]:
    """Gloves, gowns, tubing and similar items billed as separate lines."""
    supplies = supplies or _load_supplies()
    kws = supplies["keywords"]
    hits = []
    for line in bill.lines:
        if line.cpt_hcpcs:
            continue  # a coded lab, drug, or procedure is never a routine supply
        desc = _norm(line.description)
        # whole-word keyword match on the description; revenue-code-only match is limited to cheap 0270-series lines
        if any(re.search(r"\b" + re.escape(k) + r"s?\b", desc) for k in kws) or (line.revenue_code in {"0270", "0271"} and line.total_charge < 150):
            hits.append(line)
    if not hits:
        return []
    total = sum(l.total_charge for l in hits)
    return [Finding(
        rule="routine_supplies",
        severity=Severity.medium,
        line_ids=[l.line_id for l in hits],
        title=f"{len(hits)} routine supply line(s) billed separately (gloves, tubing, kits, etc.)",
        explanation="Medicare's Provider Reimbursement Manual treats these as routine supplies whose cost is included in the room, procedure, or visit charge, not billable as separate items. Ask for them to be removed or absorbed into the primary charge.",
        disputed_amount=round(total, 2),
        evidence=["CMS Provider Reimbursement Manual Part 1, ch. 22, sections 2202.6 and 2203"],
        confidence="deduction",
    )]


def rule_missing_codes(bill: Bill) -> list[Finding]:
    """Charges with no CPT/HCPCS and no revenue code cannot be benchmarked or verified."""
    missing = [l for l in bill.lines if not l.cpt_hcpcs and not l.revenue_code and l.total_charge >= 100]
    if not missing:
        return []
    return [Finding(
        rule="uncoded_charge",
        severity=Severity.medium,
        line_ids=[l.line_id for l in missing],
        title=f"{len(missing)} charge(s) over $100 carry no CPT/HCPCS or revenue code",
        explanation="Without a code the charge cannot be matched to the chargemaster, the claim, or any benchmark. Request a corrected itemized statement that shows the billing code and date for every line. Hold payment on these lines until coded.",
        disputed_amount=round(sum(l.total_charge for l in missing), 2),
        evidence=["Hospital price transparency rule requires every standard charge to be tied to a billing code (45 CFR 180.50)"],
        confidence="deduction",
    )]


def rule_dates(bill: Bill) -> list[Finding]:
    """Service dates outside the admission window, and room and board on the discharge day."""
    out = []
    if bill.admit_date and bill.discharge_date:
        outside = [l for l in bill.lines if l.service_date and not (bill.admit_date <= l.service_date <= bill.discharge_date)]
        if outside:
            out.append(Finding(
                rule="date_outside_stay",
                severity=Severity.high,
                line_ids=[l.line_id for l in outside],
                title=f"{len(outside)} line(s) dated outside the {bill.admit_date} to {bill.discharge_date} stay",
                explanation="Charges dated before admission or after discharge usually belong to another patient or encounter, or were posted on the wrong date. Ask for proof of service or removal.",
                disputed_amount=round(sum(l.total_charge for l in outside), 2),
                confidence="deduction",
                requires_records=True,
            ))
        rb_discharge = [l for l in bill.lines if l.revenue_code in ROOM_BOARD_REV and l.service_date == bill.discharge_date]
        if rb_discharge and bill.discharge_date != bill.admit_date:
            out.append(Finding(
                rule="room_board_discharge_day",
                severity=Severity.medium,
                line_ids=[l.line_id for l in rb_discharge],
                title="Room and board charged for the day of discharge",
                explanation="Medicare counts inpatient days by midnights; the day of discharge is not a billable day. Many commercial contracts follow the same convention. Ask that the discharge-day accommodation charge be removed.",
                disputed_amount=round(sum(l.total_charge for l in rb_discharge), 2),
                evidence=["Medicare Benefit Policy Manual ch. 3 section 20.1 (day of discharge not counted)"],
                confidence="deduction",
            ))
        nights = (bill.discharge_date - bill.admit_date).days
        rb_lines = [l for l in bill.lines if l.revenue_code in ROOM_BOARD_REV]
        rb_days = sum(l.units for l in rb_lines)
        if rb_lines and nights >= 0 and rb_days > max(nights, 1):
            out.append(Finding(
                rule="room_board_units",
                severity=Severity.high,
                line_ids=[l.line_id for l in rb_lines],
                title=f"{rb_days:g} accommodation days billed for a {nights}-night stay",
                explanation="Accommodation units exceed the number of midnights in the stay.",
                disputed_amount=round((rb_days - max(nights, 1)) * (sum(l.total_charge for l in rb_lines) / rb_days), 2),
                confidence="deduction",
            ))
    return out



def rule_observation_hours(bill: Bill) -> list[Finding]:
    """Observation hours that exceed the possible hours in the encounter window."""
    obs = [l for l in bill.lines if l.cpt_hcpcs in OBSERVATION_HOURLY]
    if not obs or not (bill.admit_date and bill.discharge_date):
        return []
    hours = sum(l.units for l in obs)
    max_hours = ((bill.discharge_date - bill.admit_date).days + 1) * 24
    if hours > max_hours:
        unit = sum(l.total_charge for l in obs) / hours
        return [Finding(
            rule="observation_hours",
            severity=Severity.high,
            line_ids=[l.line_id for l in obs],
            title=f"{hours:g} observation hours billed; the encounter window allows at most {max_hours}",
            explanation="Observation (G0378) is billed per hour of actual observation care, excluding time in procedures and after the discharge order. Hours beyond the encounter window are not possible.",
            disputed_amount=round((hours - max_hours) * unit, 2),
            evidence=["Medicare Claims Processing Manual ch. 4 section 290.2.2"],
            confidence="fact",
        )]
    return []


def rule_pharmacy_markup(bill: Bill, threshold: float = 50.0) -> list[Finding]:
    """Common drugs with unit charges far above any plausible acquisition cost."""
    cheap = {"J1885": ("ketorolac 15 mg", 2.0), "J2405": ("ondansetron 1 mg", 1.0), "J7030": ("normal saline 1000 mL", 3.0),
             "J7040": ("normal saline 500 mL", 2.0), "J1100": ("dexamethasone 1 mg", 1.0), "J2550": ("promethazine 50 mg", 2.0),
             "J0171": ("epinephrine 0.1 mg", 2.0), "J1200": ("diphenhydramine 50 mg", 2.0), "J2270": ("morphine 10 mg", 3.0),
             "J0690": ("cefazolin 500 mg", 3.0), "J1642": ("heparin 10 units", 1.0)}
    out = []
    for l in bill.lines:
        if l.cpt_hcpcs in cheap:
            name, approx_cost = cheap[l.cpt_hcpcs]
            unit = l.total_charge / max(l.units, 1)
            if unit / approx_cost >= threshold:
                out.append(Finding(
                    rule="pharmacy_markup",
                    severity=Severity.low,
                    line_ids=[l.line_id],
                    title=f"{name} billed at about {unit / approx_cost:.0f}x a typical acquisition cost",
                    explanation="Hospitals may lawfully mark up drugs, so this is a negotiation point rather than an error. Anchor the drug lines to the Medicare average sales price plus 6 percent, which is what Medicare pays.",
                    disputed_amount=round(l.total_charge - approx_cost * 1.06 * max(l.units, 1), 2),
                    evidence=["CMS ASP drug pricing files (quarterly)"],
                    confidence="deduction",
                ))
    return out


def rule_eob_reconciliation(bill: Bill, eob: Optional[EOB]) -> list[Finding]:
    """Patient billed more than the EOB says they owe, or balance billed by an in-network provider."""
    if not eob:
        return []
    out = []
    eob_pr = eob.total_patient_responsibility
    if eob_pr is None:
        eob_pr = sum((l.patient_responsibility or 0) for l in eob.lines)
    billed_pr = bill.patient_responsibility if bill.patient_responsibility is not None else bill.computed_total
    if billed_pr - eob_pr > 1.0:
        in_net = eob.in_network if eob.in_network is not None else bill.in_network
        if in_net:
            rule, title_tail, expl, conf = "balance_billing", "", (
                "An in-network provider agreed by contract to accept the plan's allowed amount. Billing the patient for the difference between charges and the allowed amount is balance billing and is prohibited by the network contract. Pay only the EOB patient responsibility and send the EOB with your dispute."), "fact"
        elif bill.setting == "emergency" or (bill.setting in {"inpatient", "observation"} and bill.admit_date and bill.lines and any(l.cpt_hcpcs in ED_FACILITY_LEVELS for l in bill.lines)):
            rule, title_tail, expl, conf = "nsa_balance_billing", " (emergency care, No Surprises Act)", (
                "The encounter began as emergency care. Under the No Surprises Act the patient owes only in-network cost sharing for emergency services and for post-stabilization care until a valid notice and consent is signed, even when the facility is out of network. The provider must remove the balance bill; the plan and provider settle the rest between themselves."), "fact"
        else:
            rule, title_tail, expl, conf = "oon_balance_bill", " (out of network)", (
                "The provider is out of network and, outside No Surprises Act protections, may bill the difference between its charge and what the plan paid. This amount is negotiable: anchor to the plan's allowed amount or the hospital's cash price, and ask the plan for a network-gap exception."), "deduction"
        out.append(Finding(
            rule=rule,
            severity=Severity.high,
            line_ids=[l.line_id for l in bill.lines],
            title=f"Provider bills ${billed_pr:,.2f} but the insurer's explanation of benefits says you owe ${eob_pr:,.2f}" + title_tail,
            explanation=expl,
            disputed_amount=round(billed_pr - eob_pr, 2),
            evidence=["Network participation agreement (request a copy of the hold-harmless clause)" if in_net else "No Surprises Act, 42 USC 300gg-111, 300gg-131, 300gg-132; 45 CFR 149.410 to 149.420"],
            confidence=conf,
        ))
    denied = [l for l in eob.lines if l.denial_code and (l.plan_paid or 0) == 0]
    if denied:
        out.append(Finding(
            rule="denied_lines",
            severity=Severity.medium,
            line_ids=[],
            title=f"{len(denied)} line(s) denied by the insurer",
            explanation="Denied lines are often coding or authorization problems on the provider's side (wrong diagnosis pointer, missing modifier, no prior auth). Provider-caused denials cannot be shifted to the patient under most network contracts. Ask the provider to correct and resubmit, and file a plan appeal in parallel.",
            disputed_amount=round(sum((l.patient_responsibility or 0) for l in denied), 2),
            evidence=[f"Denial codes: {', '.join(sorted({l.denial_code for l in denied if l.denial_code}))}"],
            confidence="deduction",
        ))
    return out


def rule_gfe_variance(bill: Bill) -> list[Finding]:
    """Self-pay bill exceeds the good faith estimate by $400 or more."""
    if bill.insured or bill.good_faith_estimate_total is None:
        return []
    total = bill.patient_responsibility if bill.patient_responsibility is not None else bill.computed_total
    diff = total - bill.good_faith_estimate_total
    if diff >= 400:
        return [Finding(
            rule="gfe_variance",
            severity=Severity.high,
            line_ids=[],
            title=f"Bill exceeds the good faith estimate by ${diff:,.2f}",
            explanation="Uninsured and self-pay patients billed at least $400 above the good faith estimate for a provider may file a federal patient-provider dispute within 120 days of the bill. The provider must pause collections during the dispute. The dispute entity generally holds the provider to the estimate unless the extra charges were unforeseeable and documented.",
            disputed_amount=round(diff, 2),
            evidence=["No Surprises Act patient-provider dispute resolution, 45 CFR 149.620; CMS 'Dispute a medical bill' page"],
            confidence="fact",
        )]
    return []


ALL_RULES = [
    rule_duplicates,
    rule_mue,
    rule_unbundling,
    rule_ed_level,
    rule_routine_supplies,
    rule_missing_codes,
    rule_dates,
    rule_observation_hours,
    rule_pharmacy_markup,
    rule_gfe_variance,
]


def run_audit(bill: Bill, eob: Optional[EOB] = None, ptp_path: Optional[Path] = None, mue_path: Optional[Path] = None) -> list[Finding]:
    ptp = _load_ptp(ptp_path)
    mue = _load_mue(mue_path)
    findings: list[Finding] = []
    for rule in ALL_RULES:
        if rule is rule_mue:
            findings += rule(bill, mue)
        elif rule is rule_unbundling:
            findings += rule(bill, ptp)
        else:
            findings += rule(bill)
    findings += rule_eob_reconciliation(bill, eob)
    sev_order = {Severity.high: 0, Severity.medium: 1, Severity.low: 2}
    findings.sort(key=lambda f: (sev_order[f.severity], -f.disputed_amount))
    return findings


REMEDY_RULES = {"gfe_variance"}  # legal remedies, not line-item errors; reported separately


def disputed_total(findings: Iterable[Finding]) -> float:
    """Sum disputed dollars without double counting a line across rules. Remedy-type findings are excluded."""
    seen: set[str] = set()
    total = 0.0
    for f in findings:
        if f.rule in REMEDY_RULES:
            continue
        new_lines = [l for l in f.line_ids if l not in seen]
        if not f.line_ids or new_lines:
            total += f.disputed_amount
            seen.update(f.line_ids)
    return round(total, 2)
