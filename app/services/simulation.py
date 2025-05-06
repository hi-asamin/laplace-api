import numpy as np
from .market import get_price_history
from app.models.enums import PERIOD_MAP

SCENARIOS = {
    "optimistic": 0.75,
    "base": 0.50,
    "pessimistic": 0.25,
}

def monte_carlo(symbol: str, years: int, simulations: int):
    hist = get_price_history(symbol, PERIOD_MAP["max"])
    returns = hist["Close"].pct_change().dropna()
    mu = returns.mean()
    sigma = returns.std()
    dt = 1/252
    results = {k: [] for k in SCENARIOS}

    for scenario, quantile in SCENARIOS.items():
        adj_mu = np.quantile(returns, quantile)
        for _ in range(simulations):
            price = 1.0
            for _ in range(years*252):
                drift = adj_mu - 0.5*sigma**2
                shock = sigma * np.random.normal()
                price *= np.exp(drift*dt + shock*np.sqrt(dt))
            results[scenario].append(price)
    return results
