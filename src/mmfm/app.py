"""
MMFM Analyzer — Streamlit Web Dashboard

Run locally:    streamlit run src/mmfm/app.py
Deploy:         streamlit.io/cloud → connect GitHub repo

Tabs:
  1. Portfolio Overview  — MAP 5-market comparison table + IRR/NPV bar charts
  2. Scenario Analysis   — Cash flow projection with base/optimistic/pessimistic
  3. Sensitivity         — Tornado chart
  4. Monte Carlo         — NPV distribution histogram
  5. AI Narrative        — Generate narrative with Ollama or Claude (mocked if no backend)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Streamlit Cloud compatibility: ensure src/ is on the path when the package
# isn't pip-installed (e.g. deployed from GitHub without editable install).
_src_dir = Path(__file__).parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

import streamlit as st

# ── Page config must be first Streamlit call ────────────────────────────────
st.set_page_config(
    page_title="MMFM Analyzer",
    page_icon="📊",
    layout="wide",
)

# ── Sidebar — always visible ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Model Parameters")

    base_stall_rental_income = st.slider(
        "Base Stall Rental Income (USD)",
        min_value=50_000,
        max_value=500_000,
        value=200_000,
        step=10_000,
        format="$%d",
    )
    total_capex = st.slider(
        "Total CapEx (USD)",
        min_value=200_000,
        max_value=3_000_000,
        value=1_000_000,
        step=50_000,
        format="$%d",
    )
    discount_rate = st.slider(
        "Discount Rate (%)",
        min_value=5,
        max_value=25,
        value=10,
        step=1,
    ) / 100.0
    horizon_years = st.slider(
        "Projection Horizon (years)",
        min_value=10,
        max_value=30,
        value=20,
        step=5,
    )
    fee_collection_rate = st.slider(
        "Fee Collection Rate (Lusaka avg: 0.38)",
        min_value=0.10,
        max_value=1.0,
        value=0.65,
        step=0.05,
    )

    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        "Built by **Shreyas**  \n"
        "Michigan Ross MBA 2026  \n"
        "ICLEI Africa MAP Capstone"
    )
    st.markdown("[GitHub](https://github.com/snagaraj1510/mmfm-analyzer)")


# ── Page title ───────────────────────────────────────────────────────────────
st.title("📊 MMFM Analyzer")
st.markdown(
    "*Municipal Market Financial Model | ICLEI Africa MAP Capstone*"
)

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_portfolio, tab_scenarios, tab_sensitivity, tab_monte_carlo, tab_ai = st.tabs(
    ["🌍 Portfolio", "📈 Scenarios", "🎯 Sensitivity", "🎲 Monte Carlo", "🤖 AI Narrative"]
)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Portfolio Overview
# ─────────────────────────────────────────────────────────────────────────────
with tab_portfolio:
    st.header("🌍 Portfolio Overview")
    st.markdown(
        "Five MAP markets across East and Southern Africa assessed for investment readiness. "
        "Markets are evaluated on IRR, NPV, DSCR, and governance using the Municipal Investment "
        "Readiness Index (MIRI). The investment-readiness threshold is **IRR ≥ 12%** and "
        "**DSCR ≥ 1.2**."
    )

    import pandas as pd
    import plotly.graph_objects as go
    from mmfm.demo.demo_markets import DEMO_PORTFOLIO
    from mmfm.engine.comparison import compare_markets

    result = compare_markets(DEMO_PORTFOLIO)
    ready_names = set(result.investment_ready(min_irr=0.12, min_dscr=1.2))
    summary = result.summary_table()

    df = pd.DataFrame(summary)
    df.rename(
        columns={
            "market": "Market",
            "country": "Country",
            "npv_usd": "NPV (USD)",
            "irr_pct": "IRR (%)",
            "payback_years": "Payback (yrs)",
            "min_dscr": "Min DSCR",
            "miri_score": "MIRI Score",
            "governance_score": "Gov. Score",
            "fee_collection_rate": "Fee Coll. Rate",
        },
        inplace=True,
    )

    def _color_irr(val):
        if val is None:
            return "color: gray"
        return "color: green; font-weight: bold" if val >= 12.0 else "color: red"

    def _color_dscr(val):
        if val is None:
            return "color: gray"
        return "color: green; font-weight: bold" if val >= 1.2 else "color: red"

    styled = (
        df.style
        .format(
            {
                "NPV (USD)": lambda v: f"${v:,.0f}" if v is not None else "N/A",
                "IRR (%)": lambda v: f"{v:.1f}%" if v is not None else "N/A",
                "Payback (yrs)": lambda v: f"{v:.1f}" if v is not None else "N/A",
                "Min DSCR": lambda v: f"{v:.2f}" if v is not None else "N/A",
                "MIRI Score": lambda v: f"{v:.0f}" if v is not None else "—",
                "Gov. Score": lambda v: f"{v:.0f}" if v is not None else "—",
                "Fee Coll. Rate": lambda v: f"{v:.0%}" if v is not None else "—",
            }
        )
        .map(_color_irr, subset=["IRR (%)"])
        .map(_color_dscr, subset=["Min DSCR"])
    )

    st.dataframe(styled, use_container_width=True, height=220)

    # ── Investment-ready metric row ──────────────────────────────────────────
    st.markdown("#### Investment Readiness (IRR ≥ 12% AND DSCR ≥ 1.2)")
    metric_cols = st.columns(len(DEMO_PORTFOLIO))
    for col, market in zip(metric_cols, DEMO_PORTFOLIO):
        is_ready = market.name in ready_names
        irr_display = f"{market.irr * 100:.1f}%" if market.irr is not None else "N/A"
        if is_ready:
            col.success(f"**{market.name.split()[0]}**  \n{irr_display} ✓")
        else:
            col.error(f"**{market.name.split()[0]}**  \n{irr_display} ✗")

    # ── Side-by-side bar charts ──────────────────────────────────────────────
    st.markdown("---")
    chart_col1, chart_col2 = st.columns(2)

    market_names = [m.name for m in DEMO_PORTFOLIO]
    irr_values = [
        (m.irr * 100 if m.irr is not None else 0.0) for m in DEMO_PORTFOLIO
    ]
    npv_values = [
        (m.npv_usd if m.npv_usd is not None else 0.0) for m in DEMO_PORTFOLIO
    ]
    bar_colors = [
        "#2ecc71" if name in ready_names else "#e74c3c" for name in market_names
    ]

    with chart_col1:
        fig_irr = go.Figure(
            go.Bar(
                x=market_names,
                y=irr_values,
                marker_color=bar_colors,
                text=[f"{v:.1f}%" for v in irr_values],
                textposition="outside",
            )
        )
        fig_irr.add_hline(
            y=12.0,
            line_dash="dash",
            line_color="orange",
            annotation_text="Min IRR (12%)",
        )
        fig_irr.update_layout(
            title="IRR by Market",
            yaxis_title="IRR (%)",
            xaxis_tickangle=-20,
            height=400,
            margin=dict(t=50, b=80),
        )
        st.plotly_chart(fig_irr, use_container_width=True)

    with chart_col2:
        fig_npv = go.Figure(
            go.Bar(
                x=market_names,
                y=npv_values,
                marker_color=bar_colors,
                text=[f"${v:,.0f}" for v in npv_values],
                textposition="outside",
            )
        )
        fig_npv.add_hline(y=0, line_dash="solid", line_color="gray")
        fig_npv.update_layout(
            title="NPV by Market (USD)",
            yaxis_title="NPV (USD)",
            xaxis_tickangle=-20,
            height=400,
            margin=dict(t=50, b=80),
        )
        st.plotly_chart(fig_npv, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Scenario Analysis
# ─────────────────────────────────────────────────────────────────────────────
with tab_scenarios:
    st.header("📈 Scenario Analysis")
    st.markdown(
        "Compare cash flow trajectories across **base**, **optimistic**, and **pessimistic** "
        "scenarios. Adjust inputs in the sidebar. Key levers: fee collection rate "
        "(Lusaka avg: 0.38), CapEx size, and discount rate."
    )

    import plotly.express as px
    from mmfm.engine.projections import RevenueInputs, CapexInputs, OpexInputs
    from mmfm.engine.scenarios import run_all_scenarios

    @st.cache_data(show_spinner="Running scenario analysis...")
    def _run_scenarios(
        stall_income: float,
        capex: float,
        disc_rate: float,
        horizon: int,
        fcr: float,
    ):
        revenue = RevenueInputs(
            base_stall_rental_income=stall_income,
            occupancy_rate=0.60,
            vendor_fees_annual=stall_income * 0.15,
            market_levies_annual=stall_income * 0.08,
            rental_escalation_rate=0.06,
            fee_escalation_rate=0.06,
            occupancy_ramp_years=3,
            occupancy_target=0.70,
            other_income_annual=0.0,
            fee_collection_rate=fcr,
        )
        capex_inputs = CapexInputs(
            total_capex=capex,
            construction_schedule={0: 0.60, 1: 0.40},
            overrun_contingency=0.10,
            grant_amount=0.0,
            grant_disbursement_year=0,
        )
        opex_inputs = OpexInputs(
            base_opex=stall_income * 0.30,
            opex_escalation_rate=0.05,
            debt_service_annual=capex * 0.08,
        )
        comparison = run_all_scenarios(
            revenue=revenue,
            capex=capex_inputs,
            opex=opex_inputs,
            discount_rate=disc_rate,
            horizon_years=horizon,
        )
        return comparison

    comparison = _run_scenarios(
        base_stall_rental_income, total_capex, discount_rate, horizon_years, fee_collection_rate
    )

    # ── Cumulative cash flow line chart ─────────────────────────────────────
    scenario_order = ["pessimistic", "base", "optimistic"]
    scenario_colors = {"base": "#3498db", "optimistic": "#2ecc71", "pessimistic": "#e74c3c"}

    cf_rows = []
    for name in scenario_order:
        res = comparison.results[name]
        for yr in res.projection.years:
            cf_rows.append(
                {
                    "Year": yr.year,
                    "Cumulative Cash Flow (USD)": yr.cumulative_cash_flow,
                    "Scenario": name.capitalize(),
                }
            )

    df_cf = pd.DataFrame(cf_rows)
    fig_cf = px.line(
        df_cf,
        x="Year",
        y="Cumulative Cash Flow (USD)",
        color="Scenario",
        color_discrete_map={
            "Base": scenario_colors["base"],
            "Optimistic": scenario_colors["optimistic"],
            "Pessimistic": scenario_colors["pessimistic"],
        },
        title="Cumulative Cash Flow Over Time",
        markers=False,
    )
    fig_cf.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig_cf.update_layout(height=420)
    st.plotly_chart(fig_cf, use_container_width=True)

    # ── NPV / IRR / Payback grouped bar chart ────────────────────────────────
    summary_rows = comparison.summary_table()
    df_summary = pd.DataFrame(summary_rows)

    bar_col1, bar_col2, bar_col3 = st.columns(3)

    with bar_col1:
        fig_npv_sc = go.Figure(
            go.Bar(
                x=[r["scenario"].capitalize() for r in summary_rows],
                y=[r["npv"] for r in summary_rows],
                marker_color=[scenario_colors[r["scenario"]] for r in summary_rows],
                text=[f"${r['npv']:,.0f}" for r in summary_rows],
                textposition="outside",
            )
        )
        fig_npv_sc.add_hline(y=0, line_color="gray")
        fig_npv_sc.update_layout(title="NPV (USD)", height=350, margin=dict(t=45))
        st.plotly_chart(fig_npv_sc, use_container_width=True)

    with bar_col2:
        irr_vals = [
            (r["irr"] * 100 if r["irr"] is not None else 0.0) for r in summary_rows
        ]
        fig_irr_sc = go.Figure(
            go.Bar(
                x=[r["scenario"].capitalize() for r in summary_rows],
                y=irr_vals,
                marker_color=[scenario_colors[r["scenario"]] for r in summary_rows],
                text=[f"{v:.1f}%" for v in irr_vals],
                textposition="outside",
            )
        )
        fig_irr_sc.update_layout(title="IRR (%)", height=350, margin=dict(t=45))
        st.plotly_chart(fig_irr_sc, use_container_width=True)

    with bar_col3:
        payback_vals = [
            (r["payback_years"] if r["payback_years"] is not None else 0.0)
            for r in summary_rows
        ]
        fig_pb = go.Figure(
            go.Bar(
                x=[r["scenario"].capitalize() for r in summary_rows],
                y=payback_vals,
                marker_color=[scenario_colors[r["scenario"]] for r in summary_rows],
                text=[
                    f"{v:.1f} yrs" if v > 0 else "N/A" for v in payback_vals
                ],
                textposition="outside",
            )
        )
        fig_pb.update_layout(title="Payback (years)", height=350, margin=dict(t=45))
        st.plotly_chart(fig_pb, use_container_width=True)

    # ── Base scenario summary metrics ────────────────────────────────────────
    st.markdown("#### Base Scenario Key Metrics")
    base_res = comparison.results["base"]
    m1, m2, m3 = st.columns(3)
    m1.metric("Base NPV", f"${base_res.npv.value:,.0f}")
    base_irr_display = (
        f"{base_res.irr.value * 100:.1f}%"
        if base_res.irr.value is not None
        else "N/A"
    )
    m2.metric("Base IRR", base_irr_display)
    base_pb = (
        f"{base_res.payback.years:.1f} yrs"
        if base_res.payback.years is not None
        else "N/A"
    )
    m3.metric("Base Payback", base_pb)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Sensitivity Analysis
# ─────────────────────────────────────────────────────────────────────────────
with tab_sensitivity:
    st.header("🎯 Sensitivity Analysis (Tornado Chart)")
    st.markdown(
        "Each bar shows the range of NPV outcomes as a single input variable is swept across "
        "its realistic range, holding all others at base values. Sorted by magnitude of impact."
    )

    from mmfm.engine.sensitivity import run_sensitivity

    @st.cache_data(show_spinner="Running sensitivity analysis...")
    def _run_sensitivity(
        stall_income: float,
        capex: float,
        disc_rate: float,
        horizon: int,
        fcr: float,
    ):
        from mmfm.engine.projections import RevenueInputs, CapexInputs, OpexInputs

        revenue = RevenueInputs(
            base_stall_rental_income=stall_income,
            occupancy_rate=0.60,
            vendor_fees_annual=stall_income * 0.15,
            market_levies_annual=stall_income * 0.08,
            rental_escalation_rate=0.06,
            fee_escalation_rate=0.06,
            occupancy_ramp_years=3,
            occupancy_target=0.70,
            other_income_annual=0.0,
            fee_collection_rate=fcr,
        )
        capex_inputs = CapexInputs(
            total_capex=capex,
            construction_schedule={0: 0.60, 1: 0.40},
            overrun_contingency=0.10,
            grant_amount=0.0,
            grant_disbursement_year=0,
        )
        opex_inputs = OpexInputs(
            base_opex=stall_income * 0.30,
            opex_escalation_rate=0.05,
            debt_service_annual=capex * 0.08,
        )
        return run_sensitivity(
            revenue=revenue,
            capex=capex_inputs,
            opex=opex_inputs,
            discount_rate=disc_rate,
            inflation_rate=0.05,
            horizon_years=horizon,
        )

    sens_result = _run_sensitivity(
        base_stall_rental_income, total_capex, discount_rate, horizon_years, fee_collection_rate
    )

    tornado_vars = sens_result.tornado_order()
    base_npv = sens_result.base_npv

    # Build tornado chart data
    labels = [v.label for v in tornado_vars]
    low_delta = [v.npv_at_low - base_npv for v in tornado_vars]
    high_delta = [v.npv_at_high - base_npv for v in tornado_vars]

    fig_tornado = go.Figure()
    for i, var in enumerate(tornado_vars):
        lo = var.npv_at_low - base_npv
        hi = var.npv_at_high - base_npv
        # Positive swing bar (green)
        pos_val = max(lo, hi)
        neg_val = min(lo, hi)
        fig_tornado.add_trace(
            go.Bar(
                name=var.label,
                y=[var.label],
                x=[pos_val],
                orientation="h",
                marker_color="#2ecc71",
                showlegend=False,
                hovertemplate=f"{var.label}<br>High swing: ${{x:,.0f}}<extra></extra>",
            )
        )
        fig_tornado.add_trace(
            go.Bar(
                name=var.label + "_neg",
                y=[var.label],
                x=[neg_val],
                orientation="h",
                marker_color="#e74c3c",
                showlegend=False,
                hovertemplate=f"{var.label}<br>Low swing: ${{x:,.0f}}<extra></extra>",
            )
        )

    fig_tornado.update_layout(
        title=f"Tornado Chart — NPV Sensitivity (Base NPV: ${base_npv:,.0f})",
        xaxis_title="NPV Change from Base (USD)",
        barmode="overlay",
        height=max(350, 60 * len(tornado_vars)),
        margin=dict(l=180, t=60),
    )
    fig_tornado.add_vline(x=0, line_color="black", line_width=1.5)
    st.plotly_chart(fig_tornado, use_container_width=True)

    # ── Raw sensitivity table ────────────────────────────────────────────────
    st.markdown("#### Raw Sensitivity Results")
    raw_rows = []
    for v in tornado_vars:
        raw_rows.append(
            {
                "Variable": v.label,
                "Base Value": f"{v.base_value:.3f}",
                "NPV at Low": f"${v.npv_at_low:,.0f}",
                "NPV at High": f"${v.npv_at_high:,.0f}",
                "Swing (USD)": f"${v.npv_swing:,.0f}",
            }
        )
    st.dataframe(pd.DataFrame(raw_rows), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — Monte Carlo
# ─────────────────────────────────────────────────────────────────────────────
with tab_monte_carlo:
    st.header("🎲 Monte Carlo Simulation")
    st.markdown(
        "Runs thousands of randomized projections to produce a probability distribution "
        "of NPV outcomes. Inputs are sampled from calibrated distributions around base values."
    )

    mc_col1, mc_col2 = st.columns([2, 1])
    with mc_col1:
        iterations = st.slider(
            "Iterations",
            min_value=1_000,
            max_value=50_000,
            value=5_000,
            step=1_000,
        )
    with mc_col2:
        use_seed = st.checkbox("Fix random seed (seed=42)", value=True)
    mc_seed = 42 if use_seed else None

    from mmfm.engine.monte_carlo import run_monte_carlo

    @st.cache_data(show_spinner="Running Monte Carlo simulation...")
    def _run_mc(
        stall_income: float,
        capex: float,
        disc_rate: float,
        horizon: int,
        fcr: float,
        iters: int,
        seed,
    ):
        from mmfm.engine.projections import RevenueInputs, CapexInputs, OpexInputs

        revenue = RevenueInputs(
            base_stall_rental_income=stall_income,
            occupancy_rate=0.60,
            vendor_fees_annual=stall_income * 0.15,
            market_levies_annual=stall_income * 0.08,
            rental_escalation_rate=0.06,
            fee_escalation_rate=0.06,
            occupancy_ramp_years=3,
            occupancy_target=0.70,
            other_income_annual=0.0,
            fee_collection_rate=fcr,
        )
        capex_inputs = CapexInputs(
            total_capex=capex,
            construction_schedule={0: 0.60, 1: 0.40},
            overrun_contingency=0.10,
            grant_amount=0.0,
            grant_disbursement_year=0,
        )
        opex_inputs = OpexInputs(
            base_opex=stall_income * 0.30,
            opex_escalation_rate=0.05,
            debt_service_annual=capex * 0.08,
        )
        return run_monte_carlo(
            revenue=revenue,
            capex=capex_inputs,
            opex=opex_inputs,
            iterations=iters,
            seed=seed,
            discount_rate=disc_rate,
            horizon_years=horizon,
        )

    mc_result = _run_mc(
        base_stall_rental_income,
        total_capex,
        discount_rate,
        horizon_years,
        fee_collection_rate,
        iterations,
        mc_seed,
    )

    # ── NPV distribution histogram ───────────────────────────────────────────
    import plotly.express as px

    fig_hist = px.histogram(
        x=mc_result.npv_values,
        nbins=80,
        labels={"x": "NPV (USD)"},
        title=f"NPV Distribution ({mc_result.iterations:,} iterations)",
        color_discrete_sequence=["#3498db"],
    )
    fig_hist.add_vline(
        x=mc_result.npv_p10, line_dash="dash", line_color="#e74c3c",
        annotation_text="P10", annotation_position="top right",
    )
    fig_hist.add_vline(
        x=mc_result.npv_p50, line_dash="dash", line_color="orange",
        annotation_text="P50", annotation_position="top right",
    )
    fig_hist.add_vline(
        x=mc_result.npv_p90, line_dash="dash", line_color="#2ecc71",
        annotation_text="P90", annotation_position="top right",
    )
    fig_hist.add_vline(x=0, line_color="black", line_width=1.5)
    fig_hist.update_layout(height=420)
    st.plotly_chart(fig_hist, use_container_width=True)

    # ── Metric cards ─────────────────────────────────────────────────────────
    mc_m1, mc_m2, mc_m3, mc_m4, mc_m5 = st.columns(5)
    mc_m1.metric("P10 NPV", f"${mc_result.npv_p10:,.0f}")
    mc_m2.metric("P50 NPV (Median)", f"${mc_result.npv_p50:,.0f}")
    mc_m3.metric("P90 NPV", f"${mc_result.npv_p90:,.0f}")
    mc_m4.metric(
        "Prob. Positive NPV",
        f"{mc_result.prob_positive_npv:.0%}",
    )
    mc_m5.metric(
        "Prob. DSCR < 1.2",
        f"{mc_result.prob_dscr_below_threshold:.0%}",
    )

    if mc_result.input_npv_correlations:
        st.markdown("#### Input–NPV Correlations (Pearson r)")
        corr_rows = [
            {"Input Variable": k, "Correlation with NPV": f"{v:.3f}"}
            for k, v in mc_result.input_npv_correlations.items()
        ]
        st.dataframe(pd.DataFrame(corr_rows), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — AI Narrative
# ─────────────────────────────────────────────────────────────────────────────
with tab_ai:
    st.header("🤖 AI Narrative Generator")

    backend_env = os.environ.get("MMFM_LLM_BACKEND", "ollama")
    st.markdown(f"**Current LLM backend:** `{backend_env}`")

    st.info(
        "Using Ollama (free)? Run: `ollama serve`  then  `ollama pull llama3.2`  \n"
        "Using Claude? Set `MMFM_LLM_BACKEND=claude` and `ANTHROPIC_API_KEY` in your environment."
    )

    sample_data = {
        "market": "Chainda Market, Lusaka",
        "npv_usd": 290000,
        "irr_pct": 14.0,
        "payback_years": 10.5,
        "min_dscr": 1.28,
        "miri_score": 74,
        "governance_score": 82,
        "fee_collection_rate": 0.55,
        "total_capex_usd": 680000,
        "scenario": "base",
        "horizon_years": 20,
        "discount_rate_pct": 10,
    }

    import json

    financial_json = st.text_area(
        "Financial Data (JSON)",
        value=json.dumps(sample_data, indent=2),
        height=260,
    )

    if st.button("Generate Narrative", type="primary"):
        try:
            financial_data = json.loads(financial_json)
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
            st.stop()

        with st.spinner("Generating narrative..."):
            try:
                from mmfm.ai.narrator import generate_financial_narrative

                narrative = generate_financial_narrative(financial_data)

                with st.expander("Executive Summary", expanded=True):
                    st.markdown(narrative.get("executive_summary", "_No summary returned._"))

                with st.expander("Key Risks"):
                    risks = narrative.get("key_risks", [])
                    if isinstance(risks, list):
                        for risk in risks:
                            st.markdown(f"- {risk}")
                    else:
                        st.markdown(str(risks))

                with st.expander("Recommendation"):
                    rec = narrative.get("recommendation", "")
                    rec_lower = str(rec).lower()
                    if "proceed" in rec_lower and "condition" not in rec_lower and "do_not" not in rec_lower:
                        st.success(str(rec))
                    elif "condition" in rec_lower or "conditional" in rec_lower:
                        st.warning(str(rec))
                    else:
                        st.error(str(rec))

                with st.expander("Confidence Level"):
                    st.markdown(str(narrative.get("confidence_level", "_Not provided._")))

                with st.expander("Data Gaps"):
                    gaps = narrative.get("data_gaps", [])
                    if isinstance(gaps, list):
                        for gap in gaps:
                            st.markdown(f"- {gap}")
                    elif gaps:
                        st.markdown(str(gaps))
                    else:
                        st.markdown("_No data gaps reported._")

                with st.expander("Anomalies Flagged"):
                    anomalies = narrative.get("anomalies_flagged", [])
                    if isinstance(anomalies, list):
                        for a in anomalies:
                            st.markdown(f"- {a}")
                    elif anomalies:
                        st.markdown(str(anomalies))
                    else:
                        st.markdown("_No anomalies flagged._")

            except Exception as exc:
                st.warning(
                    f"Could not reach the LLM backend ({backend_env}). "
                    f"Error: `{exc}`  \n\n"
                    "**To fix with Ollama (free):**  \n"
                    "1. Install Ollama: https://ollama.com  \n"
                    "2. Run `ollama serve` in a terminal  \n"
                    "3. Run `ollama pull llama3.2`  \n"
                    "4. Reload this page and try again.  \n\n"
                    "**To use Claude API:**  \n"
                    "Set `MMFM_LLM_BACKEND=claude` and `ANTHROPIC_API_KEY=<your-key>` "
                    "in your environment before launching Streamlit."
                )
