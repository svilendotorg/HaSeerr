# Development

## Local setup

```bash
git clone https://github.com/svilendotorg/haseerr
cd haseerr
python -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt aioresponses
```

## Test + lint

```bash
pytest -q                # full suite — fast, no live network
ruff check .             # linter
black --check .          # formatter (use `black .` to apply)
```

CI runs `pytest`, `ruff`, `black`, plus `hassfest` and `HACS validate` on every push to main and on PRs.

## Test architecture

Three layers, mocking at the right boundary:

1. **`tests/test_hub.py`** — pure HTTP. Uses `aioresponses` to mock Seerr's REST API. Asserts request URLs, body shapes, error mapping, response normalization.
2. **`tests/test_matching.py`** — pure logic. The user-mapping matcher is fully testable without HA — `pytest tests/test_matching.py` runs in milliseconds.
3. **`tests/test_{config,options,services,sensor,intent,webhook}_flow.py`** — HA integration tests via `pytest-homeassistant-custom-component`'s `hass` fixture. Mocks `SeerrClient.method` at the seam.
4. **`tests/test_integration.py`** — full-stack: real `SeerrClient` via `aioresponses`, real service handlers, real sensor + event bus. Catches bugs that mocked-method tests miss (URL encoding, 204 None responses).

Fixtures are recorded Seerr API responses in `tests/fixtures/seerr/`. **Tests never hit a live Seerr instance.**

## Deploying to your HA for live testing

```bash
rsync -avh --delete custom_components/haseerr/ \
  root@<your-ha-host>:/homeassistant/custom_components/haseerr/
ssh root@<your-ha-host> 'rm -rf /homeassistant/custom_components/haseerr/__pycache__ && ha core restart'
```

Then watch logs for the webhook URL line:

```bash
ssh root@<your-ha-host> 'ha core logs -n 200 | grep "HaSeerr webhook URL"'
```

## Releasing

1. Bump `manifest.json` `"version"` and `pyproject.toml` `version` to the new tag.
2. Update `CHANGELOG.md`.
3. Commit: `git commit -am "chore: bump version to X.Y.Z"`.
4. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z — <summary>"`.
5. Push: `git push origin main --tags`.

GitHub Actions runs hassfest + HACS validators on the tag automatically.

## Repository layout

```
haseerr/
├── README.md                      # public-facing
├── CHANGELOG.md                   # release notes
├── LICENSE                        # MIT
├── hacs.json                      # HACS metadata
├── info.md                        # short HACS-displayed blurb
├── pyproject.toml                 # ruff + black + pytest config
├── requirements_test.txt
│
├── custom_components/haseerr/
│   ├── __init__.py                # entry, services, intents, card, webhook, migrator
│   ├── config_flow.py             # URL + API key wizard
│   ├── options_flow.py            # user-mapping wizard
│   ├── hub.py                     # SeerrClient
│   ├── webhook.py                 # status webhook receiver
│   ├── intent.py                  # voice intents (multi-turn)
│   ├── matching.py                # HA-user ↔ Seerr-user matcher
│   ├── sensor.py                  # diagnostic sensor
│   ├── const.py / manifest.json / strings.json
│   ├── translations/{en,bg}.json
│   ├── intents/{en,bg}.yaml       # not auto-loaded — see docs/voice.md
│   ├── icon.png / icon@2x.png     # HACS / brand icons
│   └── www/haseerr-card.js        # Lit web component + GUI editor
│
├── tests/
│   ├── conftest.py
│   ├── fixtures/seerr/*.json
│   ├── test_hub.py / test_matching.py
│   ├── test_config_flow.py / test_options_flow.py
│   ├── test_services.py / test_sensor.py / test_intent.py
│   ├── test_webhook.py
│   └── test_integration.py
│
├── docs/
│   ├── design.md                  # architecture, services, events, flows
│   ├── development.md             # this file
│   ├── voice.md                   # custom_sentences setup, multi-turn details
│   ├── webhook.md                 # webhook URL + Seerr config
│   ├── lovelace-example.yaml      # YAML-only fallback (no custom card)
│   ├── automations-examples.yaml  # mobile actionable notifications, logbook
│   └── screenshots/               # logo + UI screenshots
│
└── .github/
    ├── workflows/{tests,lint,validate}.yml
    └── ISSUE_TEMPLATE/
```

## Frontend (Lovelace card) cache busting

The card is served by `__init__.py` at `/haseerr_static/haseerr-card.js?v=<integration_version>`. The `?v=` suffix is read from `manifest.json` at module load — every release rotates it, which forces the HA Companion app's webview (Android/iOS) and browser caches to re-fetch.

`_register_lovelace_resource` matches existing resource entries by **base path** (`/haseerr_static/haseerr-card.js`) and updates them in place when the version differs. This means HACS users upgrading from older releases get the cache-bust on first restart, without manual cache clears.

When iterating on the card during development, bump `manifest.json` `version` (or change `CARD_URL_PATH` temporarily) to force the bust without a release.

## Contributing

Issues and PRs welcome. Run the test suite locally before submitting; CI will block merges that lower coverage or break linting.
