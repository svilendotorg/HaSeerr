<p align="center">
  <img src="docs/screenshots/banner.png" alt="HaSeerr — Search & request movies, TV, and music from Home Assistant" />
</p>

<p align="center">
  <a href="docs/design.md">Design</a> ·
  <a href="docs/development.md">Development</a> ·
  <a href="docs/voice.md">Voice</a> ·
  <a href="docs/webhook.md">Webhook</a> ·
  <a href="docs/overview-dashboard.md">Overview dashboard</a> ·
  <a href="CHANGELOG.md">Changelog</a>
</p>

<p align="center">
  <a href="https://github.com/svilendotorg/haseerr/actions/workflows/tests.yml"><img src="https://github.com/svilendotorg/haseerr/actions/workflows/tests.yml/badge.svg" alt="tests" /></a>
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="hacs" /></a>
</p>

> **HaSeerr complements** the [built-in `overseerr` integration](https://www.home-assistant.io/integrations/overseerr/) (read-only). Both can run side-by-side.

## Features

- **`haseerr-card`** — custom Lovelace card with search, posters, click-to-pick, per-row Seerr links, season picker, and 4K toggle. Auto-registers; no Lovelace resource setup needed.
- **Services** — `search`, `request`, `approve_request`, `decline_request`, `user_quota`.
- **Smart user mapping** — wizard pairs each HA user with a Seerr user (email-exact → name-exact → fuzzy ≥ 0.85). Per-user request quotas displayed on the card.
- **Voice (Assist)** — `RequestMedia` / `ConfirmRequest` / `CancelRequest` intents in English and Bulgarian, full multi-turn flow: *"request Dune Part Two"* → *"Did you mean…"* → *"yes"* → submitted.
- **Status events** — Seerr's webhook can post directly to HaSeerr; emits `haseerr_request_status_changed` events for approved / available / declined / failed transitions. No core `overseerr` integration required.
- **Music + 4K + TV seasons** — request music if Lidarr is configured in Seerr, request 4K if your user has the permission, pick specific TV seasons.

## Install

### HACS (recommended)

1. **HACS** → **Integrations** → ⋮ → **Custom repositories**
2. Repository: `https://github.com/svilendotorg/haseerr` · Type: **Integration**
3. **Download HaSeerr**, restart Home Assistant
4. **Settings → Devices & Services → Add Integration → HaSeerr**

### Manual

Copy `custom_components/haseerr/` into your HA `config/custom_components/` and restart HA.

## Configuration

The setup wizard asks for:

- **Seerr URL** — e.g. `https://seerr.example.com` or `http://192.168.1.10:5055`
- **API key** — Seerr → Settings → General → API Key

After setup, the **Configure** button opens the **user-mapping wizard**: each HA user gets a dropdown pre-filled with the suggested Seerr user. Save to persist. Re-runnable anytime when family members are added.

## The dashboard card

```yaml
type: custom:haseerr-card
# all fields optional:
title: ""                  # default empty (no header)
limit: 5                   # search results to show; default 5
poster_size: w200          # tmdb image size; default w200
hide_unavailable: false    # if true, skip "already in library" results
allow_season_picker: true  # if false, TV always requests all seasons
show_quota: true           # show monthly quota in card header
```

The card auto-registers from the integration on both YAML and UI-mode Lovelace dashboards. No need to add the JS as a resource manually.

## Services (quick reference)

```yaml
# Search
service: haseerr.search
data: { query: "Dune", media_type: all, limit: 5 }
# response: { results: [...], seerr_url: "..." }

# Request
service: haseerr.request
data:
  tmdb_id: 693134
  media_type: movie       # movie | tv | music
  # seasons: "all"        # TV: "all" or [1, 2]
  # is_4k: true           # if user has 4K permission in Seerr
  # title: "Dune"         # included in haseerr_request_submitted event

# Approve / decline
service: haseerr.approve_request
data: { request_id: 1247 }

service: haseerr.decline_request
data: { request_id: 1247, reason: "too violent" }

# Quota for the caller's mapped user
service: haseerr.user_quota
# response: { movie: {limit, used, ...}, tv: {limit, used, ...} }
```

Full design + event payloads in [`docs/design.md`](docs/design.md).

## Voice (Assist)

> 🎤 *"Hey Assist, request Dune Part Two"*
> 🔊 *"Did you mean Dune: Part Two from 2024, the movie?"*
> 🎤 *"Yes."*
> 🔊 *"Requested Dune: Part Two."*

Confirmation window is **60 seconds**. Bulgarian variants: `поискай <title>` → `да` / `не`.

**One-time setup**: HA's conversation matcher requires sentence patterns to live in `<config>/custom_sentences/<lang>/` rather than inside the integration. Copy from [`docs/voice.md`](docs/voice.md) into your config and restart HA.

## Status events from Seerr (optional webhook)

After installing HaSeerr, your webhook URL is generated automatically. Find it in HA logs at startup — search for `HaSeerr webhook URL:`. Paste it into Seerr → Settings → Notifications → Webhook. Subsequent status changes fire `haseerr_request_status_changed` events. Details: [`docs/webhook.md`](docs/webhook.md).

## Coexistence with the built-in `overseerr` integration

Run both. The built-in `overseerr` integration provides read-only sensors and a `seerr.get_requests` action. HaSeerr adds submission + smart user mapping + the card + voice + a richer event stream. No overlapping domains or services.

## Automation recipes

See [`docs/automations-examples.yaml`](docs/automations-examples.yaml). Includes mobile actionable notifications for Approve/Decline, plus a logbook entry on each successful submit.

## Development

```bash
git clone https://github.com/svilendotorg/haseerr
cd haseerr
python -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt aioresponses
pytest -v
```

More: [`docs/development.md`](docs/development.md).

## License

MIT — see [`LICENSE`](LICENSE).
