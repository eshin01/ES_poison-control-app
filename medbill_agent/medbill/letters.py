"""Letter and script templates. Plain prose, no model needed; the agent can refine them."""
from __future__ import annotations

from datetime import date
from typing import Optional

from .models import Bill, CaseFile, Finding, Letter


def _acct(bill: Bill) -> str:
    return f", account {bill.account_number}" if bill.account_number else ""


def _hdr(bill: Bill, today: date) -> str:
    return (f"{today.strftime('%B %d, %Y')}\n\n{bill.provider_name}\nPatient Financial Services\n\n"
            f"Re: Patient {bill.patient_name or '[name]'}, Account {bill.account_number or '[account number]'}, "
            f"dates of service {bill.admit_date or '[date]'}" + (f" to {bill.discharge_date}" if bill.discharge_date and bill.discharge_date != bill.admit_date else "") + "\n\n")


def itemized_request(bill: Bill, patient_is_medicare: bool = False, today: Optional[date] = None) -> Letter:
    today = today or date.today()
    body = _hdr(bill, today) + (
        "To whom it may concern,\n\n"
        "Please send me the following for the account above:\n\n"
        "1. A complete itemized statement showing, for every line, the date of service, description, CPT or HCPCS code, revenue code, units, and charge.\n"
        "2. A copy of the UB-04 (CMS-1450) claim form submitted to my insurer, if any.\n"
        "3. A copy of my medical record for this encounter, including nursing flow sheets, the medication administration record, and physician orders. I am making this request under my HIPAA right of access, 45 CFR 164.524, and ask that it be fulfilled within 30 days in electronic form.\n"
        "4. A copy of the hospital's financial assistance policy and plain-language summary, and its emergency department facility leveling criteria.\n\n"
        + ("As a Medicare beneficiary I am entitled to a free itemized statement under section 1806(b) of the Social Security Act.\n\n" if patient_is_medicare else "")
        + "Please place the account on hold and send nothing to collections while this request is open and the charges are under review. I will respond promptly once I receive the documents.\n\n"
        "Sincerely,\n\n[Patient name]\n[Address]\n[Phone / email]"
    )
    return Letter(kind="itemized_request", subject=f"Request for itemized statement and records{_acct(bill)}", body=body, send_via="mail")


def dispute_letter(case: CaseFile, today: Optional[date] = None) -> Letter:
    today = today or date.today()
    bill = case.bill
    from .audit import REMEDY_RULES
    rows = []
    for f in case.findings:
        if f.rule in REMEDY_RULES:
            continue
        rows.append(f"- Lines {', '.join(f.line_ids) or 'n/a'}: {f.title}. {f.explanation.split('. ')[0]}. Amount in dispute: ${f.disputed_amount:,.2f}." + (f" Basis: {'; '.join(f.evidence)}." if f.evidence else ""))
    disputed = case.plan.disputed_total if case.plan else sum(f.disputed_amount for f in case.findings)
    body = _hdr(bill, today) + (
        "To whom it may concern,\n\n"
        f"I have reviewed the itemized statement for this account and dispute the following charges, totaling ${disputed:,.2f}:\n\n"
        + "\n".join(rows) +
        "\n\nPlease review each item against the medical record and send me a corrected itemized statement. Where a charge is supported, send the documentation that supports it. "
        "I am not refusing to pay for care I received; I am asking to be billed correctly.\n\n"
        "While this dispute is open, please hold the account, do not assess interest or late fees, and do not refer it to a collection agency or report it to a credit bureau. "
        + ("As a nonprofit hospital, you are required to make reasonable efforts to determine my eligibility for financial assistance before any extraordinary collection action (26 CFR 1.501(r)-6). " if bill.nonprofit is not False else "")
        + "I will pay the undisputed balance once the corrected statement arrives.\n\n"
        "Sincerely,\n\n[Patient name]\n[Address]\n[Phone / email]\n\nEnclosures: itemized statement with disputed lines marked; explanation of benefits (if applicable)"
    )
    return Letter(kind="dispute", subject=f"Dispute of itemized charges{_acct(bill)}", body=body, send_via="mail")


def fap_cover_letter(case: CaseFile, today: Optional[date] = None) -> Letter:
    today = today or date.today()
    bill, elig, pt = case.bill, case.eligibility, case.patient
    body = _hdr(bill, today) + (
        "To the Financial Assistance Office,\n\n"
        "Enclosed is my application for financial assistance under your financial assistance policy, with proof of income and household size.\n\n"
        + (f"My household of {pt.household_size} has an annual income of ${pt.annual_household_income:,.0f}, which is about {elig.fpl_percent}% of the federal poverty guideline. " if pt and elig and elig.fpl_percent is not None else "")
        + (f"The balance of ${bill.patient_responsibility or bill.computed_total:,.2f} is a hardship relative to that income. " if pt else "")
        + "\n\nI ask that you:\n\n"
        "1. Screen me for presumptive eligibility using any data sources your policy allows.\n"
        "2. Suspend all collection activity while the application is pending, as required for 501(c)(3) hospitals under 26 CFR 1.501(r)-6(c).\n"
        "3. If I qualify for any discount tier, limit my charges to the amounts generally billed to insured patients under 26 CFR 1.501(r)-5, and refund any amount I have already paid above that figure.\n"
        "4. Send a written determination with the basis for the decision and the appeal process.\n\n"
        + (f"I understand the application period runs through at least {elig.fap_application_deadline}. " if elig and elig.fap_application_deadline else "")
        + "Please confirm receipt.\n\n"
        "Sincerely,\n\n[Patient name]\n[Address]\n[Phone / email]\n\nEnclosures: application form, pay stubs or tax return, proof of household size"
    )
    return Letter(kind="fap_cover", subject=f"Financial assistance application{_acct(bill)}", body=body, send_via="mail")


