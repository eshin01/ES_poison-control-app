# Assessment: QI / Documentation-Analytics Pivot (vs. the Med-Legal Wedge)

**Research date:** August 2026
**Question evaluated:** Instead of (or alongside) legal protection, build department-level documentation analytics — e.g., sepsis and stroke record quality, guideline-landmark compliance — plus a cross-hospital shared platform for comparisons and improvement strategies. Does Epic/EMR analytics already cover this? Is there room for a shared benchmarking platform?

---

## TL;DR

This pivot walks out of the whitespace and into the most contested territory in healthcare IT. Every layer of the idea has an entrenched, well-funded incumbent: Epic (Slicer Dicer + Cosmos) for self-service and cross-hospital analytics, a mature multi-billion-dollar CDI industry (Solventum, Iodine, Nuance/Microsoft, Optum) for AI documentation review, CMS/registry infrastructure (SEP-1, Get With The Guidelines) for condition-specific documentation compliance, and Vizient/Premier PINC AI for cross-system benchmarking — plus a new generation of LLM chart-abstraction startups (notably Layer Health) attacking the remaining manual-abstraction gap. The defensibility/med-legal lens from the earlier thesis remains the differentiated core; QI analytics is best treated as an expansion module built on the same engine, not the wedge.

---

## 1. Does Epic already provide enough analytics? Mostly yes — for structured data

- **Slicer Dicer** is exactly "divide documentation by department and run analytics": a self-service exploration tool for physicians and department managers with filters, cohorts, trends, and percentage/variance measures. Every Epic shop already has it.
- **Epic Cosmos** is the part many people underestimate: a shared research/analytics dataset pooling **1,500+ hospitals and 34,000+ clinics** across the Epic community — billions of encounters, queryable through the same Slicer Dicer interface for national comparisons. The "shared platform across multiple hospital systems" you describe *already exists inside Epic* at a scale no startup can replicate, and participation is essentially free for Epic customers.
- Beneath those sit Reporting Workbench, Cogito/Caboodle (the enterprise data warehouse), and Epic's quality-measure dashboards.

**Epic's real gap:** all of this runs on *structured* data — orders, timestamps, flowsheets, diagnosis codes. Epic's analytics say "antibiotics given at hour 4" but not "the note never documents the clinical reasoning for delayed antibiotics" or "the narrative contradicts the flowsheet." Analytics on the *narrative quality* of documentation is genuinely underserved by Epic itself — but it is not unclaimed (see CDI, below).

## 2. The condition-specific documentation-quality idea collides with three existing industries

**a) CDI (Clinical Documentation Integrity) — the direct occupant.** A mature market (8%+ CAGR, multi-billion) of AI/NLP products that review documentation and query physicians to improve it: **Solventum (ex-3M) 360 Encompass / CDI Collaborate, Iodine Software (AI unicorn, AwareCDI), Nuance/Microsoft CDE One, Optum, CorroHealth**, etc. Critical nuance: CDI's center of gravity is **revenue** — DRG/CC-MCC capture, coding compliance — not clinical quality or defensibility. But the pipes (NLP over notes, physician queries, department dashboards) are the same, and CDI vendors increasingly market "quality" modules. Any pitch of "AI that reviews notes by department" will be heard by hospital CFOs as "CDI, which we already own."

**b) CMS measures and registries — the condition-specific layer already exists.** For your two examples:
- **Sepsis:** SEP-1 is a CMS measure (pay-for-performance under Hospital VBP since 2024). Hospitals already run quarterly manual chart abstraction, and documentation-improvement education for SEP-1 compliance is an established niche (Sepsis Alliance courses, published QI studies moving compliance 54%→77% with documentation aids).
- **Stroke:** AHA **Get With The Guidelines** – Stroke is a national registry benchmarking program most stroke centers participate in, with documentation-driven abstraction at its core.
- The burden here is real but the shape of the demand is **abstraction automation**, and LLM startups are already on it — **Layer Health** (MIT spinout) sells LLM-based chart review for quality-measure abstraction and registries, and is named alongside Solventum/Optum/Iodine in enterprise evaluations.

**c) Cross-system benchmarking platforms.** **Vizient Clinical Data Base** and **Premier PINC AI** (claims 45% of US hospital discharges, 20+ years of data, AI-selected peer cohorts, by-name hospital comparisons) are the incumbent "compare and improve across systems" products, sold through GPO relationships nearly every hospital already has. Add Epic Cosmos and the improvement-collaborative world (IHI, Solutions for Patient Safety, state sepsis collaboratives) for the "share improvement strategies" half.

## 3. What's actually still open in the QI direction

