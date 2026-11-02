from medbill.simulate import cholecystectomy_bill, default_scenarios, run_all, simulate
from medbill.audit import run_audit
from medbill.strategy import prioritize


def test_bill_generator_errors_are_detected():
    b = cholecystectomy_bill()
    rules = {f.rule for f in run_audit(b)}
    assert {"duplicate_charge", "unbundling", "mue_exceeded", "routine_supplies", "uncoded_charge", "room_board_discharge_day", "gfe_variance"} <= rules
    clean = cholecystectomy_bill(with_errors=False)
    assert not {"duplicate_charge", "unbundling", "mue_exceeded", "routine_supplies", "uncoded_charge"} & {f.rule for f in run_audit(clean)}


def test_prioritize_orders_by_expected_value():
    b = cholecystectomy_bill()
    rows = prioritize(run_audit(b), b, None)
    evs = [r["expected_value"] for r in rows]
    assert evs == sorted(evs, reverse=True)
    assert rows[0]["p_success"] > 0


def test_scenarios_run_and_agent_beats_baseline():
    res = run_all()
    assert len(res) == 4
    for r in res:
        assert 0 <= r.agent_balance <= r.patient_alone_balance <= r.starting_balance
        assert r.rounds and r.rounds[0].actor == "agent"
    by = {r.scenario.name[0]: r for r in res}
    assert by["A"].agent_balance == 0          # free care under 200% FPL
    assert by["D"].agent_balance < 10000       # No Surprises Act removes the balance bill


def test_in_network_corrections_do_not_move_patient_when_oop_max_binds():
    scn = default_scenarios()[2]
    r = simulate(scn)
    facility = [p for p in r.priority_table if p["rule"] in {"duplicate_charge", "unbundling", "mue_exceeded"}]
    assert facility and all(p["expected_value"] == 0 for p in facility)
