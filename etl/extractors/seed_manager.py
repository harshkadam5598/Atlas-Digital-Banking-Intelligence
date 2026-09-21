"""
Atlas – Deterministic Seed Manager
Provides isolated, reproducible RNG streams per domain and per customer.
Every random draw in the system traces back to DATA_SEED=42.
"""

import hashlib
from functools import lru_cache

import numpy as np


MASTER_SEED: int = 42  # Overridden by config at runtime


def derive_seed(master_seed: int, domain: str) -> int:
    """
    Deterministically derive a child seed for a named domain.
    The same (master_seed, domain) pair always produces the same integer.
    """
    hash_input = f"{master_seed}:{domain}".encode()
    return int(hashlib.md5(hash_input).hexdigest(), 16) % (2 ** 32)


def get_rng(domain: str, master_seed: int = MASTER_SEED) -> np.random.Generator:
    """Return a seeded Generator for a named domain."""
    return np.random.default_rng(derive_seed(master_seed, domain))


def get_customer_rng(customer_index: int, domain: str,
                     master_seed: int = MASTER_SEED) -> np.random.Generator:
    """
    Return a Generator isolated to a specific customer and domain.
    Customer i's draws are completely independent of customer i+1's draws.
    Supports parallel generation and single-customer regeneration.
    """
    seed = derive_seed(master_seed, f"customer:{customer_index}:{domain}")
    return np.random.default_rng(seed)


# Pre-computed domain seeds for documentation / audit purposes
DOMAIN_SEEDS = {
    domain: derive_seed(MASTER_SEED, domain)
    for domain in [
        "customers", "transactions", "events", "fraud",
        "support", "kyc", "marketing", "revenue", "faker",
    ]
}
