# Simulation: ED visit for abdominal pain, laparoscopic cholecystectomy

Synthetic bill, rule-based hospital model, four coverage scenarios. The hospital's behavior follows the assumptions in `HOSPITAL_POLICY` (acceptance rates by finding confidence, self-pay discounts, a typical nonprofit financial assistance policy). Dollar outcomes are expected values under those assumptions, not measured results.

Bill: 48 lines, gross charges $104,458, 2026-10-06 to 2026-10-08. Planted errors: duplicate CT and pathology, unbundled hepatic panel / CT pelvis / IV start / diagnostic laparoscopy, two ED levels, venipuncture x4, discharge-day room and board, routine OR supplies billed separately, a $2,400 uncoded 'miscellaneous OR charge'.

| Scenario | Starting balance | Patient alone | With agent | Agent savings | Savings % |
|---|---:|---:|---:|---:|---:|
| A. Uninsured, nonprofit hospital, 185% FPL | $104,458 | $95,932 | $0 | $104,458 | 100% |
| B. Uninsured, for-profit hospital, 350% FPL | $104,458 | $95,932 | $40,054 | $64,404 | 62% |
| C. Insured in network, $6,500 deductible plan, nonprofit, 320% FPL | $10,900 | $8,641 | $4,067 | $6,833 | 63% |
| D. Insured, out-of-network ED (emergency), nonprofit, 250% FPL | $59,455 | $57,196 | $3,600 | $55,855 | 94% |

## A. Uninsured, nonprofit hospital, 185% FPL

Hourly worker, household of 3, $48,000 income. No insurance. Nonprofit hospital with a typical financial assistance policy (free care to 200% FPL, sliding discount to 400%). Good faith estimate was $38,000.

Priority order (expected value = disputed dollars x probability of success, given this coverage and hospital type):

| Rank | Finding | Disputed | P(success) | Expected value | Why |
|---:|---|---:|---:|---:|---|
| 1 | Possible duplicate: 'CT ABDOMEN PELVIS W CONTRAST' billed 2 times on 2026-10-06 | $6,840 | 0.65 | $4,446 | Record review usually confirms; ask for the documentation. |
| 2 | 74177 billed 2 units on 2026-10-06; Medicare's unit ceiling is 1 | $6,840 | 0.65 | $4,446 | Record review usually confirms; ask for the documentation. |
| 3 | 49320 ('DIAGNOSTIC LAPAROSCOPY') is a component of 47562 and should not be billed separately | $4,200 | 0.92 | $3,864 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). |
| 4 | 72193 ('CT PELVIS W CONTRAST') is a component of 74177 and should not be billed separately | $3,980 | 0.92 | $3,662 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). |
| 5 | 3 accommodation days billed for a 2-night stay | $4,850 | 0.65 | $3,152 | Record review usually confirms; ask for the documentation. |
| 6 | Room and board charged for the day of discharge | $4,850 | 0.65 | $3,152 | Record review usually confirms; ask for the documentation. |
| 7 | 99284 ('EMERGENCY DEPT VISIT LEVEL 4') is a component of 99285 and should not be billed separately | $2,890 | 0.92 | $2,659 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). |
| 8 | 1 charge(s) over $100 carry no CPT/HCPCS or revenue code | $2,400 | 0.50 | $1,200 | Hospitals usually itemize or partially remove 'miscellaneous' charges when pressed. |

Negotiation transcript:

1. **agent**: Requests itemized statement with codes, UB-04, and the medical record under 45 CFR 164.524; asks for a hold on the account. Does not pay. _(balance $104,458)_
2. **hospital**: Sends itemized statement and places a 30-day hold; records follow in 3 weeks. _(balance $104,458)_
3. **agent**: Sends written dispute, highest expected value first: Possible duplicate: 'CT ABDOMEN PELVIS W CONTRAST' billed 2 times on 2026-10-06 (expected $4,446 of $6,840); 49320 ('DIAGNOSTIC LAPAROSCOPY') is a component of 47562 and should not be billed separately (expected $3,864 of $4,200); 72193 ('CT PELVIS W CONTRAST') is a component of 74177 and should not be billed separately (expected $3,662 of $3,980); 3 accommodation days billed for a 2-night stay (expected $3,152 of $4,850); 99284 ('EMERGENCY DEPT VISIT LEVEL 4') is a component of 99285 and should not be billed separately (expected $2,659 of $2,890); 1 charge(s) over $100 carry no CPT/HCPCS or revenue code (expected $1,200 of $2,400) ... _(balance $83,613)_
4. **hospital**: Reviews against the record. Corrects $20,845 of the patient's balance. Issues corrected statement. _(balance $83,613)_
5. **agent**: Submits financial assistance application: income is 180.1% of poverty, under the policy's free-care line. Cites 26 CFR 1.501(r)-6 to keep collections paused. _(balance $83,613)_
6. **hospital**: Approves 100% financial assistance. Balance written off as charity care. _(balance $0)_

