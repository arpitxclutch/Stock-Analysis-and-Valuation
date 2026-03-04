"""
Damodaran DCF Valuation Models
==============================
Implements:
  - Model Selector (model1.xls logic) with full Q&A trail
  - DDM   (Stable, 2-stage, 3-stage) with year-by-year tables
  - FCFE  (Stable, 2-stage, 3-stage) with year-by-year tables
  - FCFF  (Stable, 2-stage, 3-stage) with year-by-year tables

Every model returns:
  - intrinsic value
  - year_by_year: list of dicts (one per year) for tabular display
  - summary: key aggregates
"""

import numpy as np


# ═════════════════════════════════════════════════════════════════════════════
#  MODEL SELECTOR with full decision trail
# ═════════════════════════════════════════════════════════════════════════════

def choose_valuation_model(inputs: dict) -> dict:
    """
    Replicates Damodaran's 'Choosing the Right Valuation Model' (model1.xls).
    Returns the model choice AND the full Q&A decision trail.
    """

    economy_growth = inputs["inflation_rate"] + inputs["real_growth_rate"]
    firm_g = inputs["firm_growth_rate"]
    dr = inputs["debt_ratio"]

    # Compute FCFE
    fcfe = (
        inputs["net_income"]
        - (inputs["capex"] - inputs["depreciation"]) * (1 - dr)
        - inputs["delta_wc"] * (1 - dr)
    )

    # ── Build Q&A trail ─────────────────────────────────────────────────────
    qa = []
    qa.append({
        "question": "Level of Earnings",
        "answer": f"{inputs.get('currency', '$')}{inputs['net_income']:,.0f} {inputs.get('unit', '')}",
    })
    qa.append({
        "question": "Are your earnings positive?",
        "answer": "Yes" if inputs["earnings_positive"] else "No",
    })

    if inputs["earnings_positive"]:
        qa.append({
            "question": "What is the expected inflation rate in the economy?",
            "answer": f"{inputs['inflation_rate']:.2%}",
        })
        qa.append({
            "question": "What is the expected real growth rate in the economy?",
            "answer": f"{inputs['real_growth_rate']:.2%}",
        })
        qa.append({
            "question": "Implied nominal growth rate of the economy (inflation + real growth)?",
            "answer": f"{economy_growth:.2%}",
        })
        qa.append({
            "question": "What is the expected growth rate in earnings for this firm?",
            "answer": f"{firm_g:.2%}",
        })
        qa.append({
            "question": "Does this firm have a significant and sustainable competitive advantage?",
            "answer": "Yes" if inputs["has_competitive_adv"] else "No",
            "note": ("Differential advantages include: legal monopoly, technological edge, "
                     "strong brand name, or economies of scale — both existing and future."),
        })
    else:
        qa.append({
            "question": "Are the earnings negative because the firm is in a cyclical business?",
            "answer": "Yes" if inputs.get("cyclical_negative") else "No",
        })
        qa.append({
            "question": "Are the earnings negative because of a one-time or temporary occurrence?",
            "answer": "Yes" if inputs.get("temporary_negative") else "No",
        })
        qa.append({
            "question": "Are the earnings negative because the firm has too much debt?",
            "answer": "Yes" if inputs.get("excess_debt_negative") else "No",
        })
        if inputs.get("excess_debt_negative"):
            qa.append({
                "question": "If yes, is there a strong likelihood of bankruptcy?",
                "answer": "Yes" if inputs.get("bankruptcy_likely") else "No",
            })
        qa.append({
            "question": "Are the earnings negative because the firm is just starting up?",
            "answer": "Yes" if inputs.get("startup_negative") else "No",
        })

    # Financial leverage
    qa.append({
        "section": "Financial Leverage",
        "question": "What is the current debt ratio (in market value terms)?",
        "answer": f"{dr:.2%}",
    })
    qa.append({
        "question": "Is this debt ratio expected to change significantly?",
        "answer": "Yes" if inputs["debt_ratio_changing"] else "No",
    })

    # Dividend policy
    qa.append({
        "section": "Dividend Policy",
        "question": "What did the firm pay out as dividends in the current year?",
        "answer": f"{inputs.get('currency', '$')}{inputs['dividends']:,.2f} {inputs.get('unit', '')}",
    })
    qa.append({
        "question": "Can you estimate capital expenditures and working capital requirements?",
        "answer": "Yes" if inputs["can_estimate_capex"] else "No",
    })

    # FCFE computation trail
    qa.append({
        "section": "FCFE Computation",
        "question": "Net Income (NI)",
        "answer": f"{inputs.get('currency', '$')}{inputs['net_income']:,.2f}",
    })
    qa.append({
        "question": "Depreciation and Amortization",
        "answer": f"{inputs.get('currency', '$')}{inputs['depreciation']:,.2f}",
    })
    qa.append({
        "question": "Capital Spending (incl. acquisitions)",
        "answer": f"{inputs.get('currency', '$')}{inputs['capex']:,.2f}",
    })
    qa.append({
        "question": "Δ Non-cash Working Capital (ΔWC)",
        "answer": f"{inputs.get('currency', '$')}{inputs['delta_wc']:,.2f}",
    })
    qa.append({
        "question": "FCFE = NI - (CapEx - Dep)×(1-DR) - ΔWC×(1-DR)",
        "answer": f"{inputs.get('currency', '$')}{fcfe:,.2f}",
        "formula": (f"= {inputs['net_income']:,.2f} "
                    f"- ({inputs['capex']:,.2f} - {inputs['depreciation']:,.2f})×(1-{dr:.4f}) "
                    f"- {inputs['delta_wc']:,.2f}×(1-{dr:.4f})"),
    })

    # ── Decision logic ──────────────────────────────────────────────────────
    result = {
        "model_type": "",
        "earnings_level": "",
        "cashflow_type": "",
        "growth_period": "",
        "growth_pattern": "",
        "model_code": "",
        "model_description": "",
        "decision_trail": [],
        "qa_inputs": qa,
    }

    trail = []

    # Model type
    if inputs["earnings_positive"]:
        result["model_type"] = "Discounted CF Model"
        result["earnings_level"] = "Current Earnings"
        trail.append("✅ Earnings are positive → Use Discounted Cash Flow model with current earnings.")
    else:
        if inputs.get("cyclical_negative") or inputs.get("temporary_negative"):
            result["model_type"] = "Discounted CF Model"
            result["earnings_level"] = "Normalized Earnings"
            trail.append("⚠️ Earnings negative due to cyclical/temporary factors → Normalize earnings, then use DCF.")
        elif inputs.get("excess_debt_negative"):
            if inputs.get("bankruptcy_likely"):
                result["model_type"] = "Option Pricing Model"
                result["earnings_level"] = "Current Earnings"
                trail.append("🔴 Earnings negative due to excess debt with bankruptcy risk → Use Option Pricing Model.")
            else:
                result["model_type"] = "Discounted CF Model"
                result["earnings_level"] = "Normalized Earnings"
                trail.append("⚠️ Earnings negative due to excess debt but no bankruptcy → Normalize earnings, use DCF.")
        elif inputs.get("startup_negative"):
            result["model_type"] = "Discounted CF Model"
            result["earnings_level"] = "Current Earnings"
            trail.append("⚠️ Startup with negative earnings → Use DCF with projected revenue growth path.")
        else:
            result["model_type"] = "Discounted CF Model"
            result["earnings_level"] = "Normalized Earnings"
            trail.append("⚠️ Earnings negative (other reason) → Normalize earnings, use DCF.")

    # Cashflow type
    if inputs["debt_ratio_changing"]:
        result["cashflow_type"] = "FCFF (Value firm)"
        trail.append(
            f"📊 Debt ratio ({dr:.1%}) is expected to change significantly → "
            f"Use FCFF to value the entire firm, then subtract debt."
        )
    elif inputs["can_estimate_capex"]:
        div_payout = inputs["dividends"]
        if abs(fcfe) > 0 and abs(fcfe - div_payout) / max(abs(fcfe), 1) > 0.20:
            result["cashflow_type"] = "FCFE (Value equity)"
            trail.append(
                f"📊 Dividends ({inputs.get('currency','$')}{div_payout:,.0f}) differ "
                f"significantly from FCFE ({inputs.get('currency','$')}{fcfe:,.0f}) → Use FCFE model."
            )
        else:
            result["cashflow_type"] = "Dividends"
            trail.append(
                f"📊 Dividends ({inputs.get('currency','$')}{div_payout:,.0f}) ≈ "
                f"FCFE ({inputs.get('currency','$')}{fcfe:,.0f}) → Use Dividend Discount Model."
            )
    else:
        result["cashflow_type"] = "Dividends"
        trail.append("📊 Cannot estimate CapEx/WC → Default to Dividend Discount Model.")

    # Growth period & pattern
    if firm_g <= economy_growth * 1.1:
        result["growth_period"] = "Stable"
        result["growth_pattern"] = "Stable Growth"
        trail.append(
            f"📈 Firm growth ({firm_g:.1%}) ≈ Economy growth ({economy_growth:.1%}) → Stable growth model."
        )
    elif firm_g <= economy_growth * 2.0:
        result["growth_period"] = "5 to 10 years"
        result["growth_pattern"] = "Two-stage Growth"
        trail.append(
            f"📈 Firm growth ({firm_g:.1%}) is moderately above economy ({economy_growth:.1%}) "
            f"→ Two-stage model (high growth for 5-10 yrs, then stable)."
        )
    else:
        if inputs["has_competitive_adv"]:
            result["growth_period"] = "10 or more years"
            result["growth_pattern"] = "Three-stage Growth"
            trail.append(
                f"📈 Firm growth ({firm_g:.1%}) >> Economy ({economy_growth:.1%}) "
                f"AND has sustainable competitive advantage → Three-stage model."
            )
        else:
            result["growth_period"] = "5 to 10 years"
            result["growth_pattern"] = "Two-stage Growth"
            trail.append(
                f"📈 Firm growth ({firm_g:.1%}) >> Economy ({economy_growth:.1%}) "
                f"BUT no sustainable advantage → Two-stage (growth will fade faster)."
            )

    result["decision_trail"] = trail

    # Map to model code
    cf = result["cashflow_type"]
    pat = result["growth_pattern"]

    model_map = {
        ("Dividends", "Stable Growth"):                 ("ddmst",   "Stable Growth DDM (Gordon Growth Model)"),
        ("Dividends", "Two-stage Growth"):              ("ddm2st",  "Two-Stage Dividend Discount Model"),
        ("Dividends", "Three-stage Growth"):            ("ddm3st",  "Three-Stage Dividend Discount Model"),
        ("FCFE (Value equity)", "Stable Growth"):       ("fcfest",  "Stable Growth FCFE Model"),
        ("FCFE (Value equity)", "Two-stage Growth"):    ("fcfe2st", "Two-Stage FCFE Discount Model"),
        ("FCFE (Value equity)", "Three-stage Growth"):  ("fcfe3st", "Three-Stage FCFE Discount Model"),
        ("FCFF (Value firm)", "Stable Growth"):         ("fcffst",  "Stable Growth FCFF Model"),
        ("FCFF (Value firm)", "Two-stage Growth"):      ("fcff2st", "Two-Stage FCFF Discount Model"),
        ("FCFF (Value firm)", "Three-stage Growth"):    ("fcff3st", "Three-Stage FCFF Discount Model"),
    }

    key = (cf, pat)
    if key in model_map:
        result["model_code"], result["model_description"] = model_map[key]
    else:
        result["model_code"] = "fcff2st"
        result["model_description"] = "Two-Stage FCFF (Default Fallback)"

    trail.append(f"✅ SELECTED MODEL: **{result['model_description']}** (`{result['model_code']}.xls`)")

    return result


