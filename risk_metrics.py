import numpy as np


def calculate_metrics(final_prices, s0, mu, sigma, rf=0.04):
    """Calculates comprehensive financial risk metrics and a recommendation."""
    returns = (final_prices - s0) / s0
    avg_price = np.mean(final_prices)
    median_price = np.median(final_prices)
    prob_profit = np.mean(final_prices > s0)
    expected_return_pct = (avg_price - s0) / s0

    # ── Recommendation Logic ────────────────────────────────────────────────
    if expected_return_pct > 0.15 and prob_profit > 0.65:
        recommendation = "🟢 STRONG BUY"
    elif expected_return_pct > 0.05 and prob_profit > 0.55:
        recommendation = "🟡 ACCUMULATE / HOLD"
    else:
        recommendation = "🔴 AVOID / SELL"

    # ── Core percentiles ────────────────────────────────────────────────────
    var_95 = np.percentile(returns, 5)
    cvar_95 = np.mean(returns[returns <= var_95])
    var_99 = np.percentile(returns, 1)
    cvar_99 = np.mean(returns[returns <= var_99])

    # ── Upside / Downside stats ─────────────────────────────────────────────
    upside_returns = returns[returns > 0]
    downside_returns = returns[returns < 0]

    avg_upside = float(np.mean(upside_returns)) if len(upside_returns) > 0 else 0.0
    avg_downside = float(np.mean(downside_returns)) if len(downside_returns) > 0 else 0.0

    # ── Sortino Ratio (downside deviation) ──────────────────────────────────
    downside_dev = np.std(returns[returns < 0]) * np.sqrt(252) if len(downside_returns) > 0 else 0.0
    sortino = (mu - rf) / downside_dev if downside_dev != 0 else 0.0

    # ── Max potential drawdown from current price ───────────────────────────
    worst_price = np.min(final_prices)
    best_price = np.max(final_prices)
    max_drawdown = (worst_price - s0) / s0
    max_upside = (best_price - s0) / s0

    # ── Risk-Reward Ratio ───────────────────────────────────────────────────
    risk_reward = abs(avg_upside / avg_downside) if avg_downside != 0 else 0.0

    metrics = {
        # Price targets
        "Expected Price": avg_price,
        "Median Price": median_price,
        "Best Case Price": best_price,
        "Worst Case Price": worst_price,
        "10th Percentile Price": np.percentile(final_prices, 10),
        "90th Percentile Price": np.percentile(final_prices, 90),

        # Return stats
        "Expected Return": expected_return_pct * 100,
        "Std Dev": np.std(final_prices),
        "Volatility (Annual)": sigma * 100,

        # Risk metrics
        "VaR 95% (Rel)": var_95,
        "CVaR 95%": cvar_95,
        "VaR 99% (Rel)": var_99,
        "CVaR 99%": cvar_99,
        "Max Drawdown": max_drawdown * 100,
        "Max Upside": max_upside * 100,

        # Probability
        "Prob. of Profit": prob_profit * 100,
        "Prob. of >10% Gain": np.mean(returns > 0.10) * 100,
        "Prob. of >25% Gain": np.mean(returns > 0.25) * 100,
        "Prob. of >10% Loss": np.mean(returns < -0.10) * 100,

        # Ratios
        "Sharpe Ratio": (mu - rf) / sigma if sigma != 0 else 0,
        "Sortino Ratio": sortino,
        "Risk-Reward Ratio": risk_reward,
        "Avg Upside": avg_upside * 100,
        "Avg Downside": avg_downside * 100,

        # Signal
        "Signal": recommendation,
    }
    return metrics