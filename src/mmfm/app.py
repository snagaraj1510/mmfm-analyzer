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


def _build_inputs(sv: dict):
    """Construct engine input objects from sidebar state dict."""
    from mmfm.engine.projections import RevenueInputs, CapexInputs, OpexInputs

    rev_model_map = {
        "Simple": "simple",
        "Facility Types": "facility_types",
        "Produce Market": "produce",
        "Combined": "combined",
    }
    rev_model = rev_model_map.get(sv.get("revenue_model_type", "Simple"), "simple")

    revenue = RevenueInputs(
        base_stall_rental_income=sv.get("base_rental", 200_000),
        occupancy_rate=0.60,
        vendor_fees_annual=sv.get("base_rental", 200_000) * 0.15,
        market_levies_annual=sv.get("base_rental", 200_000) * 0.075,
        rental_escalation_rate=sv.get("fee_escalation", 0.03),
        fee_escalation_rate=sv.get("fee_escalation", 0.03),
        fee_collection_rate=sv.get("fee_collection_rate", 0.65),
        revenue_model=rev_model,
        lockup_count=int(sv.get("lockup_count", 0)),
        lockup_utilization=sv.get("lockup_util", 0.88),
        lockup_collection_rate=sv.get("lockup_coll", 0.46),
        lockup_monthly_rent_usd=sv.get("lockup_rent", 25.0),
        stall_count=int(sv.get("stall_count", 0)),
        stall_utilization=sv.get("stall_util", 0.56),
        stall_collection_rate=sv.get("stall_coll", 0.21),
        stall_monthly_rent_usd=sv.get("stall_rent", 5.0),
        pitch_count=int(sv.get("pitch_count", 0)),
        pitch_utilization=sv.get("pitch_util", 0.49),
        pitch_collection_rate=sv.get("pitch_coll", 0.23),
        pitch_monthly_rent_usd=sv.get("pitch_rent", 3.0),
        produce_throughput_tonnes=sv.get("produce_tonnes", 0.0),
        produce_price_usd_per_tonne=sv.get("produce_price", 380.0),
        commission_rate=sv.get("commission_rate_val", 0.05),
        food_waste_factor=sv.get("food_waste", 0.20),
    )

    capex = CapexInputs(
        total_capex=sv.get("total_capex", 1_000_000),
        construction_schedule={0: 0.60, 1: 0.40},
        overrun_contingency=sv.get("capex_overrun", 0.10),
        grant_amount=sv.get("grant_amount", 200_000),
        grant_disbursement_year=0,
        cold_storage_units=int(sv.get("cold_units", 0)),
        cold_storage_cost_per_m3=sv.get("cold_cost_m3", 1527.78),
        solar_pv_kw=float(sv.get("solar_kw", 0.0)),
        solar_pv_cost_per_kw=sv.get("solar_cost_kw", 1070.0),
    )

    opex_model_str = "pct_revenue" if sv.get("opex_model_choice") == "% of Revenue" else "fixed"
    opex = OpexInputs(
        base_opex=sv.get("base_opex", 80_000),
        opex_escalation_rate=sv.get("cost_escalation", 0.05),
        debt_service_annual=sv.get("debt_service", 50_000),
        opex_model=opex_model_str,
        cost_escalation_rate=sv.get("cost_escalation", 0.05),
        personnel_pct=sv.get("personnel_pct", 0.33),
        operations_pct=sv.get("operations_pct", 0.22),
        rm_pct=sv.get("rm_pct", 0.06),
        finance_admin_pct=sv.get("finance_admin_pct", 0.07),
    )

    return revenue, capex, opex


# ── Page config must be first Streamlit call ────────────────────────────────
st.set_page_config(
    page_title="MMFM Analyzer",
    page_icon="📊",
    layout="wide",
)

