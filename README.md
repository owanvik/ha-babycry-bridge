# BabyCry Bridge (Tapo)

Custom Home Assistant integration that polls a Tapo camera directly and exposes a binary sensor for baby-cry events.

## Features

- Direct local login to Tapo camera (`pytapo`)
- Polls recent events and maps configured alarm types to baby-cry
- Exposes one entity: `binary_sensor.barnerom_baby_cry_direct` (entity name: **Barnerom Baby Cry (Direct)**)
- Configurable poll interval, on-hold duration, and alarm types

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
- Hold seconds (default 90)
- Alarm types (comma-separated, default `7`)

## Notes

- Alarm type mapping may vary by camera firmware/model.
- Start with `7` (observed on C200 setup) and adjust if needed.
