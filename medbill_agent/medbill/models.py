"""Pydantic models shared across the package."""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """One row of an itemized hospital or professional bill."""

    line_id: str = Field(description="Stable identifier for the row (e.g. '12').")
    service_date: Optional[date] = None
    description: str
    cpt_hcpcs: Optional[str] = Field(default=None, description="5-character CPT or HCPCS code, if printed.")
    modifiers: list[str] = Field(default_factory=list)
    revenue_code: Optional[str] = Field(default=None, description="4-digit UB-04 revenue code, if printed.")
    ndc: Optional[str] = Field(default=None, description="National Drug Code for drug lines, if printed.")
    units: float = 1
    unit_charge: Optional[float] = None
    total_charge: float
    department: Optional[str] = None
    raw_text: Optional[str] = Field(default=None, description="Verbatim row text for audit trail.")


class Bill(BaseModel):
    provider_name: str
    provider_npi: Optional[str] = None
    provider_type: Literal["hospital_facility", "professional", "ambulance", "lab", "other"] = "hospital_facility"
    nonprofit: Optional[bool] = Field(default=None, description="True if the provider is a 501(c)(3) hospital. Drives 501(r) rights.")
    state: Optional[str] = Field(default=None, description="Two-letter state of the facility.")
    account_number: Optional[str] = None
    patient_name: Optional[str] = None
    admit_date: Optional[date] = None
    discharge_date: Optional[date] = None
    setting: Literal["emergency", "inpatient", "observation", "outpatient", "office", "unknown"] = "unknown"
    drg: Optional[str] = None
    first_statement_date: Optional[date] = Field(default=None, description="Date of the first post-discharge billing statement. Starts the 501(r) clocks.")
    insured: bool = True
    in_network: Optional[bool] = None
    good_faith_estimate_total: Optional[float] = Field(default=None, description="Total on a No Surprises Act good faith estimate, if one was given.")
    lines: list[LineItem]
    total_charges: Optional[float] = None
    insurance_paid: Optional[float] = None
    adjustments: Optional[float] = None
    patient_responsibility: Optional[float] = None

    @property
    def computed_total(self) -> float:
        return round(sum(line.total_charge for line in self.lines), 2)


class EOBLine(BaseModel):
    cpt_hcpcs: Optional[str] = None
    description: Optional[str] = None
    billed: float
    allowed: Optional[float] = None
    plan_paid: Optional[float] = None
    patient_responsibility: Optional[float] = None
    denial_code: Optional[str] = None
    denial_reason: Optional[str] = None


class EOB(BaseModel):
    payer_name: str
    claim_number: Optional[str] = None
    in_network: Optional[bool] = None
    lines: list[EOBLine]
    total_billed: Optional[float] = None
    total_allowed: Optional[float] = None
    total_plan_paid: Optional[float] = None
    total_patient_responsibility: Optional[float] = None


class PatientProfile(BaseModel):
    household_size: int = 1
    annual_household_income: float
    state: str = "GA"
    insured: bool = True
    medicare_beneficiary: bool = False
    medicaid_eligible_possible: bool = False
    assets_liquid: Optional[float] = None
    can_pay_lump_sum: Optional[float] = Field(default=None, description="Cash the patient could pay today in exchange for a steep discount.")
    monthly_payment_capacity: Optional[float] = None
    hardship_notes: Optional[str] = None


class Severity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Finding(BaseModel):
    rule: str
    severity: Severity
    line_ids: list[str]
    title: str
    explanation: str
    disputed_amount: float = Field(description="Dollars the patient should ask to have removed or corrected.")
    evidence: list[str] = Field(default_factory=list, description="Citations to rules, codes, or data behind the finding.")
    confidence: Literal["fact", "deduction", "speculation"] = "deduction"
    requires_records: bool = Field(default=False, description="True when medical records are needed to confirm.")


class Benchmark(BaseModel):
    line_id: str
    cpt_hcpcs: Optional[str]
    billed: float
    medicare_rate: Optional[float] = None
    medicare_source: Optional[str] = None
    hospital_cash_price: Optional[float] = None
    payer_min_negotiated: Optional[float] = None
    payer_median_negotiated: Optional[float] = None
    mrf_source: Optional[str] = None
    markup_vs_medicare: Optional[float] = Field(default=None, description="billed / medicare_rate")


class EligibilityResult(BaseModel):
    fpl_percent: Optional[float] = None
    charity_care_likely: bool = False
    charity_care_basis: list[str] = Field(default_factory=list)
    fap_application_deadline: Optional[date] = None
    eca_earliest_date: Optional[date] = None
    agb_cap_applies: bool = False
    nsa_ppdr_eligible: bool = False
    nsa_ppdr_basis: Optional[str] = None
    nsa_ppdr_deadline: Optional[date] = None
    nsa_balance_billing_protected: bool = False
    state_protections: list[str] = Field(default_factory=list)
    medicaid_screen: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class NegotiationPlan(BaseModel):
    current_balance: float
    disputed_total: float
    undisputed_balance: float
    medicare_total: Optional[float]
    cash_price_total: Optional[float]
    anchor: float
    target: float
    walk_away: float
    patient_batna: list[str]
    provider_batna: list[str]
    patient_interests: list[str]
    provider_interests: list[str]
    objective_criteria: list[str]
    value_creating_options: list[str]
    concession_ladder: list[dict]
    recommended_sequence: list[str]
    leverage_assessment: str
    relationship_note: str
    if_assistance_denied: Optional[dict] = Field(default=None, description="Anchor/target/walk-away to fall back on if the financial assistance application is denied.")


class Letter(BaseModel):
    kind: str
    subject: str
    body: str
    send_via: Literal["mail", "email", "portal", "phone_script"] = "email"
    requires_human_approval: bool = True


class CaseFile(BaseModel):
    """Everything the agent knows about one bill."""

    bill: Bill
    eob: Optional[EOB] = None
    patient: Optional[PatientProfile] = None
    findings: list[Finding] = Field(default_factory=list)
    benchmarks: list[Benchmark] = Field(default_factory=list)
    eligibility: Optional[EligibilityResult] = None
    plan: Optional[NegotiationPlan] = None
    letters: list[Letter] = Field(default_factory=list)
    log: list[str] = Field(default_factory=list)