Result: $104,458 to $0 with the agent versus $95,932 alone. Corrections alone were worth $20,845.

## B. Uninsured, for-profit hospital, 350% FPL

Self-employed, household of 2, $74,000 income. No insurance. For-profit hospital: no 501(r) duties, but the price transparency file and the No Surprises Act good faith estimate still apply.

Priority order (expected value = disputed dollars x probability of success, given this coverage and hospital type):

| Rank | Finding | Disputed | P(success) | Expected value | Why |
|---:|---|---:|---:|---:|---|
| 1 | Possible duplicate: 'CT ABDOMEN PELVIS W CONTRAST' billed 2 times on 2026-10-06 | $6,840 | 0.65 | $4,446 | Record review usually confirms; ask for the documentation. |
| 2 | 74177 billed 2 units on 2026-10-06; Medicare's unit ceiling is 1 | $6,840 | 0.65 | $4,446 | Record review usually confirms; ask for the documentation. |
| 3 | 49320 ('DIAGNOSTIC LAPAROSCOPY') is a component of 47562 and should not be billed separately | $4,200 | 0.92 | $3,864 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). |
| 4 | 72193 ('CT PELVIS W CONTRAST') is a component of 74177 and should not be billed separately | $3,980 | 0.92 | $3,662 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). |
| 5 | 3 accommodation days billed for a 2-night stay | $4,850 | 0.65 | $3,152 | Record review usually confirms; ask for the documentation. |
| 6 | Room and board charged for the day of discharge | $4,850 | 0.65 | $3,152 | Record review usually confirms; ask for the documentation. |
| 7 | 99284 ('EMERGENCY DEPT VISIT LEVEL 4') is a component of 99285 and should not be billed separately | $2,890 | 0.92 | $2,659 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). |
| 8 | 1 charge(s) over $100 carry no CPT/HCPCS or revenue code | $2,400 | 0.50 | $1,200 | Hospitals usually itemize or partially remove 'miscellaneous' charges when pressed. |

Negotiation transcript:

1. **agent**: Requests itemized statement with codes, UB-04, and the medical record under 45 CFR 164.524; asks for a hold on the account. Does not pay. _(balance $104,458)_
2. **hospital**: Sends itemized statement and places a 30-day hold; records follow in 3 weeks. _(balance $104,458)_
3. **agent**: Sends written dispute, highest expected value first: Possible duplicate: 'CT ABDOMEN PELVIS W CONTRAST' billed 2 times on 2026-10-06 (expected $4,446 of $6,840); 49320 ('DIAGNOSTIC LAPAROSCOPY') is a component of 47562 and should not be billed separately (expected $3,864 of $4,200); 72193 ('CT PELVIS W CONTRAST') is a component of 74177 and should not be billed separately (expected $3,662 of $3,980); 3 accommodation days billed for a 2-night stay (expected $3,152 of $4,850); 99284 ('EMERGENCY DEPT VISIT LEVEL 4') is a component of 99285 and should not be billed separately (expected $2,659 of $2,890); 1 charge(s) over $100 carry no CPT/HCPCS or revenue code (expected $1,200 of $2,400) ... _(balance $83,613)_
4. **hospital**: Reviews against the record. Corrects $20,845 of the patient's balance. Issues corrected statement. _(balance $83,613)_
5. **agent**: Corrected balance $83,613 still exceeds the $38,000 good faith estimate. Files the No Surprises Act patient-provider dispute (deadline 2027-02-19); collections must pause. Offers to settle at the estimate. _(balance $83,613)_
6. **hospital**: Cannot show the extra charges were unforeseeable; settles at the estimate rather than litigate the dispute. Balance $47,123 (expected value). _(balance $47,123)_
7. **agent**: Asks for a prompt-pay discount on the estimate amount and a zero-interest plan at $400/month. _(balance $47,123)_
8. **hospital**: Grants 15% for a signed plan. Final balance $40,054. _(balance $40,054)_

