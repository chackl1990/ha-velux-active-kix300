# Velux Active KIX 300 – Home Assistant Custom Integration (HACS)

This repository contains a **HACS-compatible** Home Assistant custom integration for **VELUX ACTIVE with NETATMO (KIX 300)** using the cloud API (`app.velux-active.com`).

> ⚠️ **Not official:** This integration is **not** affiliated with, endorsed by, or supported by VELUX/NETATMO.  
> It uses an **unofficial / undocumented** cloud API and may break at any time if the backend changes. Use at your own risk.

## What this integration is for

This integration is intentionally **limited to retrieving missing diagnostics/metadata** that are not exposed through Homekit working setups.

**Device control (open/close) and primary sensor readings (e.g., CO₂) should be obtained via HomeKit**, which works reliably and is the recommended approach here.

In short:
- ✅ Use **HomeKit** for **open/close control** and **CO₂ values**
- ✅ Use this integration for **additional missing values** (gateway/room/module diagnostics)

## Features

- **Config Flow** (UI setup):
  - `Account` (VELUX ACTIVE username)
  - `Password`
- **Persistent token storage** using Home Assistant storage (`.storage`)
- Central polling via `DataUpdateCoordinator`
- API health monitoring:
  - `binary_sensor.velux_active_api_ok` with attribute `last_http_status` (**HTTP status of the last request overall**)
  - If API errors continue for longer than **1 hour**, entities become `unavailable`
- Exposes (when returned by the API):
  - Gateway flags: busy / calibrating / raining / locked / locking / secure
  - Gateway info: last seen timestamp, Wi‑Fi strength
  - Room: air quality, CO2, lux, humidity, temperature *(and whatever the API provides)*
  - Module: current/target position, battery, last seen, reachable

## Fixed polling interval (5 minutes)

The polling interval is **fixed to 5 minutes** and **cannot / should not be changed**.

This is intentional:
- Most devices are **battery-powered**
- They **do not publish data frequently**
- Polling faster provides no benefit and only adds unnecessary load

## Installation (HACS)
[![HACS Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=chackl1990&repository=ha-velux-active-kix300&category=integration)

1. In Home Assistant, go to **HACS → Integrations → ⋮ → Custom repositories**
2. Add this repository URL and select category **Integration**
3. Install **Velux Active KIX 300**
4. Restart Home Assistant
5. Go to **Settings → Devices & services → Add integration**
6. Search for **Velux Active KIX 300** and enter your credentials

## Installation (Manual)

1. Copy the folder `custom_components/velux_active` into your Home Assistant `config/custom_components/`
2. Restart Home Assistant
3. Add the integration via **Settings → Devices & services**

## Entities

Entity names depend on what your VELUX backend returns for your homes/rooms/modules.

- **API status**
  - `binary_sensor.velux_active_api_ok`
    - `on`: last update succeeded **and** last HTTP status was 200
    - `off`: otherwise
    - attribute: `last_http_status`

- **Gateway (per home)**
  - Gateway flags (binary sensors): busy / calibrating / raining / locked / locking / secure
  - `sensor.*gateway_last_seen` (timestamp)
  - `sensor.*gateway_wifi_strength` (%)

- **Room (per room, if values exist)**
  - air quality, CO2, lux, humidity, temperature
  - battery / last seen / reachable if the room sensor is exposed as a module without positions

- **Modules (per module, if values exist)**
  - current/target position, battery, last seen
  - reachable (binary sensor)

## Sensor list (overview)

Sensors are only created if the API returns the corresponding field.

- **Gateway sensors**
  - `sensor.velux_*_gateway_last_seen` (timestamp)
  - `sensor.velux_*_gateway_wifi_strength` (%)

- **Room sensors** (only created if the API returns the field)
  - `sensor.velux_*_*_air_quality`
  - `sensor.velux_*_*_co2` (ppm)
  - `sensor.velux_*_*_humidity` (%)
  - `sensor.velux_*_*_lux` (lx)
  - `sensor.velux_*_*_temperature` (°C)
  - `sensor.velux_*_*_battery` (%)
  - `sensor.velux_*_*_last_seen` (timestamp)
  - `binary_sensor.velux_*_*_reachable`

- **Module sensors** (only created if the API returns the field)
  - `sensor.velux_*_*_current_position` (%)
  - `sensor.velux_*_*_target_position` (%)
  - `sensor.velux_*_*_last_seen` (timestamp)
  - `sensor.velux_*_*_battery` (%)
  - `binary_sensor.velux_*_*_reachable`

## Translations

The integration includes UI translations for:
- English
- German (Deutsch)

## Troubleshooting

Enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.velux_active: debug
```

Then check `binary_sensor.velux_active_api_ok` and its attribute `last_http_status`.

## Security Notes

- Your account credentials are stored by Home Assistant in the config entry.
- OAuth tokens are stored in Home Assistant's `.storage` via the integration.

## License

MIT License. See [LICENSE](LICENSE).

