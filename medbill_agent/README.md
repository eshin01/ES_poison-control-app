# MedBill Agent

An AI agent that audits itemized medical bills, prices them against what the hospital already accepts, screens the patient for financial assistance and federal dispute rights, and runs an interest-based negotiation with the provider. Every outbound letter or call goes through a human approval gate.

The research behind the design is in `docs/RESEARCH.md`.

## What it does

1. Ingest. CSV or JSON bills load directly. PDFs, photos, and pasted text go to Claude with a structured-output schema (`medbill/ingest.py`).
2. Audit. Deterministic rules flag duplicates, unit ceilings (CMS Medically Unlikely Edits), unbundled code pairs (NCCI procedure-to-procedure edits), ED level without supporting intensity, ED level plus critical care, routine supplies billed separately, uncoded charges, dates outside the stay, discharge-day room and board, impossible observation hours, drug markups, EOB mismatches and balance billing, and good faith estimate overages (`medbill/audit.py`). Each finding carries a confidence label (fact, deduction, speculation) and the rule it rests on.
3. Benchmark. Each coded line is compared to Medicare and, when the hospital's price transparency file is loaded, to its cash price and payer negotiated rates (`medbill/benchmarks.py`).
4. Screen. Household income against the federal poverty guideline, common charity care thresholds, 501(r) timelines, No Surprises Act protections, and state rules (`medbill/eligibility.py`).
5. Plan. Both sides' BATNA, positions vs interests, objective criteria, value-expanding options, anchor / target / walk-away, and a concession ladder (`medbill/strategy.py`).
6. Draft. Itemized records request, dispute letter, financial assistance cover letter, settlement offer, No Surprises Act checklist, collections response, phone script (`medbill/letters.py`).
7. Negotiate. A Claude tool-runner agent orchestrates the above, refines letters, logs provider responses, and asks for approval before anything is sent (`medbill/agent.py`).

## Quick start

```bash
cd medbill_agent
pip install -r requirements.txt
python -m pytest -q tests

# Offline analysis (no API key needed)
python -m medbill.cli analyze samples/sample_itemized_bill.csv \
  --bill-meta samples/sample_bill_meta.json \
  --patient samples/sample_patient.json --out out/

# Agent mode (needs ANTHROPIC_API_KEY or `ant auth login`)
python -m medbill.cli agent samples/sample_itemized_bill.csv \
  --bill-meta samples/sample_bill_meta.json \
  --patient samples/sample_patient.json \
  "Audit this bill and draft the dispute letter, then tell me what to do first."

# Web UI
streamlit run app.py
```

Outputs land in `out/`: `report.md`, `case.json`, and one text file per letter.

## Simulation and pitch deck

`python -m medbill.simulate docs/SIMULATION.md` builds a synthetic 48-line bill for an emergency visit for abdominal pain followed by a laparoscopic cholecystectomy, plants the error types the research found most often, and runs four coverage scenarios (uninsured at a nonprofit, uninsured at a for-profit, insured in network with a high deductible, insured out-of-network emergency) against a rule-based hospital billing office. It prints the priority order the agent uses (dollars at stake times probability of success, recomputed through the patient's deductible and out-of-pocket maximum), a round-by-round transcript, and the outcome against a "patient alone" baseline. Every behavioral assumption is a named constant in `HOSPITAL_POLICY`. Results are expected values under those assumptions, not measurements.

The pitch deck lives in `deck/` as slide files (the same files published to the Claude Slides artifact) and in `docs/SIMULATION.md` for the numbers behind it.

## Loading real benchmark data

The package ships illustrative Medicare rates so it runs offline. Before using numbers in a real dispute:

- Download the current OPPS Addendum B and the PFS national payment file from CMS and pass them with `--opps` and `--pfs`.
- Find the hospital's machine-readable file. Hospitals must post `cms-hpt.txt` at their web root naming the file URL (`HospitalMRF.discover_url`). Pass the downloaded JSON or CSV with `--mrf`.
- Replace `medbill/data/ncci_ptp_sample.csv` and `mue_sample.csv` with the full CMS NCCI tables (same column names).
- Update `medbill/data/fpl.json` each January.

## Approval gate

`Approval` in `medbill/agent.py` is the only path to the outside world. By default it collects pending letters for a human to review. Pass `ask=` with a function that shows the letter and returns True/False, or wire `decide()` to your email or portal integration. The agent's system prompt tells it to stop and summarize after requesting a send.

## Limits

- The 501(r) day counts, the No Surprises Act filing fee, and the state protections marked `verify` in `state_protections.json` were not re-verified against primary text in this build. Check before citing in a letter.
- Findings labeled `speculation` (ED visit level) need the medical record before they are raised with the provider.
- The agent describes rights and cites rules; it does not give legal advice.

## Layout

```
medbill_agent/
  app.py                 Streamlit UI
  medbill/
    models.py            Pydantic data model
    ingest.py            CSV/JSON loaders and Claude extraction
    audit.py             Deterministic audit rules
    benchmarks.py        Medicare rates and hospital MRF reader
    eligibility.py       FPL, charity care, 501(r), NSA, state rules
    strategy.py          Interest-based negotiation plan and expected-value prioritization
    simulate.py          Cholecystectomy bill generator, coverage scenarios, hospital model
    letters.py           Letter and script templates
    agent.py             Claude tool-runner agent and approval gate
    cli.py               Command line
    data/                Reference tables (see notes inside each file)
  samples/               Synthetic bill, EOB, patient, and metadata
  tests/                 pytest suite (no network, no API key)
  docs/RESEARCH.md       Market and regulatory research
  docs/SIMULATION.md     Scenario results and transcripts
  deck/                  Pitch deck slide files
```
