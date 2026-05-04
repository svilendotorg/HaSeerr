# HaSeerr — Design

## Naming and coexistence

- **HA integration domain**: `haseerr`. Avoids clash with HA core's read-only `overseerr` integration (which uses domain `overseerr` and `seerr.*` services).
- HaSeerr fills the gap that the core integration leaves: **submission**, **search-with-response**, **smart user mapping**, and a **status-event webhook**.
- Both can be installed simultaneously without overlap.

## Architecture

```
┌─ Home Assistant ───────────────────────────────────────────────┐
│                                                                 │
│  custom_components/haseerr/                                     │
│   ├─ __init__.py        entry, services, intents,               │
│   │                      static path, webhook, options listener │
│   ├─ config_flow.py     URL + admin API key                     │
│   ├─ options_flow.py    user-mapping wizard                     │
│   ├─ hub.py             SeerrClient — aiohttp wrapper           │
│   ├─ webhook.py         receive Seerr notifications             │
│   ├─ sensor.py          sensor.haseerr_status                   │
│   ├─ intent.py          RequestMedia / Confirm / Cancel         │
│   ├─ matching.py        HA-user ↔ Seerr-user matcher            │
│   ├─ services.yaml      service definitions                     │
│   ├─ services_impl.py   service handlers                        │
│   ├─ const.py / manifest.json / strings.json                    │
│   ├─ translations/{en,bg}.json                                  │
│   ├─ intents/{en,bg}.yaml                                       │
│   └─ www/haseerr-card.js   Lit web component, auto-registered   │
│                                                                 │
│  <config>/custom_sentences/{en,bg}/haseerr.yaml                 │
│   (sentence patterns; required for HA conversation matcher)     │
└─────────────────────────────────────────────────────────────────┘
                  │ HTTPS              ▲ HTTPS
                  ▼ to Seerr API       │ Seerr webhook
                ┌─ Seerr ──────────┐
                │ /api/v1/{search, │
                │  request, user,  │
                │  status,         │
                │  request/N/      │
                │  {approve,       │
                │   decline}}      │
                └──────────────────┘
```

**Key decisions:**

1. **Backend / UX decoupled.** The integration exposes services + events + a diagnostic sensor; the Lovelace YAML, voice intents, and automations wire those up.
2. **Single config entry, multi-user inside.** Connection in config flow, mapping wizard in options flow. Adding/removing family members never requires reinstall.
3. **Card auto-registers** via both YAML-mode Lovelace (`add_extra_js_url`) and UI/Storage-mode (`lovelace.resources.async_create_item`). Users add `type: custom:haseerr-card` to a dashboard with no extra setup.
4. **Voice multi-turn via pending state.** `RequestMedia` plants `(tmdb_id, media_type, title, expires_at)` keyed by user_id in `hass.data`; `ConfirmRequest` consumes it and submits.

## Services

| Service | Schema | Response |
|---------|--------|----------|
| `haseerr.search` | `query`, `media_type` (all/movie/tv/music), `limit` (1–20) | `{results: [...], seerr_url: "..."}` — each result: `{tmdb_id, media_type, title, year, poster_url, overview, status}`. `status` ∈ `not_requested` / `requested` / `available`. Person results filtered out. |
| `haseerr.request` | `tmdb_id`, `media_type`, optional `seasons`, `user_override`, `title`, `is_4k` | `{request_id, status, seerr_user_id, seerr_user_display}`. Fires `haseerr_request_submitted` event. TV defaults `seasons: "all"` (Seerr 500s otherwise). |
| `haseerr.approve_request` | `request_id` | `{ok, status}` |
| `haseerr.decline_request` | `request_id`, optional `reason` | `{ok, status}` |
| `haseerr.user_quota` | optional `user_override` | Seerr quota dict for the caller's mapped user |

**User resolution.** Every service that submits work resolves the caller's HA `context.user_id` to a Seerr user via `entry.options["user_mapping"]`. Unmapped callers get `"user not mapped, complete options flow"`. Admins may pass `user_override: <seerr_user_id>` to act for someone else.

## Events

```yaml
event_type: haseerr_request_submitted        # we submitted a request
event_data:
  tmdb_id: 693134
  media_type: movie
  title: "Dune: Part Two"
  request_id: 1247
  ha_user_id: "abc123…"
  seerr_user_id: 4
  status: pending

event_type: haseerr_request_status_changed   # Seerr webhook → us
event_data:
  tmdb_id: 693134
  media_type: movie
  title: "Dune: Part Two"
  request_id: 1247
  status: approved          # | pending | available | declined | failed
  requested_by: "Maria"
```

## Sensors

| Sensor | State | Attributes |
|--------|-------|------------|
| `sensor.haseerr_status` | `connected` / `error` / `unmapped_user` | `mapped_users_count`, `last_request_id`, `last_request_at`, `last_error` |

Listing/status sensors are intentionally **not** provided — that's HA core's `overseerr` integration's role. Combine with it if you want full coverage.

