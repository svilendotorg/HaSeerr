# Voice (Assist)

HaSeerr ships three intents:

- **`RequestMedia`** — searches Seerr and asks for confirmation
- **`ConfirmRequest`** — submits the pending request
- **`CancelRequest`** — drops the pending request

## Multi-turn flow

> 🎤 *"Hey Assist, request Dune Part Two"*
> 🔊 *"Did you mean Dune: Part Two from 2024, the movie?"*
> 🎤 *"Yes."*
> 🔊 *"Requested Dune: Part Two."*

Confirmation window is **60 seconds**. After that, "yes" replies *"Nothing to confirm."*

Bulgarian: `поискай <title>` → `да` (confirm) / `не` (cancel).

## ⚠️ One-time setup: custom sentences

HA's built-in conversation matcher (`conversation.home_assistant`) does NOT auto-discover sentence patterns from a custom integration's `intents/<lang>.yaml` files. The intent **handler** is registered by HaSeerr automatically, but the sentence **patterns** (what HA matches against your speech) must live at `<config>/custom_sentences/<lang>/haseerr.yaml`.

Without this step, Assist will reply *"Sorry, I couldn't understand that"* to `request <title>`.

### Install the sentences

Drop these two files into your HA config directory:

**`<config>/custom_sentences/en/haseerr.yaml`**

```yaml
language: en
intents:
  RequestMedia:
    data:
      - sentences:
          - "request {title}"
          - "(can you|please) request {title}"
          - "add {title} to (Seerr|Plex|Jellyfin)"
        slots:
          title: "{title}"
        requires_context: {}
      - sentences:
          - "request {title} season {season}"
        slots:
          title: "{title}"
          season: "{season}"
        requires_context: {}
  ConfirmRequest:
    data:
      - sentences:
          - "yes"
          - "yes please"
          - "confirm"
          - "go ahead"
          - "do it"
  CancelRequest:
    data:
      - sentences:
          - "no"
          - "cancel"
          - "abort"
          - "never mind"
          - "nevermind"
lists:
  title:
    wildcard: true
  season:
    wildcard: true
```

**`<config>/custom_sentences/bg/haseerr.yaml`** (Bulgarian)

```yaml
language: bg
intents:
  RequestMedia:
    data:
      - sentences:
          - "поискай {title}"
          - "(можеш ли да|моля) поискай {title}"
          - "добави {title} в (Seerr|Plex|Jellyfin)"
        slots:
          title: "{title}"
      - sentences:
          - "поискай {title} сезон {season}"
        slots:
          title: "{title}"
          season: "{season}"
  ConfirmRequest:
    data:
      - sentences:
          - "да"
          - "да моля"
          - "потвърди"
          - "давай"
  CancelRequest:
    data:
      - sentences:
          - "не"
          - "отказ"
          - "забрави"
lists:
  title:
    wildcard: true
  season:
    wildcard: true
```

Restart HA after creating the files. Test in **Settings → Voice assistants → Assist** by typing `request The Bear`. You should get the confirmation prompt.

## Why doesn't HaSeerr install the sentences automatically?

HA core deliberately scopes what's writable: integrations have access to `hass.data` and `hass.config_entries`, not arbitrary write access to `<config>/custom_sentences/`. Asking the user to drop a file is the supported pattern.

## Pipelines (en + bg)

To talk in both languages, set up two Assist pipelines:

| Pipeline | Conversation language | STT | TTS |
|----------|----------------------|-----|-----|
| English | `en` | faster-whisper / Cloud | Piper / Cloud |
| Български | `bg` | faster-whisper (multilingual model, e.g. `small-int8`, language `bg` or `auto`) | Edge TTS (HACS) → `bg-BG-KalinaNeural` (Piper has no Bulgarian voice) |

The HaSeerr intent handler reads `intent_obj.language`; replies in Bulgarian when language starts with `bg`.

## Voice satellites (ESP32-S3-Box, Atom Echo, Voice PE)

These devices are language-agnostic — they stream audio to whichever pipeline you assign per-device in **Settings → Voice assistants → Devices**. No firmware changes needed for HaSeerr.

## Limitations

- Free-form natural language ("could you maybe request that one Tarantino film…") needs an LLM-backed conversation agent (e.g. `OpenAI Conversation`). HaSeerr's intents work with HA's built-in rule-based matcher.
- Movie titles in Seerr's response come back in the language of your Seerr's locale. To get English, change Seerr → Settings → Users → your user → Display Language → English.
