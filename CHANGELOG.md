# Changelog

All notable changes to HaSeerr.

## v0.3.0 — 2026-05-04

### Added

- **Webhook migrator** — v0.1 config entries lacking `webhook_id` are auto-back-filled on next start (`async_migrate_entry`). Existing installs get the v0.2 webhook capability without re-adding the integration.
- **Card Overseerr links** — each search result row's title is now a clickable link that opens the Seerr detail page in a new tab. URL is built from the Seerr base in the search response.
- **Card UI polish** — title header empty by default (was "HaSeerr"); media types capitalized (`Movie` / `TV` / `Music`); "avail" → "Available".
- **Project icons** — `icon.png` (256×256) and `icon@2x.png` (512×512) for HACS / HA-brands; logo variants in `docs/screenshots/`.
- **Documentation reorg** — public-facing `docs/` folder with separate `design.md`, `development.md`, `voice.md`, `webhook.md`. README streamlined to a quick-start with links into the docs.

### Changed

- `haseerr.search` response now includes `seerr_url` (the configured base) so cards/automations can build per-result deep links.

## v0.2.0 — 2026-05-04

### Added

- **Multi-turn voice flow** — `RequestMedia` plants pending state; `ConfirmRequest` ("yes") submits, `CancelRequest` ("no") drops. 60 s confirmation window. Bulgarian + English.
- **Webhook receiver** — HA webhook endpoint accepts Seerr `notification_type` payloads; emits `haseerr_request_status_changed` events. No core `overseerr` integration required for status updates.
- **4K profile** — optional `is_4k` flag on `haseerr.request`. Honors Seerr's per-user 4K permission.
- **User quota** — `haseerr.user_quota` service returns Seerr's monthly quota. Card displays `🎬 X/N · 📺 X/N` in the header.
- **Music (Lidarr) requests** — search returns music when Lidarr is configured in Seerr; `haseerr.request` accepts `media_type: music`.
- **Card GUI editor** — visual form when adding `type: custom:haseerr-card` via dashboard "+ Add card".
- **Localized intent responses** — Bulgarian replies in `bg` pipelines, English elsewhere.
- **Integration tests** — full HTTP-stack tests via `aioresponses` (54 tests total).

### Changed

- Config-flow `unique_id` now uses `<url>|<commitTag-or-version>` instead of bare URL — survives URL renames.
- `haseerr_request_submitted` event payload now includes `title`.
- Removed redundant `aiohttp>=3.9` from manifest `requirements`.
- Removed the `haseerr.reload_user_mapping` stub (use the integration tile's **Configure** button).

### Fixed

- TV requests now default `seasons: "all"` (Seerr returned 500 when omitted).

## v0.1.0 — 2026-05-04

### Initial release

- HA integration domain `haseerr` (avoids clash with core `overseerr`).
- Services: `haseerr.search`, `haseerr.request`, `haseerr.approve_request`, `haseerr.decline_request`.
- Smart user-mapping wizard (email-exact → name-exact → fuzzy ≥ 0.85).
- Custom Lovelace card (Lit web component); auto-registers in YAML and UI-mode Lovelace.
- Voice intent `RequestMedia` (en + bg).
- `sensor.haseerr_status` diagnostic sensor.
- HACS-installable, hassfest + HACS validators in CI.

### Live-deployed fixes that landed before v0.2

- `async_setup_intents` (was `async_register_intents`) — HA's intent platform discovery name.
- Options changes now refresh the sensor via an update listener.
- Search query RFC 3986 percent-encoding (Seerr rejects form-style `+`).
- Lovelace card auto-registration for UI/Storage-mode dashboards (was YAML-only).