# ── Sidebar — always visible ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Model Parameters")

    # ── Revenue Model ──────────────────────────────────────────────────────
    with st.expander("💰 Revenue Model", expanded=True):
        revenue_model_type = st.radio(
            "Revenue type",
            ["Simple", "Facility Types", "Produce Market", "Combined"],
            help="Simple: single stall rental. Facility Types: lock-ups/stalls/pitches with real collection rates (ReMark data). Produce: commission on wholesale throughput.",
        )

        if revenue_model_type == "Simple":
            base_rental = st.slider("Annual Stall Rental Income (USD)", 50_000, 500_000, 200_000, 10_000, format="$%d")
            fee_collection_rate = st.slider(
                "Fee Collection Rate", 0.10, 1.0, 0.65, 0.05,
                help="Lusaka system avg: 38%. Well-managed: 65–85%.",
            )
            lockup_count = stall_count = pitch_count = 0
            lockup_util = stall_util = pitch_util = 0.0
            lockup_coll = stall_coll = pitch_coll = 1.0
            lockup_rent = stall_rent = pitch_rent = 0.0
            produce_tonnes = produce_price = commission_rate_val = food_waste = 0.0

        elif revenue_model_type == "Facility Types":
            base_rental = 0.0; fee_collection_rate = 1.0
            st.markdown("**Lock-up Facilities** (highest revenue)")
            c1, c2 = st.columns(2)
            lockup_count = c1.number_input("Count", 0, 2000, 530, 10, key="lu_cnt")
            lockup_rent = c2.number_input("Rent (USD/mo)", 1, 500, 25, key="lu_rent")
            lockup_util = st.slider("Utilisation", 0.0, 1.0, 0.88, 0.01, key="lu_util", format="%.0f%%")
            lockup_coll = st.slider("Collection Rate", 0.0, 1.0, 0.46, 0.01, key="lu_coll",
                format="%.0f%%", help="ReMark benchmark: 46%")
            st.markdown("**Market Stalls**")
            c1, c2 = st.columns(2)
            stall_count = c1.number_input("Count", 0, 5000, 980, 10, key="st_cnt")
            stall_rent = c2.number_input("Rent (USD/mo)", 1, 200, 5, key="st_rent")
            stall_util = st.slider("Utilisation", 0.0, 1.0, 0.56, 0.01, key="st_util", format="%.0f%%")
            stall_coll = st.slider("Collection Rate", 0.0, 1.0, 0.21, 0.01, key="st_coll",
                format="%.0f%%", help="ReMark benchmark: 21%")
            st.markdown("**Pitches / Open Spaces**")
            c1, c2 = st.columns(2)
            pitch_count = c1.number_input("Count", 0, 5000, 1400, 10, key="pt_cnt")
            pitch_rent = c2.number_input("Rent (USD/mo)", 1, 100, 3, key="pt_rent")
            pitch_util = st.slider("Utilisation", 0.0, 1.0, 0.49, 0.01, key="pt_util", format="%.0f%%")
            pitch_coll = st.slider("Collection Rate", 0.0, 1.0, 0.23, 0.01, key="pt_coll",
                format="%.0f%%", help="ReMark benchmark: 23%")
            produce_tonnes = produce_price = commission_rate_val = food_waste = 0.0

            # Live revenue estimate
            est_rev = (lockup_count * lockup_util * lockup_coll * lockup_rent * 12
                       + stall_count * stall_util * stall_coll * stall_rent * 12
                       + pitch_count * pitch_util * pitch_coll * pitch_rent * 12)
            st.metric("Est. Year 1 Revenue", f"${est_rev:,.0f}")

        elif revenue_model_type == "Produce Market":
            base_rental = 0.0; fee_collection_rate = 1.0
            lockup_count = stall_count = pitch_count = 0
            lockup_util = stall_util = pitch_util = lockup_coll = stall_coll = pitch_coll = 0.0
            lockup_rent = stall_rent = pitch_rent = 0.0
            produce_tonnes = st.slider("Annual Throughput (tonnes)", 100, 50_000, 5_000, 100)
            produce_price = st.slider("Produce Price (USD/tonne)", 50, 1_000, 380, 10)
            commission_rate_val = st.slider("Commission Rate", 0.01, 0.15, 0.05, 0.005, format="%.1f%%")
            food_waste = st.slider("Food Waste Factor", 0.05, 0.40, 0.20, 0.01,
                help="Cold storage reduces this. 20% is the ReMark baseline.")
            est_rev = produce_tonnes * (1 - food_waste) * produce_price * commission_rate_val
            st.metric("Est. Year 1 Revenue", f"${est_rev:,.0f}")

        else:  # Combined
            base_rental = 0.0; fee_collection_rate = 1.0
            st.markdown("**Lock-ups / Stalls / Pitches**")
            c1, c2 = st.columns(2)
            lockup_count = c1.number_input("Lock-ups", 0, 2000, 530, 10, key="lu_cnt")
            lockup_rent = c2.number_input("Lock-up Rent (USD/mo)", 1, 500, 25, key="lu_rent")
            lockup_util = st.slider("Lock-up Utilisation", 0.0, 1.0, 0.88, 0.01, key="lu_util", format="%.0f%%")
            lockup_coll = st.slider("Lock-up Collection", 0.0, 1.0, 0.46, 0.01, key="lu_coll", format="%.0f%%")
            c1, c2 = st.columns(2)
            stall_count = c1.number_input("Stalls", 0, 5000, 980, 10, key="st_cnt")
            stall_rent = c2.number_input("Stall Rent (USD/mo)", 1, 200, 5, key="st_rent")
            stall_util = st.slider("Stall Utilisation", 0.0, 1.0, 0.56, 0.01, key="st_util", format="%.0f%%")
            stall_coll = st.slider("Stall Collection", 0.0, 1.0, 0.21, 0.01, key="st_coll", format="%.0f%%")
            c1, c2 = st.columns(2)
            pitch_count = c1.number_input("Pitches", 0, 5000, 1400, 10, key="pt_cnt")
            pitch_rent = c2.number_input("Pitch Rent (USD/mo)", 1, 100, 3, key="pt_rent")
            pitch_util = st.slider("Pitch Utilisation", 0.0, 1.0, 0.49, 0.01, key="pt_util", format="%.0f%%")
            pitch_coll = st.slider("Pitch Collection", 0.0, 1.0, 0.23, 0.01, key="pt_coll", format="%.0f%%")
            st.markdown("**Produce Revenue**")
            produce_tonnes = st.slider("Throughput (tonnes/yr)", 100, 50_000, 2_000, 100)
            produce_price = st.slider("Produce Price (USD/tonne)", 50, 1_000, 380, 10)
            commission_rate_val = st.slider("Commission Rate", 0.01, 0.15, 0.05, 0.005, format="%.1f%%")
            food_waste = st.slider("Food Waste Factor", 0.05, 0.40, 0.20, 0.01)

        fee_escalation = st.slider("Fee Escalation/yr", 0.0, 0.15, 0.03, 0.01, format="%.0f%%",
            help="Annual rental/fee growth rate (ReMark: 3%)")

    # ── Capital Costs ──────────────────────────────────────────────────────
    with st.expander("🏗️ Capital Costs", expanded=True):
        total_capex = st.slider("Construction CapEx (USD)", 200_000, 5_000_000, 1_000_000, 50_000, format="$%d")
        grant_amount = st.slider("Grant / Subsidy (USD)", 0, 2_000_000, 200_000, 50_000, format="$%d")
        capex_overrun = st.slider("Contingency", 0.0, 0.50, 0.10, 0.05, format="%.0f%%",
            help="Expected cost overrun above budget (10% is standard)")

        st.markdown("**Technology Modules**")
        col_cs, col_sol = st.columns(2)
        cold_storage_on = col_cs.checkbox("❄️ Cold Storage")
        solar_on = col_sol.checkbox("☀️ Solar PV")

        if cold_storage_on:
            cold_units = st.number_input("Cold Storage Rooms", 1, 200, 9)
            cold_cost_m3 = st.number_input("Install Cost (USD/m³)", 500, 5_000, 1_528,
                help="ICLEI Africa benchmark: $1,528/m³")
        else:
            cold_units, cold_cost_m3 = 0, 1527.78

        if solar_on:
            solar_kw = float(st.number_input("Solar Capacity (kW)", 10, 5_000, 150))
            solar_cost_kw = st.number_input("Install Cost (USD/kW)", 500, 3_000, 1_070,
                help="ICLEI Africa benchmark: $1,070/kW")
        else:
            solar_kw, solar_cost_kw = 0.0, 1070.0

        # Show total capex estimate
        tech_capex = cold_units * 18.0 * cold_cost_m3 + solar_kw * solar_cost_kw
        total_with_overrun = total_capex * (1 + capex_overrun) + tech_capex - grant_amount
        st.metric("Net CapEx (after grant + tech)", f"${max(total_with_overrun, 0):,.0f}")

    # ── Operating Costs ────────────────────────────────────────────────────
    with st.expander("⚙️ Operating Costs"):
        opex_model_choice = st.radio(
            "OpEx model",
            ["Fixed Amount", "% of Revenue"],
            help="Fixed: set a dollar amount. % of Revenue scales with the market — more realistic for large markets.",
        )
        if opex_model_choice == "Fixed Amount":
            base_opex = st.slider("Annual OpEx (USD)", 20_000, 500_000, 80_000, 5_000, format="$%d")
            personnel_pct = operations_pct = rm_pct = finance_admin_pct = 0.0
        else:
            base_opex = 0
            st.caption("Cost structure (% of annual revenue) — ReMark Type A benchmarks:")
            personnel_pct = st.slider("Personnel", 0.10, 0.50, 0.33, 0.01, format="%.0f%%")
            operations_pct = st.slider("Operations", 0.05, 0.40, 0.22, 0.01, format="%.0f%%")
            rm_pct = st.slider("Repairs & Maintenance", 0.02, 0.20, 0.06, 0.01, format="%.0f%%")
            finance_admin_pct = st.slider("Finance & Admin", 0.02, 0.20, 0.07, 0.01, format="%.0f%%")
            st.metric("Total OpEx ratio", f"{personnel_pct + operations_pct + rm_pct + finance_admin_pct:.0%}")

        cost_escalation = st.slider("Cost Escalation/yr", 0.0, 0.15, 0.05, 0.01, format="%.0f%%",
            help="Annual cost growth (typically 5%, higher than fee escalation)")

    # ── Financing ──────────────────────────────────────────────────────────
    with st.expander("🏦 Financing"):
        financing_model = st.radio(
            "Financing model",
            ["Simple", "Structured Debt"],
            help="Simple: enter annual payment directly. Structured: set loan amounts + rates, payment is auto-calculated.",
        )
        if financing_model == "Simple":
            debt_service = st.slider("Annual Debt Service (USD)", 0, 300_000, 50_000, 5_000, format="$%d")
        else:
            st.markdown("**Senior Debt** (commercial)")
            c1, c2, c3 = st.columns(3)
            senior_amt = c1.number_input("Amount (USD)", 0, 5_000_000, 300_000, 50_000, key="s_amt")
            senior_rate_val = c2.slider("Rate", 0.05, 0.20, 0.10, 0.005, key="s_rate", format="%.1f%%")
            senior_tenor = c3.slider("Tenor (yrs)", 3, 15, 8, key="s_tenor")
            st.markdown("**Concessional Debt** (subordinate)")
            c1, c2, c3 = st.columns(3)
            sub_amt = c1.number_input("Amount (USD)", 0, 5_000_000, 200_000, 50_000, key="sub_amt")
            sub_rate_val = c2.slider("Rate", 0.01, 0.12, 0.065, 0.005, key="sub_rate", format="%.1f%%")
            sub_tenor = c3.slider("Tenor (yrs)", 5, 20, 10, key="sub_tenor")
            try:
                from mmfm.engine.projections import DebtStructure, calculate_debt_service
                debt_service = calculate_debt_service(DebtStructure(
                    senior_debt_amount=senior_amt, senior_rate=senior_rate_val, senior_tenor_years=senior_tenor,
                    subordinate_debt_amount=sub_amt, subordinate_rate=sub_rate_val, subordinate_tenor_years=sub_tenor,
                ))
            except Exception:
                debt_service = 50_000
            st.metric("→ Annual Debt Service", f"${debt_service:,.0f}")

    # ── Market Parameters ──────────────────────────────────────────────────
    with st.expander("📊 Market Parameters"):
        discount_rate = st.slider("Discount Rate", 0.05, 0.25, 0.10, 0.01, format="%.0f%%")
        horizon_years = st.slider("Projection Horizon (years)", 10, 30, 20, 5)
        inflation_rate = st.slider("Inflation Rate", 0.02, 0.15, 0.05, 0.01, format="%.0f%%")

    st.markdown("---")
    st.markdown("### About")
    st.markdown("Built by **Shreyas**  \nMichigan Ross MBA 2026  \nICLEI Africa MAP Capstone")
    st.markdown("[GitHub](https://github.com/snagaraj1510/mmfm-analyzer)")

