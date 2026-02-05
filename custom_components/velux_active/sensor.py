from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import VeluxKixDataUpdateCoordinator
from .entity_helpers import VeluxKixBaseEntity, gateway_device_info, module_device_info, room_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VeluxKixDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    data = coordinator.data or {}
    for home_id, h in (data.get("homes", {}) or {}).items():
        meta = h.get("meta", {}) or {}
        status = h.get("status", {}) or {}
        home_name = meta.get("name", f"home_{home_id}")

        modules_meta = (meta.get("modules") or [])
        rooms_meta = (meta.get("rooms") or [])

        modules_status = status.get("modules") or []
        module_status_by_id = {str(m.get("id")): m for m in modules_status if m.get("id") is not None}

        rooms_status = status.get("rooms") or []
        room_status_by_id = {str(r.get("id")): r for r in rooms_status if r.get("id") is not None}
        module_room_map: dict[str, tuple[str, str]] = {}
        for room in rooms_meta:
            rid = str(room.get("id"))
            rname = room.get("name", rid)
            for mid in (room.get("module_ids") or []):
                module_room_map[str(mid)] = (rid, rname)

        # Gateway data: first module id
        gateway_id = None
        if modules_meta:
            gateway_id = str(modules_meta[0].get("id"))
            entities.extend(
                [
                    VeluxKixGatewaySensor(coordinator, home_id, home_name, gateway_id, "last_seen", "Last Seen", SensorDeviceClass.TIMESTAMP),
                    VeluxKixGatewaySensor(coordinator, home_id, home_name, gateway_id, "wifi_strength", "WiFi Strength", None, unit="%"),
                ]
            )

        # Room sensors
        for room in rooms_meta:
            rid = str(room.get("id"))
            rname = room.get("name", rid)
            rstat = room_status_by_id.get(rid) or {}
            room_entities: list[SensorEntity] = []
            # Only create sensors that exist in room status
            if "air_quality" in rstat:
                room_entities.append(VeluxKixRoomAirQualitySensor(coordinator, home_id, home_name, rid, rname, gateway_id))
            if "co2" in rstat:
                room_entities.append(VeluxKixRoomSensor(coordinator, home_id, home_name, rid, rname, gateway_id, "co2", "CO2", unit="ppm"))
            if "humidity" in rstat:
                room_entities.append(VeluxKixRoomSensor(coordinator, home_id, home_name, rid, rname, gateway_id, "humidity", "Humidity", unit="%"))
            if "lux" in rstat:
                room_entities.append(VeluxKixRoomSensor(coordinator, home_id, home_name, rid, rname, gateway_id, "lux", "Lux", unit="lx"))
            if "temperature" in rstat:
                room_entities.append(VeluxKixRoomTemperatureSensor(coordinator, home_id, home_name, rid, rname, gateway_id))
            if "battery_percent" in rstat:
                room_entities.append(VeluxKixRoomSensor(coordinator, home_id, home_name, rid, rname, gateway_id, "battery_percent", "Battery", unit="%"))
            elif "battery" in rstat:
                room_entities.append(VeluxKixRoomSensor(coordinator, home_id, home_name, rid, rname, gateway_id, "battery", "Battery", unit="%"))

            entities.extend(room_entities)

        # Module sensors
        for m in modules_meta:
            mid = str(m.get("id"))
            mname = m.get("name", mid)
            mstat = module_status_by_id.get(mid) or {}

            # Skip gateway module to avoid duplicate "gateway" entities
            if gateway_id is not None and mid == gateway_id:
                continue

            # Positions
            module_has_position = ("current_position" in mstat) or ("target_position" in mstat)
            room_info = module_room_map.get(mid) if not module_has_position else None
            device_model = "IO Homecontrol Device" if module_has_position else None
            if "current_position" in mstat:
                entities.append(
                    VeluxKixModuleSensor(
                        coordinator,
                        home_id,
                        home_name,
                        mid,
                        mname,
                        gateway_id,
                        "current_position",
                        "Current Position",
                        unit="%",
                        device_model=device_model,
                    )
                )
            if "target_position" in mstat:
                entities.append(
                    VeluxKixModuleSensor(
                        coordinator,
                        home_id,
                        home_name,
                        mid,
                        mname,
                        gateway_id,
                        "target_position",
                        "Target Position",
                        unit="%",
                        device_model=device_model,
                    )
                )
            if "last_seen" in mstat:
                entities.append(
                    VeluxKixModuleSensor(
                        coordinator,
                        home_id,
                        home_name,
                        mid,
                        mname,
                        gateway_id,
                        "last_seen",
                        "Last Seen",
                        SensorDeviceClass.TIMESTAMP,
                        room_info=room_info,
                        device_model=device_model,
                    )
                )
            if "battery_percent" in mstat:
                entities.append(
                    VeluxKixModuleSensor(
                        coordinator,
                        home_id,
                        home_name,
                        mid,
                        mname,
                        gateway_id,
                        "battery_percent",
                        "Battery",
                        SensorDeviceClass.BATTERY,
                        unit="%",
                        room_info=room_info,
                        device_model=device_model,
                    )
                )
            elif "battery" in mstat:
                entities.append(
                    VeluxKixModuleSensor(
                        coordinator,
                        home_id,
                        home_name,
                        mid,
                        mname,
                        gateway_id,
                        "battery",
                        "Battery",
                        SensorDeviceClass.BATTERY,
                        unit="%",
                        room_info=room_info,
                        device_model=device_model,
                    )
                )

    async_add_entities(entities)


