# Case Study: Sample Market D — Kenya

A full end-to-end walkthrough of one MAP demo market — from raw inputs through sensitivity analysis to investment recommendation.

---

## Why This Market

Sample Market D is the most analytically instructive of the five MAP demo markets because it sits at the boundary between viable and unviable depending on which assumptions you trust. It is not an obvious success (like Sample Market C's 45.5% IRR) or an obvious failure (like Sample Market E's 10% collection rate). This market rewards careful analysis — and that is precisely where this tool adds value.

Key characteristics:
- Active market with an established vendor base (~340 stalls)
- Existing income statement available (Kenya field data)
- Proposed solar PV upgrade creates a genuine cost-benefit tension
- Fee collection estimated at 40-50% — above field system average but below target
- MIRI score of 64/100 — investable with conditions

---

## 1. Inputs

### Market Configuration

| Parameter | Value | Source |
|---|---|---|
| Stall count | 340 | Field assessment |
| Lock-up units | 45 | Field assessment |
| Open pitches | 120 | Field assessment |
| Monthly rent — stalls | $32 | Field income statement (avg; range $28-38) |
| Monthly rent — lock-ups | $78 | Field income statement |
| Monthly rent — pitches | $12 | Field income statement |
| Base-case occupancy | 68% | Year-3 post-rehab target |
| Fee collection rate | 48% | Above field system avg (38%), below digital payment target (65%) |

### Capital Costs

| Item | Cost (USD) |
|---|---|
| Structural rehabilitation | $820,000 |
| Roofing replacement | $310,000 |
| Sanitation and drainage | $95,000 |
| Solar PV system (42 kW) | $1,074,000 |
| Cold storage (18 m³) | $27,500 |
| Contingency (10%) | $233,000 |
| **Total CapEx** | **$2,559,500** |
| Grant (ICLEI/municipal) | ($1,400,000) |
| **Net municipal CapEx** | **$1,159,500** |

> **Note on the solar figure:** The solar system costs $1.07M against an existing annual market revenue of approximately $1.03M. This is the central tension in this model — addressed in Section 4.

### Financing

- Senior loan: $700,000 at 8% over 10 years → annual debt service ~$104,000
- Concessional tranche: $459,500 at 3% over 15 years → annual debt service ~$38,000
- **Total annual debt service: ~$142,000**

### Operating Costs

| Item | Annual (USD) |
|---|---|
| Personnel (3 FTE) | $48,000 |
| Operations and maintenance | $31,000 |
| Solar O&M | $12,800 |
| Cold storage O&M | $4,100 |
| Finance and administration | $18,000 |
| **Total OpEx (Year 1)** | **$113,900** |

OpEx escalation: 4% per year (Kenya CPI-aligned).

### Macro Assumptions

| Parameter | Value |
|---|---|
| Discount rate | 10% |
| Inflation | 5.5% (Kenya 5-year avg) |
| Projection horizon | 20 years |

---

## 2. Base Case Results

```
mmfm analyze --file resources/models/sample_market_d.xlsx --scenario base
```

| Metric | Year 1 | Year 5 | Year 10 | Year 20 |
|---|---|---|---|---|
| Gross revenue | $328,000 | $405,000 | $514,000 | $826,000 |
| Effective revenue (×48% collection) | $157,000 | $194,000 | $247,000 | $396,000 |
| Operating costs | $114,000 | $139,000 | $169,000 | $251,000 |
| Net operating income | $43,000 | $55,000 | $78,000 | $145,000 |
| Debt service | $142,000 | $142,000 | $104,000 | $0 |
| Free cash flow | ($99,000) | ($87,000) | ($26,000) | $145,000 |
| DSCR | 0.30 | 0.39 | 0.75 | n/a |
| Operating margin | 27% | 28% | 31% | 37% |

**Base case NPV: ($318,000)**
**Base case IRR: 3.2%**
**Payback: Does not occur within 20-year horizon**

The base case is **not financially viable** under a 10% discount rate with the proposed solar system included. DSCR remains below 1.0x for the first 10 years of operation — a significant red flag for debt financing.

---

## 3. Scenario Comparison

```
mmfm analyze --file resources/models/sample_market_d.xlsx --scenario all
```

| Metric | Pessimistic | Base | Optimistic |
|---|---|---|---|
| Occupancy | 50% | 68% | 82% |
| Fee collection rate | 38% | 48% | 65% |
| CapEx overrun | 25% | 10% | 0% |
| Fee escalation | CPI | CPI +1% | CPI +3% |
| Grant timing | 12-month delay | On schedule | Early disbursement |
| **NPV** | **($1.1M)** | **($318K)** | **$214K** |
| **IRR** | **Negative** | **3.2%** | **11.8%** |
| **DSCR (Year 5)** | **0.25x** | **0.39x** | **0.68x** |
| **Payback** | **None** | **None** | **18.4 years** |

Three observations from the scenario table:

1. **The range is wide.** NPV swings from -$1.1M to +$214K — a spread of $1.3M on a $2.6M project. This is an unusually wide range and signals high parameter sensitivity relative to project scale.

2. **Even the optimistic case barely works.** An 18.4-year payback and 11.8% IRR in the optimistic scenario meets the hurdle rate but leaves no margin for surprises. A funder pricing this at a commercial rate would likely decline.

3. **The pessimistic DSCR is catastrophic.** A 0.25x DSCR means the market generates 25 cents of operating income for every dollar of debt service owed. This is not a covenant breach — it is an insolvency trajectory.

---

## 4. The Solar PV Tension

The $1.07M solar PV system is the central design decision in this model. It is worth unpacking carefully because it illustrates a common error in infrastructure bundling.

**The case for solar:**
- Reduces utility costs (Kenya grid electricity is expensive and unreliable)
- Enables cold storage operations (cold storage requires stable power)
- Improves vendor experience and market competitiveness
- Aligns with green infrastructure mandates for grant eligibility

**The case against bundling it in this model:**

```
mmfm analyze --file resources/models/sample_market_d.xlsx --scenario base --exclude solar
```

| Metric | With Solar | Without Solar |
|---|---|---|
| Total CapEx | $2,559,500 | $1,457,500 |
| Net municipal CapEx | $1,159,500 | $57,500* |
| Annual debt service | $142,000 | $5,400* |
| Year 5 DSCR | 0.39x | 1.42x |
| Base NPV | ($318,000) | $187,000 |
| IRR | 3.2% | 12.1% |

*Assumes the same $1.4M grant covers nearly all remaining CapEx.

**Removing solar from the bundle transforms the project from financially non-viable to clearly viable.** The operating cash flows are sufficient to service a much smaller debt load, and the DSCR exceeds 1.2x by Year 5 — the standard DFI covenant threshold.

This does not mean solar is wrong for this market. It means solar should be financed separately — either as a standalone energy access project with its own grant or revenue-sharing structure, or deferred to Phase 2 once the market's operational cash flows are established. Bundling a $1.07M capital item into a market that generates $157K of effective revenue in Year 1 creates a financing structure that cannot work at any reasonable cost of capital.

> **The anomaly detector flags this automatically:**
> `ANOMALY: Solar PV CapEx ($1,074,000) is 104% of Year 1 effective market revenue ($157,000). This exceeds the 80% threshold for viable bundling without technical assistance support.`

---

## 5. Sensitivity Analysis

```
mmfm sensitivity --file resources/models/sample_market_d.xlsx --tornado
```

### Tornado Chart (NPV Impact, Base Case = -$318K)

```
Variable                          Pessimistic ◄────────────────────────► Optimistic
                                                    Base (-$318K)
Fee collection rate (48%)         ████████████████████|████████████████  ±$412K
Occupancy rate (68%)              ███████████████████ |█████████████████  ±$374K
Discount rate (10%)               █████████████       |███████████████    ±$287K
CapEx overrun (10%)               ████████████        |██████             ±$198K
Grant delay (0 months)            ██████████          |████               ±$134K
Fee escalation (CPI+1%)           ████████            |████████           ±$121K
Vendor growth rate (2%)           ████                |████               ±$68K
```

**Reading the tornado:**

Fee collection rate is the top driver by a significant margin. A swing from 38% (field floor) to 65% (digital payment target) moves NPV by ±$412K on its own. This confirms what the scenario analysis implied: the single highest-leverage intervention is not additional capital investment — it is improving fee collection.

Occupancy rate is close behind at ±$374K. Together, collection rate and occupancy explain 58% of the total NPV variance in the tornado. Operational management quality matters more than financing structure for this market.

The discount rate sensitivity (±$287K) is high because the cash flows are back-loaded — most positive cash flows occur in Years 12-20 after debt is repaid. At 15%, the terminal-year cash flows are worth very little. At 5%, they carry the project.

CapEx overrun (±$198K) and grant delay (±$134K) are meaningful but not dominant. This is partly because the base-case project structure already carries a 10% contingency.

---

## 6. Monte Carlo Results

```
mmfm simulate --file resources/models/sample_market_d.xlsx --iterations 10000
```

**Distribution assumptions:**
- Occupancy: Beta(7, 3) — mode at 70%, right tail toward 90%
- Fee collection: Beta(5, 5) — symmetric around 50%
- CapEx overrun: LogNormal(μ=0, σ=0.3) — right-skewed
- Inflation: Normal(5.5%, 1.5%) — symmetric

| Percentile | NPV |
|---|---|
| P10 | ($892,000) |
| P25 | ($561,000) |
| P50 (median) | ($267,000) |
| P75 | $42,000 |
| P90 | $318,000 |

**Probability of positive NPV: 22%**
**Probability of DSCR < 1.2x in Year 5: 89%**