Result: $104,458 to $40,054 with the agent versus $95,932 alone. Corrections alone were worth $20,845.

## C. Insured in network, $6,500 deductible plan, nonprofit, 320% FPL

Household of 4, $107,000 income. High-deductible plan, $6,500 deductible remaining, 20% coinsurance, $9,000 out-of-pocket max. Hospital posted the EOB wrong and billed $1,900 above the patient responsibility.

Priority order (expected value = disputed dollars x probability of success, given this coverage and hospital type):

| Rank | Finding | Disputed | P(success) | Expected value | Why |
|---:|---|---:|---:|---:|---|
| 1 | Provider bills $10,900.00 but the insurer's explanation of benefits says you owe $9,000.00 | $1,900 | 0.98 | $1,862 | Arithmetic against the insurer's EOB; contractually binding. |
| 2 | Possible duplicate: 'CT ABDOMEN PELVIS W CONTRAST' billed 2 times on 2026-10-06 | $6,840 | 0.65 | $0 | Record review usually confirms; ask for the documentation. Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 3 | 74177 billed 2 units on 2026-10-06; Medicare's unit ceiling is 1 | $6,840 | 0.65 | $0 | Record review usually confirms; ask for the documentation. Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 4 | 3 accommodation days billed for a 2-night stay | $4,850 | 0.65 | $0 | Record review usually confirms; ask for the documentation. Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 5 | 49320 ('DIAGNOSTIC LAPAROSCOPY') is a component of 47562 and should not be billed separately | $4,200 | 0.92 | $0 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 6 | 72193 ('CT PELVIS W CONTRAST') is a component of 74177 and should not be billed separately | $3,980 | 0.92 | $0 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 7 | 99284 ('EMERGENCY DEPT VISIT LEVEL 4') is a component of 99285 and should not be billed separately | $2,890 | 0.92 | $0 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 8 | Possible duplicate: 'SURGICAL PATHOLOGY LEVEL III' billed 2 times on 2026-10-07 | $690 | 0.65 | $0 | Record review usually confirms; ask for the documentation. Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |

Negotiation transcript:

1. **agent**: Requests itemized statement with codes, UB-04, and the medical record under 45 CFR 164.524; asks for a hold on the account. Does not pay. _(balance $10,900)_
2. **hospital**: Sends itemized statement and places a 30-day hold; records follow in 3 weeks. _(balance $10,900)_
3. **agent**: Sends written dispute, highest expected value first: Provider bills $10,900.00 but the insurer's explanation of benefits says you owe $9,000.00 (expected $1,862 of $1,900) _(balance $9,038)_
4. **hospital**: Reviews against the record. Corrects $1,862 of the patient's balance. Issues corrected statement. _(balance $9,038)_
5. **agent**: Applies for hardship assistance on the remaining cost sharing (income 332.8% of poverty; balance is 8% of income). _(balance $9,038)_
6. **hospital**: Approves 50% hardship reduction on patient cost sharing. New balance $4,519. _(balance $4,519)_
7. **agent**: Cost sharing is contractual; asks for prompt-pay discount on the corrected patient share and a zero-interest plan. _(balance $4,519)_
8. **hospital**: Grants 10% prompt-pay discount. Final balance $4,067. _(balance $4,067)_

Result: $10,900 to $4,067 with the agent versus $8,641 alone. Corrections alone were worth $1,862.

## D. Insured, out-of-network ED (emergency), nonprofit, 250% FPL

Household of 2, $53,000 income. Went to the nearest ED, which was out of network. Plan paid at 60% of charges; hospital balance-billed the rest. Emergency care is protected under the No Surprises Act.

Priority order (expected value = disputed dollars x probability of success, given this coverage and hospital type):

