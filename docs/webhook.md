# Webhook — Seerr → HaSeerr

When configured, Seerr posts notifications to HaSeerr's webhook URL. HaSeerr normalizes them and fires `haseerr_request_status_changed` events on the HA event bus. This is **optional** — submission via `haseerr.request` works without it. Use the webhook if you want HaSeerr (rather than the core `overseerr` integration) to be the source of status updates.

## 1. Find your webhook URL

After installing HaSeerr, the webhook URL is generated automatically. Find it in HA logs at startup:

```bash
ssh root@<your-ha> 'ha core logs -n 200 | grep "HaSeerr webhook URL"'
```

Output looks like:

```
HaSeerr webhook URL: https://your-ha.example.com/api/webhook/<64-char-hex>
```

If you upgraded from v0.1, the integration auto-migrates the entry on next start to add the missing `webhook_id`. No manual action required.

## 2. Configure Seerr

In Seerr → **Settings → Notifications → Webhook**:

| Field | Value |
|-------|-------|
| Webhook URL | the URL from step 1 |
| Authorization Header | leave empty |
| Notification Types | enable any of: Request Pending Approval, Request Approved, Request Available, Request Declined, Request Failed, Request Auto-Approved |
| JSON Payload | leave default |

Click **Save**, then **Test** — you should see HaSeerr accept the test payload (200 OK) and silently ignore it (TEST_NOTIFICATION isn't a real status change).

## 3. Listen for events in HA

```yaml
# automations.yaml
- alias: "Notify when my Seerr request is available"
  trigger:
    - platform: event
      event_type: haseerr_request_status_changed
      event_data:
        status: available
  action:
    - service: notify.mobile_app_<your_device>
      data:
        title: "🎬 Now playing"
        message: >
          {{ trigger.event.data.title }} is available — open Plex.
```

## Event payload

```yaml
event_type: haseerr_request_status_changed
event_data:
  tmdb_id: 693134
  media_type: movie         # movie | tv
  request_id: 1247
  status: approved          # pending | approved | available | declined | failed
  requested_by: "Maria"
  title: "Dune: Part Two"
```

## Status mapping

| Seerr `notification_type` | HaSeerr `status` |
|--------------------------|-----------------|
| `MEDIA_PENDING` | `pending` |
| `MEDIA_AUTO_REQUESTED` | `pending` |
| `MEDIA_APPROVED` | `approved` |
| `MEDIA_AUTO_APPROVED` | `approved` |
| `MEDIA_AVAILABLE` | `available` |
| `MEDIA_DECLINED` | `declined` |
| `MEDIA_FAILED` | `failed` |
| Other (e.g. `TEST_NOTIFICATION`) | ignored, returns 200 |

## External access

The webhook URL must be reachable from your Seerr server. If Seerr runs on the same LAN as HA, use the LAN URL. If Seerr is hosted elsewhere (or behind a different network), expose HA via Nabu Casa Cloud, Tailscale, or a reverse proxy.

## Webhook conflict with core `overseerr`

Seerr supports **one webhook destination at a time**. If you have both HaSeerr and core `overseerr` installed, they can't both consume the webhook. Pick one:

- **HaSeerr webhook** → `haseerr_request_status_changed` events; no auto-populated request lists from core
- **Core `overseerr` webhook** → status sensors + `seerr.get_requests` action; HaSeerr won't see status changes

Most users keep core's webhook and rely on its sensors for state, then trigger automations off those sensors. HaSeerr's webhook path is for setups without core `overseerr` installed.
