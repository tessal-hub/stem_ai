import pytest

from logic.rarity_utils import RARITY_TIERS, RarityTier, resolve_rarity


def test_resolve_rarity_returns_unlearned_below_threshold() -> None:
    tier = resolve_rarity(0)
    assert tier.label == "UNLEARNED"
    assert tier.min_count == 0


def test_resolve_rarity_returns_common_at_threshold() -> None:
    tier = resolve_rarity(10)
    assert tier.label == "COMMON"


def test_resolve_rarity_returns_common_just_below_uncommon() -> None:
    tier = resolve_rarity(19)
    assert tier.label == "COMMON"


def test_resolve_rarity_returns_uncommon_at_threshold() -> None:
    tier = resolve_rarity(20)
    assert tier.label == "UNCOMMON"


def test_resolve_rarity_returns_rare_at_threshold() -> None:
    tier = resolve_rarity(50)
    assert tier.label == "RARE"


def test_resolve_rarity_returns_epic_at_threshold() -> None:
    tier = resolve_rarity(100)
    assert tier.label == "EPIC"


def test_resolve_rarity_returns_epic_well_above_threshold() -> None:
    tier = resolve_rarity(9999)
    assert tier.label == "EPIC"


def test_resolve_rarity_returns_unlearned_for_count_of_one() -> None:
    tier = resolve_rarity(1)
    assert tier.label == "UNLEARNED"


@pytest.mark.parametrize(
    "count, expected_label",
    [
        (0, "UNLEARNED"),
        (9, "UNLEARNED"),
        (10, "COMMON"),
        (19, "COMMON"),
        (20, "UNCOMMON"),
        (49, "UNCOMMON"),
        (50, "RARE"),
        (99, "RARE"),
        (100, "EPIC"),
        (500, "EPIC"),
    ],
)
def test_resolve_rarity_parametrized(count: int, expected_label: str) -> None:
    assert resolve_rarity(count).label == expected_label


def test_rarity_tier_is_frozen() -> None:
    tier = RarityTier(min_count=0, label="UNLEARNED", color="#000000")
    with pytest.raises((AttributeError, TypeError)):
        tier.label = "CHANGED"  # type: ignore[misc]


def test_rarity_tiers_are_ordered_by_min_count() -> None:
    counts = [t.min_count for t in RARITY_TIERS]
    assert counts == sorted(counts)


def test_resolve_rarity_result_is_a_rarity_tier_instance() -> None:
    result = resolve_rarity(50)
    assert isinstance(result, RarityTier)
