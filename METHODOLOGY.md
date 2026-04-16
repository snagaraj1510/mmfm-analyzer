# Financial Modeling Methodology

This document explains the core analytical choices in the MMFM Analyzer: why the seven sensitivity variables were selected, how fee collection rates were calibrated from field data, and what the MIRI composite score represents.

---

## 1. The Seven Sensitivity Variables

Tornado analysis sweeps one variable at a time while holding all others at their base-case values, then ranks by NPV swing. The seven variables below were selected because they jointly explain the vast majority of NPV variance in Sub-Saharan African municipal market models — and because each is genuinely uncertain at appraisal time.

### 1.1 Occupancy Rate (`occupancy_rate`)

**Range tested:** 30% – 95%

Occupancy is the single largest NPV driver in any stall-rental model. Revenue is mechanically `stall_count × monthly_rent × occupancy_rate × 12 × escalation`. A 20-percentage-point swing in occupancy produces roughly the same NPV impact as a 30% capex overrun in most market configurations.

The 30% floor reflects markets in early post-construction phase or with active vendor displacement. The 95% ceiling reflects mature markets with waiting lists (observed in assessed Malawi and Zambia central markets). The base case of 70% follows the ICLEI Africa benchmark for newly rehabilitated markets in Year 3 of operation.

### 1.2 Rental Fee Escalation (`rental_fee_escalation`)

**Range tested:** 0% – 10% nominal annual increase

Fee escalation directly compounds over the projection horizon, making it especially impactful in 15-20 year models. At 0% escalation, real fee revenue declines every year against inflation. At CPI + 3% (the optimistic case), fees keep pace with municipal cost structures.

The upper bound of 10% was chosen because nominal rent increases above that level are politically difficult to sustain in East African municipal contexts — city councils face vendor pushback and informal market competition. The base case of CPI + 1% reflects observed patterns in Kenya and Zambia sample markets where fees have historically tracked inflation with modest real growth.

### 1.3 CapEx Overrun (`capex_overrun_pct`)

**Range tested:** 0% – 50%

Construction cost overruns are endemic in Sub-Saharan African public infrastructure. The 10% base-case contingency is the ICLEI standard; the pessimistic case uses 25%, reflecting documented overruns in comparable municipal construction. The 50% ceiling captures extreme scenarios (contractor failure, currency depreciation during construction, procurement delays).

Note: this variable interacts with grant timing. If a grant is disbursed at financial close but construction takes longer than planned, the municipal co-financing gap widens — which is modeled separately via `grant_disbursement_delay_months`.

### 1.4 Discount Rate (`discount_rate`)

**Range tested:** 5% – 20%

The discount rate is the model's single most influential parameter for long-duration projects (15+ years), where most value is in the terminal years. The range spans:
- **5%:** Concessional or grant-funded projects where the relevant hurdle is social cost of capital
- **10%:** Standard development finance institution (DFI) benchmark for East Africa municipal infrastructure
- **20%:** Commercial capital cost in high-inflation or high-risk environments

Projects with long payback periods are particularly sensitive here. A market that shows a positive NPV at 8% may be deeply negative at 15% — making discount rate the key variable for communicating risk to funders with different return expectations.

### 1.5 Inflation Rate (`inflation_rate`)

**Range tested:** 2% – 15%

Inflation is included separately from fee escalation because it drives the real value of fixed-nominal cost structures (debt service, long-term leases) while simultaneously eroding real revenue if fees are not indexed. At high inflation (12-15%, observed in some Sub-Saharan markets in recent years), markets with nominal-fixed debt service benefit while those with floating-rate obligations face cash flow compression.

The model uses inflation as both a cost escalator (opex) and a revenue deflator (real fee benchmarking). The base case of 5% reflects the IMF World Economic Outlook median for Sub-Saharan Africa.

### 1.6 Grant Disbursement Delay (`grant_disbursement_delay_months`)

**Range tested:** 0 – 24 months

Grant timing is one of the least-discussed but most financially impactful variables in public infrastructure finance. When a grant is delayed, the municipal government must either:
1. Bridge-finance the shortfall (increasing debt service)
2. Pause construction (increasing total project cost and delaying revenue start)