## User-mapping algorithm

In `matching.py`. Tiered match, first hit wins:

1. **Email exact** (lowercase)
2. **Display-name exact** after `normalize` (lowercase, strip diacritics, collapse whitespace)
3. **Display-name fuzzy** with `difflib.SequenceMatcher.ratio() >= 0.85`
4. **No match** → `--skip--` (user must edit before saving)

Same Seerr user can be mapped to multiple HA users (shared family account scenario) — flagged in the wizard but allowed.

## Data flow: dashboard → search → submit

```
User types "Dune Part Two" in haseerr-card
  → hass.callService("haseerr", "search", {...}, return_response)
  → SeerrClient.search() → GET /api/v1/search?query=Dune%20Part%20Two
    (RFC 3986 percent-encoding required — Seerr rejects form-style "+")
  → filter mediaType=person, normalize results, slice to limit
  → return {results, seerr_url}
User clicks a result row
  → hass.callService("haseerr", "request", {tmdb_id, media_type, title})
  → context.user_id resolved via user_mapping → seerr_user_id
  → SeerrClient.request() → POST /api/v1/request
  → fire haseerr_request_submitted
  → toast "Requested X for <Maria> — pending"
```

## Voice multi-turn flow

```
intent: RequestMedia (slot: title)
  → search top 3 results
  → store pending = {tmdb_id, media_type, title, expires_at} in hass.data[DOMAIN].pending_confirm[user_id]
  → speak "Did you mean <top.title> from <year>, the <movie|show>?"

intent: ConfirmRequest (sentences: yes / yes please / confirm / go ahead)
  → pop pending; if expired or missing, say "Nothing to confirm"
  → call haseerr.request with stored fields
  → speak "Requested <title>."

intent: CancelRequest (sentences: no / cancel / abort / never mind)
  → pop pending → "Cancelled."
```

Confirmation window: 60 s, configurable via `PENDING_CONFIRM_TTL_S` in `const.py`.

## Webhook receiver

- HA `webhook` integration registers the webhook on entry setup (`webhook_id` is a 64-char hex generated during config flow).
- Pre-v0.2 entries lacking `webhook_id` are auto-migrated via `async_migrate_entry`.
- `_handle_webhook` accepts Seerr's `notification_type` payload, normalizes to our 5 status states, fires `haseerr_request_status_changed`.
- Mapped notification types: `MEDIA_PENDING`, `MEDIA_APPROVED`, `MEDIA_AVAILABLE`, `MEDIA_DECLINED`, `MEDIA_FAILED`, `MEDIA_AUTO_APPROVED`, `MEDIA_AUTO_REQUESTED`. Unknown types (e.g. `TEST_NOTIFICATION`) get `200` and are silently ignored.

## Coexistence with core `overseerr`

| Capability | Source |
|------------|--------|
| List pending / recent requests (sensors) | core `overseerr` |
| `seerr.get_requests` action | core |
| Status sensors (approved / available / failed) | core |
| **Submit a request** | **haseerr** |
| **Search with response** | **haseerr** |
| **HA-user → Seerr-user mapping** | **haseerr** |
| **Custom Lovelace card** | **haseerr** |
| **Voice intents (multi-turn)** | **haseerr** |
| **Status events via webhook** | **haseerr** (or core's, pick one) |

Different domains, different service prefixes (`overseerr.*` / `seerr.*` vs `haseerr.*`). Zero conflict.

## Lessons learned (writing this integration)

Captured during the build. Useful if you're writing your own custom HA integration:

- **Intent platform discovery**: HA scans `custom_components/<x>/intent.py` for the exact symbol **`async_setup_intents(hass)`**. Other names silently fail.
- **Conversation matcher does NOT auto-discover** the integration's `intents/<lang>.yaml`. Sentence patterns must live at `<config>/custom_sentences/<lang>/<file>.yaml` in full hassil schema; wildcard slots only work there. The simplified `conversation.intents:` block in `configuration.yaml` doesn't support wildcards.
- **Lovelace card auto-registration**: `add_extra_js_url` only works for YAML-mode Lovelace. UI/Storage-mode requires inserting into `hass.data["lovelace"].resources.async_create_item`. We do both.
- **Seerr URL encoding**: Seerr strict-checks for RFC 3986 percent-encoding on `query` params. aiohttp's default `params=` uses form-style (`+` for space) which Seerr rejects. Manual `urllib.parse.quote(query, safe="")` is required.
- **TV requests need `seasons`**: Seerr returns 500 if a TV `request` omits `seasons`. We default to `"all"`.
- **OptionsFlow** in current HA: `config_entry` is a read-only property. Custom flows store as `self._config_entry` and expose via `@property`.
- **204 No Content**: `approve` and `decline` endpoints return 204 sometimes — the SeerrClient `_request` returns `None` on those; methods guard with `or {}`.
- **Options updates don't refresh entities by default**: register an update listener in `async_setup_entry` and call `hass.config_entries.async_reload(entry.entry_id)` from it.
