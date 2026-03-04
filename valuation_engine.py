"""
Valuation Engine — unchanged logic, updated to pass currency/unit to selector.
"""

import numpy as np
from financial_data import get_fundamental_data
from valuation_models import (
    choose_valuation_model,
    compute_fcfe, compute_fcff,
    ddm_stable, ddm_two_stage, ddm_three_stage,
    fcfe_stable, fcfe_two_stage, fcfe_three_stage,
    fcff_stable, fcff_two_stage, fcff_three_stage,
)


def run_valuation(ticker: str) -> dict:
    fd = get_fundamental_data(ticker)

    earnings_positive = fd["net_income"] > 0
    shares = fd["shares_outstanding"]
    cur = "₹" if fd["currency"] == "INR" else "$"

    selector_inputs = {
        "earnings_positive": earnings_positive,
        "inflation_rate": fd["inflation_rate"],
        "real_growth_rate": fd["real_growth_rate"],
        "firm_growth_rate": fd["firm_growth_rate"],
        "has_competitive_adv": fd["has_competitive_adv"],
        "cyclical_negative": fd.get("cyclical_negative", False),
        "temporary_negative": fd.get("temporary_negative", False),
        "excess_debt_negative": fd.get("excess_debt_negative", False),
        "bankruptcy_likely": fd.get("bankruptcy_likely", False),
        "startup_negative": fd.get("startup_negative", False),
        "debt_ratio": fd["debt_ratio"],
        "debt_ratio_changing": fd["debt_ratio_changing"],
        "dividends": fd["dividends_total"],
        "can_estimate_capex": True,
        "net_income": fd["net_income"],
        "depreciation": fd["depreciation"],
        "capex": fd["capex"],
        "delta_wc": fd["delta_wc"],
        "shares_outstanding": shares,
        "currency": cur,
        "unit": fd["unit"],
    }

    model_choice = choose_valuation_model(selector_inputs)

    dps = fd["dividends_total"] / shares if shares > 0 else 0
    eps = fd["net_income"] / shares if shares > 0 else 0

    fcfe_total = compute_fcfe(
        fd["net_income"], fd["depreciation"], fd["capex"],
        fd["delta_wc"], fd["debt_ratio"]
    )
    fcfe_ps = fcfe_total / shares if shares > 0 else 0

    fcff_total = compute_fcff(
        fd["ebit"], fd["tax_rate"], fd["depreciation"],
        fd["capex"], fd["delta_wc"]
    )

    ke = fd["cost_of_equity"]
    wacc = fd["wacc"]
    hg = fd["firm_growth_rate"]
    sg = fd["stable_growth"]

    code = model_choice["model_code"]
    val_result = {}

    if code == "ddmst":
        val_result = ddm_stable(dps, ke, sg)
    elif code == "ddm2st":
        val_result = ddm_two_stage(dps, ke, hg, sg, high_growth_years=7)
    elif code == "ddm3st":
        val_result = ddm_three_stage(dps, ke, hg, sg, high_years=5, transition_years=5)
    elif code == "fcfest":
        val_result = fcfe_stable(fcfe_ps, ke, sg)
    elif code == "fcfe2st":
        val_result = fcfe_two_stage(fcfe_ps, ke, hg, sg, high_years=7)
    elif code == "fcfe3st":
        val_result = fcfe_three_stage(fcfe_ps, ke, hg, sg, high_years=5, transition_years=5)
    elif code == "fcffst":
        val_result = fcff_stable(fcff_total, wacc, sg, fd["total_debt"], fd["cash"], shares)
    elif code == "fcff2st":
        val_result = fcff_two_stage(
            fcff_total, wacc, wacc * 0.95, hg, sg, high_years=7,
            total_debt=fd["total_debt"], cash=fd["cash"], shares_outstanding=shares
        )
    elif code == "fcff3st":
        val_result = fcff_three_stage(
            fcff_total, wacc, wacc * 0.95, hg, sg, high_years=5, transition_years=5,
            total_debt=fd["total_debt"], cash=fd["cash"], shares_outstanding=shares
        )
    else:
        val_result = fcff_two_stage(
            fcff_total, wacc, wacc * 0.95, hg, sg, high_years=7,
            total_debt=fd["total_debt"], cash=fd["cash"], shares_outstanding=shares
        )

    if "intrinsic_value_per_share" in val_result:
        intrinsic = val_result["intrinsic_value_per_share"]
    elif "intrinsic_value" in val_result:
        intrinsic = val_result["intrinsic_value"]
    else:
        intrinsic = 0

    return {
        "ticker": ticker,
        "company": fd["company"],
        "currency": fd["currency"],
        "unit": fd["unit"],
        "intrinsic_value_per_share": intrinsic,
        "model_selection": model_choice,
        "valuation_detail": val_result,
        "fundamentals": fd,
        "computed": {
            "EPS": eps,
            "DPS": dps,
            "FCFE_per_share": fcfe_ps,
            "FCFE_total": fcfe_total,
            "FCFF_total": fcff_total,
        },
    }