1. **Narrative-quality analytics** (as opposed to structured-measure compliance): scoring the *reasoning, completeness, and internal consistency* of free-text documentation at department/condition level. CDI touches this only where revenue is at stake; Epic barely touches it. This is real whitespace — and it is **exactly the same engine as the defensibility product** (the inconsistency audit, generalized).
2. **The documentation-gap → education loop.** "Your ED's sepsis notes systematically omit reassessment rationale — here's the targeted micro-education (CME-accredited) for that gap, and here's the premium-discount/QI credit it earns." Nobody found couples gap detection to accredited education; malpractice carriers already discount premiums for CME, which ties this back to the med-legal channel. (Note: worth distinguishing CMS measures from CME credits — the compliance landmarks are CMS/registry constructs; CME is the education currency. The loop uses both.)
3. **Cross-system sharing specifically of documentation-quality benchmarks** — Cosmos/Vizient/Premier benchmark outcomes and utilization, not note quality. A "documentation defensibility/quality index" benchmarked across systems would be novel — but only sellable once the note-scoring engine has credibility, and it faces the cold-start problem every multi-hospital network product has.

## 4. Recommendation

**Don't swap the wedge; sequence it.** The QI/analytics framing as a *standalone entry* is a red ocean: Epic + CDI + Vizient/Premier + Layer Health each already own a piece, all with distribution advantages. The med-legal defensibility product from the v2 thesis remains the differentiated entry point — no incumbent owns it, the buyer's pain is acute and personal, and the PSQIA/PSO structure gives it a legal moat.

The QI direction then falls out almost for free as the expansion:
- The same narrative-analysis engine that audits a flagged encounter for inconsistencies can run in aggregate across departments → the documentation-quality analytics product (module 2).
- The PSO structure from the privilege architecture is *literally designed* for cross-provider aggregate safety learning — it is the lawful, pre-built pathway for the shared multi-hospital benchmarking platform (module 3), with privilege protection as the differentiator Vizient/Premier can't match for sensitive documentation-quality data.
- The gap→CME loop bridges both worlds and deepens the malpractice-carrier channel.

Sequence: **defensibility wedge → departmental documentation-quality analytics → PSO-mediated cross-system benchmarking.** Same engine, three products, each opening the door for the next — versus entering the QI market head-on against five incumbents with the engine's least differentiated application.

---

## Sources

- [Epic Cosmos](https://cosmos.epic.com/) · [Epic Healthcare Intelligence](https://www.epic.com/software/healthcare-intelligence/) · [UC Davis on Cosmos](https://health.ucdavis.edu/data/epic-cosmos.html) · [Slicer Dicer overview](https://www.mindbowser.com/understanding-epic-slicer-dicer/) · [UC Davis on SlicerDicer](https://health.ucdavis.edu/data/epic-slicer-dicer.html)
- [Top CDI software vendors 2026](https://www.rapidclaims.ai/blogs/top-clinical-documentation-improvement-software-vendors) · [CDI market forecast (MarketsandMarkets)](https://www.marketsandmarkets.com/Market-Reports/clinical-documentation-improvement-market-120216147.html) · [Iodine Software unicorn round (MedCity)](https://medcitynews.com/2021/12/new-private-equity-investment-makes-iodine-software-the-latest-healthcare-unicorn/) · [Nuance CDE One](https://www.nuance.com/healthcare/provider-solutions/clinical-documentation-improvement/cde-one.html) · [KLAS comments: Iodine AwareCDI](https://klasresearch.com/comments/iodine-software-awarecdi/192399)
- [Sepsis Alliance: documentation for SEP-1 compliance (CE)](https://learn.sepsis.org/products/strengthening-documentation-to-drive-sep-1-compliance-and-quality-performance-ce-session) · [SEP-1 documentation QI study (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12425435/) · [SEP-1 pay-for-performance 2024](https://caretakermedical.net/blog/sep1-hospital-vbp-program-2/) · [ED SEP-1 compliance improvement study (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9448659/) · [ACEP E-QUAL SEP-1 benchmarking guide](https://www.acep.org/siteassets/uploads/uploaded-files/acep/advocacy/federal-issues/equal/sep-1-data-submission-guide_.pdf)
- [Vizient Clinical Data Base](https://www.vizientinc.com/what-we-do/data-and-digital-solutions/clinical-data-base) · [PINC AI INsights launch](https://premierinc.com/newsroom/pinc-ai/pinc-ai-launches-insights) · [PINC AI peer-group benchmarking methodology](https://premierinc.com/newsroom/blog/create-better-peer-groups-with-new-pinc-ai-benchmarking-methodology) · [HFMA on Premier's AI platform](https://www.hfma.org/finance-and-business-strategy/benchmarking-and-forecasting/premiers-ai-platform-offers-a-data-driven-solution-for-medical-group-leaders/)
- Prior docs in this folder: `prior-art-and-competitive-landscape.md`, `riskscore-ai-comparison.md`, `product-thesis-clinician-flagged-coaching.md`, `psqia-pso-privilege-architecture.md`
