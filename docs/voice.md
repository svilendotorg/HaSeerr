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
| Български | `bg` | faster-whisper, ideally a Bulgarian fine-tune (see below) | Edge TTS (HACS) → `bg-BG-KalinaNeural` (Piper has no Bulgarian voice) |

The HaSeerr intent handler reads `intent_obj.language`; replies in Bulgarian when language starts with `bg`.

### Bulgarian STT — fine-tuned Whisper for better recognition

Vanilla `whisper-medium-int8` on Bulgarian has ~25% WER, and the BG verb `изтегли` ("download") is consistently mistranscribed as `истегли`, `изтеглий`, `изтъгли`, etc. The shipped HaSeerr `intents/bg.yaml` already absorbs the common variants, but you can also (or instead) swap in a Bulgarian fine-tuned Whisper model.

The HA `core_whisper` add-on accepts custom HuggingFace models:

```yaml
beam_size: 0
custom_model: svilendotorg/whisper-medium-bg-ct2  # or another HF model id
custom_model_type: faster-whisper
debug_logging: false
language: bg
model: custom
stt_library: faster-whisper
```

`svilendotorg/whisper-medium-bg-ct2` is `shripadbhat/whisper-medium-bg` (medium fine-tune on FLEURS) converted to CTranslate2 with `int8_float16` quantization — drop-in swap with the vanilla `medium-int8` size.

Two add-on caveats worth knowing:

1. **`custom_model:` must be an HF repo ID, not a local path.** The wyoming-faster-whisper version bundled with the add-on calls `huggingface_hub.snapshot_download()` directly without the `os.path.isdir()` check newer faster-whisper has — local paths fail with `HFValidationError`.
2. **`stt_library: transformers` is in the schema but not implemented** — selecting it crashes the runtime. Only `faster-whisper` works.

To convert a transformers-format Whisper fine-tune yourself:

```bash
pip install ctranslate2 transformers torch huggingface_hub
ct2-transformers-converter \
  --model <hf_id> --output_dir <name>-ct2 --quantization int8_float16
# Some BG fine-tunes don't ship tokenizer.json/preprocessor_config.json — pull from openai/whisper-<size>:
python -c "from huggingface_hub import hf_hub_download; import shutil
for f in ['tokenizer.json', 'preprocessor_config.json']:
    shutil.copy(hf_hub_download('openai/whisper-medium', f), '<name>-ct2/' + f)"
huggingface-cli upload <namespace>/<name>-ct2 <name>-ct2
```

## Voice satellites (ESP32-S3-Box, Atom Echo, Voice PE)

These devices are language-agnostic — they stream audio to whichever pipeline you assign per-device in **Settings → Voice assistants → Devices**. No firmware changes needed for HaSeerr.

## Limitations

- Free-form natural language ("could you maybe request that one Tarantino film…") needs an LLM-backed conversation agent (e.g. `OpenAI Conversation`). HaSeerr's intents work with HA's built-in rule-based matcher.
- Movie titles in Seerr's response come back in the language of your Seerr's locale. To get English, change Seerr → Settings → Users → your user → Display Language → English.