# ═════════════════════════════════════════════════════════════════════════════
#  HELPER: compute FCFE & FCFF
# ═════════════════════════════════════════════════════════════════════════════

def compute_fcfe(net_income, depreciation, capex, delta_wc, debt_ratio):
    return net_income - (capex - depreciation) * (1 - debt_ratio) - delta_wc * (1 - debt_ratio)


def compute_fcff(ebit, tax_rate, depreciation, capex, delta_wc):
    return ebit * (1 - tax_rate) + depreciation - capex - delta_wc


# ═════════════════════════════════════════════════════════════════════════════
#  DDM MODELS — with year-by-year tables
# ═════════════════════════════════════════════════════════════════════════════

def ddm_stable(dps, cost_of_equity, stable_growth):
    """Gordon Growth Model with explicit calculation."""
    ke, g = cost_of_equity, stable_growth
    if ke <= g:
        return {"error": "Cost of equity must exceed stable growth rate"}

    dps1 = dps * (1 + g)
    value = dps1 / (ke - g)

    year_by_year = [{
        "Year": "Terminal (∞)",
        "Dividend": dps1,
        "Growth Rate": g,
        "Discount Rate": ke,
        "PV Factor": "1/(Ke-g)",
        "Present Value": value,
    }]

    return {
        "intrinsic_value": value,
        "model": "Stable DDM (Gordon Growth Model)",
        "formula": f"Value = DPS₁ / (Ke - g) = {dps1:,.2f} / ({ke:.4f} - {g:.4f}) = {value:,.2f}",
        "year_by_year": year_by_year,
        "summary": {
            "Current DPS (D₀)": dps,
            "Next Year DPS (D₁)": dps1,
            "Cost of Equity (Ke)": ke,
            "Stable Growth Rate (g)": g,
            "Intrinsic Value per Share": value,
        },
    }