class VeluxKixGatewaySensor(VeluxKixBaseEntity, SensorEntity):
    def __init__(
        self,
        coordinator,
        home_id: str,
        home_name: str,
        gateway_id: str,
        key: str,
        label: str,
        device_class: SensorDeviceClass | None,
        unit: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._home_id = str(home_id)
        self._gateway_id = str(gateway_id)
        self._key = key
        self._attr_name = f"Velux {home_name} Gateway {label}"
        self._attr_unique_id = f"{DOMAIN}_{self._home_id}_gateway_{self._gateway_id}_{key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = gateway_device_info(self._home_id, home_name, self._gateway_id)
        if key == "last_seen":
            self._attr_icon = "mdi:clock-check"
        elif key == "wifi_strength":
            self._attr_icon = "mdi:wifi-strength-4"

    @property
    def native_value(self) -> Any:
        h = self._get_home(self._home_id) or {}
        status = (h.get("status", {}) or {})
        modules = status.get("modules") or []
        mod_by_id = {str(m.get("id")): m for m in modules if m.get("id") is not None}
        gw = mod_by_id.get(self._gateway_id) or {}
        if self._key not in gw:
            return None
        val = gw.get(self._key)
        if self._attr_device_class == SensorDeviceClass.TIMESTAMP:
            ts = _coerce_timestamp(val)
            return dt_util.utc_from_timestamp(ts) if ts is not None else None
        # Timestamps are epoch seconds in the API (based on your Ruby usage)
        return float(val) if isinstance(val, (int, float, str)) and str(val).strip() != "" else val


class VeluxKixRoomSensor(VeluxKixBaseEntity, SensorEntity):
    def __init__(
        self,
        coordinator,
        home_id: str,
        home_name: str,
        room_id: str,
        room_name: str,
        gateway_id: str | None,
        key: str,
        label: str,
        unit: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._home_id = str(home_id)
        self._room_id = str(room_id)
        self._key = key
        self._attr_name = f"Velux {home_name} {room_name} Sensor {label}"
        self._attr_unique_id = f"{DOMAIN}_{self._home_id}_room_{self._room_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = room_device_info(self._home_id, home_name, self._room_id, room_name, gateway_id)
        if key == "air_quality":
            self._attr_icon = "mdi:air-filter"
        elif key == "co2":
            self._attr_icon = "mdi:molecule-co2"
        elif key == "humidity":
            self._attr_icon = "mdi:water-percent"
        elif key == "lux":
            self._attr_icon = "mdi:brightness-5"
        elif key == "temperature":
            self._attr_icon = "mdi:thermometer"
        elif key in ("battery", "battery_percent"):
            self._attr_icon = "mdi:battery"

    @property
    def native_value(self) -> Any:
        h = self._get_home(self._home_id) or {}
        status = (h.get("status", {}) or {})
        rooms = status.get("rooms") or []
        room_by_id = {str(r.get("id")): r for r in rooms if r.get("id") is not None}
        r = room_by_id.get(self._room_id) or {}
        if self._key not in r:
            return None
        return float(r.get(self._key))


class VeluxKixRoomTemperatureSensor(VeluxKixRoomSensor):
    def __init__(self, coordinator, home_id: str, home_name: str, room_id: str, room_name: str, gateway_id: str | None) -> None:
        super().__init__(coordinator, home_id, home_name, room_id, room_name, gateway_id, "temperature", "Temperature", unit="°C")

    @property
    def native_value(self) -> Any:
        h = self._get_home(self._home_id) or {}
        status = (h.get("status", {}) or {})
        rooms = status.get("rooms") or []
        room_by_id = {str(r.get("id")): r for r in rooms if r.get("id") is not None}
        r = room_by_id.get(self._room_id) or {}
        if "temperature" not in r:
            return None
        # Ruby divides by 10.0
        return float(r.get("temperature")) / 10.0


class VeluxKixRoomAirQualitySensor(VeluxKixRoomSensor):
    _AQ_OPTIONS = ["excellent", "very_good", "good", "poor", "warning"]

    def __init__(self, coordinator, home_id: str, home_name: str, room_id: str, room_name: str, gateway_id: str | None) -> None:
        super().__init__(coordinator, home_id, home_name, room_id, room_name, gateway_id, "air_quality", "Air Quality")
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = list(self._AQ_OPTIONS)
        self._attr_translation_key = "air_quality"
        self._attr_icon = "mdi:air-filter"

    @property
    def native_value(self) -> Any:
        h = self._get_home(self._home_id) or {}
        status = (h.get("status", {}) or {})
        rooms = status.get("rooms") or []
        room_by_id = {str(r.get("id")): r for r in rooms if r.get("id") is not None}
        r = room_by_id.get(self._room_id) or {}
        if "air_quality" not in r:
            return None
        val = r.get("air_quality")
        try:
            idx = int(val)
        except (TypeError, ValueError):
            return None
        if 0 <= idx < len(self._AQ_OPTIONS):
            return self._AQ_OPTIONS[idx]
        return None


class VeluxKixModuleSensor(VeluxKixBaseEntity, SensorEntity):
    def __init__(
        self,
        coordinator,
        home_id: str,
        home_name: str,
        module_id: str,
        module_name: str,
        gateway_id: str | None,
        key: str,
        label: str,
        device_class: SensorDeviceClass | None = None,
        unit: str | None = None,
        room_info: tuple[str, str] | None = None,
        device_model: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._home_id = str(home_id)
        self._module_id = str(module_id)
        self._key = key
        if room_info:
            room_id, room_name = room_info
            self._attr_name = f"Velux {home_name} {room_name} Sensor {label}"
            self._attr_device_info = room_device_info(self._home_id, home_name, room_id, room_name, gateway_id)
        else:
            self._attr_name = f"Velux {home_name} {module_name} {label}"
            self._attr_device_info = module_device_info(
                self._home_id,
                home_name,
                self._module_id,
                module_name,
                gateway_id,
                model=device_model,
            )
        self._attr_unique_id = f"{DOMAIN}_{self._home_id}_module_{self._module_id}_{key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        if key == "current_position":
            self._attr_icon = "mdi:window-shutter"
        elif key == "target_position":
            self._attr_icon = "mdi:target"
        elif key == "last_seen":
            self._attr_icon = "mdi:clock-check"
        elif key in ("battery", "battery_percent"):
            self._attr_icon = "mdi:battery"

    @property
    def native_value(self) -> Any:
        h = self._get_home(self._home_id) or {}
        status = (h.get("status", {}) or {})
        modules = status.get("modules") or []
        mod_by_id = {str(m.get("id")): m for m in modules if m.get("id") is not None}
        m = mod_by_id.get(self._module_id) or {}
        if self._key not in m:
            return None
        val = m.get(self._key)
        if self._attr_device_class == SensorDeviceClass.TIMESTAMP:
            ts = _coerce_timestamp(val)
            return dt_util.utc_from_timestamp(ts) if ts is not None else None
        return float(val) if isinstance(val, (int, float, str)) and str(val).strip() != "" else val


def _coerce_timestamp(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    # Heuristic: treat large values as milliseconds
    if ts >= 1_000_000_000_000:
        ts = ts / 1000.0
    return ts
