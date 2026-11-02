"""Financial assistance, No Surprises Act, and 501(r) timeline screening."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from .models import Bill, EligibilityResult, PatientProfile

DATA = Path(__file__).parent / "data"


def fpl_percent(income: float, household: int, state: str = "GA") -> float:
    g = json.loads((DATA / "fpl.json").read_text())
    table = g.get(state.upper(), g["contiguous"]) if state.upper() in {"AK", "HI"} else g["contiguous"]
    threshold = table["base"] + table["per_additional_person"] * max(household - 1, 0)
    return round(100 * income / threshold, 1)


def screen(bill: Bill, patient: Optional[PatientProfile], today: Optional[date] = None,
           fap_free_threshold_pct: float = 200.0, fap_discount_threshold_pct: float = 400.0) -> EligibilityResult:
    """Screen against common financial assistance thresholds and federal rights.

    The 200 / 400 percent of poverty thresholds are the most common nonprofit hospital
    policy design in secondary sources and in the Lown Institute's review of 2,500
    hospital policies; they are defaults, not law. Replace them with the hospital's
    actual financial assistance policy once retrieved.
    """
    today = today or date.today()
    res = EligibilityResult()
    protections = json.loads((DATA / "state_protections.json").read_text())

    if patient:
        res.fpl_percent = fpl_percent(patient.annual_household_income, patient.household_size, patient.state)
        if res.fpl_percent <= fap_free_threshold_pct:
            res.charity_care_likely = True
            res.charity_care_basis.append(f"Household income is {res.fpl_percent}% of the federal poverty level, under the {fap_free_threshold_pct:.0f}% free-care threshold most nonprofit hospitals use.")
        elif res.fpl_percent <= fap_discount_threshold_pct:
            res.charity_care_likely = True
            res.charity_care_basis.append(f"Household income is {res.fpl_percent}% of the federal poverty level, within the {fap_discount_threshold_pct:.0f}% discounted-care band many policies use.")
        else:
            res.charity_care_basis.append(f"Household income is {res.fpl_percent}% of the federal poverty level, above typical thresholds. Catastrophic provisions (bill exceeding a share of annual income) may still apply.")
        balance = bill.patient_responsibility if bill.patient_responsibility is not None else bill.computed_total
        if patient.annual_household_income and balance / patient.annual_household_income >= 0.10:
            res.charity_care_likely = True
            res.charity_care_basis.append(f"Balance equals {100 * balance / patient.annual_household_income:.0f}% of annual income; many policies have a medical-hardship clause at 10 to 20%.")
        if not patient.insured and res.fpl_percent <= 138:
            res.medicaid_screen = "Income is at or below 138% of poverty. In expansion states the patient is likely Medicaid eligible, and Medicaid can cover bills retroactively up to three months before the application month. In Georgia, which has not expanded Medicaid, check Pathways or disability-based eligibility."

    if bill.nonprofit is not False:
        res.agb_cap_applies = True
        res.notes.append("If the hospital is a 501(c)(3), a patient eligible under its financial assistance policy may not be charged more than the amounts generally billed to insured patients (26 CFR 1.501(r)-5), and gross charges may never be used for that patient.")
        if bill.first_statement_date:
            res.eca_earliest_date = bill.first_statement_date + timedelta(days=120)
            res.fap_application_deadline = bill.first_statement_date + timedelta(days=240)
            res.notes.append("501(r) timelines: no extraordinary collection action (credit reporting, lawsuit, sale of debt, wage garnishment) before 120 days after the first post-discharge statement, and a financial assistance application must be accepted until at least 240 days after that statement (26 CFR 1.501(r)-6(c)). These two durations come from the regulation as recalled, not from text fetched today; confirm before citing.")

    if not bill.insured and bill.good_faith_estimate_total is not None:
        total = bill.patient_responsibility if bill.patient_responsibility is not None else bill.computed_total
        if total - bill.good_faith_estimate_total >= 400:
            res.nsa_ppdr_eligible = True
            res.nsa_ppdr_basis = f"Bill is ${total - bill.good_faith_estimate_total:,.2f} above the good faith estimate (threshold $400)."
            if bill.first_statement_date:
                res.nsa_ppdr_deadline = bill.first_statement_date + timedelta(days=120)
    began_in_ed = any(l.cpt_hcpcs in {"99281", "99282", "99283", "99284", "99285", "99291"} for l in bill.lines)
    if bill.insured and (bill.setting == "emergency" or began_in_ed):
        res.nsa_balance_billing_protected = True
        res.notes.append("Emergency services are protected under the No Surprises Act: the patient owes only in-network cost sharing even if the hospital or ED physician was out of network (42 USC 300gg-111 and 300gg-131).")
    if bill.insured and bill.in_network is False and bill.setting in {"inpatient", "outpatient", "observation"}:
        res.notes.append("Out-of-network ancillary clinicians (anesthesia, radiology, pathology, hospitalists) at an in-network facility may not balance bill under the No Surprises Act unless the patient signed a valid notice-and-consent waiver, which is not allowed for ancillary services.")

    res.state_protections = [p["text"] + (" [verify]" if p.get("verify") else "") for p in protections.get("ALL", [])]
    res.state_protections += [p["text"] + (" [verify]" if p.get("verify") else "") for p in protections.get((bill.state or (patient.state if patient else "")).upper(), [])]
    return res
