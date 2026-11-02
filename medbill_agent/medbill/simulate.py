"""Scenario simulation: a synthetic cholecystectomy bill, several coverage situations,
a rule-based hospital billing office, and a comparison of the agent's negotiation
against what a patient typically achieves alone.

Everything here is a model, not data. The hospital's behavior is a set of explicit
assumptions (listed in HOSPITAL_POLICY) chosen to be conservative: facts win,
speculation loses, financial assistance follows the written policy, and settlement
discounts track what published accounts of self-pay negotiations report.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .agent import run_offline
from .audit import REMEDY_RULES
from .models import Bill, CaseFile, EOB, EOBLine, Finding, LineItem, PatientProfile
from .strategy import prioritize

# --------------------------------------------------------------------------- bill generator

def cholecystectomy_bill(provider_name: str = "Example Regional Medical Center", nonprofit: bool = True, state: str = "GA",
                         insured: bool = False, in_network: Optional[bool] = None, inpatient: bool = True,
                         with_errors: bool = True) -> Bill:
    """ED visit for abdominal pain on day 1, admitted, laparoscopic cholecystectomy day 2, discharged day 3.

    Charges are chargemaster-scale (roughly 4x to 25x Medicare), which matches national markup studies.
    with_errors=True plants the error types the research found most often.
    """
    d1, d2, d3 = date(2026, 10, 6), date(2026, 10, 7), date(2026, 10, 8)
    L = []
    n = [0]

    def add(sd, desc, code=None, rev=None, units=1, total=0.0, dept=None, mods=None):
        n[0] += 1
        L.append(LineItem(line_id=str(n[0]), service_date=sd, description=desc, cpt_hcpcs=code, revenue_code=rev,
                          units=units, unit_charge=total / units if units else None, total_charge=total, department=dept, modifiers=mods or []))

    # Day 1: emergency department
    add(d1, "EMERGENCY DEPT VISIT LEVEL 5", "99285", "0450", 1, 4120.00, "ED")
    add(d1, "CT ABDOMEN PELVIS W CONTRAST", "74177", "0352", 1, 6840.00, "RADIOLOGY")
    add(d1, "US ABDOMEN COMPLETE", "76700", "0402", 1, 2310.00, "RADIOLOGY")
    add(d1, "COMPREHENSIVE METABOLIC PANEL", "80053", "0301", 1, 486.00, "LAB")
    add(d1, "LIPASE", "83690", "0301", 1, 312.00, "LAB")
    add(d1, "CBC WITH DIFFERENTIAL", "85025", "0305", 1, 268.00, "LAB")
    add(d1, "URINALYSIS AUTO W MICRO", "81001", "0307", 1, 164.00, "LAB")
    add(d1, "IV INFUSION INITIAL HOUR", "96365", "0260", 1, 1310.00, "ED")
    add(d1, "MORPHINE 10MG INJ", "J2270", "0636", 1, 142.00, "PHARMACY")
    add(d1, "ONDANSETRON 4MG INJ", "J2405", "0636", 4, 248.00, "PHARMACY")
    add(d1, "SODIUM CHLORIDE 0.9% 1000ML", "J7030", "0250", 2, 398.00, "PHARMACY")
    add(d1, "IOHEXOL CONTRAST 100ML", "Q9967", "0255", 100, 1150.00, "PHARMACY")
    if with_errors:
        add(d1, "CT ABDOMEN PELVIS W CONTRAST", "74177", "0352", 1, 6840.00, "RADIOLOGY")          # duplicate
        add(d1, "CT PELVIS W CONTRAST", "72193", "0352", 1, 3980.00, "RADIOLOGY")                   # component of 74177 (added below to PTP)
        add(d1, "HEPATIC FUNCTION PANEL", "80076", "0301", 1, 402.00, "LAB")                       # unbundled from CMP
        add(d1, "VENIPUNCTURE", "36415", "0300", 4, 236.00, "LAB")                                 # MUE 1
        add(d1, "IV START", "36000", "0260", 1, 410.00, "ED")                                      # bundled into infusion
        add(d1, "EMERGENCY DEPT VISIT LEVEL 4", "99284", "0450", 1, 2890.00, "ED")                 # second ED level
    # Day 1-2: admission, room and board
    rb_days = 2
    add(d1, "SEMI-PRIVATE ROOM SURGICAL", None, "0120", 1, 4850.00, "NURSING")
    add(d2, "SEMI-PRIVATE ROOM SURGICAL", None, "0120", 1, 4850.00, "NURSING")
    if with_errors:
        add(d3, "SEMI-PRIVATE ROOM SURGICAL", None, "0120", 1, 4850.00, "NURSING")                 # discharge-day R&B
    add(d2, "CBC WITH DIFFERENTIAL", "85025", "0305", 1, 268.00, "LAB")
    add(d2, "BASIC METABOLIC PANEL", "80048", "0301", 1, 356.00, "LAB")
    # Day 2: surgery
    add(d2, "OR TIME LEVEL 3 FIRST 60 MIN", None, "0360", 1, 14600.00, "SURGERY")
    add(d2, "OR TIME ADDL 15 MIN", None, "0360", 3, 5250.00, "SURGERY")
    add(d2, "LAPAROSCOPIC CHOLECYSTECTOMY", "47562", "0360", 1, 9800.00, "SURGERY")
    add(d2, "ANESTHESIA GENERAL FIRST HOUR", None, "0370", 1, 3980.00, "ANESTHESIA")
    add(d2, "ANESTHESIA ADDL 15 MIN", None, "0370", 3, 1860.00, "ANESTHESIA")
    add(d2, "RECOVERY ROOM PHASE 1 PER HOUR", None, "0710", 2, 3120.00, "PACU")
    add(d2, "PROPOFOL 10MG", "J2704", "0636", 20, 310.00, "PHARMACY")
    add(d2, "CEFAZOLIN 500MG", "J0690", "0636", 4, 288.00, "PHARMACY")
    add(d2, "DEXAMETHASONE 1MG", "J1100", "0636", 8, 176.00, "PHARMACY")
    add(d2, "HYDROMORPHONE 4MG", "J1170", "0636", 2, 164.00, "PHARMACY")
    add(d2, "SURGICAL PATHOLOGY LEVEL III", "88304", "0310", 1, 690.00, "PATHOLOGY")
    add(d2, "LAPAROSCOPIC TROCAR 12MM", None, "0272", 2, 1880.00, "OR SUPPLY")
    add(d2, "LAPAROSCOPIC TROCAR 5MM", None, "0272", 2, 1240.00, "OR SUPPLY")
    add(d2, "CLIP APPLIER DISPOSABLE", None, "0272", 1, 1460.00, "OR SUPPLY")
    add(d2, "SPECIMEN RETRIEVAL BAG", None, "0272", 1, 720.00, "OR SUPPLY")
    add(d2, "LAPAROSCOPIC INSTRUMENT TRAY", None, "0272", 1, 2850.00, "OR SUPPLY")
    if with_errors:
        add(d2, "DIAGNOSTIC LAPAROSCOPY", "49320", "0360", 1, 4200.00, "SURGERY")                 # included in 47562
        add(d2, "SURGICAL PATHOLOGY LEVEL III", "88304", "0310", 1, 690.00, "PATHOLOGY")          # duplicate
        add(d2, "GLOVES SURGICAL STERILE", None, "0270", 6, 258.00, "OR SUPPLY")                   # routine supply
        add(d2, "GOWN SURGICAL", None, "0270", 3, 186.00, "OR SUPPLY")                            # routine supply
        add(d2, "DRAPE LAPAROTOMY", None, "0270", 1, 142.00, "OR SUPPLY")                         # routine supply
        add(d2, "IV TUBING PRIMARY", None, "0270", 2, 96.00, "CENTRAL SUPPLY")                     # routine supply
        add(d2, "MISCELLANEOUS OR CHARGE", None, None, 1, 2400.00, "SURGERY")                      # uncoded
    # Day 3: discharge
    add(d3, "BASIC METABOLIC PANEL", "80048", "0301", 1, 356.00, "LAB")
    add(d3, "ONDANSETRON 4MG INJ", "J2405", "0636", 1, 62.00, "PHARMACY")

    total = round(sum(l.total_charge for l in L), 2)
    return Bill(
        provider_name=provider_name, provider_type="hospital_facility", nonprofit=nonprofit, state=state,
        account_number="SIM-2026-CHOLE", patient_name="Simulated Patient", admit_date=d1, discharge_date=d3,
        setting="inpatient" if inpatient else "observation", drg="419" if inpatient else None,
        first_statement_date=date(2026, 10, 22), insured=insured, in_network=in_network,
        good_faith_estimate_total=None if insured else 38000.00,
        lines=L, total_charges=total, patient_responsibility=total,
    )


def eob_for(bill: Bill, deductible_remaining: float, coinsurance: float, oop_max_remaining: float, in_network: bool,
            allowed_ratio: float = 0.28, deny_codes: tuple = ("49320", "36000", "72193")) -> EOB:
    """Build an insurer EOB. In network: allowed = ratio of charges (commercial rates ~2-3x Medicare, ~25-30% of chargemaster).
    Cost sharing: deductible first, then coinsurance up to the out-of-pocket maximum. Duplicates and bundled codes are denied."""
    lines = []
    ded, oop = deductible_remaining, oop_max_remaining
    seen = set()
    for l in bill.lines:
        key = (l.service_date, l.cpt_hcpcs or l.description, l.total_charge)
        allowed = round(l.total_charge * (allowed_ratio if in_network else 0.6), 2)
        denial = None
        if l.cpt_hcpcs in deny_codes:
            denial, allowed = ("CO-97", 0.0)
        elif key in seen:
            denial, allowed = ("CO-18", 0.0)  # exact duplicate claim line
        seen.add(key)
        pr = 0.0
        if allowed:
            take_ded = min(ded, allowed); ded -= take_ded
            coins = round((allowed - take_ded) * coinsurance, 2)
            pr = min(take_ded + coins, oop); oop -= pr
        paid = round(allowed - pr, 2)
        lines.append(EOBLine(cpt_hcpcs=l.cpt_hcpcs, description=l.description, billed=l.total_charge, allowed=allowed, plan_paid=paid,
                             patient_responsibility=round(pr, 2), denial_code=denial,
                             denial_reason={"CO-97": "Payment included in another service", "CO-18": "Duplicate claim/service"}.get(denial)))
    return EOB(payer_name="Example Health Plan", in_network=in_network, lines=lines,
               total_billed=round(sum(x.billed for x in lines), 2), total_allowed=round(sum(x.allowed or 0 for x in lines), 2),
               total_plan_paid=round(sum(x.plan_paid or 0 for x in lines), 2), total_patient_responsibility=round(sum(x.patient_responsibility or 0 for x in lines), 2))


# --------------------------------------------------------------------------- scenarios

@dataclass
class Scenario:
    name: str
    description: str
    nonprofit: bool
    insured: bool
    in_network: Optional[bool]
    patient: PatientProfile
    deductible_remaining: float = 0.0
    coinsurance: float = 0.0
    oop_max_remaining: float = 0.0
    statement_markup_on_eob: float = 0.0  # dollars the hospital bills above the EOB patient responsibility (balance billing / posting error)


def default_scenarios() -> list[Scenario]:
    return [
        Scenario("A. Uninsured, nonprofit hospital, 185% FPL",
                 "Hourly worker, household of 3, $48,000 income. No insurance. Nonprofit hospital with a typical financial assistance policy (free care to 200% FPL, sliding discount to 400%). Good faith estimate was $38,000.",
                 nonprofit=True, insured=False, in_network=None,
                 patient=PatientProfile(household_size=3, annual_household_income=48000, state="GA", insured=False, can_pay_lump_sum=2500, monthly_payment_capacity=150)),
        Scenario("B. Uninsured, for-profit hospital, 350% FPL",
                 "Self-employed, household of 2, $74,000 income. No insurance. For-profit hospital: no 501(r) duties, but the price transparency file and the No Surprises Act good faith estimate still apply.",
                 nonprofit=False, insured=False, in_network=None,
                 patient=PatientProfile(household_size=2, annual_household_income=74000, state="GA", insured=False, can_pay_lump_sum=8000, monthly_payment_capacity=400)),
        Scenario("C. Insured in network, $6,500 deductible plan, nonprofit, 320% FPL",
                 "Household of 4, $107,000 income. High-deductible plan, $6,500 deductible remaining, 20% coinsurance, $9,000 out-of-pocket max. Hospital posted the EOB wrong and billed $1,900 above the patient responsibility.",
                 nonprofit=True, insured=True, in_network=True,
                 patient=PatientProfile(household_size=4, annual_household_income=107000, state="GA", insured=True, can_pay_lump_sum=4000, monthly_payment_capacity=300),
                 deductible_remaining=6500, coinsurance=0.20, oop_max_remaining=9000, statement_markup_on_eob=1900),
        Scenario("D. Insured, out-of-network ED (emergency), nonprofit, 250% FPL",
                 "Household of 2, $53,000 income. Went to the nearest ED, which was out of network. Plan paid at 60% of charges; hospital balance-billed the rest. Emergency care is protected under the No Surprises Act.",
                 nonprofit=True, insured=True, in_network=False,
                 patient=PatientProfile(household_size=2, annual_household_income=53000, state="GA", insured=True, can_pay_lump_sum=1500, monthly_payment_capacity=200),
                 deductible_remaining=3000, coinsurance=0.30, oop_max_remaining=8000, statement_markup_on_eob=0),
    ]


# --------------------------------------------------------------------------- hospital model

HOSPITAL_POLICY = {
    # Probability the billing office accepts a correction, by finding confidence and rule type.
    "accept_fact": 0.95,            # NCCI pair with indicator 0, impossible hours, EOB arithmetic
    "accept_deduction": 0.70,       # duplicates, MUE, routine supplies, discharge-day room and board (records usually confirm)
    "accept_speculation": 0.25,     # ED leveling challenges without the record
    "uncoded_remove_share": 0.5,    # share of an uncoded 'miscellaneous' charge removed once itemization is demanded
    "pharmacy_markup_concession": 0.0,   # hospitals rarely reprice drugs line by line; this is folded into the settlement discount
    # Self-pay discounts (secondary sources: automatic self-pay discounts of 20-40%; negotiated lump sums commonly 40-60% off corrected charges)
    "self_pay_auto_discount": 0.30,
    "lump_sum_settlement_discount_nonprofit": 0.55,
    "lump_sum_settlement_discount_forprofit": 0.45,
    # Financial assistance tiers for a 'typical' nonprofit policy
    "fap_free_to_fpl": 200, "fap_tiers": [(250, 0.80), (300, 0.65), (400, 0.50)],  # (upper FPL %, discount)
    "fap_cap_to_agb_ratio_of_charges": 0.30,  # amounts generally billed ~ average allowed amount ~ 30% of charges
    # Insured, in network: the contract fixes the allowed amount; hospital corrects posting errors and refunds balance billing
    "in_network_prompt_pay_discount": 0.10,
    "hardship_discount_in_network_if_fap_eligible": 0.50,
    # Patient negotiating alone (baseline), from consumer-finance reporting: most do not request itemization; some ask for a discount
    "ppdr_settle_at_gfe_prob": 0.80,     # dispute entities generally hold providers to the estimate absent documented unforeseeable care
    "post_gfe_prompt_pay_discount": 0.15,
    "patient_alone_asks_discount_prob": 0.40, "patient_alone_discount": 0.15,
    "patient_alone_catches_duplicate_prob": 0.30,
}


@dataclass
class RoundLog:
    round: int
    actor: str
    message: str
    balance_after: float


@dataclass
class SimResult:
    scenario: Scenario
    starting_balance: float
    patient_alone_balance: float
    agent_balance: float
    corrections_won: float
    priority_table: list[dict]
    rounds: list[RoundLog] = field(default_factory=list)
    case: Optional[CaseFile] = None

    @property
    def agent_savings(self):
        return round(self.starting_balance - self.agent_balance, 2)

    @property
    def alone_savings(self):
        return round(self.starting_balance - self.patient_alone_balance, 2)


def simulate(scn: Scenario, policy: dict = HOSPITAL_POLICY) -> SimResult:
    bill = cholecystectomy_bill(nonprofit=scn.nonprofit, insured=scn.insured, in_network=scn.in_network)
    eob = None
    if scn.insured:
        eob = eob_for(bill, scn.deductible_remaining, scn.coinsurance, scn.oop_max_remaining, in_network=bool(scn.in_network))
        bill.patient_responsibility = round(eob.total_patient_responsibility + scn.statement_markup_on_eob, 2) if scn.in_network else round(bill.total_charges - eob.total_plan_paid, 2)
    case = run_offline(CaseFile(bill=bill, eob=eob, patient=scn.patient))
    start = case.plan.current_balance

    payoff_fn = None
    if scn.insured and eob:
        allowed_total = eob.total_allowed or 0.0
        ratio = 0.28  # commercial allowed amount as a share of chargemaster charges (in network, or the NSA recognized amount)

        def cost_share(allowed: float) -> float:
            ded = min(scn.deductible_remaining, allowed)
            return min(scn.oop_max_remaining, ded + scn.coinsurance * (allowed - ded))

        def payoff_fn(disputed_charges: float) -> float:
            # dollars the patient's own share falls when the hospital removes `disputed_charges` of billed charges
            return max(0.0, cost_share(allowed_total) - cost_share(max(0.0, allowed_total - disputed_charges * ratio)))
    rounds: list[RoundLog] = []
    bal = start
    r = 0

    def log(actor, msg):
        rounds.append(RoundLog(len(rounds) + 1, actor, msg, round(bal, 2)))

    # ---- Baseline: patient alone (expected value)
    alone = start
    if not scn.insured:
        alone -= policy["patient_alone_asks_discount_prob"] * policy["patient_alone_discount"] * start
    dup = sum(f.disputed_amount for f in case.findings if f.rule == "duplicate_charge")
    alone -= policy["patient_alone_catches_duplicate_prob"] * dup
    alone = round(alone, 2)

    # ---- Agent path
    pri = prioritize(case.findings, bill, case.eligibility, payoff_fn=payoff_fn)
    log("agent", "Requests itemized statement with codes, UB-04, and the medical record under 45 CFR 164.524; asks for a hold on the account. Does not pay.")
    log("hospital", "Sends itemized statement and places a 30-day hold; records follow in 3 weeks.")

    e = case.eligibility
    nsa_f = next((f for f in case.findings if f.rule == "nsa_balance_billing"), None)
    if scn.insured and scn.in_network is False and nsa_f:
        protected = round(bal - (eob.total_patient_responsibility if eob else 0), 2)
        if protected > 0:
            log("agent", f"Cites the No Surprises Act: emergency services are limited to in-network cost sharing (42 USC 300gg-131). Demands removal of ${protected:,.0f} balance bill and a corrected statement.")
            bal = round(eob.total_patient_responsibility, 2)
            log("hospital", f"Compliance reviews; agrees the encounter is protected. Reduces balance to in-network cost sharing of ${bal:,.0f}.")

    # Step 1: coding corrections, in priority order
    won = 0.0
    accepted_titles, refused_titles, no_value_titles = [], [], []
    seen_lines: set[str] = set()
    for row in pri:
        f = row["finding"]
        if f.rule in REMEDY_RULES or f.rule == "nsa_balance_billing" or f.disputed_amount <= 0:
            continue
        if f.line_ids and all(l in seen_lines for l in f.line_ids):
            continue  # same lines already disputed under another rule (duplicate also trips the unit ceiling)
        seen_lines.update(f.line_ids)
        amt = row["expected_value"]
        if amt > 0:
            won += amt
            accepted_titles.append(f"{f.title} (expected ${amt:,.0f} of ${f.disputed_amount:,.0f})")
        elif row["p_success"] > 0 and scn.insured:
            no_value_titles.append(f.title)
        else:
            refused_titles.append(f.title)
    won = round(min(won, bal), 2)
    bal -= won
    if accepted_titles:
        log("agent", "Sends written dispute, highest expected value first: " + "; ".join(accepted_titles[:6]) + (" ..." if len(accepted_titles) > 6 else ""))
    if no_value_titles and not accepted_titles:
        log("agent", f"Files {len(no_value_titles)} facility coding corrections that lower the plan's payment but not the patient's share, because the out-of-pocket maximum already binds. They go in the letter but do not drive the strategy.")
    elif no_value_titles:
        log("agent", f"Also files {len(no_value_titles)} facility coding corrections that lower the plan's payment but not the patient's share, because the out-of-pocket maximum already binds. They go in the letter but do not drive the strategy.")
    if won == 0 and not accepted_titles:
        log("hospital", "Corrects the coding on the claim and refunds the plan; the patient's cost sharing is unchanged.")
    else:
        log("hospital", f"Reviews against the record. Corrects ${won:,.0f} of the patient's balance" + (" (pharmacy markups folded into settlement rather than repriced)" if refused_titles else "") + ". Issues corrected statement.")

    # Step 2: entitlement programs
    if scn.nonprofit and e.fpl_percent is not None and not scn.insured:
        fpl = e.fpl_percent
        if fpl <= policy["fap_free_to_fpl"]:
            log("agent", f"Submits financial assistance application: income is {fpl}% of poverty, under the policy's free-care line. Cites 26 CFR 1.501(r)-6 to keep collections paused.")
            bal = 0.0
            log("hospital", "Approves 100% financial assistance. Balance written off as charity care.")
        else:
            disc = next((d for cap, d in policy["fap_tiers"] if fpl <= cap), None)
            if disc:
                cap_agb = round(bill.total_charges * policy["fap_cap_to_agb_ratio_of_charges"], 2)
                new_bal = round(min(bal * (1 - disc), cap_agb), 2)
                log("agent", f"Submits financial assistance application at {fpl}% of poverty; asks for the {int(disc*100)}% tier and the AGB cap under 1.501(r)-5.")
                log("hospital", f"Approves {int(disc*100)}% discount; charges capped at amounts generally billed (${cap_agb:,.0f}). New balance ${new_bal:,.0f}.")
                bal = new_bal
    if not scn.insured and e.nsa_ppdr_eligible and bal > (bill.good_faith_estimate_total or 0):
        gfe = bill.good_faith_estimate_total
        log("agent", f"Corrected balance ${bal:,.0f} still exceeds the ${gfe:,.0f} good faith estimate. Files the No Surprises Act patient-provider dispute (deadline {e.nsa_ppdr_deadline}); collections must pause. Offers to settle at the estimate.")
        bal = round(gfe * policy["ppdr_settle_at_gfe_prob"] + bal * (1 - policy["ppdr_settle_at_gfe_prob"]), 2)
        log("hospital", f"Cannot show the extra charges were unforeseeable; settles at the estimate rather than litigate the dispute. Balance ${bal:,.0f} (expected value).")
        settled_at_gfe = True
    else:
        settled_at_gfe = False
    if scn.insured and scn.nonprofit and e.charity_care_likely and bal > 0:
        log("agent", f"Applies for hardship assistance on the remaining cost sharing (income {e.fpl_percent}% of poverty; balance is {100*bal/scn.patient.annual_household_income:.0f}% of income).")
        bal = round(bal * (1 - policy["hardship_discount_in_network_if_fap_eligible"]), 2)
        log("hospital", f"Approves 50% hardship reduction on patient cost sharing. New balance ${bal:,.0f}.")

    # Step 3: settlement on what remains
    if bal > 0:
        if not scn.insured and settled_at_gfe:
            disc = policy["post_gfe_prompt_pay_discount"]
            new = round(bal * (1 - disc), 2)
            log("agent", f"Asks for a prompt-pay discount on the estimate amount and a zero-interest plan at ${scn.patient.monthly_payment_capacity or 100:,.0f}/month.")
            bal = new
            log("hospital", f"Grants {int(disc*100)}% for a signed plan. Final balance ${new:,.0f}.")
        elif not scn.insured:
            disc = policy["lump_sum_settlement_discount_nonprofit"] if scn.nonprofit else policy["lump_sum_settlement_discount_forprofit"]
            auto = round(bal * (1 - policy["self_pay_auto_discount"]), 2)
            offer = round(bal * (1 - disc), 2)
            can = scn.patient.can_pay_lump_sum or 0
            log("agent", f"Opens settlement at the Medicare equivalent (${case.plan.if_assistance_denied['anchor'] if case.plan.if_assistance_denied else case.plan.anchor:,.0f}) citing the hospital's own cash price file; offers lump sum within 10 days for a paid-in-full letter.")
            log("hospital", f"Applies the 30% self-pay discount (${auto:,.0f}) and counters.")
            if can >= offer:
                bal = offer
                log("agent", f"Accepts ${offer:,.0f} lump sum ({int(disc*100)}% off the corrected balance). Gets written zero-balance confirmation before paying.")
            else:
                months = scn.patient.monthly_payment_capacity or 100
                plan_total = round(bal * (1 - policy["self_pay_auto_discount"] - 0.10), 2)
                bal = plan_total
                log("agent", f"Cannot fund the lump sum (${can:,.0f} available). Takes a zero-interest plan on ${plan_total:,.0f} at ${months:,.0f}/month ({int((policy['self_pay_auto_discount']+0.10)*100)}% off), with the remaining lines still in dispute.")
        else:
            disc = policy["in_network_prompt_pay_discount"]
            new = round(bal * (1 - disc), 2)
            log("agent", f"Cost sharing is contractual; asks for prompt-pay discount on the corrected patient share and a zero-interest plan.")
            bal = new
            log("hospital", f"Grants {int(disc*100)}% prompt-pay discount. Final balance ${new:,.0f}.")

    return SimResult(scenario=scn, starting_balance=start, patient_alone_balance=alone, agent_balance=round(bal, 2),
                     corrections_won=won, priority_table=[{k: v for k, v in r.items() if k != "finding"} for r in pri], rounds=rounds, case=case)


def run_all(scenarios: Optional[list[Scenario]] = None) -> list[SimResult]:
    return [simulate(s) for s in (scenarios or default_scenarios())]


def render_markdown(results: list[SimResult]) -> str:
    out = ["# Simulation: ED visit for abdominal pain, laparoscopic cholecystectomy", "",
           "Synthetic bill, rule-based hospital model, four coverage scenarios. The hospital's behavior follows the assumptions in `HOSPITAL_POLICY` (acceptance rates by finding confidence, self-pay discounts, a typical nonprofit financial assistance policy). Dollar outcomes are expected values under those assumptions, not measured results.", ""]
    b = results[0].case.bill
    out += [f"Bill: {len(b.lines)} lines, gross charges ${b.total_charges:,.0f}, {b.admit_date} to {b.discharge_date}. Planted errors: duplicate CT and pathology, unbundled hepatic panel / CT pelvis / IV start / diagnostic laparoscopy, two ED levels, venipuncture x4, discharge-day room and board, routine OR supplies billed separately, a $2,400 uncoded 'miscellaneous OR charge'.", ""]
    out += ["| Scenario | Starting balance | Patient alone | With agent | Agent savings | Savings % |", "|---|---:|---:|---:|---:|---:|"]
    for r in results:
        out.append(f"| {r.scenario.name} | ${r.starting_balance:,.0f} | ${r.patient_alone_balance:,.0f} | ${r.agent_balance:,.0f} | ${r.agent_savings:,.0f} | {100*r.agent_savings/r.starting_balance:.0f}% |")
    out.append("")
    for r in results:
        out += [f"## {r.scenario.name}", "", r.scenario.description, ""]
        out += ["Priority order (expected value = disputed dollars x probability of success, given this coverage and hospital type):", ""]
        out += ["| Rank | Finding | Disputed | P(success) | Expected value | Why |", "|---:|---|---:|---:|---:|---|"]
        for i, p in enumerate(r.priority_table[:8], 1):
            out.append(f"| {i} | {p['title']} | ${p['disputed']:,.0f} | {p['p_success']:.2f} | ${p['expected_value']:,.0f} | {p['why']} |")
        out += ["", "Negotiation transcript:", ""]
        for rd in r.rounds:
            out.append(f"{rd.round}. **{rd.actor}**: {rd.message} _(balance ${rd.balance_after:,.0f})_")
        out += ["", f"Result: ${r.starting_balance:,.0f} to ${r.agent_balance:,.0f} with the agent versus ${r.patient_alone_balance:,.0f} alone. Corrections alone were worth ${r.corrections_won:,.0f}.", ""]
    out += ["## What a patient alone usually does", "",
            "Consumer-finance reporting and advocacy sources describe the typical path: the patient receives a summary statement, does not request itemization, and either pays, sets up a plan at face value, or asks for a discount and gets the hospital's standard self-pay reduction. The baseline here assumes a 40% chance of asking for a 15% discount and a 30% chance of spotting an obvious duplicate. Both numbers are assumptions and are easy to change in `HOSPITAL_POLICY`.", "",
            "## Where the agent's gains come from", "",
            "1. It never negotiates from the summary statement. Itemization plus the record is what makes the coding disputes enforceable.",
            "2. It ranks disputes by expected value for this coverage. Uninsured patients gain most from facility coding errors and entitlement programs; in-network insured patients gain most from EOB reconciliation and hardship programs, since the allowed amount is contractual.",
            "3. It treats financial assistance and the No Surprises Act as entitlements with deadlines, not favors, and sequences them before any settlement.",
            "4. It anchors settlement to prices the hospital already accepts (Medicare, its own cash price) and trades a prompt lump sum for a paid-in-full letter.",
            "5. It keeps every exchange in writing and asks for a hold, which removes the collections pressure that pushes patients to pay inflated balances."]
    return "\n".join(out)


if __name__ == "__main__":  # python -m medbill.simulate [out.md]
    import sys
    results = run_all()
    text = render_markdown(results)
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(text)
    print(text)
