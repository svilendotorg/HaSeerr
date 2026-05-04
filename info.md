## HaSeerr

Submit media requests to **Seerr / Jellyseerr / Overseerr** from Home Assistant — via dashboard card, voice (Assist), or service call. Maps each HA user to their Seerr account so requests carry the right identity and approval rules.

**Complements** the built-in `overseerr` integration (read-only). Both can be installed together.

### Features
- Custom `haseerr-card` Lovelace card with search-and-pick UX
- `haseerr.search`, `haseerr.request`, `haseerr.approve_request`, `haseerr.decline_request` services
- Smart HA-user → Seerr-user mapping wizard (email-exact → name-exact → fuzzy)
- Voice intent (`en` + `bg`)
- Coexists with the built-in `overseerr` integration without conflict
