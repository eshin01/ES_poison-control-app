"""Command line entry point.

  python -m medbill.cli analyze samples/sample_itemized_bill.csv --patient samples/sample_patient.json --eob samples/sample_eob.csv --out out/
  python -m medbill.cli agent  samples/sample_itemized_bill.csv --patient samples/sample_patient.json "Audit this bill and draft the dispute letter"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from .agent import Approval, MedBillAgent, run_offline
from .benchmarks import HospitalMRF, MedicareRates
from .ingest import extract_bill_with_claude, load_bill_csv, load_bill_json, load_eob_csv
from .models import CaseFile, PatientProfile


def _load_case(args) -> CaseFile:
    meta = json.loads(Path(args.bill_meta).read_text()) if args.bill_meta else {}
    for k in ("admit_date", "discharge_date", "first_statement_date"):
        if meta.get(k):
            meta[k] = date.fromisoformat(meta[k])
    meta.setdefault("provider_name", "Provider")
    path = Path(args.bill)
    if path.suffix.lower() == ".csv":
        bill = load_bill_csv(path, **meta)
    elif path.suffix.lower() == ".json":
        bill = load_bill_json(path)
    else:
        bill = extract_bill_with_claude(path, insured=meta.get("insured", True), **meta)
    patient = PatientProfile.model_validate_json(Path(args.patient).read_text()) if args.patient else None
    if patient:
        bill.insured = patient.insured
        bill.state = bill.state or patient.state
    eob = load_eob_csv(Path(args.eob), in_network=bill.in_network) if args.eob else None
    return CaseFile(bill=bill, eob=eob, patient=patient)


def _write_outputs(case: CaseFile, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "case.json").write_text(case.model_dump_json(indent=2))
    for l in case.letters:
        (out / f"{l.kind}.txt").write_text(f"Subject: {l.subject}\nVia: {l.send_via}\n\n{l.body}")
    (out / "report.md").write_text(render_report(case))


def render_report(case: CaseFile) -> str:
    b, p = case.bill, case.plan
    lines = [f"# Bill review: {b.provider_name}", ""]
    lines.append(f"Balance on statement: ${p.current_balance:,.2f}. Amount in dispute: ${p.disputed_total:,.2f}. Undisputed: ${p.undisputed_balance:,.2f}.")
    if p.medicare_total is not None:
        lines.append(f"Medicare would pay roughly ${p.medicare_total:,.2f} for the undisputed services.")
    lines += ["", "## Findings", ""]
    for f in case.findings:
        lines.append(f"- [{f.severity.value}, {f.confidence}] {f.title} (${f.disputed_amount:,.2f}). {f.explanation}")
    if case.eligibility:
        e = case.eligibility
        lines += ["", "## Assistance and rights", ""]
        if e.fpl_percent is not None:
            lines.append(f"- Household income is {e.fpl_percent}% of the poverty guideline. Financial assistance likely: {'yes' if e.charity_care_likely else 'no'}.")
        for s in e.charity_care_basis + e.notes:
            lines.append(f"- {s}")
        if e.nsa_ppdr_eligible:
            lines.append(f"- No Surprises Act dispute available: {e.nsa_ppdr_basis} Deadline {e.nsa_ppdr_deadline}.")
    lines += ["", "## Negotiation plan", "", f"Anchor ${p.anchor:,.2f}, target ${p.target:,.2f}, walk away ${p.walk_away:,.2f}."]
    if p.if_assistance_denied:
        fb = p.if_assistance_denied
        lines.append(f"If financial assistance is denied: anchor ${fb['anchor']:,.2f}, target ${fb['target']:,.2f}, walk away ${fb['walk_away']:,.2f}.")
    lines += ["", "Patient BATNA:"]
    lines += [f"- {x}" for x in p.patient_batna]
    lines += ["", "Provider BATNA:"] + [f"- {x}" for x in p.provider_batna]
    lines += ["", "Objective criteria:"] + [f"- {x}" for x in p.objective_criteria]
    lines += ["", "Options that expand value:"] + [f"- {x}" for x in p.value_creating_options]
    lines += ["", "Sequence:"] + [f"{i}. {x}" for i, x in enumerate(p.recommended_sequence, 1)]
    lines += ["", f"Leverage: {p.leverage_assessment}", "", f"Relationship: {p.relationship_note}", ""]
    lines += ["## Drafts", ""] + [f"- {l.kind} ({l.send_via}, {'needs approval' if l.requires_human_approval else 'informational'})" for l in case.letters]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="medbill")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("analyze", "agent"):
        s = sub.add_parser(name)
        s.add_argument("bill", help="Itemized bill: .csv, .json, .pdf, .png/.jpg, or .txt")
        s.add_argument("--bill-meta", help="JSON with provider_name, setting, nonprofit, state, dates, insured, good_faith_estimate_total, patient_responsibility")
        s.add_argument("--patient", help="JSON PatientProfile")
        s.add_argument("--eob", help="EOB CSV")
        s.add_argument("--mrf", help="Hospital price transparency file (.json or .csv)")
        s.add_argument("--opps", help="CMS OPPS Addendum B CSV")
        s.add_argument("--pfs", help="CMS PFS national payment CSV")
        s.add_argument("--out", default="out")
    sub.choices["agent"].add_argument("instruction", nargs="?", default="Audit this bill, benchmark it, screen for assistance, build the negotiation plan, and draft the itemized request and dispute letter. Then summarize for the patient.")
    sub.choices["agent"].add_argument("--auto-approve", action="store_true", help="Approve outbound letters without asking (testing only)")
    args = ap.parse_args(argv)

    case = _load_case(args)
    medicare = MedicareRates.illustrative()
    if args.opps:
        medicare = medicare.merge(MedicareRates.from_opps_addendum_b(Path(args.opps)))
    if args.pfs:
        medicare = medicare.merge(MedicareRates.from_pfs_national(Path(args.pfs)))
    mrf = None
    if args.mrf:
        mrf = HospitalMRF.from_json(Path(args.mrf)) if args.mrf.endswith(".json") else HospitalMRF.from_csv_tall(Path(args.mrf))

    if args.cmd == "analyze":
        from .benchmarks import benchmark_bill
        case = run_offline(case)
        case.benchmarks = benchmark_bill(case.bill, medicare, mrf)
        _write_outputs(case, Path(args.out))
        print(render_report(case))
        return 0

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("No Anthropic credentials found. Set ANTHROPIC_API_KEY or run `ant auth login`. Falling back to `analyze`.", file=sys.stderr)
        case = run_offline(case)
        _write_outputs(case, Path(args.out))
        print(render_report(case))
        return 2

    def ask(letter):
        print(f"\n=== APPROVAL NEEDED: {letter.kind} via {letter.send_via} ===\nSubject: {letter.subject}\n\n{letter.body}\n")
        return input("Send? [y/N] ").strip().lower() == "y"

    agent = MedBillAgent(case, approval=Approval(ask=None if args.auto_approve else ask, auto_approve=args.auto_approve), medicare=medicare, mrf=mrf)
    print(agent.run(args.instruction))
    _write_outputs(case, Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