| Rank | Finding | Disputed | P(success) | Expected value | Why |
|---:|---|---:|---:|---:|---|
| 1 | Provider bills $59,455.20 but the insurer's explanation of benefits says you owe $8,000.00 (emergency care, No Surprises Act) | $51,455 | 0.00 | $0 | Legal remedy with its own process; pursued as an entitlement step, not a line dispute. |
| 2 | Possible duplicate: 'CT ABDOMEN PELVIS W CONTRAST' billed 2 times on 2026-10-06 | $6,840 | 0.65 | $0 | Record review usually confirms; ask for the documentation. Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 3 | 74177 billed 2 units on 2026-10-06; Medicare's unit ceiling is 1 | $6,840 | 0.65 | $0 | Record review usually confirms; ask for the documentation. Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 4 | 3 accommodation days billed for a 2-night stay | $4,850 | 0.65 | $0 | Record review usually confirms; ask for the documentation. Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 5 | 49320 ('DIAGNOSTIC LAPAROSCOPY') is a component of 47562 and should not be billed separately | $4,200 | 0.92 | $0 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 6 | 72193 ('CT PELVIS W CONTRAST') is a component of 74177 and should not be billed separately | $3,980 | 0.92 | $0 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 7 | 99284 ('EMERGENCY DEPT VISIT LEVEL 4') is a component of 99285 and should not be billed separately | $2,890 | 0.92 | $0 | Rests on rule text (NCCI, Medicare manuals, EOB arithmetic). Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |
| 8 | Possible duplicate: 'SURGICAL PATHOLOGY LEVEL III' billed 2 times on 2026-10-07 | $690 | 0.65 | $0 | Record review usually confirms; ask for the documentation. Insured: value to the patient is the change in cost sharing only, which is zero while the out-of-pocket maximum binds. |

Negotiation transcript:

1. **agent**: Requests itemized statement with codes, UB-04, and the medical record under 45 CFR 164.524; asks for a hold on the account. Does not pay. _(balance $59,455)_
2. **hospital**: Sends itemized statement and places a 30-day hold; records follow in 3 weeks. _(balance $59,455)_
3. **agent**: Cites the No Surprises Act: emergency services are limited to in-network cost sharing (42 USC 300gg-131). Demands removal of $51,455 balance bill and a corrected statement. _(balance $59,455)_
4. **hospital**: Compliance reviews; agrees the encounter is protected. Reduces balance to in-network cost sharing of $8,000. _(balance $8,000)_
5. **agent**: Files 14 facility coding corrections that lower the plan's payment but not the patient's share, because the out-of-pocket maximum already binds. They go in the letter but do not drive the strategy. _(balance $8,000)_
6. **hospital**: Corrects the coding on the claim and refunds the plan; the patient's cost sharing is unchanged. _(balance $8,000)_
7. **agent**: Applies for hardship assistance on the remaining cost sharing (income 250.6% of poverty; balance is 15% of income). _(balance $8,000)_
8. **hospital**: Approves 50% hardship reduction on patient cost sharing. New balance $4,000. _(balance $4,000)_
9. **agent**: Cost sharing is contractual; asks for prompt-pay discount on the corrected patient share and a zero-interest plan. _(balance $4,000)_
10. **hospital**: Grants 10% prompt-pay discount. Final balance $3,600. _(balance $3,600)_

Result: $59,455 to $3,600 with the agent versus $57,196 alone. Corrections alone were worth $0.

## What a patient alone usually does

Consumer-finance reporting and advocacy sources describe the typical path: the patient receives a summary statement, does not request itemization, and either pays, sets up a plan at face value, or asks for a discount and gets the hospital's standard self-pay reduction. The baseline here assumes a 40% chance of asking for a 15% discount and a 30% chance of spotting an obvious duplicate. Both numbers are assumptions and are easy to change in `HOSPITAL_POLICY`.

## Where the agent's gains come from

1. It never negotiates from the summary statement. Itemization plus the record is what makes the coding disputes enforceable.
2. It ranks disputes by expected value for this coverage. Uninsured patients gain most from facility coding errors and entitlement programs; in-network insured patients gain most from EOB reconciliation and hardship programs, since the allowed amount is contractual.
3. It treats financial assistance and the No Surprises Act as entitlements with deadlines, not favors, and sequences them before any settlement.
4. It anchors settlement to prices the hospital already accepts (Medicare, its own cash price) and trades a prompt lump sum for a paid-in-full letter.
5. It keeps every exchange in writing and asks for a hold, which removes the collections pressure that pushes patients to pay inflated balances.