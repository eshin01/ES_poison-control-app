# RiskScore AI vs. Proposed Venture — Head-to-Head Comparison

**Research date:** August 2026
**Caveat on sourcing:** riskscoreai.com and app.riskscoreai.com did not resolve (DNS) from this research environment, so this analysis is built from search-index content of their marketing site and API docs page. Details should be verified with a live demo/teardown. The fact that the site may be unreliable is itself a (weak) signal of company maturity.

---

## What RiskScore AI actually is

From available material: a HIPAA-compliant, **patent-pending** platform, built on their "AI Clinical Scribe™" technology, that:

- **Scores clinical notes** for clarity, completeness, and compliance — evaluating structure, clinical rationale, follow-ups, consent, and documentation patterns.
- **Works "without accessing PHI"** — their signature design choice, marketed heavily to insurers.
- **Sells insurer-first:** portfolio-scale documentation risk audits so malpractice carriers can "measure risk, reduce litigation, and improve profitability," **flag at-risk providers**, and track trends for early intervention.
- **Physician-second:** AI feedback that "strengthens chart quality, reduces malpractice exposure, and saves time," plus real-time structured note generation.
- Tagline logic: "Every malpractice case hinges on one thing: the note."

No funding announcements, named founders, customer logos, or press coverage were found — it presents as very early stage (pre-seed/bootstrap profile).

---

## Dimension-by-dimension comparison

| Dimension | RiskScore AI | Your idea |
|---|---|---|
| **Core question answered** | "How defensible is this note?" | "Which *encounter* is likely to become a lawsuit — and how do I fortify its documentation *now*?" |
| **Unit of analysis** | The note; aggregated to the provider ("flag at-risk providers") | The patient encounter / unfolding clinical situation |
| **Timing** | Retrospective audit at scale; some real-time note generation | Prospective: detect elevated suit risk at/near point of care, intervene before the chart closes and before a claim exists |
| **Risk signal** | Documentation quality itself (structure, rationale, consent, completeness) | Lawsuit *likelihood* signals (bad outcomes, complaints, communication breakdown — the PARS-validated predictors) **plus** documentation quality |
| **Intervention** | Score + feedback + generated note | Agentic, case-specific coaching: what to document for *this* complication, *this* refusal of care, *this* angry family |
| **Primary buyer** | Malpractice insurers | Clinicians (MD/NP/PA) and health systems |
| **PHI stance** | Explicitly avoids PHI (eases insurer sales, no EHR integration needed) | Requires PHI + EHR/complaint-system integration (harder sales, deeper product) |
| **Data moat** | Scoring rubric (patent pending) | Encounter-level risk model fused with coaching outcomes; complaint + outcome + chart data |
| **Maturity** | Live product claims, but no funding/team/customer evidence found; site unreliable | Concept stage |

---

## The critical difference

**RiskScore AI grades the note. Your idea predicts the lawsuit.**

Their model treats documentation quality as the risk to be measured — a note is scored in isolation against a rubric, then rolled up to flag risky *providers* for their insurer customers. There is **no evidence they identify which specific patient encounters are likely to generate claims**, and their no-PHI architecture makes that structurally hard: you cannot detect "post-op complication + three angry portal messages + missed follow-up" if you refuse to see patient data. Their patent-pending method and their sales motion are both anchored to PHI-free note scoring.

Your first module — locating the encounters most likely to be named — is exactly what their architecture forecloses, and it's the half of the product with the strongest scientific validation (Vanderbilt PARS: complaints predict suits at ~81% concordance; suits cluster in ~3% of physicians and, by extension, in identifiable encounter types). Coaching triggered by *predicted suit risk* is far more clinically credible and attention-worthy than a generic quality score on every note: physicians ignore blanket documentation nagging, but "this case has lawsuit written on it — here's what your chart is missing" is a different conversation.

## Where they overlap (and the risks)

1. **The coaching layer overlaps directly.** "AI-driven feedback that strengthens chart quality and reduces malpractice exposure" is your module 2. Their **pending patent** on documentation risk scoring is the single biggest thing to investigate — if claims are broad (scoring notes for legal risk generally), it's an FTO issue; if narrow (their specific PHI-free scoring method), it's irrelevant to a PHI-native product.
2. **The insurer channel is contested.** They got to carriers first with a no-PHI pitch that insurers will find easy to buy (no BAA, no integration). If your go-to-market includes carriers subsidizing the tool, expect to meet them in deals.
3. **They validate the category** — which cuts both ways: easier to explain the market, but their "note score" framing could define the category cheaply before a deeper product arrives.

## Where you're structurally advantaged

- **Encounter-level prediction is defensible whitespace.** It requires PHI, EHR integration, and complaint-system data — all things they've architected away from. Matching their note-scoring feature later is easy for you; adding encounter prediction later is a rebuild for them.
- **Your buyer owns the data.** Health systems (your stated customer) control the EHR, the complaint/advocacy data, and get dragged into every suit — they have both the data your model needs and vicarious-liability incentive to pay. RiskScore's insurer-first model reaches physicians only indirectly.
- **Point-of-care timing.** A retrospective audit finds a bad note after the chart closed — often after the claim window opened. Coaching before signature is when documentation can still legitimately be improved (and after-the-fact "improvement" is exactly the spoliation trap to avoid).

## Recommended next actions

1. **USPTO search for their pending application** (search assignee/keywords: "RiskScore," documentation risk scoring, "AI Clinical Scribe") — determines how carefully your scoring layer must be designed around theirs.
2. **Demo their product** (site permitting) — verify whether "real-time" note generation includes any case-specific legal coaching, and whether "flag at-risk providers" involves any outcome/claims data or is purely note-derived.
3. **Position against them deliberately:** "note graders tell you your chart was weak; we tell you which patient is going to sue and make that chart strong before it matters."
4. **Decide the PHI question consciously** — it is the fork in the road that separates the two products. Their no-PHI stance is a sales hack that caps product depth; your PHI-native stance is a product moat that raises sales friction. The health-system channel resolves that tension in your favor.
