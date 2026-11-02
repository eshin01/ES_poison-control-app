"""Streamlit front end for the MedBill agent. Run: streamlit run medbill_agent/app.py"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from medbill.agent import Approval, MedBillAgent, run_offline  # noqa: E402
from medbill.cli import render_report  # noqa: E402
from medbill.ingest import extract_bill_with_claude, load_bill_csv, load_eob_csv  # noqa: E402
from medbill.models import CaseFile, PatientProfile  # noqa: E402

st.set_page_config(page_title="MedBill Agent", layout="wide")
st.title("MedBill Agent")
st.caption("Audit an itemized bill, benchmark it, screen for assistance, and plan the negotiation. Nothing is sent without your approval.")

with st.sidebar:
    st.header("Bill")
    bill_file = st.file_uploader("Itemized bill (CSV, PDF, image)", type=["csv", "pdf", "png", "jpg", "jpeg", "txt"])
    eob_file = st.file_uploader("Explanation of benefits (CSV, optional)", type=["csv"])
    provider_name = st.text_input("Provider name", "Hospital")
    setting = st.selectbox("Setting", ["emergency", "inpatient", "observation", "outpatient", "office", "unknown"])
    nonprofit = st.selectbox("Nonprofit hospital?", ["unknown", "yes", "no"])
    state = st.text_input("State (2 letters)", "GA")
    admit = st.date_input("Admit / service date", date.today())
    discharge = st.date_input("Discharge date", date.today())
    first_stmt = st.date_input("Date of first statement", date.today())
    pr = st.number_input("Balance the provider says you owe", min_value=0.0, value=0.0, step=1.0)
    gfe = st.number_input("Good faith estimate total (self-pay only; 0 if none)", min_value=0.0, value=0.0, step=1.0)

    st.header("Patient")
    insured = st.checkbox("Insured", value=True)
    in_network = st.checkbox("Provider in network", value=True, disabled=not insured)
    household = st.number_input("Household size", 1, 15, 1)
    income = st.number_input("Annual household income", min_value=0.0, value=40000.0, step=1000.0)
    lump = st.number_input("Cash available for a lump-sum settlement", min_value=0.0, value=0.0, step=100.0)
    monthly = st.number_input("Affordable monthly payment", min_value=0.0, value=0.0, step=25.0)

    use_model = st.checkbox("Use Claude for extraction and letter refinement", value=bool(os.environ.get("ANTHROPIC_API_KEY")))

if st.button("Analyze", type="primary", disabled=bill_file is None):
    tmpdir = Path(tempfile.mkdtemp())
    bpath = tmpdir / bill_file.name
    bpath.write_bytes(bill_file.getvalue())
    meta = dict(provider_name=provider_name, setting=setting, state=state.upper(), admit_date=admit, discharge_date=discharge,
                first_statement_date=first_stmt, insured=insured, in_network=in_network if insured else None,
                nonprofit=None if nonprofit == "unknown" else nonprofit == "yes",
                patient_responsibility=pr or None, good_faith_estimate_total=gfe or None)
    if bpath.suffix.lower() == ".csv":
        bill = load_bill_csv(bpath, **meta)
    elif use_model:
        with st.spinner("Reading the bill with Claude..."):
            bill = extract_bill_with_claude(bpath, **meta)
    else:
        st.error("PDF and image bills need Claude. Upload a CSV or enable the model.")
        st.stop()
    eob = None
    if eob_file:
        epath = tmpdir / eob_file.name
        epath.write_bytes(eob_file.getvalue())
        eob = load_eob_csv(epath, in_network=in_network if insured else None)
    patient = PatientProfile(household_size=household, annual_household_income=income, state=state.upper(), insured=insured,
                             can_pay_lump_sum=lump or None, monthly_payment_capacity=monthly or None)
    case = run_offline(CaseFile(bill=bill, eob=eob, patient=patient))
    st.session_state["case"] = case

case: CaseFile | None = st.session_state.get("case")
if case:
    p = case.plan
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Balance", f"${p.current_balance:,.0f}")
    c2.metric("In dispute", f"${p.disputed_total:,.0f}")
    c3.metric("Medicare equivalent (undisputed)", f"${p.medicare_total:,.0f}" if p.medicare_total else "n/a")
    c4.metric("Target settlement", f"${p.target:,.0f}")

    tabs = st.tabs(["Findings", "Assistance and rights", "Negotiation plan", "Letters", "Agent", "Raw"])
    with tabs[0]:
        for f in case.findings:
            with st.expander(f"[{f.severity.value}] {f.title}  (${f.disputed_amount:,.2f})"):
                st.write(f.explanation)
                st.caption(f"Confidence: {f.confidence}. Lines: {', '.join(f.line_ids) or 'n/a'}. " + ("Records needed. " if f.requires_records else "") + " | ".join(f.evidence))
    with tabs[1]:
        e = case.eligibility
        st.write(f"Income is {e.fpl_percent}% of the federal poverty guideline." if e.fpl_percent is not None else "No income given.")
        for s in e.charity_care_basis + e.notes:
            st.write("- " + s)
        if e.nsa_ppdr_eligible:
            st.success(f"No Surprises Act dispute available: {e.nsa_ppdr_basis} Deadline {e.nsa_ppdr_deadline}.")
        with st.expander("State and federal protections"):
            for s in e.state_protections:
                st.write("- " + s)
    with tabs[2]:
        st.markdown(render_report(case).split("## Negotiation plan", 1)[1].split("## Drafts")[0])
    with tabs[3]:
        for l in case.letters:
            with st.expander(f"{l.kind} ({l.send_via})"):
                st.text_area("Subject", l.subject, key=f"s_{l.kind}")
                st.text_area("Body", l.body, height=400, key=f"b_{l.kind}")
                st.download_button("Download", f"Subject: {l.subject}\n\n{l.body}", file_name=f"{l.kind}.txt", key=f"d_{l.kind}")
    with tabs[4]:
        st.write("Ask the agent to refine letters, reason about a provider's counteroffer, or plan the next round. Sending requires your approval below.")
        instr = st.text_area("Instruction", "Review the findings, improve the dispute letter so it reads as a patient wrote it, and tell me what to do first.")
        if st.button("Run agent", disabled=not use_model):
            approval = Approval()  # collects pending letters instead of sending
            agent = MedBillAgent(case, approval=approval)
            with st.spinner("Working..."):
                out = agent.run(instr)
            st.markdown(out)
            for l in approval.pending:
                st.warning(f"Agent wants to send: {l.kind} via {l.send_via}. Review it in the Letters tab, then send it yourself or approve here.")
                if st.button(f"Approve sending {l.kind}", key=f"ap_{l.kind}"):
                    st.info("Approved. Connect an email or portal integration in medbill/agent.py Approval.decide to transmit.")
    with tabs[5]:
        st.json(json.loads(case.model_dump_json()))
