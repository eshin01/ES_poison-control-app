# Product Thesis v2: Clinician-Flagged, Real-Time Defensive Documentation Coaching

**Research date:** August 2026
**Refined thesis:** Rather than fully automated lawsuit prediction, the clinician (or care team) flags an encounter they sense is a liability risk. The agent then (1) provides near-real-time coaching while the note is being drafted — maximizing legal strength without falsifying — and (2) audits all documentation for that encounter for inconsistencies (physician vs. nursing notes, flowsheets vs. narrative, timeline gaps) that plaintiff attorneys exploit.

---

## Why the clinician-triggered design is the right call

1. **It sidesteps the hardest (maybe unsolvable) ML problem.** The Harvard Medical Practice Study line of research found a profound mismatch between negligent adverse events and actual claims — most negligent injuries never become claims, and many claims involve no negligence. Studies through the 1990s concluded reliable event-level claim prediction was not possible (AHRQ PSNet review). Later work (Studdert et al., NEJM 2016) succeeded at identifying claim-prone *physicians* (1% of physicians account for 32% of paid claims) but not claim-prone *encounters*. A physician-in-the-loop trigger replaces a brittle prediction model with distributed human judgment on day one — and generates the labeled training data (flagged encounters → eventual claim outcomes) that could make automated flagging feasible later. That data flywheel is the long-term moat.

2. **It maps onto existing behavior.** Hospitals already ask clinicians to file incident reports and notify risk management after concerning events. "Flag this encounter" is a lighter-weight version of a workflow clinicians already know — except this one gives them something back immediately (help with the chart) instead of just creating committee work. That reciprocity should drive adoption in a way incident reporting never achieved.

3. **It sharpens the RiskScore AI differentiation.** They score every note shallowly for insurers. This design activates deeply on the encounters that matter, at the moment of drafting, for the clinician. Different trigger, different depth, different buyer, different moment in time.

## The inconsistency audit is the killer feature

Cross-document contradiction is a primary plaintiff attack vector: nursing notes that contradict the physician narrative, vital-sign flowsheets that don't match "patient stable," copy-paste artifacts, reassessments that never happened, timeline gaps around the critical event. Plaintiff-side AI (Justpoint, Darrow, the record-review platforms) explicitly hunts for these "red flags." No product found does this **prospectively, before the chart closes, for the defense**. Running the same adversarial review plaintiff attorneys will run — but 30 minutes after the encounter instead of 3 years — is a genuinely novel and defensible capability. Frame it internally as "adversarial self-review."

---

## Two legal constraints that must shape the architecture

### 1. The EHR audit trail is discoverable — timing is everything