def ddm_two_stage(dps, cost_of_equity, high_growth, stable_growth,
                   high_growth_years=7):
    ke, hg, sg = cost_of_equity, high_growth, stable_growth
    rows = []
    pv_dividends = 0
    current_dps = dps

    for yr in range(1, high_growth_years + 1):
        current_dps *= (1 + hg)
        pv_factor = 1 / ((1 + ke) ** yr)
        pv = current_dps * pv_factor
        pv_dividends += pv
        rows.append({
            "Year": yr,
            "Expected Growth": f"{hg:.2%}",
            "Dividend (DPS)": current_dps,
            "Cost of Equity": f"{ke:.2%}",
            "PV Factor": pv_factor,
            "PV of Dividend": pv,
        })

    terminal_dps = current_dps * (1 + sg)
    terminal_value = terminal_dps / (ke - sg)
    pv_terminal = terminal_value / ((1 + ke) ** high_growth_years)

    rows.append({
        "Year": f"Terminal (Yr {high_growth_years}+)",
        "Expected Growth": f"{sg:.2%} (stable)",
        "Dividend (DPS)": terminal_dps,
        "Cost of Equity": f"{ke:.2%}",
        "PV Factor": 1 / ((1 + ke) ** high_growth_years),
        "PV of Dividend": pv_terminal,
    })

    intrinsic = pv_dividends + pv_terminal

    return {
        "intrinsic_value": intrinsic,
        "model": "Two-Stage DDM",
        "year_by_year": rows,
        "summary": {
            "Current DPS (D₀)": dps,
            "High Growth Rate": hg,
            "High Growth Period": f"{high_growth_years} years",
            "Stable Growth Rate": sg,
            "Cost of Equity": ke,
            "PV of High-Growth Dividends": pv_dividends,
            "Terminal Value": terminal_value,
            "PV of Terminal Value": pv_terminal,
            "Intrinsic Value per Share": intrinsic,
        },
    }