The range of 0-24 months reflects real experience: on-schedule disbursement is rare; 12-18 month delays are common in multilateral-funded projects. A 12-month delay shifts the revenue start date by a year, eliminating one full year of early cash flows — which, when discounted, can reduce NPV by 10-20% in typical configurations.

### 1.7 Vendor Count Growth Rate (`vendor_count_growth_rate`)

**Range tested:** -5% – +10% annual

This variable captures demand-side market dynamics that are independent of occupancy rate. A market can have high occupancy but declining vendor count (if remaining vendors occupy larger spaces), or low occupancy with growing vendor count (a market still filling up).

Vendor count growth primarily affects fee-per-vendor revenue streams (market levies, produce commissions) rather than stall rental income. It was included because several MAP markets have explicit vendor formalization programs with target growth rates, making it a programmatic lever — not just a market parameter.

**Why not include more variables?**

Variables excluded from the tornado include municipal governance quality, political risk, and FX rate changes. These matter, but they are difficult to parameterize meaningfully — governance quality is captured structurally in the MIRI score, and FX risk is treated as a scenario-level adjustment rather than a continuous sensitivity variable.

---

## 2. Fee Collection Rate Calibration

The fee collection rate is arguably the most important field-calibration decision in the model. It answers: of the fees that are theoretically owed by vendors, what fraction is actually collected in cash?

### 2.1 Source Data

Three primary sources informed the calibration:

**Zambia — fee collection audit reports**
The Zambia dataset provides the most granular collection-rate data in the source corpus. Key findings:
- System average across assessed Zambia markets: **38%**
- Best-performing sample market: 55-60%
- Worst-performing sample market: 10-15%
- Primary cause of shortfall: informal collection by unauthorized agents, vendors paying competitors instead of municipal collectors, and market days where supervisors are absent

**Malawi — MIRI assessment data**
The Malawi data shows collection rates of 35-45% across assessed markets, consistent with the Zambia figures. Higher-scoring governance markets showed collection rates of 48-52%.

**Kenya — income statement data**
The Kenya sample market income statements showed realized revenue significantly below theoretical maximum at observed occupancy, implying an effective collection rate of approximately 40-50%.

### 2.2 Calibrated Values

| Scenario | Fee Collection Rate | Basis |
|---|---|---|
| Optimistic | 80% | Reflects markets with digital payment infrastructure and active enforcement |
| Base case | 65% | Midpoint of well-managed markets; achievable with moderate governance investment |
| Pessimistic | 38% | Zambia system average — a realistic floor for unreformed markets |
| Worst case (stress) | 10% | Observed low in poorest-performing sample market; used only in extreme stress tests |

The pessimistic default of 38% is intentionally conservative. Using 50% (which might seem intuitive as a "halfway" pessimistic assumption) would overstate realistic downside for East African municipal markets. The field data is unambiguous: collection rates below 40% are common, not exceptional.

### 2.3 Why This Matters

Fee collection rate interacts multiplicatively with occupancy rate. If a market has 80% occupancy but 38% collection, effective revenue is only 30.4% of theoretical maximum. This compounding effect means that revenue projections based on occupancy alone significantly overstate actual cash flow — a common error in pre-feasibility studies that do not incorporate field collection data.

---

## 3. MIRI Scoring Methodology

The Market Investment Readiness Index (MIRI) is a composite score that summarizes a market's overall readiness to absorb investment and generate sustainable returns. It synthesizes financial, governance, infrastructure, and demand indicators into a single 0-100 score for portfolio comparison.

### 3.1 Score Architecture

MIRI is calculated from four pillars, each assessed independently before aggregation:

| Pillar | Weight | What It Measures |
|---|---|---|
| **Financial Sustainability** | 35% | Revenue coverage of operating costs, debt service capacity, fee collection reliability |
| **Governance Quality** | 30% | Management accountability, audit compliance, collection enforcement, political stability |
| **Infrastructure Condition** | 20% | Physical asset state, remaining useful life, maintenance backlog, technology readiness |
| **Market Activity & Demand** | 15% | Vendor occupancy trends, catchment population, competition from informal markets |

### 3.2 Pillar Scoring Detail

**Financial Sustainability (35 points)**

