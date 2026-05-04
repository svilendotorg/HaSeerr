"""Tests for HA-user → Seerr-user matching (pure logic, no IO)."""

from __future__ import annotations

from custom_components.haseerr.matching import normalize, suggest_pairings


def _ha(name, email=None, user_id="ha-1"):
    return {"id": user_id, "name": name, "email": email}


def _se(uid, name, email=None):
    return {"id": uid, "display_name": name, "email": email}


def test_normalize_strips_diacritics_and_case():
    assert normalize("María-José") == "maria-jose"


def test_email_exact_wins_over_name():
    pairs = suggest_pairings(
        ha_users=[_ha("Alice", "alice@example.com", user_id="ha-1")],
        seerr_users=[_se(4, "A.", "alice@example.com"), _se(5, "Alice", None)],
    )
    assert pairs == {"ha-1": (4, "email-exact")}


def test_name_exact_after_normalize():
    pairs = suggest_pairings(
        ha_users=[_ha("Álex", None, user_id="ha-1")],
        seerr_users=[_se(4, "Alex")],
    )
    assert pairs == {"ha-1": (4, "name-exact")}


def test_name_fuzzy_above_threshold():
    pairs = suggest_pairings(
        ha_users=[_ha("Catlin", None, user_id="ha-1")],  # near-typo of "Caitlin"
        seerr_users=[_se(4, "Caitlin")],
    )
    assert pairs["ha-1"][1] == "name-fuzzy"


def test_name_fuzzy_below_threshold_no_match():
    pairs = suggest_pairings(
        ha_users=[_ha("Bob", None, user_id="ha-1")],
        seerr_users=[_se(4, "Caroline")],
    )
    assert pairs == {"ha-1": (None, "no-match")}


def test_multiple_users():
    pairs = suggest_pairings(
        ha_users=[
            _ha("Alice", "alice@example.com", user_id="ha-s"),
            _ha("Bob", "bob@example.com", user_id="ha-m"),
            _ha("Guest", None, user_id="ha-g"),
        ],
        seerr_users=[
            _se(1, "Alice", "alice@example.com"),
            _se(4, "Bob", "bob@example.com"),
        ],
    )
    assert pairs["ha-s"] == (1, "email-exact")
    assert pairs["ha-m"] == (4, "email-exact")
    assert pairs["ha-g"] == (None, "no-match")
