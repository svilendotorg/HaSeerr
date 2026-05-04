# Adding HaSeerr to the Overview dashboard (HA 2026.2+)

The new **Overview** dashboard auto-populates from your areas, devices, and a few core integrations. Custom integrations like HaSeerr can't inject themselves directly — instead you add the card to one of the dashboard's sections.

## Quick add

> **Heads up:** the new Overview dashboard's "+ Add card" panel opens with an **entity-first** flow ("Pick an entity, then a card"). HaSeerr-card doesn't bind to a single entity — searching for it there shows *"No entities found for custom:haseerr-card"*. You need the **Manual** card route instead.

1. Open your dashboard: `https://<your-ha>/home/overview` (or just **Overview** in the sidebar).
2. Click **Edit dashboard** (pencil icon, top-right).
3. Pick a section (or **+ Add section**) → click **+ Add card** *inside* the section.
4. In the card picker, scroll to the **bottom** of the list → **Manual**.
5. Paste:

   ```yaml
   type: custom:haseerr-card
   show_quota: true
   ```

6. **Save** the card → **Save dashboard**.

If your picker has a "By card" tab at the top, click it; HaSeerr appears in the list with its icon/description (registered via `window.customCards`). Selecting it from that tab also lets you skip the entity-first flow.

## Recommended section layout

A complete media-request section that uses HaSeerr alongside the built-in `overseerr` integration:

```yaml
title: Media
type: grid
cards:
  - type: heading
    heading: Request something to watch
    heading_style: title

  - type: custom:haseerr-card
    show_quota: true

  - type: heading
    heading: Pending in Seerr
    heading_style: subtitle

  - type: tile
    entity: sensor.overseerr_pending_requests
    name: Pending requests
    state_content: state
    icon: mdi:movie-search-outline
    tap_action:
      action: url
      url_path: !secret seerr_url   # or hard-code https://seerr.example.com

  - type: tile
    entity: sensor.haseerr_status
    name: HaSeerr health
    state_content: state
    icon: mdi:shield-check-outline
```

The **first** card is the search/request UI; the **second** shows pending requests via the core `overseerr` sensor; the **third** is HaSeerr's diagnostic state (`connected` / `unmapped_user` / `error`).

## Why HaSeerr can't auto-add a section

The Overview dashboard's auto-population (Discovered Devices, area summaries, primary sensors) runs against entities that:

- Have a known device class (`temperature`, `humidity`, …)
- Are assigned to an area
- Belong to a "device" with appropriate categorisation

HaSeerr ships exactly one entity, `sensor.haseerr_status` (diagnostic, no device class), so the dashboard's auto-rules don't surface it as a tile. Manual placement is intentional — search-and-request is a deliberate user action, not a passive widget.

## Pin to an area (optional)

If you want HaSeerr's status sensor in the area summary on Overview:

1. Settings → Devices & Services → HaSeerr → **Devices** tile (if present) → **HaSeerr** → **Edit** → set the **Area**.
2. Or directly: Settings → Devices → search `HaSeerr` → set area.

The status sensor will then appear in that area's section on the Overview dashboard.

## Multiple users on one dashboard

If you want different family members to see different defaults (e.g. hide the quota for kids), use **dashboards per-user** — Settings → Dashboards → Manage → Visibility per user. Each user can have their own card config.