def settlement_offer(case: CaseFile, offer: float, today: Optional[date] = None) -> Letter:
    today = today or date.today()
    bill, plan = case.bill, case.plan
    criteria = "\n".join(f"- {c}" for c in (plan.objective_criteria if plan else []))
    body = _hdr(bill, today) + (
        "To whom it may concern,\n\n"
        f"Thank you for the corrected statement. I am prepared to resolve this account in full with a payment of ${offer:,.2f} within ten business days of your written acceptance.\n\n"
        "This offer reflects what the hospital already accepts for these services:\n\n"
        + criteria +
        "\n\nIn exchange I ask for a letter confirming the account is settled in full with a zero balance, that no portion will be billed later or sent to collections, and that nothing will be reported to a credit bureau.\n\n"
        "If a lump sum is not acceptable, I can pay the same amount over 12 months at zero interest. Please reply in writing.\n\n"
        "Sincerely,\n\n[Patient name]\n[Address]\n[Phone / email]"
    )
    return Letter(kind="settlement_offer", subject=f"Settlement offer{_acct(bill)}", body=body, send_via="email")


def ppdr_checklist(case: CaseFile) -> Letter:
    bill, elig = case.bill, case.eligibility
    body = (
        "No Surprises Act patient-provider dispute resolution checklist\n\n"
        f"Eligibility: {elig.nsa_ppdr_basis if elig and elig.nsa_ppdr_basis else 'Bill must be at least $400 above the good faith estimate for this provider.'}\n"
        f"Deadline: {elig.nsa_ppdr_deadline if elig and elig.nsa_ppdr_deadline else '120 calendar days from the date on the bill.'}\n\n"
        "Steps:\n"
        "1. Gather the good faith estimate, the itemized bill, and the provider's contact details.\n"
        "2. File online through the CMS medical bill rights portal (cms.gov/medical-bill-rights) or by mail. There is a small administrative fee, refunded if you prevail. Verify the current fee on the CMS page.\n"
        "3. Notify the provider in writing that a dispute is filed. During the dispute the provider may not send the bill to collections, must pause existing collections, may not charge late fees, and may not retaliate.\n"
        "4. The dispute resolution entity decides whether the extra charges were reasonably unforeseeable. Keep negotiating in parallel; a settlement must be reported to the entity within three business days.\n"
    )
    return Letter(kind="ppdr_checklist", subject="No Surprises Act dispute checklist", body=body, send_via="portal", requires_human_approval=False)


def collections_response(case: CaseFile, collector_name: str, today: Optional[date] = None) -> Letter:
    today = today or date.today()
    bill = case.bill
    body = (
        f"{today.strftime('%B %d, %Y')}\n\n{collector_name}\n\nRe: Account referenced in your notice regarding {bill.provider_name}\n\n"
        "This letter is a timely written dispute of the debt under 15 USC 1692g(b). Please provide validation of the debt, including an itemized statement from the original creditor with CPT/HCPCS and revenue codes, the itemization date, and documentation of the amount claimed.\n\n"
        "The underlying charges are disputed with the provider for billing errors. Until you validate the debt, cease collection activity. Do not report this account to any consumer reporting agency; if it has been reported, mark it disputed as required by 15 USC 1692e(8).\n\n"
        + ("Under Colorado law a written request for an itemized statement pauses collection until it is provided. " if (bill.state or '').upper() == 'CO' else "")
        + "Communicate with me in writing only.\n\nSincerely,\n\n[Patient name]\n[Address]"
    )
    return Letter(kind="collections_response", subject="Debt validation and dispute", body=body, send_via="mail")


def phone_script(case: CaseFile) -> Letter:
    plan = case.plan
    anchor = plan.anchor if plan else 0
    target = plan.target if plan else 0
    body = (
        "Phone script for patient financial services\n\n"
        "Opening: 'I'm calling about account [number]. I've reviewed the itemized statement and I want to resolve the balance today. Before we talk about payment, I need three line items corrected.' (Name the top findings by line number. Stay factual; cite the rule, not the motive.)\n\n"
        "If they push back: 'I understand. Please send me the record entries that support those charges and I'll review them. Meanwhile, can you place a 30-day hold on the account?'\n\n"
        f"Settlement: 'For the remaining balance, I can pay ${anchor:,.0f} today. Medicare pays about that for these services and your own cash price list is in the same range.' Pause. Let them counter.\n\n"
        f"Concede slowly: move toward ${target:,.0f} only in exchange for something: a paid-in-full letter, removal of a disputed line, or zero-interest terms.\n\n"
        "Always ask: 'Have I been screened for financial assistance? Please run the presumptive screen and note it on the account.'\n\n"
        "Close: 'Please email me written confirmation of what we agreed before I pay.' Get the representative's name and a reference number. Do not give card details until the written terms arrive.\n"
    )
    return Letter(kind="phone_script", subject="Call script", body=body, send_via="phone_script", requires_human_approval=False)
