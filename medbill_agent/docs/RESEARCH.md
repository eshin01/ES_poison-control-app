# Research memo: patient-side medical bill negotiation and the agents that do it

Date: November 2, 2026. Prepared as the design basis for the MedBill agent in this folder.

Confidence labels used below: (fact) means sourced to a primary document or a direct quote from one; (deduction) means inferred from several secondary sources that agree; (speculation) means a reasonable guess that needs checking. Direct fetches of cms.gov, law.cornell.edu, and dollarfor.org were blocked by this session's network policy, so regulatory details rely on search excerpts and prior knowledge of the rules and are labeled accordingly.

## 1. Who already does this

The market splits into three groups: AI products that negotiate directly with providers, human advocacy services that charge a share of savings, and tools that attack the insurer side (denials) rather than the hospital bill.

AI, patient side

- Pine AI (19pine.ai) sells a general consumer agent that calls companies on the user's behalf; medical bill reduction is one offering. Its own materials say it charges a 25 percent success fee after savings are confirmed and places a hold on the card for the estimated fee for up to seven days. It claims a 93 percent negotiation success rate and over $3 million saved. Those numbers are self-reported (fact that they are claimed; speculation as to accuracy). [1][2]
- Avelis Health, founded February 2025, took a $500,000 Y Combinator pre-seed. Its agents review bills for errors, compare them against a database of hospital rates, and contact providers or insurers. Press coverage cites one patient whose debt fell by $250,000. No fee structure was found. (fact as to funding and description; the outcome is a company anecdote.) [3][4]
- Goodbill uses automation and machine learning to find mistakes and then negotiates. Its help center lists a fee of 20 percent of savings, charged only when a settlement is reached; a third-party guide says the fee caps at $1,000. [5][6]
- Counterforce Health (Research Triangle Park) is free, grant-funded, and drafts insurer appeal letters from an uploaded denial; a voice agent follows up by phone. Leaders cite 70 to 75 percent success. This is denial appeals, not hospital bill negotiation, but the voice follow-up pattern is directly reusable. [7][8]
- The best-known 2025 case was not a product. A Threads user posted in late October 2025 that Claude had audited a $195,000 four-hour ICU bill after a relative's death, flagged duplicate charges and inpatient codes used for an emergency encounter, and helped write an appeal demanding Medicare-level payment. The bill fell to about $33,000. Tom's Hardware and others reported it without independent verification. [9][10]

Human services, contingency fee

- Resolve Medical Bills: 10 to 25 percent of savings, tiered; one 2026 comparison cites a 70 percent success rate. [11][12]
- Dollar For: a nonprofit that screens patients for hospital charity care and helps them apply. Free. It appears in comparison guides as the charity-care specialist. [11][12]

