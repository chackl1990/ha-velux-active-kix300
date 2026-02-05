from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import VeluxKixDataUpdateCoordinator
from .entity_helpers import VeluxKixBaseEntity, module_device_info, room_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VeluxKixDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = [VeluxKixApiOkBinarySensor(coordinator)]

    data = coordinator.data or {}
    for home_id, h in (data.get("homes", {}) or {}).items():
        meta = h.get("meta", {}) or {}
        home_name = meta.get("name", f"home_{home_id}")

        modules_meta = (meta.get("modules") or [])
        rooms_meta = (meta.get("rooms") or [])
        gateway_id = None
        if modules_meta:
            gateway_id = str(modules_meta[0].get("id"))

        # Module reachable per module
        status = h.get("status", {}) or {}
        modules_status = status.get("modules") or []
        module_status_by_id = {str(m.get("id")): m for m in modules_status if m.get("id") is not None}
        module_room_map: dict[str, tuple[str, str]] = {}
        for room in rooms_meta:
            rid = str(room.get("id"))
            rname = room.get("name", rid)
            for mid in (room.get("module_ids") or []):
                module_room_map[str(mid)] = (rid, rname)

        for m in (meta.get("modules") or []):
            mid = str(m.get("id"))
            mname = m.get("name", mid)
            mstat = module_status_by_id.get(mid) or {}
            if "reachable" in mstat:
                module_has_position = ("current_position" in mstat) or ("target_position" in mstat)
                room_info = module_room_map.get(mid) if not module_has_position else None
                device_model = "IO Homecontrol Device" if module_has_position else None
                entities.append(
                    VeluxKixModuleReachableBinarySensor(
                        coordinator,
                        home_id,
                        home_name,
                        mid,
                        mname,
                        gateway_id,
                        room_info=room_info,
                        device_model=device_model,
                    )
                )

    async_add_entities(entities)


class VeluxKixApiOkBinarySensor(VeluxKixBaseEntity, BinarySensorEntity):
    _attr_name = "Velux Active KIX 300 API OK"
    _attr_unique_id = f"{DOMAIN}_api_ok"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:cloud-check"
    _attr_device_info = DeviceInfo(
        identifiers={(DOMAIN, "api")},
        name="Velux API",
        manufacturer="Velux",
        model="Cloud API",
    )

    @property
    def is_on(self) -> bool | None:
        # "Letzter Request insgesamt": evaluate based on last HTTP status and coordinator success
        status = self.coordinator.last_http_status
        return bool(self.coordinator.last_update_success and status == 200)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"last_http_status": self.coordinator.last_http_status}


class VeluxKixModuleReachableBinarySensor(VeluxKixBaseEntity, BinarySensorEntity):
    def __init__(
        self,
        coordinator,
        home_id: str,
        home_name: str,
        module_id: str,
        module_name: str,
        gateway_id: str | None,
        room_info: tuple[str, str] | None = None,
        device_model: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._home_id = str(home_id)
        self._module_id = str(module_id)
        if room_info:
            room_id, room_name = room_info
            self._attr_name = f"Velux {home_name} {room_name} Sensor Reachable"
            self._attr_device_info = room_device_info(self._home_id, home_name, room_id, room_name, gateway_id)
        else:
            self._attr_name = f"Velux {home_name} {module_name} Reachable"
            self._attr_device_info = module_device_info(
                self._home_id,
                home_name,
                self._module_id,
                module_name,
                gateway_id,
                model=device_model,
            )
        self._attr_unique_id = f"{DOMAIN}_{self._home_id}_module_{self._module_id}_reachable"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:lan-connect"

    @property
    def is_on(self) -> bool | None:
        h = self._get_home(self._home_id) or {}
        status = (h.get("status", {}) or {})
        modules = status.get("modules") or []
        mod_by_id = {str(m.get("id")): m for m in modules if m.get("id") is not None}
        m = mod_by_id.get(self._module_id) or {}
        if "reachable" not in m:
            return None
        return bool(m.get("reachable"))