Courts routinely compel production of EHR audit trails/metadata showing who wrote, edited, and viewed what, and when ([DCBA](https://www.dcba.org/mpage/v34-Saira-Pasha), [Comperio Legal](https://comperiolegal.com/resources/legal-strategies-for-discovering-emr-metadata-audit-trails/), [plaintiff-side motion templates](https://walshwoodard.com/blog/draft-motion-to-compel-production-of-audit-trail/)). Documented cases show defenses destroyed by a note modified three days after a patient's death — during the window when the family requested records — and by backdated shift notes.

**Design consequences:**
- Coaching must operate **at draft time, before signature** — that is ordinary, contemporaneous documentation and is unimpeachable in the audit trail.
- The product must **hard-refuse post-signature "improvement"** of existing notes. Any post-event additions must go through proper addendum discipline: clearly labeled, accurately dated, never altering the original entry. Build this as an enforced guardrail, not a guideline — it protects the user *and* the company.
- This constraint is also a moat: retrospective note-scoring products (RiskScore AI's audit posture) structurally arrive *after* the chart closes, when legitimate improvement is no longer possible. Draft-time is the only window where the product can act; owning that window is the product.

### 2. The flag itself is discoverable unless privilege is engineered

"Dr. Shin flagged this case as a lawsuit risk, then an AI helped strengthen the chart" is a plaintiff attorney's dream exhibit — *unless the flag and coaching layer are privileged*. Key facts:

- All 50 states + DC have peer-review privilege statutes, but scope varies enormously ([50-state survey, Butler Snow](https://www.butlersnow.com/wp-content/uploads/pdfs/attorney_publications/case-law-a-fifty-state-survey-of-the-medical-peer-review-privilege.pdf)). Incident reports and risk-management documents created **outside a formal peer-review process are frequently held discoverable** (e.g., Pennsylvania courts limit protection to formal peer review; risk-management/claims-defense documents excluded).
- The federal **Patient Safety and Quality Improvement Act (PSQIA)** creates a stronger, uniform privilege for "Patient Safety Work Product" — but only for data assembled within a **Patient Safety Evaluation System (PSES)** reporting to a federally listed **Patient Safety Organization (PSO)**.
- The medical record itself is never privileged — and doesn't need to be. The *chart* should be better because of the tool; the *deliberation layer* (the flag, the risk reasoning, the coaching dialogue, the inconsistency findings) is what needs protection.

**Design consequences:**
- Architect the flag + coaching + audit layer as PSWP inside a PSES from day one; consider partnering with or becoming a listed PSO. This is a genuine barrier to entry — competitors bolting on a "flag" feature without privilege engineering create discoverable evidence against their own users.
- For health-system deployments, route the feature through the risk-management/quality structure that qualifies for state peer-review privilege in that state. Privilege becomes a *sales feature*: "our flag is protected; a homegrown one is discoverable."
- For independent physicians (no hospital PSES), the analysis is harder — PSO membership for small practices exists and could be bundled with the product.

## "Without falsifying" as enforced product design

The integrity constraint should be architectural, not aspirational — it is also the defense against the chart-polishing/spoliation optics:

- **Elicitation-only coaching:** the agent asks the clinician what happened and prompts for legitimately omitted content — the informed-consent conversation, the differential considered and why alternatives were rejected, the patient's refusal or nonadherence, the follow-up plan, the reassessment that occurred but wasn't charted. It never generates or suggests clinical facts.
- Every inserted element traces to an explicit clinician assertion (attestation trail — which, being privileged if PSWP, protects rather than exposes).
- Marketing frame follows the same line: this is **complete, accurate, contemporaneous documentation** — which is genuinely also a patient-safety and care-continuity good, not just a legal one. Candello's finding (documentation failures in 20% of claims, 140% higher indemnity odds) supports the claim that better documentation is better medicine, not chart cosmetics.

## Honest limits of the physician's gut (and the roadmap answer)

The clinician-trigger bet has a known weakness: clinicians' liability intuition is good but incomplete. Hickson's work shows claim-prone physicians often *lack insight* into the communication breakdowns driving their risk — the doctor most likely to be sued may be least likely to flag. Many suits also surprise the physician entirely (routine-seeming encounters, delayed-diagnosis claims that crystallize years later). Mitigations, in roadmap order:

1. **v1:** anyone on the care team can flag (nurses often sense it first), plus risk managers.
2. **v1.5:** cheap deterministic triggers — unexpected death/ICU transfer, return-to-OR, AMA discharge, complaint filed, records request received.
3. **v2:** learned flagging from the accumulating flag→outcome dataset and complaint-stream signals (the PARS-validated predictor) — sold to health systems that own that data.
4. Keep an always-on light-touch documentation pass (the RiskScore-like layer) as tailwind coverage for the unflagged misses.

## Regulatory note

A documentation-quality tool triggered by clinician judgment, making no diagnostic or treatment recommendations and no outcome predictions, sits well clear of FDA device territory (administrative/documentation support). The v2 automated-flagging roadmap step deserves a regulatory re-check when it arrives, but the v1 design is clean — one more advantage of the human-triggered architecture.

---

## Sources

- [AHRQ PSNet: adverse-event detection to predict claims](https://psnet.ahrq.gov/resources/resource/28956/designing-highly-reliable-adverse-event-detection-systems-to-predict-subsequent-claims) · [Harvard Medical Practice Study III (NEJM 1991)](https://www.nejm.org/doi/full/10.1056/NEJM199107253250405) · [Studdert et al., claim-prone physicians (NEJM 2016)](https://www.nejm.org/doi/full/10.1056/NEJMsa1506137) · [AHRQ PSNet: doctors with multiple claims](https://psnet.ahrq.gov/perspective/doctors-multiple-malpractice-claims-disciplinary-actions-and-complaints-what-do-we-know)
- [DCBA: Audit Trails, the Not-So-Silent Witness](https://www.dcba.org/mpage/v34-Saira-Pasha) · [Comperio: discovering EMR metadata](https://comperiolegal.com/resources/legal-strategies-for-discovering-emr-metadata-audit-trails/) · [Walsh Woodard: motion to compel audit trail](https://walshwoodard.com/blog/draft-motion-to-compel-production-of-audit-trail/) · [Lexcura: how audit trails make or break cases](https://www.lexcura-summit.com/medical-legal-blog/how-ehr-audit-trails-can-make-or-break-a-case)
- [Butler Snow: 50-state peer-review privilege survey](https://www.butlersnow.com/wp-content/uploads/pdfs/attorney_publications/case-law-a-fifty-state-survey-of-the-medical-peer-review-privilege.pdf) · [McGuireWoods: five things on peer-review privilege](https://www.mcguirewoods.com/client-resources/alerts/2023/7/five-things-healthcare-providers-peer-review-privilege/) · [IOM/To Err Is Human: protecting reporting systems from discovery](https://www.ncbi.nlm.nih.gov/books/NBK225185/) · [Barley Snyder: erosion of self-review privileges](https://www.barley.com/missed-opportunity-by-the-supreme-court-to-address-the-erosion-of-hospital-selfreview-privileges/)
- Prior docs in this folder: `prior-art-and-competitive-landscape.md`, `riskscore-ai-comparison.md`
