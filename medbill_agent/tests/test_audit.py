from datetime import date
from pathlib import Path

from medbill.audit import disputed_total, run_audit
from medbill.ingest import load_bill_csv, load_eob_csv
from medbill.models import Bill, LineItem

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def _sample_bill(**over):
    meta = dict(provider_name="Test Hospital", nonprofit=True, state="GA", admit_date=date(2026, 9, 14), discharge_date=date(2026, 9, 15),
                setting="emergency", first_statement_date=date(2026, 10, 1), insured=False, good_faith_estimate_total=9500.0, patient_responsibility=25525.0)
    meta.update(over)
    return load_bill_csv(SAMPLES / "sample_itemized_bill.csv", **meta)


def test_sample_bill_loads():
    b = _sample_bill()
    assert len(b.lines) == 24
    assert b.computed_total == 25525.0


def test_rules_fire_on_sample():
    f = run_audit(_sample_bill())
    rules = {x.rule for x in f}
    assert {"duplicate_charge", "mue_exceeded", "unbundling", "ed_level_plus_critical_care", "routine_supplies",
            "uncoded_charge", "pharmacy_markup", "gfe_variance"} <= rules


def test_duplicate_ct_detected():
    f = [x for x in run_audit(_sample_bill()) if x.rule == "duplicate_charge"]
    assert any(set(x.line_ids) == {"3", "4"} and x.disputed_amount == 2975.0 for x in f)


def test_unbundling_pairs():
    f = [x for x in run_audit(_sample_bill()) if x.rule == "unbundling"]
    pairs = {tuple(x.line_ids) for x in f}
    assert ("5", "6") in pairs      # BMP inside CMP
    assert ("7", "8") in pairs      # CBC w/o diff inside CBC w/ diff
    assert ("11", "12") in pairs    # 93010 inside 93000
    assert ("13", "14") in pairs    # IV start inside infusion


def test_mue_venipuncture():
    f = [x for x in run_audit(_sample_bill()) if x.rule == "mue_exceeded" and "36415" in x.title]
    assert f and f[0].disputed_amount == 110.0  # 2 excess units at $55


def test_observation_hours_exceed_window():
    f = [x for x in run_audit(_sample_bill()) if x.rule == "observation_hours"]
    assert not f  # 36 hours fits a 2-day window
    b = _sample_bill(discharge_date=date(2026, 9, 14))
    f = [x for x in run_audit(b) if x.rule == "observation_hours"]
    assert f and f[0].disputed_amount == round(12 * 160.0, 2)


def test_gfe_variance_only_when_uninsured():
    assert any(x.rule == "gfe_variance" for x in run_audit(_sample_bill()))
    assert not any(x.rule == "gfe_variance" for x in run_audit(_sample_bill(insured=True)))


def test_eob_balance_billing():
    b = _sample_bill(insured=True, in_network=True, patient_responsibility=5000.0)
    eob = load_eob_csv(SAMPLES / "sample_eob.csv", in_network=True)
    f = run_audit(b, eob)
    bb = [x for x in f if x.rule == "balance_billing"]
    assert bb and bb[0].disputed_amount == 5000.0 - 334.0
    assert any(x.rule == "denied_lines" for x in f)


def test_disputed_total_no_double_count():
    f = run_audit(_sample_bill())
    total = disputed_total(f)
    assert 0 < total <= 25525.0


def test_clean_bill_has_no_findings():
    b = Bill(provider_name="Clean", setting="outpatient", insured=True, lines=[
        LineItem(line_id="1", service_date=date(2026, 1, 1), description="Office visit", cpt_hcpcs="99213", total_charge=180.0),
        LineItem(line_id="2", service_date=date(2026, 1, 1), description="Lipid panel", cpt_hcpcs="80061", total_charge=60.0),
    ])
    assert run_audit(b) == []
