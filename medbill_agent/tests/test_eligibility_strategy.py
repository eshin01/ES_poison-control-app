from datetime import date
from pathlib import Path

from medbill.agent import run_offline
from medbill.benchmarks import MedicareRates, benchmark_bill, summarize
from medbill.eligibility import fpl_percent, screen
from medbill.ingest import load_bill_csv
from medbill.models import CaseFile, PatientProfile

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def _bill(**over):
    meta = dict(provider_name="Test Hospital", nonprofit=True, state="GA", admit_date=date(2026, 9, 14), discharge_date=date(2026, 9, 15),
                setting="emergency", first_statement_date=date(2026, 10, 1), insured=False, good_faith_estimate_total=9500.0, patient_responsibility=25525.0)
    meta.update(over)
    return load_bill_csv(SAMPLES / "sample_itemized_bill.csv", **meta)


def test_fpl_math():
    assert fpl_percent(15650, 1) == 100.0
    assert fpl_percent(52000, 3) == round(100 * 52000 / (15650 + 2 * 5500), 1)


def test_screen_timelines_and_ppdr():
    pt = PatientProfile(household_size=3, annual_household_income=52000, state="GA", insured=False)
    e = screen(_bill(), pt, today=date(2026, 11, 2))
    assert e.charity_care_likely
    assert e.eca_earliest_date == date(2027, 1, 29)
    assert e.fap_application_deadline == date(2027, 5, 29)
    assert e.nsa_ppdr_eligible and e.nsa_ppdr_deadline == date(2027, 1, 29)
    assert e.agb_cap_applies


def test_insured_emergency_is_nsa_protected():
    e = screen(_bill(insured=True), None)
    assert e.nsa_balance_billing_protected
    assert not e.nsa_ppdr_eligible


def test_benchmarks_and_plan():
    b = _bill()
    bm = benchmark_bill(b, MedicareRates.illustrative())
    s = summarize(bm)
    assert s["lines_with_medicare"] >= 15
    assert s["median_markup_vs_medicare"] > 3
    case = run_offline(CaseFile(bill=b, patient=PatientProfile(household_size=3, annual_household_income=52000, state="GA", insured=False)))
    p = case.plan
    assert p.anchor <= p.target <= p.walk_away <= p.current_balance
    assert p.disputed_total > 0 and round(p.undisputed_balance + p.disputed_total, 2) == p.current_balance
    assert p.if_assistance_denied and p.if_assistance_denied["anchor"] > 0
    assert len(p.patient_batna) >= 3 and len(p.provider_batna) >= 2
    assert len(p.value_creating_options) >= 2
    kinds = {l.kind for l in case.letters}
    assert {"itemized_request", "dispute", "settlement_offer", "fap_cover", "ppdr_checklist", "phone_script"} <= kinds
    assert "—" not in "".join(l.body for l in case.letters)
