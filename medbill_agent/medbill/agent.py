"""The negotiation agent.

Claude drives the case with a small set of tools. Anything that leaves the machine
(email, portal submission, phone call) passes through an approval gate: the tool
returns a request for approval instead of acting, and the human decides. Everything
else (auditing, benchmarking, drafting) runs freely.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Callable, Optional

import anthropic
from anthropic import beta_tool

from . import letters
from .audit import run_audit
from .benchmarks import HospitalMRF, MedicareRates, benchmark_bill, summarize
from .eligibility import screen
from .models import CaseFile, Letter, PatientProfile
from .strategy import build_plan

MODEL = "claude-opus-5-5"

SYSTEM = """You are a patient-side medical billing advocate. Your job is to lower what this patient pays, within the law and the facts.

Working rules:
- Start from the itemized bill. Audit before you negotiate. Never dispute a charge you cannot tie to a rule, a benchmark, or a documentation gap.
- Separate facts (rule text, EOB figures, published prices) from deductions and from speculation, and label each when you write to the provider or the patient.
- Negotiate on interests and objective criteria: Medicare rates, the hospital's own cash price and negotiated-rate file, 501(r) amounts generally billed, and the hospital's cost to collect. Do not bluff, threaten, or misstate the law.
- Sequence: records and itemization first, written dispute second, financial assistance third, settlement fourth, escalation last.
- Nothing leaves this system without human approval. When you want to send a letter or make a call, call the send tool and stop; the human will approve or edit.
- Report to the patient in plain language: what was found, what it is worth, what happens next, and what they must decide.
- Do not give legal advice; describe rights and point to the statute or rule, and suggest a lawyer or state consumer office for disputes beyond billing.
"""


class Approval:
    """Outbound-action gate. Replace `ask` with a UI hook."""

    def __init__(self, ask: Optional[Callable[[Letter], bool]] = None, auto_approve: bool = False):
        self.ask = ask
        self.auto_approve = auto_approve
        self.pending: list[Letter] = []
        self.sent: list[Letter] = []

    def decide(self, letter: Letter) -> bool:
        if self.auto_approve:
            ok = True
        elif self.ask:
            ok = self.ask(letter)
        else:
            self.pending.append(letter)
            return False
        if ok:
            self.sent.append(letter)
        return ok


class MedBillAgent:
    def __init__(self, case: CaseFile, approval: Optional[Approval] = None, client: Optional[anthropic.Anthropic] = None,
                 medicare: Optional[MedicareRates] = None, mrf: Optional[HospitalMRF] = None, model: str = MODEL):
        self.case = case
        self.approval = approval or Approval()
        self.client = client or anthropic.Anthropic()
        self.medicare = medicare or MedicareRates.illustrative()
        self.mrf = mrf
        self.model = model
        self.tools = self._build_tools()

    # ------------------------------------------------------------------ tools
    def _build_tools(self):
        case, approval = self.case, self.approval
        agent = self

        @beta_tool
        def get_case_summary() -> str:
            """Return the bill header, line count, totals, and what analysis has been run so far."""
            b = case.bill
            return json.dumps({
                "provider": b.provider_name, "setting": b.setting, "insured": b.insured, "nonprofit": b.nonprofit, "state": b.state,
                "lines": len(b.lines), "computed_total": b.computed_total, "patient_responsibility": b.patient_responsibility,
                "has_eob": case.eob is not None, "has_patient_profile": case.patient is not None,
                "findings": len(case.findings), "benchmarks": len(case.benchmarks),
                "eligibility_done": case.eligibility is not None, "plan_done": case.plan is not None,
                "letters_drafted": [l.kind for l in case.letters], "log": case.log[-10:],
            }, default=str)

        @beta_tool
        def list_lines(start: int = 0, limit: int = 60) -> str:
            """List itemized lines (line_id, date, code, revenue code, description, units, charge) from start, up to limit rows."""
            rows = case.bill.lines[start:start + limit]
            return "\n".join(f"{l.line_id}\t{l.service_date}\t{l.cpt_hcpcs or ''}\t{l.revenue_code or ''}\t{l.description}\t{l.units:g}\t{l.total_charge:.2f}" for l in rows)

        @beta_tool
        def run_bill_audit() -> str:
            """Run the deterministic audit rules (duplicates, unit ceilings, unbundling, ED level, routine supplies, dates, EOB reconciliation, good-faith-estimate variance). Returns findings as JSON."""
            case.findings = run_audit(case.bill, case.eob)
            case.log.append(f"{date.today()}: audit run, {len(case.findings)} findings")
            return json.dumps([f.model_dump() for f in case.findings], default=str)

        @beta_tool
        def add_finding(rule: str, severity: str, line_ids: list[str], title: str, explanation: str, disputed_amount: float, evidence: list[str], confidence: str = "deduction") -> str:
            """Add a finding the rules missed (something you spotted reading the lines). severity: high|medium|low. confidence: fact|deduction|speculation."""
            from .models import Finding, Severity
            case.findings.append(Finding(rule=rule, severity=Severity(severity), line_ids=line_ids, title=title, explanation=explanation,
                                         disputed_amount=disputed_amount, evidence=evidence, confidence=confidence))
            return f"added; {len(case.findings)} findings total"

        @beta_tool
        def run_benchmarks() -> str:
            """Benchmark each coded line against Medicare and, if loaded, the hospital's price transparency file. Returns per-line benchmarks and a summary."""
            case.benchmarks = benchmark_bill(case.bill, agent.medicare, agent.mrf)
            case.log.append(f"{date.today()}: benchmarks run")
            return json.dumps({"summary": summarize(case.benchmarks), "lines": [b.model_dump() for b in case.benchmarks if b.medicare_rate or b.hospital_cash_price]}, default=str)

        @beta_tool
        def set_patient_profile(household_size: int, annual_household_income: float, state: str, insured: bool,
                                medicare_beneficiary: bool = False, can_pay_lump_sum: Optional[float] = None,
                                monthly_payment_capacity: Optional[float] = None, hardship_notes: Optional[str] = None) -> str:
            """Record the patient's household and finances for financial assistance screening and offer sizing."""
            case.patient = PatientProfile(household_size=household_size, annual_household_income=annual_household_income, state=state, insured=insured,
                                          medicare_beneficiary=medicare_beneficiary, can_pay_lump_sum=can_pay_lump_sum,
                                          monthly_payment_capacity=monthly_payment_capacity, hardship_notes=hardship_notes)
            case.bill.insured = insured
            return "profile saved"

        @beta_tool
        def run_eligibility_screen() -> str:
            """Screen for charity care / financial assistance, No Surprises Act rights, 501(r) timelines, and state protections."""
            case.eligibility = screen(case.bill, case.patient)
            case.log.append(f"{date.today()}: eligibility screened")
            return case.eligibility.model_dump_json()

        @beta_tool
        def build_negotiation_plan() -> str:
            """Build the interest-based plan: both BATNAs, interests, objective criteria, options, anchor/target/walk-away, concession ladder."""
            if not case.findings:
                case.findings = run_audit(case.bill, case.eob)
            if not case.benchmarks:
                case.benchmarks = benchmark_bill(case.bill, agent.medicare, agent.mrf)
            if case.eligibility is None:
                case.eligibility = screen(case.bill, case.patient)
            case.plan = build_plan(case.bill, case.findings, case.benchmarks, case.eligibility, case.patient)
            case.log.append(f"{date.today()}: plan built")
            return case.plan.model_dump_json()

        @beta_tool
        def draft_letter(kind: str, offer_amount: Optional[float] = None, collector_name: Optional[str] = None) -> str:
            """Draft a document from templates. kind: itemized_request | dispute | fap_cover | settlement_offer | ppdr_checklist | collections_response | phone_script. Returns the draft; edit it with revise_letter before sending."""
            if kind == "itemized_request":
                letter = letters.itemized_request(case.bill, patient_is_medicare=bool(case.patient and case.patient.medicare_beneficiary))
            elif kind == "dispute":
                letter = letters.dispute_letter(case)
            elif kind == "fap_cover":
                letter = letters.fap_cover_letter(case)
            elif kind == "settlement_offer":
                amt = offer_amount if offer_amount is not None else (case.plan.anchor if case.plan else 0.0)
                letter = letters.settlement_offer(case, amt)
            elif kind == "ppdr_checklist":
                letter = letters.ppdr_checklist(case)
            elif kind == "collections_response":
                letter = letters.collections_response(case, collector_name or "[Collection agency]")
            elif kind == "phone_script":
                letter = letters.phone_script(case)
            else:
                return f"unknown kind {kind}"
            case.letters = [l for l in case.letters if l.kind != kind] + [letter]
            return letter.model_dump_json()

        @beta_tool
        def revise_letter(kind: str, new_body: str, new_subject: Optional[str] = None) -> str:
            """Replace the body (and optionally subject) of a drafted letter with your improved version. Keep citations accurate; do not add facts not in the case file."""
            for l in case.letters:
                if l.kind == kind:
                    l.body = new_body
                    if new_subject:
                        l.subject = new_subject
                    return "revised"
            return f"no draft of kind {kind}; call draft_letter first"

        @beta_tool
        def send_letter(kind: str, recipient: str) -> str:
            """Request to send a drafted letter to the provider or collector. This does NOT send; it asks the human for approval and returns the decision. Stop after calling this and summarize for the patient."""
            for l in case.letters:
                if l.kind == kind:
                    ok = approval.decide(l)
                    case.log.append(f"{date.today()}: send {kind} to {recipient}: {'approved' if ok else 'pending approval'}")
                    return "approved and queued for sending" if ok else "pending human approval; do not assume it was sent"
            return f"no draft of kind {kind}"

        @beta_tool
        def record_provider_response(summary: str, counter_offer: Optional[float] = None, corrections_made: Optional[float] = None) -> str:
            """Log what the provider said or offered so the next round can be planned."""
            case.log.append(f"{date.today()}: provider response: {summary}; counter={counter_offer}; corrections={corrections_made}")
            if case.plan and corrections_made:
                case.plan.current_balance = round(case.plan.current_balance - corrections_made, 2)
            return "recorded"

        return [get_case_summary, list_lines, run_bill_audit, add_finding, run_benchmarks, set_patient_profile,
                run_eligibility_screen, build_negotiation_plan, draft_letter, revise_letter, send_letter, record_provider_response]

    # ------------------------------------------------------------------ run
    def run(self, instruction: str, max_iterations: int = 30) -> str:
        runner = self.client.beta.messages.tool_runner(
            model=self.model,
            max_tokens=16000,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            tools=self.tools,
            messages=[{"role": "user", "content": instruction}],
            max_iterations=max_iterations,
        )
        final = runner.until_done()
        if final.stop_reason == "refusal":
            return f"The model declined this request ({final.stop_details.category if final.stop_details else 'no category'})."
        return "\n".join(b.text for b in final.content if b.type == "text")


def run_offline(case: CaseFile) -> CaseFile:
    """Full deterministic pipeline with no model calls. Useful for tests, CI, and when no API key is set."""
    case.findings = run_audit(case.bill, case.eob)
    case.benchmarks = benchmark_bill(case.bill)
    case.eligibility = screen(case.bill, case.patient)
    case.plan = build_plan(case.bill, case.findings, case.benchmarks, case.eligibility, case.patient)
    case.letters = [
        letters.itemized_request(case.bill, patient_is_medicare=bool(case.patient and case.patient.medicare_beneficiary)),
        letters.dispute_letter(case),
        letters.settlement_offer(case, case.plan.anchor),
        letters.phone_script(case),
    ]
    if case.eligibility.charity_care_likely:
        case.letters.append(letters.fap_cover_letter(case))
    if case.eligibility.nsa_ppdr_eligible:
        case.letters.append(letters.ppdr_checklist(case))
    case.log.append(f"{date.today()}: offline pipeline run")
    return case
