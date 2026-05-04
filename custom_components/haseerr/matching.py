"""HA-user ↔ Seerr-user pairing suggestions."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from difflib import SequenceMatcher

from .const import NAME_FUZZY_THRESHOLD


def normalize(s: str | None) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    no_marks = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(no_marks.lower().split())


def _email_match(ha: dict, seerr_users: Iterable[dict]) -> int | None:
    if not ha.get("email"):
        return None
    target = ha["email"].lower()
    for s in seerr_users:
        if s.get("email") and s["email"].lower() == target:
            return s["id"]
    return None


def _name_exact_match(ha: dict, seerr_users: Iterable[dict]) -> int | None:
    target = normalize(ha.get("name"))
    if not target:
        return None
    for s in seerr_users:
        if normalize(s.get("display_name")) == target:
            return s["id"]
    return None


def _name_fuzzy_match(ha: dict, seerr_users: Iterable[dict]) -> int | None:
    target = normalize(ha.get("name"))
    if not target:
        return None
    best_id, best_ratio = None, 0.0
    for s in seerr_users:
        candidate = normalize(s.get("display_name"))
        if not candidate:
            continue
        ratio = SequenceMatcher(None, target, candidate).ratio()
        if ratio > best_ratio:
            best_id, best_ratio = s["id"], ratio
    if best_ratio >= NAME_FUZZY_THRESHOLD:
        return best_id
    return None


def suggest_pairings(
    *, ha_users: list[dict], seerr_users: list[dict]
) -> dict[str, tuple[int | None, str]]:
    """For each HA user, return (seerr_user_id_or_None, reason)."""
    out: dict[str, tuple[int | None, str]] = {}
    for ha in ha_users:
        if (sid := _email_match(ha, seerr_users)) is not None:
            out[ha["id"]] = (sid, "email-exact")
            continue
        if (sid := _name_exact_match(ha, seerr_users)) is not None:
            out[ha["id"]] = (sid, "name-exact")
            continue
        if (sid := _name_fuzzy_match(ha, seerr_users)) is not None:
            out[ha["id"]] = (sid, "name-fuzzy")
            continue
        out[ha["id"]] = (None, "no-match")
    return out
