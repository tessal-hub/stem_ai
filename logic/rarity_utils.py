"""
Shared rarity tier logic.
Consolidates RarityTier dataclass and rarity resolution function used across
PageWand and PageStatistics.
"""

from dataclasses import dataclass

from ui.tokens import RARITY_NONE, RARITY_COM, RARITY_UNC, RARITY_RARE, RARITY_EPIC


@dataclass(frozen=True)
class RarityTier:
    """Immutable rarity tier definition."""
    min_count: int
    label: str
    color: str


RARITY_TIERS: tuple[RarityTier, ...] = (
    RarityTier(0,   "UNLEARNED", RARITY_NONE),
    RarityTier(10,  "COMMON",    RARITY_COM),
    RarityTier(20,  "UNCOMMON",  RARITY_UNC),
    RarityTier(50,  "RARE",      RARITY_RARE),
    RarityTier(100, "EPIC",      RARITY_EPIC),
)


def resolve_rarity(count: int) -> RarityTier:
    """
    Return the highest tier whose min_count does not exceed count.
    
    Args:
        count: Number of times the rarity tier was achieved.
    
    Returns:
        RarityTier: The appropriate tier for the given count.
    """
    return max(
        (tier for tier in RARITY_TIERS if count >= tier.min_count),
        key=lambda t: t.min_count,
        default=RARITY_TIERS[0],
    )
