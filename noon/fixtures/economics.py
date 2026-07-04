"""Single source of per-offer economic truth for the FILLER generators.

Real filler must be economically coherent: platform-claimed revenue is a realistic OVER-CLAIM of
the real affiliate payout (not an independent random draw), and each platform's spend shares a
tracking token with its OWN payout slice so revenue actually joins. This module owns those facts
per offer; every filler generator consults it, so the two sides can never drift.

Research-grounded bands (industry benchmarks, 2024-2025):
  - Platform over-claim ~15-50%: Meta ~26%, Google ~15-20% (Varos / Google via EasyInsights 2024-25;
    ~15% is normal variance, 40-50% is the high end). Encoded as over_claim_factor in [1.15, 1.50].
  - Per-conversion real payout ~$5-150 (affiliate/lead-gen ranges), varied per offer+platform.
  - Claim sparsity: a realistic fraction of offers pass NO platform-claimed revenue (affiliate reality;
    the reconciler's claim-side fallback needs this to exist).

Tokens are per (offer, platform) - NOT one token per offer - so two platforms never share a token.
A shared token would trigger the reconciler's cross-platform "first-sorted-grain-wins" rule and zero
out the other platform's grain (a false zombie). Per-platform tokens keep each grain joinable.

PURE and deterministic: seeded only by (offer_id, seed) via a hashed local RNG, independent of call
order - so the same offer yields identical economics in every generator, every run.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal

_GEOS = ("US", "CA", "GB", "AU")
_SPEND_PLATFORMS = ("google", "meta", "taboola", "tiktok")


@dataclass(frozen=True)
class PlacementEconomics:
    """One (offer, platform) placement: its token and its per-conversion real-payout band."""
    platform: str
    token: str
    payout_low: Decimal
    payout_high: Decimal


@dataclass(frozen=True)
class OfferEconomics:
    """One offer's coherent economics, shared by every generator that touches this offer."""
    offer_id: str
    geo: str
    is_sparse: bool                 # True -> this offer passes NO platform-claimed revenue
    over_claim_factor: Decimal      # claim = real_payout * this (researched 1.15-1.50)
    conversions_weight: int         # typical conversions per spend row for this offer (volume anchor)
    placements: dict                # platform -> PlacementEconomics


def _rng(*parts) -> random.Random:
    """A local RNG seeded by the given parts - deterministic and independent of call order."""
    return random.Random("|".join(str(p) for p in parts))


def placement_for(offer_id: str, platform: str, seed: int = 0) -> PlacementEconomics:
    """The deterministic economics for one (offer, platform) placement. Model (a): valid for ANY
    of the four platforms - every offer can run on every platform. Token is tok_{offer}_{platform}
    (unique per pair, so no two platforms share a token -> no cross-platform false-zombie). The
    per-conversion real-payout band is seeded by (offer, platform, seed), so it is stable no matter
    which generator asks or in what order."""
    r = _rng(offer_id, platform, seed)
    low = Decimal(str(round(r.uniform(5.0, 40.0), 2)))            # per-conversion payout floor
    high = low + Decimal(str(round(r.uniform(10.0, 110.0), 2)))   # up to ~$150 ceiling
    return PlacementEconomics(
        platform=platform,
        token=f"tok_{offer_id}_{platform}",
        payout_low=low,
        payout_high=high,
    )


def offer_economics(offer_id: str, seed: int = 0) -> OfferEconomics:
    """The offer-level economics shared by every generator that touches this offer: geo,
    claim-sparsity, and the over-claim factor (claim = real_payout * factor). Every offer runs on
    all four platforms; per-platform bands/tokens come from placement_for. Deterministic by
    (offer_id, seed)."""
    r = _rng(offer_id, seed)
    geo = _GEOS[r.randint(0, len(_GEOS) - 1)]
    over_claim_factor = Decimal(str(round(r.uniform(1.15, 1.50), 2)))  # researched 1.15-1.50
    is_sparse = (r.random() < 0.20)                                    # ~1 in 5 offers, no claim
    conversions_weight = r.randint(1, 5)                              # per-offer conversion volume anchor
    placements = {p: placement_for(offer_id, p, seed) for p in _SPEND_PLATFORMS}
    return OfferEconomics(
        offer_id=offer_id, geo=geo, is_sparse=is_sparse,
        over_claim_factor=over_claim_factor, conversions_weight=conversions_weight,
        placements=placements,
    )
