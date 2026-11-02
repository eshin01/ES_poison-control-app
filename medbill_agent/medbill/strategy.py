"""Interest-based negotiation planning.

Order of operations follows Fisher and Ury: identify each side's BATNA, separate
positions from interests, anchor to objective criteria, generate options that expand
value, then set anchor / target / walk-away numbers.
"""
from __future__ import annotations

from typing import Optional

from .audit import disputed_total
from .benchmarks import summarize
from .models import Benchmark, Bill, EligibilityResult, Finding, NegotiationPlan, PatientProfile


def build_plan(bill: Bill, findings: list[Finding], benchmarks: list[Benchmark],
               eligibility: Optional[EligibilityResult], patient: Optional[PatientProfile]) -> NegotiationPlan:
    balance = bill.patient_responsibility if bill.patient_responsibility is not None else bill.computed_total
    disputed = min(disputed_total(findings), balance)
    undisputed = round(balance - disputed, 2)
    s = summarize(benchmarks)

    # Scale Medicare to the whole bill using the matched-line ratio when coverage is partial.
    medicare_total = None
    if s["lines_with_medicare"] and s["billed_on_benchmarked_lines"]:
        ratio = s["medicare_on_benchmarked_lines"] / s["billed_on_benchmarked_lines"]
        medicare_total = round(undisputed * ratio, 2)
    cash_total = s["cash_price_total"]

    insured = bill.insured
    charity = bool(eligibility and eligibility.charity_care_likely)

    # Objective criteria that the provider already accepts for the same services.
    criteria = []
    if medicare_total is not None:
        criteria.append(f"Medicare would pay about ${medicare_total:,.0f} for the undisputed services (median markup on this bill is {s['median_markup_vs_medicare']}x Medicare).")
    if cash_total:
        criteria.append(f"The hospital's own price transparency file lists a discounted cash price totaling ${cash_total:,.0f} for the matched items.")
    if eligibility and eligibility.agb_cap_applies:
        criteria.append("If financial assistance applies, 501(r) caps charges at amounts generally billed to insured patients, which is roughly the average commercial or Medicare allowed amount.")
    criteria.append("Hospitals sell self-pay debt to collectors for a small fraction of face value; a prompt lump sum at a comparable discount leaves the hospital no worse off and avoids collection costs.")

    # Anchor / target / walk-away for the undisputed portion.
    if not insured:
        anchor = _lowest([medicare_total, cash_total], default=undisputed * 0.25)
        target = _lowest([medicare_total * 1.25 if medicare_total else None, cash_total], default=undisputed * 0.40)
        walk = _lowest([medicare_total * 1.6 if medicare_total else None, cash_total * 1.1 if cash_total else None], default=undisputed * 0.55)
    else:
        # Insured: the allowed amount is already set; the fight is about disputed lines, cost-sharing accuracy, and hardship.
        anchor = 0.0 if charity else round(undisputed * 0.50, 2)
        target = round(undisputed * (0.25 if charity else 0.65), 2)
        walk = round(undisputed * (0.50 if charity else 0.85), 2)
    fallback = None
    if charity:
        fallback = {"anchor": round(anchor, 2), "target": round(target, 2), "walk_away": round(walk, 2),
                    "note": "Use these if the financial assistance application is denied or only partly approved."}
        if not insured:
            anchor, target = 0.0, min(target, round(undisputed * 0.10, 2))

    patient_batna = [
        "Apply for financial assistance; the hospital must evaluate the application and refund or reverse collections if approved within the 240-day window." if bill.nonprofit is not False else "Ask for the hospital's self-pay discount policy in writing.",
        "Pay the undisputed amount on a zero-interest payment plan and leave disputed lines unpaid pending records review.",
        "File a No Surprises Act patient-provider dispute, which freezes collections." if eligibility and eligibility.nsa_ppdr_eligible else "Dispute in writing and request records, which most hospitals treat as a hold on collection activity.",
        "Complain to the state attorney general or hospital licensing board about billing errors and 501(r) noncompliance.",
        "If the debt goes to collections, demand validation and itemization under FDCPA and Regulation F, and dispute it; medical debt under $500 and paid medical collections are not reported by the three bureaus under their voluntary 2023 policy.",
    ]
    provider_batna = [
        "Send the account to a collection agency or sell the debt; recovery on self-pay hospital debt is typically a small share of face value, and the hospital bears agency fees.",
        "Sue, which is costly, slow, bad for reputation, and barred until 120 days after the first statement for nonprofits.",
        "Write the balance off as bad debt or reclassify it as charity care, which nonprofits report as community benefit.",
    ]
    patient_interests = ["Pay a fair price tied to what the hospital accepts from others", "Avoid credit damage and collections", "Resolve quickly with a written paid-in-full confirmation", "Not pay for services that were not delivered or were miscoded"]
    provider_interests = ["Collect cash soon rather than a larger amount never", "Minimize staff time per account", "Avoid regulatory exposure (501(r), No Surprises Act, state AG) and public complaints", "Keep patient loyalty and satisfaction scores"]

    options = [
        f"Lump sum: offer ${target:,.0f} paid within 10 business days in exchange for a written paid-in-full letter and no credit reporting.",
        "Correct and pay: hospital removes the disputed lines; patient pays the remaining balance immediately at the self-pay discount.",
        "Zero-interest payment plan on the corrected balance with a monthly amount the patient can sustain; hospital gets predictable cash with no collection cost.",
        "Financial assistance first, settlement on the remainder: submit the FAP application and settle only what the policy leaves.",
        "Partial charity: hospital applies its discount tier, patient pays promptly.",
    ]
    ladder = [
        {"round": 1, "offer": round(anchor, 2), "ask": "Remove disputed lines and accept this amount for the balance, citing Medicare and cash-price benchmarks.", "concede_if": "Provider corrects the disputed items in writing."},
        {"round": 2, "offer": round((anchor + target) / 2, 2), "ask": "Lump sum within 10 days, paid-in-full letter.", "concede_if": "Provider offers a payment plan or asks for documentation of hardship."},
        {"round": 3, "offer": round(target, 2), "ask": "Final lump-sum offer, or the same total on a zero-interest plan.", "concede_if": "Provider counters above target."},
        {"round": 4, "offer": round(walk, 2), "ask": "Walk-away number; above this, escalate (patient advocate, FAP appeal, regulator complaint, PPDR).", "concede_if": "Never."},
    ]
    sequence = [
        "Request the itemized statement with CPT/HCPCS and revenue codes, the UB-04, and the medical record (45 CFR 164.524). Do not pay yet.",
        "Send the written dispute of the flagged lines and ask for a corrected statement and a hold on the account.",
        "Submit the financial assistance application with income documentation if eligible; ask for presumptive eligibility screening.",
        "After corrections, open the settlement conversation with the anchor and the objective criteria. Put every offer in writing.",
        "Escalate: patient financial advocate, then billing director, then compliance officer; cite 501(r) and the price transparency file.",
        "If no movement: No Surprises Act dispute (if eligible), state attorney general complaint, or pay undisputed balance and leave disputed lines in dispute.",
    ]
    leverage = _leverage(bill, findings, eligibility, s, charity)
    relationship = ("A hospital you or your family will use again is a repeat counterparty. Keep the tone factual, never accusatory, and let the written record carry the pressure. The billing office is not the clinical team."
                    if bill.provider_type == "hospital_facility" else
                    "Low repeat exposure; still keep it factual, since the same billing vendor may service other providers you use.")
    return NegotiationPlan(
        current_balance=round(balance, 2), disputed_total=disputed, undisputed_balance=undisputed,
        medicare_total=medicare_total, cash_price_total=cash_total,
        anchor=round(anchor, 2), target=round(target, 2), walk_away=round(walk, 2),
        patient_batna=patient_batna, provider_batna=provider_batna,
        patient_interests=patient_interests, provider_interests=provider_interests,
        objective_criteria=criteria, value_creating_options=options, concession_ladder=ladder,
        recommended_sequence=sequence, leverage_assessment=leverage, relationship_note=relationship,
        if_assistance_denied=fallback,
    )


