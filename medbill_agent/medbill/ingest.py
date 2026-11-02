"""Turn a bill (CSV, PDF, image, or pasted text) into a Bill model.

CSV and JSON load without a model. PDFs, images, and free text go to Claude with a
structured-output schema so every line lands in the same shape.
"""
from __future__ import annotations

import base64
import csv
import json
import mimetypes
from datetime import date
from pathlib import Path
from typing import Optional

from .models import EOB, Bill, EOBLine, LineItem

MODEL = "claude-opus-5-5"


def load_bill_csv(path: Path, **meta) -> Bill:
    lines = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            row = {k.strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            units = float(row.get("units") or 1)
            total = float(str(row.get("total_charge") or row.get("charge") or 0).replace("$", "").replace(",", ""))
            lines.append(LineItem(
                line_id=row.get("line_id") or str(i),
                service_date=date.fromisoformat(row["service_date"]) if row.get("service_date") else None,
                description=row.get("description") or "",
                cpt_hcpcs=(row.get("cpt_hcpcs") or row.get("cpt") or None) or None,
                modifiers=[m for m in (row.get("modifiers") or "").split("|") if m],
                revenue_code=(row.get("revenue_code") or None) or None,
                ndc=row.get("ndc") or None,
                units=units,
                unit_charge=total / units if units else None,
                total_charge=total,
                department=row.get("department") or None,
                raw_text=json.dumps(row),
            ))
    return Bill(lines=lines, **meta)


def load_eob_csv(path: Path, payer_name: str = "Insurer", in_network: Optional[bool] = None) -> EOB:
    lines = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row = {k.strip().lower(): v for k, v in row.items()}
            lines.append(EOBLine(
                cpt_hcpcs=row.get("cpt_hcpcs") or None,
                description=row.get("description") or None,
                billed=float(row.get("billed") or 0),
                allowed=float(row["allowed"]) if row.get("allowed") else None,
                plan_paid=float(row["plan_paid"]) if row.get("plan_paid") else None,
                patient_responsibility=float(row["patient_responsibility"]) if row.get("patient_responsibility") else None,
                denial_code=row.get("denial_code") or None,
                denial_reason=row.get("denial_reason") or None,
            ))
    return EOB(payer_name=payer_name, in_network=in_network, lines=lines,
               total_patient_responsibility=sum(l.patient_responsibility or 0 for l in lines))


def load_bill_json(path: Path) -> Bill:
    return Bill.model_validate_json(Path(path).read_text())


EXTRACTION_PROMPT = """You are reading a patient's medical bill. Extract every charge line exactly as printed.

Rules:
- One LineItem per printed row. Do not merge or summarize rows.
- Copy CPT/HCPCS codes (5 characters) and 4-digit revenue codes only when printed; never infer a code.
- units defaults to 1 when the bill shows none. total_charge is the row's extended charge.
- Put the verbatim row text in raw_text.
- Fill provider_name, account_number, dates, and totals from the header or summary when present. Leave unknown fields null.
- setting: 'emergency' for ED visits, 'inpatient' when there is an admission with room and board, 'observation' when observation hours (G0378) or an observation revenue code appear, 'outpatient' for same-day procedures or clinic visits.
- insured: true if an insurance payment or adjustment appears, otherwise leave as provided.
"""


def extract_bill_with_claude(path: Path, client=None, insured: bool = True, **overrides) -> Bill:
    """Use Claude vision + structured outputs to parse a PDF, image, or text file into a Bill."""
    import anthropic

    client = client or anthropic.Anthropic()
    path = Path(path)
    mime, _ = mimetypes.guess_type(str(path))
    data = base64.standard_b64encode(path.read_bytes()).decode()
    if mime == "application/pdf":
        block = {"type": "document", "source": {"type": "base64", "media_type": mime, "data": data}}
    elif mime and mime.startswith("image/"):
        block = {"type": "image", "source": {"type": "base64", "media_type": mime, "data": data}}
    else:
        block = {"type": "text", "text": path.read_text(errors="replace")}
    content = [block, {"type": "text", "text": EXTRACTION_PROMPT + f"\nThe patient reports insured = {insured}."}]
    with client.messages.stream(
        model=MODEL,
        max_tokens=64000,
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": content}],
        output_format=Bill,
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        raise RuntimeError(f"Extraction declined: {msg.stop_details}")
    bill: Bill = msg.parsed_output
    for k, v in overrides.items():
        if v is not None:
            setattr(bill, k, v)
    return bill