| Sub-indicator | Points | Calibration |
|---|---|---|
| DSCR ≥ 1.2x in base case | 10 | 1.2x is standard DFI minimum covenant |
| Operating margin ≥ 20% in Year 5 | 8 | Threshold for self-sustaining operations |
| Fee collection rate ≥ 50% | 7 | Above field system average |
| Revenue CAGR positive over projection | 5 | Trending in right direction |
| Payback period ≤ 10 years | 5 | Reasonable for development finance |

**Governance Quality (30 points)**

| Sub-indicator | Points | Calibration |
|---|---|---|
| Annual financial audit conducted | 8 | Basic accountability standard |
| Dedicated market management structure | 7 | Separate from general municipal admin |
| Fee collection via formal channels (not cash) | 6 | Reduces leakage and corruption exposure |
| Vendor dispute resolution mechanism | 5 | Reduces occupancy volatility |
| Political leadership stability | 4 | Assessed qualitatively via source docs |

**Infrastructure Condition (20 points)**

| Sub-indicator | Points | Calibration |
|---|---|---|
| Structural condition rated good/fair | 8 | From field assessment |
| Basic utilities (water, power, sanitation) functional | 6 | Hygiene compliance baseline |
| Cold storage or specialized infrastructure operational | 3 | Value-add capacity |
| Technology readiness (POS, digital payment) | 3 | Collection efficiency enabler |

**Market Activity & Demand (15 points)**

| Sub-indicator | Points | Calibration |
|---|---|---|
| Occupancy ≥ 60% | 6 | Above break-even in most configs |
| Catchment population ≥ 50,000 | 4 | Minimum viable demand base |
| No dominant nearby informal competitor | 3 | Market position security |
| Vendor waiting list or growing occupancy trend | 2 | Demand exceeds supply signal |

### 3.3 Demo Portfolio Scores

The five sample markets in the demo portfolio span a range from high-readiness to stressed:

| Market | Financial | Governance | Infrastructure | Demand | MIRI Total |
|---|---|---|---|---|---|
| Sample Market A | 29/35 | 25/30 | 16/20 | 12/15 | **82/100** |
| Sample Market B | 26/35 | 24/30 | 18/20 | 13/15 | **81/100** |
| Sample Market C | 30/35 | 18/30 | 15/20 | 11/15 | **74/100** |
| Sample Market D | 18/35 | 20/30 | 14/20 | 12/15 | **64/100** |
| Sample Market E | 10/35 | 12/30 | 11/20 | 8/15 | **41/100** |

### 3.4 Methodological Limitations

MIRI weights reflect ICLEI Africa's investment priorities for the MAP project period and should not be treated as universal. Three known limitations:

1. **Governance scores are partially subjective.** Sub-indicators like political leadership stability require qualitative judgment from field assessors. Two analysts reviewing the same market may score ±5 points.

2. **Financial pillar favors stable markets over high-growth markets.** A market with currently low revenue but strong vendor growth trajectory (e.g., a newly formalized informal market) will score poorly on DSCR even if its long-term outlook is strong. Users should read the trend analysis alongside the MIRI score.

3. **Infrastructure condition data ages quickly.** MIRI scores are point-in-time. A market that scores 18/20 on infrastructure today may score 10/20 after two years of deferred maintenance. Users should note the assessment date when comparing markets across time.

---

## 4. Projection Horizon and Discount Rate Selection

All base-case projections use a **20-year horizon** at a **10% real discount rate**.

The 20-year horizon reflects the typical useful life of major market infrastructure rehabilitation (roofing, structural reinforcement, cold storage) and aligns with standard development finance appraisal practice. Shorter horizons (10-15 years) systematically undervalue markets with back-loaded revenue profiles — which is common when vendor formalization programs take 3-5 years to reach target occupancy.

The 10% discount rate is consistent with DFI benchmarks for East Africa public infrastructure and represents a blended cost of capital for a concessional senior tranche (5-7%) plus a municipal equity component priced at a higher rate. For purely grant-funded projects, users should consider running the model at 5-7% to reflect social cost of capital rather than financial cost.

---

*For data sources behind specific constants (solar PV CapEx, cold storage benchmarks, FX rates), see the knowledge base registry at `knowledge_base/registry.json`.*