The Monte Carlo confirms the base-case story quantitatively: in roughly 8 out of 10 simulations, this market does not generate sufficient cash flow to comfortably service its debt in the medium term. The 22% probability of positive NPV is the share of the distribution where a combination of above-average occupancy, above-average fee collection, and controlled construction costs produces a viable project.

This is not a coin flip — it is a project with a clear structural problem that needs to be addressed before financing.

---

## 7. MIRI Score Breakdown

**Sample Market D MIRI: 64/100**

| Pillar | Score | Max | Notes |
|---|---|---|---|
| Financial Sustainability | 18 | 35 | DSCR fails in base case; payback >15yr; collection 48% |
| Governance Quality | 20 | 30 | Active management structure; no digital payment yet |
| Infrastructure Condition | 14 | 20 | Structural rehab planned; utilities functional; solar deferred |
| Market Activity & Demand | 12 | 15 | 68% occupancy, growing; strong catchment population |

The MIRI score of 64 positions this market in Tier 3 — investable if the solar bundle is restructured and fee collection digitization is sequenced ahead of debt drawdown.

---

## 8. AI Narrative Output

*Generated by Sonnet; cross-validated against engine outputs.*

```
EXECUTIVE SUMMARY

This market presents a viable long-term investment opportunity contingent on
two structural changes: (1) separating the solar PV component into a
standalone financing instrument, and (2) sequencing fee collection
digitization as a pre-condition for debt drawdown rather than a
post-investment improvement.

Under the current bundled structure, the project generates a base-case NPV
of -$318,000 at a 10% discount rate, with a Year 5 DSCR of 0.39x — well
below the 1.2x minimum covenant required by development finance institutions.
The solar PV system, at $1.07M, represents 104% of Year 1 effective market
revenue and is the primary driver of financial stress.

Removing solar from the bundle reduces net municipal CapEx from $1.16M to
approximately $57,500 and transforms the financial profile to a base-case NPV
of +$187,000 with DSCR exceeding 1.2x by Year 5.

TOP 3 RISKS
1. Fee collection rate (48%) remains below viable threshold — operational
   risk, not financial structure risk
2. Solar PV bundle inflates debt service beyond the market's early-stage
   cash flows
3. Grant disbursement delay of 12+ months would eliminate Year 1 revenue
   and push DSCR below 0.3x in Year 2

RECOMMENDATION: proceed_with_conditions
CONFIDENCE: medium

CONDITIONS
- Remove or separately finance solar PV system
- Require digital payment system operational at 90% of stalls prior to
  debt drawdown
- Include DSCR covenant step-up from 1.0x (Years 1-5) to 1.2x (Years 6+)
```

---

## 9. Investment Recommendation

**Recommendation: Proceed with conditions.**

This market has strong underlying economics — healthy catchment population, above-average (for the region) fee collection, an active management structure, and a physical asset that can be rehabilitated at reasonable cost. The negative base-case NPV is not evidence of an unviable market; it is evidence of an over-engineered financing structure for the current stage of market maturity.

**Recommended restructuring:**

1. **Phase 1 (finance now):** Structural rehabilitation + roofing + sanitation ($1.225M total, fully grant-covered under proposed structure). Zero debt. Market begins operating and building a 2-3 year track record.

2. **Phase 2 (finance once track record established):** Solar PV + cold storage as a separate energy access project, potentially via a PAYGO solar lease structure with the solar revenue serviced directly from utility savings — not from market operating cash flows.

3. **Pre-conditions for any Phase 1 debt:** Digital fee collection at 90% of stalls (eliminates the leakage driving the 48% effective collection rate), and 12 months of audited financials post-rehab before loan drawdown.

Under this restructured approach, the market scores as a viable investment in Years 3-5 after rehabilitation, with DSCR comfortably above covenant thresholds and a payback period of 8-12 years depending on collection rate improvement trajectory.

The tool's sensitivity analysis makes the decision logic explicit: fee collection rate is the highest-leverage variable, and it is an operational/governance problem — not a capital problem. Solving it with capital (more grant money, lower interest rate) is less efficient than solving it operationally (digital payment, better enforcement) before drawing down debt.

---

## 10. How to Reproduce This Analysis

```bash
# Run the complete analysis
mmfm analyze --file resources/models/sample_market_d.xlsx --scenario all
mmfm sensitivity --file resources/models/sample_market_d.xlsx --tornado
mmfm simulate --file resources/models/sample_market_d.xlsx --iterations 10000

# Generate full PDF report
mmfm report --file resources/models/sample_market_d.xlsx \
  --format pdf --narrative --output sample_market_d_report.pdf

# Or view interactively in the dashboard
streamlit run src/mmfm/app.py
# Navigate to Portfolio tab, select Sample Market D
```

Or open the live dashboard and explore interactively:
**[https://mmfm-analyzer-yfc86cidntp3ld43gp55pd.streamlit.app/](https://mmfm-analyzer-yfc86cidntp3ld43gp55pd.streamlit.app/)**

---

*All figures in USD. Financial model grounded in ICLEI Africa MAP field assessment data.*