_sv = {
    "revenue_model_type": revenue_model_type,
    "base_rental": base_rental,
    "fee_collection_rate": fee_collection_rate,
    "lockup_count": lockup_count, "lockup_util": lockup_util,
    "lockup_coll": lockup_coll, "lockup_rent": lockup_rent,
    "stall_count": stall_count, "stall_util": stall_util,
    "stall_coll": stall_coll, "stall_rent": stall_rent,
    "pitch_count": pitch_count, "pitch_util": pitch_util,
    "pitch_coll": pitch_coll, "pitch_rent": pitch_rent,
    "produce_tonnes": produce_tonnes, "produce_price": produce_price,
    "commission_rate_val": commission_rate_val, "food_waste": food_waste,
    "fee_escalation": fee_escalation,
    "total_capex": total_capex, "grant_amount": grant_amount,
    "capex_overrun": capex_overrun,
    "cold_units": cold_units, "cold_cost_m3": cold_cost_m3,
    "solar_kw": solar_kw, "solar_cost_kw": solar_cost_kw,
    "opex_model_choice": opex_model_choice,
    "base_opex": base_opex,
    "personnel_pct": personnel_pct, "operations_pct": operations_pct,
    "rm_pct": rm_pct, "finance_admin_pct": finance_admin_pct,
    "cost_escalation": cost_escalation,
    "debt_service": debt_service,
    "discount_rate": discount_rate, "horizon_years": horizon_years,
    "inflation_rate": inflation_rate,
}
revenue_inputs, capex_inputs, opex_inputs = _build_inputs(_sv)


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
    from mmfm.engine.scenarios import run_all_scenarios

    @st.cache_data(show_spinner="Running scenario analysis...")
    def _run_scenarios(
        base_rental: float,
        fee_collection_rate: float,
        fee_escalation: float,
        revenue_model_type: str,
        lockup_count: int,
        lockup_util: float,
        lockup_coll: float,
        lockup_rent: float,
        stall_count: int,
        stall_util: float,
        stall_coll: float,
        stall_rent: float,
        pitch_count: int,
        pitch_util: float,
        pitch_coll: float,
        pitch_rent: float,
        produce_tonnes: float,
        produce_price: float,
        commission_rate_val: float,
        food_waste: float,
        total_capex: float,
        grant_amount: float,
        capex_overrun: float,
        cold_units: int,
        cold_cost_m3: float,
        solar_kw: float,
        solar_cost_kw: float,
        opex_model_choice: str,
        base_opex: float,
        personnel_pct: float,
        operations_pct: float,
        rm_pct: float,
        finance_admin_pct: float,
        cost_escalation: float,
        debt_service: float,
        disc_rate: float,
        horizon: int,
    ):
        sv = dict(
            revenue_model_type=revenue_model_type,
            base_rental=base_rental,
            fee_collection_rate=fee_collection_rate,
            lockup_count=lockup_count, lockup_util=lockup_util,
            lockup_coll=lockup_coll, lockup_rent=lockup_rent,
            stall_count=stall_count, stall_util=stall_util,
            stall_coll=stall_coll, stall_rent=stall_rent,
            pitch_count=pitch_count, pitch_util=pitch_util,
            pitch_coll=pitch_coll, pitch_rent=pitch_rent,
            produce_tonnes=produce_tonnes, produce_price=produce_price,
            commission_rate_val=commission_rate_val, food_waste=food_waste,
            fee_escalation=fee_escalation,
            total_capex=total_capex, grant_amount=grant_amount,
            capex_overrun=capex_overrun,
            cold_units=cold_units, cold_cost_m3=cold_cost_m3,
            solar_kw=solar_kw, solar_cost_kw=solar_cost_kw,
            opex_model_choice=opex_model_choice,
            base_opex=base_opex,
            personnel_pct=personnel_pct, operations_pct=operations_pct,
            rm_pct=rm_pct, finance_admin_pct=finance_admin_pct,
            cost_escalation=cost_escalation,
            debt_service=debt_service,
        )
        revenue, capex_inp, opex_inp = _build_inputs(sv)
        comparison = run_all_scenarios(
            revenue=revenue,
            capex=capex_inp,
            opex=opex_inp,
            discount_rate=disc_rate,
            horizon_years=horizon,
        )
        return comparison

    comparison = _run_scenarios(
        base_rental=_sv["base_rental"],
        fee_collection_rate=_sv["fee_collection_rate"],
        fee_escalation=_sv["fee_escalation"],
        revenue_model_type=_sv["revenue_model_type"],
        lockup_count=_sv["lockup_count"],
        lockup_util=_sv["lockup_util"],
        lockup_coll=_sv["lockup_coll"],
        lockup_rent=_sv["lockup_rent"],
        stall_count=_sv["stall_count"],
        stall_util=_sv["stall_util"],
        stall_coll=_sv["stall_coll"],
        stall_rent=_sv["stall_rent"],
        pitch_count=_sv["pitch_count"],
        pitch_util=_sv["pitch_util"],
        pitch_coll=_sv["pitch_coll"],
        pitch_rent=_sv["pitch_rent"],
        produce_tonnes=_sv["produce_tonnes"],
        produce_price=_sv["produce_price"],
        commission_rate_val=_sv["commission_rate_val"],
        food_waste=_sv["food_waste"],
        total_capex=_sv["total_capex"],
        grant_amount=_sv["grant_amount"],
        capex_overrun=_sv["capex_overrun"],
        cold_units=_sv["cold_units"],
        cold_cost_m3=_sv["cold_cost_m3"],
        solar_kw=_sv["solar_kw"],
        solar_cost_kw=_sv["solar_cost_kw"],
        opex_model_choice=_sv["opex_model_choice"],
        base_opex=_sv["base_opex"],
        personnel_pct=_sv["personnel_pct"],
        operations_pct=_sv["operations_pct"],
        rm_pct=_sv["rm_pct"],
        finance_admin_pct=_sv["finance_admin_pct"],
        cost_escalation=_sv["cost_escalation"],
        debt_service=_sv["debt_service"],
        disc_rate=_sv["discount_rate"],
        horizon=_sv["horizon_years"],
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

    import pandas as pd
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
    import plotly.graph_objects as go
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
        base_rental: float,
        fee_collection_rate: float,
        fee_escalation: float,
        revenue_model_type: str,
        lockup_count: int,
        lockup_util: float,
        lockup_coll: float,
        lockup_rent: float,
        stall_count: int,
        stall_util: float,
        stall_coll: float,
        stall_rent: float,
        pitch_count: int,
        pitch_util: float,
        pitch_coll: float,
        pitch_rent: float,
        produce_tonnes: float,
        produce_price: float,
        commission_rate_val: float,
        food_waste: float,
        total_capex: float,
        grant_amount: float,
        capex_overrun: float,
        cold_units: int,
        cold_cost_m3: float,
        solar_kw: float,
        solar_cost_kw: float,
        opex_model_choice: str,
        base_opex: float,
        personnel_pct: float,
        operations_pct: float,
        rm_pct: float,
        finance_admin_pct: float,
        cost_escalation: float,
        debt_service: float,
        disc_rate: float,
        inflation: float,
        horizon: int,
    ):
        sv = dict(
            revenue_model_type=revenue_model_type,
            base_rental=base_rental,
            fee_collection_rate=fee_collection_rate,
            lockup_count=lockup_count, lockup_util=lockup_util,
            lockup_coll=lockup_coll, lockup_rent=lockup_rent,
            stall_count=stall_count, stall_util=stall_util,
            stall_coll=stall_coll, stall_rent=stall_rent,
            pitch_count=pitch_count, pitch_util=pitch_util,
            pitch_coll=pitch_coll, pitch_rent=pitch_rent,
            produce_tonnes=produce_tonnes, produce_price=produce_price,
            commission_rate_val=commission_rate_val, food_waste=food_waste,
            fee_escalation=fee_escalation,
            total_capex=total_capex, grant_amount=grant_amount,
            capex_overrun=capex_overrun,
            cold_units=cold_units, cold_cost_m3=cold_cost_m3,
            solar_kw=solar_kw, solar_cost_kw=solar_cost_kw,
            opex_model_choice=opex_model_choice,
            base_opex=base_opex,
            personnel_pct=personnel_pct, operations_pct=operations_pct,
            rm_pct=rm_pct, finance_admin_pct=finance_admin_pct,
            cost_escalation=cost_escalation,
            debt_service=debt_service,
        )
        revenue, capex_inp, opex_inp = _build_inputs(sv)
        return run_sensitivity(
            revenue=revenue,
            capex=capex_inp,
            opex=opex_inp,
            discount_rate=disc_rate,
            inflation_rate=inflation,
            horizon_years=horizon,
        )

    sens_result = _run_sensitivity(
        base_rental=_sv["base_rental"],
        fee_collection_rate=_sv["fee_collection_rate"],
        fee_escalation=_sv["fee_escalation"],
        revenue_model_type=_sv["revenue_model_type"],
        lockup_count=_sv["lockup_count"],
        lockup_util=_sv["lockup_util"],
        lockup_coll=_sv["lockup_coll"],
        lockup_rent=_sv["lockup_rent"],
        stall_count=_sv["stall_count"],
        stall_util=_sv["stall_util"],
        stall_coll=_sv["stall_coll"],
        stall_rent=_sv["stall_rent"],
        pitch_count=_sv["pitch_count"],
        pitch_util=_sv["pitch_util"],
        pitch_coll=_sv["pitch_coll"],
        pitch_rent=_sv["pitch_rent"],
        produce_tonnes=_sv["produce_tonnes"],
        produce_price=_sv["produce_price"],
        commission_rate_val=_sv["commission_rate_val"],
        food_waste=_sv["food_waste"],
        total_capex=_sv["total_capex"],
        grant_amount=_sv["grant_amount"],
        capex_overrun=_sv["capex_overrun"],
        cold_units=_sv["cold_units"],
        cold_cost_m3=_sv["cold_cost_m3"],
        solar_kw=_sv["solar_kw"],
        solar_cost_kw=_sv["solar_cost_kw"],
        opex_model_choice=_sv["opex_model_choice"],
        base_opex=_sv["base_opex"],
        personnel_pct=_sv["personnel_pct"],
        operations_pct=_sv["operations_pct"],
        rm_pct=_sv["rm_pct"],
        finance_admin_pct=_sv["finance_admin_pct"],
        cost_escalation=_sv["cost_escalation"],
        debt_service=_sv["debt_service"],
        disc_rate=_sv["discount_rate"],
        inflation=_sv["inflation_rate"],
        horizon=_sv["horizon_years"],
    )

    tornado_vars = sens_result.tornado_order()
    base_npv = sens_result.base_npv

    # Build tornado chart data
    labels = [v.label for v in tornado_vars]
    low_delta = [v.npv_at_low - base_npv for v in tornado_vars]
    high_delta = [v.npv_at_high - base_npv for v in tornado_vars]

    import plotly.graph_objects as go
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
    import pandas as pd
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
        base_rental: float,
        fee_collection_rate: float,
        fee_escalation: float,
        revenue_model_type: str,
        lockup_count: int,
        lockup_util: float,
        lockup_coll: float,
        lockup_rent: float,
        stall_count: int,
        stall_util: float,
        stall_coll: float,
        stall_rent: float,
        pitch_count: int,
        pitch_util: float,
        pitch_coll: float,
        pitch_rent: float,
        produce_tonnes: float,
        produce_price: float,
        commission_rate_val: float,
        food_waste: float,
        total_capex: float,
        grant_amount: float,
        capex_overrun: float,
        cold_units: int,
        cold_cost_m3: float,
        solar_kw: float,
        solar_cost_kw: float,
        opex_model_choice: str,
        base_opex: float,
        personnel_pct: float,
        operations_pct: float,
        rm_pct: float,
        finance_admin_pct: float,
        cost_escalation: float,
        debt_service: float,
        disc_rate: float,
        horizon: int,
        iters: int,
        seed,
    ):
        sv = dict(
            revenue_model_type=revenue_model_type,
            base_rental=base_rental,
            fee_collection_rate=fee_collection_rate,
            lockup_count=lockup_count, lockup_util=lockup_util,
            lockup_coll=lockup_coll, lockup_rent=lockup_rent,
            stall_count=stall_count, stall_util=stall_util,
            stall_coll=stall_coll, stall_rent=stall_rent,
            pitch_count=pitch_count, pitch_util=pitch_util,
            pitch_coll=pitch_coll, pitch_rent=pitch_rent,
            produce_tonnes=produce_tonnes, produce_price=produce_price,
            commission_rate_val=commission_rate_val, food_waste=food_waste,
            fee_escalation=fee_escalation,
            total_capex=total_capex, grant_amount=grant_amount,
            capex_overrun=capex_overrun,
            cold_units=cold_units, cold_cost_m3=cold_cost_m3,
            solar_kw=solar_kw, solar_cost_kw=solar_cost_kw,
            opex_model_choice=opex_model_choice,
            base_opex=base_opex,
            personnel_pct=personnel_pct, operations_pct=operations_pct,
            rm_pct=rm_pct, finance_admin_pct=finance_admin_pct,
            cost_escalation=cost_escalation,
            debt_service=debt_service,
        )
        revenue, capex_inp, opex_inp = _build_inputs(sv)
        return run_monte_carlo(
            revenue=revenue,
            capex=capex_inp,
            opex=opex_inp,
            iterations=iters,
            seed=seed,
            discount_rate=disc_rate,
            horizon_years=horizon,
        )

    mc_result = _run_mc(
        base_rental=_sv["base_rental"],
        fee_collection_rate=_sv["fee_collection_rate"],
        fee_escalation=_sv["fee_escalation"],
        revenue_model_type=_sv["revenue_model_type"],
        lockup_count=_sv["lockup_count"],
        lockup_util=_sv["lockup_util"],
        lockup_coll=_sv["lockup_coll"],
        lockup_rent=_sv["lockup_rent"],
        stall_count=_sv["stall_count"],
        stall_util=_sv["stall_util"],
        stall_coll=_sv["stall_coll"],
        stall_rent=_sv["stall_rent"],
        pitch_count=_sv["pitch_count"],
        pitch_util=_sv["pitch_util"],
        pitch_coll=_sv["pitch_coll"],
        pitch_rent=_sv["pitch_rent"],
        produce_tonnes=_sv["produce_tonnes"],
        produce_price=_sv["produce_price"],
        commission_rate_val=_sv["commission_rate_val"],
        food_waste=_sv["food_waste"],
        total_capex=_sv["total_capex"],
        grant_amount=_sv["grant_amount"],
        capex_overrun=_sv["capex_overrun"],
        cold_units=_sv["cold_units"],
        cold_cost_m3=_sv["cold_cost_m3"],
        solar_kw=_sv["solar_kw"],
        solar_cost_kw=_sv["solar_cost_kw"],
        opex_model_choice=_sv["opex_model_choice"],
        base_opex=_sv["base_opex"],
        personnel_pct=_sv["personnel_pct"],
        operations_pct=_sv["operations_pct"],
        rm_pct=_sv["rm_pct"],
        finance_admin_pct=_sv["finance_admin_pct"],
        cost_escalation=_sv["cost_escalation"],
        debt_service=_sv["debt_service"],
        disc_rate=_sv["discount_rate"],
        horizon=_sv["horizon_years"],
        iters=iterations,
        seed=mc_seed,
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

    import pandas as pd
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