def ddm_three_stage(dps, cost_of_equity, high_growth, stable_growth,
                     high_years=5, transition_years=5):
    ke, hg, sg = cost_of_equity, high_growth, stable_growth
    rows = []
    pv_total = 0
    current_dps = dps
    year = 0

    # Phase 1
    for yr in range(1, high_years + 1):
        current_dps *= (1 + hg)
        pv_factor = 1 / ((1 + ke) ** yr)
        pv = current_dps * pv_factor
        pv_total += pv
        rows.append({
            "Year": yr, "Phase": "High Growth",
            "Growth Rate": f"{hg:.2%}", "DPS": current_dps,
            "PV Factor": pv_factor, "PV of DPS": pv,
        })
        year = yr

    pv_phase1 = pv_total

    # Phase 2
    pv_phase2 = 0
    for i in range(1, transition_years + 1):
        blended = hg - (hg - sg) * (i / transition_years)
        current_dps *= (1 + blended)
        year += 1
        pv_factor = 1 / ((1 + ke) ** year)
        pv = current_dps * pv_factor
        pv_total += pv
        pv_phase2 += pv
        rows.append({
            "Year": year, "Phase": "Transition",
            "Growth Rate": f"{blended:.2%}", "DPS": current_dps,
            "PV Factor": pv_factor, "PV of DPS": pv,
        })

    # Phase 3
    terminal_dps = current_dps * (1 + sg)
    terminal_value = terminal_dps / (ke - sg)
    pv_terminal = terminal_value / ((1 + ke) ** year)

    rows.append({
        "Year": f"Terminal (Yr {year}+)", "Phase": "Stable",
        "Growth Rate": f"{sg:.2%}", "DPS": terminal_dps,
        "PV Factor": 1 / ((1 + ke) ** year), "PV of DPS": pv_terminal,
    })

    intrinsic = pv_total + pv_terminal

    return {
        "intrinsic_value": intrinsic,
        "model": "Three-Stage DDM",
        "year_by_year": rows,
        "summary": {
            "Current DPS (D₀)": dps,
            "High Growth Rate": hg,
            "High Growth Years": high_years,
            "Transition Years": transition_years,
            "Stable Growth Rate": sg,
            "Cost of Equity": ke,
            "PV Phase 1 (High Growth)": pv_phase1,
            "PV Phase 2 (Transition)": pv_phase2,
            "Terminal Value": terminal_value,
            "PV of Terminal Value": pv_terminal,
            "Intrinsic Value per Share": intrinsic,
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
#  FCFE MODELS — with year-by-year tables
# ═════════════════════════════════════════════════════════════════════════════

def fcfe_stable(fcfe_ps, cost_of_equity, stable_growth):
    ke, g = cost_of_equity, stable_growth
    if ke <= g:
        return {"error": "Cost of equity must exceed stable growth rate"}

    fcfe1 = fcfe_ps * (1 + g)
    value = fcfe1 / (ke - g)

    return {
        "intrinsic_value": value,
        "model": "Stable FCFE Model",
        "formula": f"Value = FCFE₁ / (Ke - g) = {fcfe1:,.2f} / ({ke:.4f} - {g:.4f}) = {value:,.2f}",
        "year_by_year": [{
            "Year": "Terminal (∞)",
            "FCFE": fcfe1, "Growth": g, "Ke": ke, "Value": value,
        }],
        "summary": {
            "Current FCFE/share": fcfe_ps,
            "Next Year FCFE/share": fcfe1,
            "Cost of Equity": ke,
            "Stable Growth": g,
            "Intrinsic Value per Share": value,
        },
    }


def fcfe_two_stage(fcfe_ps, cost_of_equity, high_growth, stable_growth,
                    high_years=7):
    ke, hg, sg = cost_of_equity, high_growth, stable_growth
    rows = []
    pv_fcfe = 0
    current = fcfe_ps

    for yr in range(1, high_years + 1):
        current *= (1 + hg)
        pv_factor = 1 / ((1 + ke) ** yr)
        pv = current * pv_factor
        pv_fcfe += pv
        rows.append({
            "Year": yr, "Growth": f"{hg:.2%}", "FCFE/Share": current,
            "PV Factor": pv_factor, "PV of FCFE": pv,
        })

    terminal = current * (1 + sg)
    tv = terminal / (ke - sg)
    pv_tv = tv / ((1 + ke) ** high_years)

    rows.append({
        "Year": f"Terminal (Yr {high_years}+)", "Growth": f"{sg:.2%} (stable)",
        "FCFE/Share": terminal, "PV Factor": 1 / ((1 + ke) ** high_years),
        "PV of FCFE": pv_tv,
    })

    intrinsic = pv_fcfe + pv_tv

    return {
        "intrinsic_value": intrinsic,
        "model": "Two-Stage FCFE Model",
        "year_by_year": rows,
        "summary": {
            "Current FCFE/share": fcfe_ps,
            "High Growth Rate": hg,
            "High Growth Period": f"{high_years} years",
            "Stable Growth Rate": sg,
            "Cost of Equity": ke,
            "PV of High-Growth FCFE": pv_fcfe,
            "Terminal Value": tv,
            "PV of Terminal Value": pv_tv,
            "Intrinsic Value per Share": intrinsic,
        },
    }


def fcfe_three_stage(fcfe_ps, cost_of_equity, high_growth, stable_growth,
                      high_years=5, transition_years=5):
    ke, hg, sg = cost_of_equity, high_growth, stable_growth
    rows = []
    pv_total = 0
    current = fcfe_ps
    year = 0

    pv_p1 = 0
    for yr in range(1, high_years + 1):
        current *= (1 + hg)
        pv_f = 1 / ((1 + ke) ** yr)
        pv = current * pv_f
        pv_total += pv
        pv_p1 += pv
        rows.append({"Year": yr, "Phase": "High Growth", "Growth": f"{hg:.2%}",
                      "FCFE/Share": current, "PV Factor": pv_f, "PV of FCFE": pv})
        year = yr

    pv_p2 = 0
    for i in range(1, transition_years + 1):
        blended = hg - (hg - sg) * (i / transition_years)
        current *= (1 + blended)
        year += 1
        pv_f = 1 / ((1 + ke) ** year)
        pv = current * pv_f
        pv_total += pv
        pv_p2 += pv
        rows.append({"Year": year, "Phase": "Transition", "Growth": f"{blended:.2%}",
                      "FCFE/Share": current, "PV Factor": pv_f, "PV of FCFE": pv})

    terminal = current * (1 + sg)
    tv = terminal / (ke - sg)
    pv_tv = tv / ((1 + ke) ** year)

    rows.append({"Year": f"Terminal (Yr {year}+)", "Phase": "Stable",
                  "Growth": f"{sg:.2%}", "FCFE/Share": terminal,
                  "PV Factor": 1 / ((1 + ke) ** year), "PV of FCFE": pv_tv})

    intrinsic = pv_total + pv_tv

    return {
        "intrinsic_value": intrinsic,
        "model": "Three-Stage FCFE Model",
        "year_by_year": rows,
        "summary": {
            "Current FCFE/share": fcfe_ps,
            "PV Phase 1 (High Growth)": pv_p1,
            "PV Phase 2 (Transition)": pv_p2,
            "Terminal Value": tv,
            "PV of Terminal Value": pv_tv,
            "Intrinsic Value per Share": intrinsic,
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
#  FCFF MODELS — with year-by-year tables
# ══════════════════════════════════════════��══════════════════════════════════

def fcff_stable(fcff, wacc, stable_growth, total_debt=0, cash=0,
                shares_outstanding=1):
    w, g = wacc, stable_growth
    if w <= g:
        return {"error": "WACC must exceed stable growth rate"}

    fcff1 = fcff * (1 + g)
    firm_value = fcff1 / (w - g)
    equity_value = firm_value - total_debt + cash
    per_share = equity_value / shares_outstanding

    return {
        "intrinsic_value_per_share": per_share,
        "firm_value": firm_value,
        "equity_value": equity_value,
        "model": "Stable FCFF Model",
        "formula": f"Firm Value = FCFF₁/(WACC-g) = {fcff1:,.2f}/({w:.4f}-{g:.4f}) = {firm_value:,.2f}",
        "year_by_year": [{
            "Year": "Terminal (∞)", "FCFF": fcff1, "Growth": g,
            "WACC": w, "Firm Value": firm_value,
        }],
        "summary": {
            "Current FCFF": fcff,
            "Next Year FCFF": fcff1,
            "WACC": w,
            "Stable Growth": g,
            "Firm Value": firm_value,
            "(-) Total Debt": total_debt,
            "(+) Cash": cash,
            "Equity Value": equity_value,
            "Shares Outstanding": shares_outstanding,
            "Intrinsic Value per Share": per_share,
        },
    }


def fcff_two_stage(fcff, wacc_high, wacc_stable, high_growth, stable_growth,
                    high_years=7, total_debt=0, cash=0, shares_outstanding=1):
    wh, ws, hg, sg = wacc_high, wacc_stable, high_growth, stable_growth
    rows = []
    pv_fcff = 0
    current = fcff

    for yr in range(1, high_years + 1):
        current *= (1 + hg)
        pv_f = 1 / ((1 + wh) ** yr)
        pv = current * pv_f
        pv_fcff += pv
        rows.append({
            "Year": yr, "Growth": f"{hg:.2%}", "FCFF": current,
            "WACC": f"{wh:.2%}", "PV Factor": pv_f, "PV of FCFF": pv,
        })

    terminal_fcff = current * (1 + sg)
    tv = terminal_fcff / (ws - sg)
    pv_tv = tv / ((1 + wh) ** high_years)

    rows.append({
        "Year": f"Terminal (Yr {high_years}+)", "Growth": f"{sg:.2%} (stable)",
        "FCFF": terminal_fcff, "WACC": f"{ws:.2%}",
        "PV Factor": 1 / ((1 + wh) ** high_years), "PV of FCFF": pv_tv,
    })

    firm_value = pv_fcff + pv_tv
    equity_value = firm_value - total_debt + cash
    per_share = equity_value / shares_outstanding

    return {
        "intrinsic_value_per_share": per_share,
        "firm_value": firm_value,
        "equity_value": equity_value,
        "model": "Two-Stage FCFF Model",
        "year_by_year": rows,
        "summary": {
            "Current FCFF": fcff,
            "High Growth Rate": hg,
            "High Growth Period": f"{high_years} years",
            "WACC (High Growth)": wh,
            "Stable Growth Rate": sg,
            "WACC (Stable)": ws,
            "PV of High-Growth FCFF": pv_fcff,
            "Terminal Value": tv,
            "PV of Terminal Value": pv_tv,
            "Firm Value (Enterprise Value)": firm_value,
            "(-) Total Debt": total_debt,
            "(+) Cash & Equivalents": cash,
            "Equity Value": equity_value,
            "Shares Outstanding": shares_outstanding,
            "Intrinsic Value per Share": per_share,
        },
    }


def fcff_three_stage(fcff, wacc_high, wacc_stable, high_growth, stable_growth,
                      high_years=5, transition_years=5,
                      total_debt=0, cash=0, shares_outstanding=1):
    wh, ws, hg, sg = wacc_high, wacc_stable, high_growth, stable_growth
    rows = []
    pv_total = 0
    current = fcff
    year = 0

    pv_p1 = 0
    for yr in range(1, high_years + 1):
        current *= (1 + hg)
        pv_f = 1 / ((1 + wh) ** yr)
        pv = current * pv_f
        pv_total += pv
        pv_p1 += pv
        rows.append({"Year": yr, "Phase": "High Growth", "Growth": f"{hg:.2%}",
                      "FCFF": current, "WACC": f"{wh:.2%}",
                      "PV Factor": pv_f, "PV of FCFF": pv})
        year = yr

    pv_p2 = 0
    for i in range(1, transition_years + 1):
        bg = hg - (hg - sg) * (i / transition_years)
        bw = wh - (wh - ws) * (i / transition_years)
        current *= (1 + bg)
        year += 1
        pv_f = 1 / ((1 + bw) ** year)
        pv = current * pv_f
        pv_total += pv
        pv_p2 += pv
        rows.append({"Year": year, "Phase": "Transition", "Growth": f"{bg:.2%}",
                      "FCFF": current, "WACC": f"{bw:.2%}",
                      "PV Factor": pv_f, "PV of FCFF": pv})

    terminal = current * (1 + sg)
    tv = terminal / (ws - sg)
    pv_tv = tv / ((1 + ws) ** year)

    rows.append({"Year": f"Terminal (Yr {year}+)", "Phase": "Stable",
                  "Growth": f"{sg:.2%}", "FCFF": terminal, "WACC": f"{ws:.2%}",
                  "PV Factor": 1 / ((1 + ws) ** year), "PV of FCFF": pv_tv})

    firm_value = pv_total + pv_tv
    equity_value = firm_value - total_debt + cash
    per_share = equity_value / shares_outstanding

    return {
        "intrinsic_value_per_share": per_share,
        "firm_value": firm_value,
        "equity_value": equity_value,
        "model": "Three-Stage FCFF Model",
        "year_by_year": rows,
        "summary": {
            "Current FCFF": fcff,
            "PV Phase 1 (High Growth)": pv_p1,
            "PV Phase 2 (Transition)": pv_p2,
            "Terminal Value": tv,
            "PV of Terminal Value": pv_tv,
            "Firm Value (Enterprise Value)": firm_value,
            "(-) Total Debt": total_debt,
            "(+) Cash & Equivalents": cash,
            "Equity Value": equity_value,
            "Shares Outstanding": shares_outstanding,
            "Intrinsic Value per Share": per_share,
        },
    }