def _lowest(values, default):
    vals = [v for v in values if v is not None]
    return round(min(vals) if vals else default, 2)


def _leverage(bill, findings, eligibility, s, charity) -> str:
    parts = []
    hard = [f for f in findings if f.confidence == "fact"]
    if hard:
        parts.append(f"{len(hard)} finding(s) rest on rule text rather than inference; these are strong.")
    soft = [f for f in findings if f.confidence == "speculation"]
    if soft:
        parts.append(f"{len(soft)} finding(s) are speculative until records arrive; do not lead with them.")
    if not bill.insured:
        parts.append("Uninsured status helps: the hospital has no payer contract to point to and its own cash price is public.")
    else:
        parts.append("Insured status limits the upside: the allowed amount is contractual, so gains come from error correction, EOB reconciliation, and hardship programs rather than rate negotiation.")
    if charity:
        parts.append("Likely financial assistance eligibility is the strongest lever; it is a policy entitlement, not a favor.")
    if s.get("median_markup_vs_medicare") and s["median_markup_vs_medicare"] >= 3:
        parts.append(f"Median markup of {s['median_markup_vs_medicare']}x Medicare is well above the roughly 2.5x national hospital average reported in price studies, which supports a steep ask.")
    if not findings and not charity and bill.insured:
        parts.append("Leverage is weak: no coding findings, no hardship eligibility, and a contractual allowed amount. Expect a payment plan or a modest prompt-pay discount, not a large reduction.")
    return " ".join(parts)