Provider side (the counterparty's tooling)

- Cedar deployed an AI voice agent to answer patient billing questions for hospitals. AgentAI sells agents that work hospital denials. Expect the billing office you call to be staffed, in part, by software that reads from the chargemaster. [13]

What is missing in the market (deduction): no product combines all four levers in one loop: coding audit, public price benchmarks (Medicare and the hospital's own transparency file), financial assistance screening under 501(r), and the No Surprises Act dispute process. Each existing player leans on one or two. No maintained open-source implementation was found; the closest is a hackathon repo (BillBuddy) that compares a photographed bill to hospital pricing data. [14]

## 2. How a hospital bill is built

The chargemaster is the hospital's master price list. Every billable item maps to a CPT or HCPCS code, a four-digit UB-04 revenue code, and a gross charge. Gross charges are list prices nobody with insurance pays; they matter because self-pay patients are billed from them. (fact) [15][16]

The claim the hospital sends an insurer is the UB-04 (CMS-1450) for facility charges, which summarizes by revenue code; individual items do not appear on it. Physician services go on a separate CMS-1500. This is why a patient receives two or more bills for one visit, and why the summary statement mailed to patients cannot be audited. The itemized statement, which lists every line with its code, is a separate document the patient has to request. (fact) [16][17]

An explanation of benefits from the insurer shows, per service, what was billed, what the plan allowed under contract, what the plan paid, and the patient's share. For an in-network provider the allowed amount is the ceiling; a patient statement that exceeds the EOB patient responsibility is either an unposted payment or balance billing. (deduction from contract structure)

Error rates. The figure "nearly 90 percent of hospital bills contain errors" traces to Medliminal Health Solutions and counts minor mistakes. Equifax audits found an average error of $1,300 on bills over $10,000. The American Medical Association's 2013 claims analysis put the error rate near 7 percent at the claim level. The spread comes from different definitions; the honest statement is that line-level errors are common on large itemized bills and claim-level errors are less so. (deduction) [18][19]

The errors that recur: duplicate charges; charges for canceled tests; unbundling (billing a component separately from a panel or procedure that includes it); upcoding (a higher ED level or a more complex procedure than documented); wrong patient or date; routine supplies (gloves, tubing, kits) billed as separate lines when Medicare's cost-reporting rules fold them into the room or procedure charge; observation hours that exceed the possible hours; room and board on the discharge day; drugs marked up far above acquisition cost. (deduction) [18][20]

Public benchmarks exist for every coded line. CMS publishes Medicare payment rates by code (OPPS for outpatient facility, the physician fee schedule, the clinical lab fee schedule, drug average sales price). Since 2021, 45 CFR 180 requires every hospital to post a machine-readable file listing, for each item, the gross charge, the discounted cash price, each payer's negotiated rate, and the de-identified minimum and maximum. From January 1, 2026, CMS replaced the "estimated allowed amount" field with new allowed-amount elements and requires organizational NPIs; the file must be linked from a footer on the homepage and discoverable through a cms-hpt.txt file at the site root. Enforcement of the 2026 elements begins April 1, 2026. (fact) [21][22][23]

Markup. A Johns Hopkins group led by Ge Bai has shown that the cash price is frequently below some negotiated commercial rates. A Trinity College analysis of transparency files found 41 to 57 percent of negotiated rates were above the hospital's cash price for the same item. For an uninsured patient this means the cash price in the file is often the right anchor, and the minimum negotiated rate is a defensible floor. (fact as to studies; deduction as to tactic) [24][25]

## 3. How patients get bills reduced or dismissed

Four levers, in the order that works.

Lever 1: records and itemization. Ask in writing for the itemized statement with codes, the UB-04, and the medical record. The HIPAA right of access (45 CFR 164.524) obliges the provider to produce records within 30 days. Medicare beneficiaries have a statutory right to a free itemized statement. Several states (Colorado, Texas, New York, Maryland among them) have their own itemization rules; a viral claim that every state does is false. Most billing offices hold collection activity while a written review request is open. (fact as to HIPAA and Medicare; deduction as to hold behavior) [26][27]

Lever 2: dispute coding errors. The NCCI procedure-to-procedure edit tables and Medically Unlikely Edits are public CMS files that define which code pairs cannot be billed together and the maximum units per day. Commercial payers largely follow them. A line that violates an edit is a strong, citable dispute. CMS's own guidance says the tables are not exhaustive and providers must still code correctly where no edit exists, so a correct-coding argument stands even without a listed edit. (fact) [28]

Lever 3: financial assistance. Every 501(c)(3) hospital must have a written financial assistance policy (26 CFR 1.501(r)-4), may not charge an eligible patient more than the amounts generally billed to insured patients (1.501(r)-5), and must make reasonable efforts to determine eligibility before any extraordinary collection action such as credit reporting, suit, or selling the debt (1.501(r)-6). The regulation sets a 120-day quiet period after the first post-discharge statement before extraordinary collection and requires applications to be accepted for at least 240 days. The 120 and 240 figures are from the regulation as recalled and were not re-verified against the text today. (fact as to the structure; verify the day counts) [29][30]

The gap here is large. KFF cites nonprofit hospitals' own 2019 estimate that about $2.7 billion of reported bad debt came from patients who were likely eligible for charity care and never got it. A University of Michigan study found only about 40 percent of hospitals notify patients of eligibility before collecting. The Lown Institute's review of 2,500 policies describes a patchwork; 200 percent of the federal poverty level for free care and 400 percent for discounts are common designs but not universal. (fact as to sources) [31][32][33]

Lever 4: the No Surprises Act. Insured patients owe only in-network cost sharing for emergency care and for out-of-network ancillary clinicians at in-network facilities. Uninsured and self-pay patients who were given a good faith estimate and then billed at least $400 more by a provider can file a patient-provider dispute within 120 days; during the dispute the provider may not send the bill to collections, must pause existing collections, may not add late fees, and may not retaliate. A small filing fee is refunded if the patient prevails. (fact; verify the current fee) [34][35]

Then negotiate. Secondary sources agree on tactics and disagree on results. Anchor to Medicare (often 100 to 125 percent) or to the hospital's cash price; offer a lump sum for a steep discount; ask for a zero-interest plan; ask for the hospital's self-pay discount, which is typically automatic once requested. Reported outcomes range from 20 to 40 percent off (a Colorado hospital association figure for uninsured patients) to vendor claims of 40 to 80 percent. Treat the high end as marketing. (deduction) [36][37]

Credit reporting. A CFPB rule that would have removed medical debt from credit reports was vacated on July 11, 2025 in Cornerstone Credit Union League v. CFPB (E.D. Tex.). The three bureaus continue their voluntary 2023 policy: paid medical collections and medical collections under $500 are not reported, and unpaid ones wait a year. Fifteen states have their own bans; whether the ruling reaches them is unsettled. (fact as to ruling and policy; speculation as to state-law status) [38]

## 4. Design implications for the agent

1. Deterministic rules first, model second. Duplicates, unit ceilings, bundling pairs, date logic, and EOB reconciliation are checkable without a language model, which makes the findings reproducible and testable. The model reads the bill, writes to the provider, and reasons about counteroffers.
2. Separate legal remedies from line-item disputes. A good faith estimate overage is a remedy with its own process; it should not be summed into "errors found."
3. Benchmark against two things the hospital already accepts: Medicare and its own transparency file.
4. Screen for assistance before settling. The anchor for an eligible patient is zero, and the fallback plan is the uninsured cash-price negotiation.
5. Keep a human on every outbound action. The agent drafts and requests approval; it does not send.
6. Label confidence on every finding and carry the label into the letter. A speculative finding (ED level) should never lead a dispute.

## 5. Open items to verify before real use

- The 120-day and 240-day 501(r) periods (26 CFR 1.501(r)-6(c)).
- The current patient-provider dispute filing fee on cms.gov.
- 2026 federal poverty guidelines; the code ships 2025 values.
- State protections in medbill/data/state_protections.json marked verify=true.
- Replace the illustrative Medicare rates with the current OPPS Addendum B and PFS files.

## Sources

[1] Pine AI, hospital and medical negotiation page, https://www.19pine.ai/hospital-and-medical-negotiation
[2] Pine AI, bill negotiation fee terms, https://www.19pine.ai/blog/pine-bill-negotiation
[3] People of Color in Tech, "Y Combinator Invests $500K In AI Startup Helping Americans Save Money On Medical Bills," June 2025, https://peopleofcolorintech.com/articles/y-combinator-invests-500k-in-ai-startup-helping-americans-save-money-on-medical-bills/
[4] AfroTech, "Avelis Health secures $500K boost," https://afrotech.com/avelis-health-secures-500k-boost
[5] Goodbill help center, "How much does it cost?", https://help.goodbill.com/en/articles/254209
[6] Goodbill, "The Goodbill Process," https://help.goodbill.com/en/articles/237889
[7] Axios Raleigh, "RTP startup uses AI to fight health insurance denials," Aug 20, 2025, https://www.axios.com/local/raleigh/2025/08/20/using-ai-to-fight-back-against-insurance-denials-counteforce
[8] CBS17, "Raleigh organization helps thousands of Americans appeal health insurance denials using AI," https://www.cbs17.com/news/local-news/wake-county-news/raleigh-organization-helps-thousands-of-americans-appeal-health-insurance-denials-using-ai/amp/
[9] TechSpot, "Family turns to AI to audit $195,000 hospital bill, reducing it to $33,000 after uncovering errors," https://www.techspot.com/news/110064-family-turns-ai-audit-195000-hospital-bill-reducing.html
[10] Gigazine, "Using AI to negotiate hospital bill down," Oct 29, 2025, https://gigazine.net/gsc_news/en/20251029-using-ai-negotiate-hospital-bill-down
[11] CareRoute, "Best Medical Bill Negotiation Services Compared (2026)," https://www.careroute.ai/bill-defense/compare-medical-bill-negotiation-services
[12] CoveredUSA, "Medical bill negotiation services compared," https://coveredusa.org/en/blog/medical-bill-negotiation-services-compared
[13] Fierce Healthcare, "Cedar rolls out AI voice agent to tackle patients' medical billing questions," https://www.fiercehealthcare.com/ai-and-machine-learning/cedar-rolls-out-ai-voice-agent-tackle-patients-billing-questions
[14] BillBuddy (GitHub), https://github.com/rushil1356/BillBuddy
[15] IntuitionLabs, "Hospital Chargemaster Explained," https://intuitionlabs.ai/videos/en/veeva/hospital-chargemaster-explained
[16] Goodbill, "UB-04s explained," https://help.goodbill.com/en/articles/227393
[17] Resolve Medical Bills, "Itemized Hospital Bills," https://www.resolvemedicalbills.com/guides/itemized-hospital-bill
[18] Becker's Hospital Review, "Nearly 90% of hospital bills contain errors, study finds," https://beckershospitalreview.com/finance/nearly-90-of-hospital-bills-contain-errors-study-finds.html
[19] Etactics, "Over 20 Woeful Medical Billing Error Statistics," https://etactics.com/blog/medical-billing-error-statistics
[20] CMS Provider Reimbursement Manual Part 1, chapter 22 (routine services and supplies)
[21] CMS, Hospital Price Transparency, https://www.cms.gov/PRIORITIES/KEY-INITIATIVES/HOSPITAL-PRICE-TRANSPARENCY
[22] CMS MLN fact sheet, hospital price transparency, https://cms.gov/files/document/mln7215754-hospital-price-transparency.pdf
[23] Penn State Office of Rural Health, "Hospital Price Transparency: Enforcement of 2026 Requirements Starts April 1," https://www.porh.psu.edu/hospital-price-transparency-enforcement-of-2026-requirements-starts-april-1/
[24] Johns Hopkins Carey Business School, Ge Bai on cash prices vs copays, https://carey.jhu.edu/articles/hospital-care-cost-less-cash-copay
[25] Trinity College, "Hospitals Often Charge More to Insured than Uninsured for Same Services," https://trincoll.edu/?p=9237
[26] VERIFY (NewsCenter Maine), itemized bill request fact check, https://newscentermaine.com/article/news/verify/health-verify/hospital-itemized-bill-request-national-state-viral-video-tik-tok-fact-check/536-7e2221fa-4dd0-4949-ab63-a95322fe63b5
[27] CareRoute, "State Medical Bill Rights & Protections," https://www.careroute.ai/states
[28] CMS, Medicare NCCI FAQ library and policy manual, https://www.cms.gov/ncci-medicare/medicare-ncci-faq-library
[29] 26 CFR 1.501(r)-1 definitions, https://www.law.cornell.edu/cfr/text/26/1.501(r)-1
[30] Hall Render, "501(r) compliance: final regulations takeaways, part two," https://hallrender.com/2015/01/16/501r-compliance-noteworthy-final-regulations-takeaways-part-two/
[31] KFF, "Hospital Charity Care: How It Works and Why It Matters," https://www.kff.org/
[32] Fierce Healthcare, "Bad debt is reclassified as charity care, but many patients remain in dark," https://www.fiercehealthcare.com/finance/more-bad-debt-reclassified-as-charity-care-but-many-patients-remain-dark
[33] Lown Institute, "Inconsistent Hospital Policies Put Patients at Greater Risk of Medical Debt," https://lowninstitute.org/press-release-inconsistent-hospital-policies-put-patients-at-greater-risk-of-medical-debt/
[34] CMS, "Providers: what to expect when a patient starts payment dispute resolution," https://www.cms.gov/nosurprises/providers-payment-resolution-with-patients
[35] Congressional Research Service, IF12338, "The Federal Patient-Provider Dispute Resolution Process," https://www.everycrsreport.com/reports/IF12338.html
[36] BizWest, "Uninsured patients negotiate final hospital bill," https://bizwest.com/?p=314725
[37] Newsweek, "Uninsured American saves $22,000 by negotiating medical bill," https://www.newsweek.com/health-insurance-uninsured-medical-bill-negotiation-american-saves-12079557
[38] ABA Banking Journal and KATV, "Federal judge kills CFPB rule that banned medical debt in credit reports," July 2025, https://bankingjournal.aba.com/?p=60010
