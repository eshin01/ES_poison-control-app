# PSQIA / PSO Privilege Architecture for the Flag-and-Coach Product

**Research date:** August 2026
**Purpose:** Explain the federal privilege framework referenced in `product-thesis-clinician-flagged-coaching.md` and map it onto the product architecture. This is strategy research, not legal advice — the design below needs sign-off from health-care regulatory counsel before it carries any weight.

---

## 1. What the PSQIA is

The **Patient Safety and Quality Improvement Act of 2005** (42 U.S.C. §§ 299b-21 through 299b-26) is a federal statute passed in response to the IOM's *To Err Is Human* report. Congress's diagnosis: clinicians won't candidly analyze their own errors and near-misses if that analysis becomes discoverable evidence against them, and the state-by-state patchwork of peer-review privileges was too inconsistent to fix that. The Act's solution is a **federal evidentiary privilege** — uniform across all states — for safety-improvement work done inside a defined structure. The implementing regulation is the **Patient Safety Rule, 42 CFR Part 3** (administered by AHRQ, enforced by OCR).

## 2. The three building blocks

**PSO — Patient Safety Organization.** An entity listed by AHRQ whose mission is to collect and analyze patient safety data from providers and feed back learnings. Listing is by self-certification to AHRQ, renewed on a 3-year cycle. A PSO can be a standalone company or a **component PSO** of a larger organization (many hospital associations, insurers' affiliates, and private companies run them), subject to separation requirements. Notably, an entity whose primary business is insurance underwriting cannot be a PSO — relevant to how malpractice-carrier partnerships get structured.

**PSES — Patient Safety Evaluation System.** The *provider's* internal machinery — people, processes, and (critically for us) software — through which information is "collected, managed, or developed **for the purpose of reporting to a PSO**." The PSES is defined by the provider's own written policies. It is the boundary line: what happens inside the PSES on the pathway to the PSO can be privileged; what happens outside cannot.

**PSWP — Patient Safety Work Product.** The protected stuff. Two flavors:
- Information collected or developed *within a PSES for reporting to a PSO* (reports, analyses, deliberations, memoranda — "deliberations and analysis" are protected even before anything is transmitted); and
- Information a PSO itself creates (its analyses and feedback).

**The protection:** PSWP is **privileged** (not subject to subpoena, discovery, or admission into evidence in any federal, state, local, or tribal civil, criminal, or administrative proceeding) and **confidential** (disclosure restricted, with civil money penalties for violations). This federal privilege preempts contrary state law — it is categorically stronger than state peer-review privilege, which varies by state and frequently excludes risk-management materials.

## 3. What is never protected — and where courts have narrowed it

The statute and case law draw hard limits that dictate product design:

1. **The medical record is never PSWP.** Original patient records, billing records, and any information "collected, maintained, or developed separately" from the PSES stay fully discoverable. You cannot launder a chart by copying it into the PSES.
2. **State-mandated reports are not PSWP.** The two landmark narrowing cases both turn on this:
   - *Tibbs v. Bunnell* (Kentucky 2014): a surgical-event incident report the hospital was required to generate under state regulation was held discoverable even though it was created inside the PSES and sent to a PSO (SCOTUS denied cert).
   - *Charles v. Southern Baptist Hospital of Florida* (Florida 2017): adverse-incident reports required under Florida law (Amendment 7) were held outside PSQIA protection; the court treated records "kept in the ordinary course of business" or under state obligation as non-PSWP.
   - *Baptist Health Richmond v. Agee* (Kentucky 2016) softened Tibbs with a more workable "dual purpose" analysis, but the lesson stands.
   - HHS's **2016 guidance on external obligations** codifies the fix: maintain information needed for state/federal reporting **outside the PSES** (or drop it out of the PSES before reporting to the PSO), and keep the PSES pathway for genuinely voluntary safety analysis.
3. **Narrow statutory exceptions** exist (criminal proceedings after in-camera review, HHS enforcement, anti-retaliation suits by reporters), and some state courts are hostile — the privilege is strong but not absolute, and PSES documentation discipline is what makes it hold up.

## 4. Mapping it onto the product

The architecture that follows from all of this:

```
DISCOVERABLE LAYER (by design)          PRIVILEGED LAYER (PSWP)
─────────────────────────────           ────────────────────────────────
The EHR chart itself                    The clinician's flag
  - the note, addenda, orders           The risk-assessment reasoning
  - audit trail metadata                The coaching dialogue/transcript
                                        The inconsistency-audit findings
Clinician writes/attests every          Aggregate analytics, benchmarks
chart entry themselves                  PSO feedback reports
        ▲                                        │
        │  clinician acts on prompts             │ collected in provider's
        │  (elicitation-only)                    │ PSES → reported to PSO
        └────────── the product ─────────────────┘
```

- **The flag, the coaching session, and the inconsistency audit run inside the provider's PSES**, under written PSES policies naming the software as part of the system, with the data flowing to an AHRQ-listed PSO. That makes the deliberation layer PSWP: a plaintiff attorney cannot discover *that* the case was flagged, *why*, or *what the coaching discussed*.
- **The chart gets better in the open.** The clinician — not the tool — writes or explicitly attests every chart entry, at draft time, before signature. The improved note and its clean audit trail are discoverable and *meant to be seen*. The line between the layers is also the falsification guardrail: nothing enters the chart except the clinician's own attested statements.
- **State-mandated incident reporting stays out of the product's pathway.** If an event also triggers a mandatory state report, that report is generated through the hospital's separate existing channel — never through the PSES flow (the Tibbs/Charles trap).
- **The company either becomes a listed PSO (or component PSO) or contracts with one.** The Rule permits PSOs and providers to use contractors within the PSES, so the software vendor can operate as a contractor to the provider's PSES and/or the PSO. Becoming the PSO ourselves maximizes control and makes the privilege a product feature; AHRQ listing is procedurally light (self-certification) but carries operational obligations (two bona fide contracts with providers within 24 months, confidentiality compliance, separation rules for component PSOs).
- **For independent physicians and small groups** (no hospital PSES): bundle PSO membership with the subscription and template PSES policies for the practice — this is exactly the segment where a turnkey privilege wrapper is most valuable, since they have no risk-management department at all.

## 5. Why this is a moat and a sales feature

- A competitor that ships a "flag this risky case" button **without** this structure manufactures discoverable evidence against its own users — arguably worse than no product. Privilege engineering is invisible in a demo but decisive in diligence by hospital counsel.
- Hospital CISOs/GCs and malpractice defense counsel will understand instantly; "our deliberation layer is PSWP inside your PSES" answers the first hostile question every risk manager will ask.
- The PSO relationship also legitimizes the data flywheel: aggregate, de-identified learning across providers is exactly what PSOs exist to do, giving the v2 learned-flagging roadmap a lawful, purpose-built data pathway.

## 6. Open questions for counsel

1. Vendor-as-PSES-contractor vs. company-as-PSO vs. both — optimal structure, and component-PSO separation requirements if we also sell adjacent analytics.
2. Whether coaching output that the clinician *copies into the chart* risks dragging PSES material out of privilege (design answer: elicitation-only, clinician authorship — but confirm).
3. State-by-state overlay: where state peer-review privilege can be stacked on top of PSQIA for belt-and-suspenders coverage.
4. The insurer channel: carriers can't be PSOs; structure of any carrier partnership so PSWP never flows to underwriting (which would both breach confidentiality and poison the well with clinicians).

---

## Sources

- [42 CFR Part 3 (eCFR): Patient Safety Organizations and Patient Safety Work Product](https://www.ecfr.gov/current/title-42/chapter-I/subchapter-A/part-3)
- [HHS: Understanding Confidentiality of Patient Safety Work Product](https://www.hhs.gov/hipaa/for-professionals/patient-safety/index.html)
- [AHRQ PSO program: PSQIA resources](https://pso.ahrq.gov/resources/psqia) · [Patient Safety Rule overview](https://pso.ahrq.gov/resources/rule)
- [HHS 2016 Guidance: PSWP and Providers' External Obligations (Federal Register)](https://www.federalregister.gov/documents/2016/05/24/2016-12312/patient-safety-and-quality-improvement-act-of-2005-hhs-guidance-regarding-patient-safety-work)
- [Hancock Daniel on Charles v. Southern Baptist (FL 2017)](https://hancockdaniel.com/2017/02/florida-supreme-court-reverses-charles-decision-holding-psqia-protection-not-apply-documents-required-state-law/) · [Hancock Daniel on Baptist Health Richmond v. Agee (KY 2016)](https://hancockdaniel.com/2016/09/kentucky-high-court-disregards-prior-tibbs-decision-confirms-preemption-integrity-federal-privilege-documents-residing-providers-pses-long-external-requirements-otherwis/) · [SCOTUSblog: Tibbs v. Bunnell](https://www.scotusblog.com/case-files/cases/tibbs-v-bunnell/)
- [McBrayer: Patient Safety Work Product — what is privileged?](https://www.mcbrayerfirm.com/blogs-professional-malpractice-and-liability,patient-safety-work-product-what-is-privileged) · [AMA on discovery of patient-safety information](https://www.ama-assn.org/health-care-advocacy/judicial-advocacy/court-rules-patient-safety-info-subject-litigation-discovery)
