import numpy as np


def run_simulation(s0, mu, sigma, T, n_sims=10000, dt=1 / 252):
    """
    Vectorized Geometric Brownian Motion (GBM) simulation.

    Returns
    -------
    path_matrix : ndarray, shape (n_steps + 1, n_sims)
        Simulated price paths.
    low_band : ndarray, shape (n_steps + 1,)
        5th-percentile price at each time step.
    high_band : ndarray, shape (n_steps + 1,)
        95th-percentile price at each time step.
    """
    n_steps = int(T * 252)

    # Random shocks Z ~ N(0, 1)  –  shape: (steps, simulations)
    shocks = np.random.normal(0, 1, (n_steps, n_sims))

    # Drift and diffusion components
    drift = (mu - 0.5 * sigma ** 2) * dt
    diffusion = sigma * np.sqrt(dt) * shocks

    # Daily multiplicative growth factors
    daily_growth = np.exp(drift + diffusion)

    # Build the full price-path matrix
    path_matrix = np.zeros((n_steps + 1, n_sims))
    path_matrix[0] = s0
    path_matrix[1:] = s0 * np.cumprod(daily_growth, axis=0)

    # Confidence bands across all simulations at each time step
    low_band = np.percentile(path_matrix, 5, axis=1)
    high_band = np.percentile(path_matrix, 95, axis=1)

    return path_matrix, low_band, high_band