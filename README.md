# BabyCry Bridge (Tapo)

Custom Home Assistant integration that polls a Tapo camera directly and exposes a binary sensor for baby-cry events.

## Features

- Direct local login to Tapo camera (`pytapo`)
- Polls recent events and maps configured alarm types to baby-cry
- Exposes one entity: `binary_sensor.barnerom_baby_cry_direct` (entity name: **Barnerom Baby Cry (Direct)**)
- Configurable poll interval, on-hold duration, and alarm types
- Writes every poll (raw camera events + metadata) to `config/babycry_bridge_events.jsonl` for debugging/tuning

## Install (HACS custom repository)

1. Push this repo to GitHub.
2. In HACS: **Integrations → ⋮ → Custom repositories**.
3. Add this repo URL and category **Integration**.
4. Install **BabyCry Bridge (Tapo)**.
5. Restart Home Assistant.

## Configure

Add integration from UI and provide:

- Host (camera IP)
- Username
- Password
- Cloud password (optional, some camera auth setups need it)
- Poll seconds (default 8)
- Hold seconds (default 30)
- Trigger delay seconds (default 0 = immediate)
- Alarm types (comma-separated, default `7`)

## Notes

- Alarm type mapping may vary by camera firmware/model.
- Start with `7` (observed on C200 setup) and adjust if needed.
- Event log rotates at ~10 MB (`babycry_bridge_events.jsonl.1` keeps previous file).

## Debug service (for tuning)

Service: `babycry_bridge.get_recent_logs` (response-only)

Example (HA API):

```bash
curl -X POST "$HA_URL/api/services/babycry_bridge/get_recent_logs?return_response" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lines": 200}'
```

This returns latest JSON log records so you can inspect lag/false positives without direct filesystem access.
