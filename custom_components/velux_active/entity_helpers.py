from __future__ import annotations

import time
from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FAIL_UNAVAILABLE_AFTER_SECONDS
from .coordinator import VeluxKixDataUpdateCoordinator


class VeluxKixBaseEntity(CoordinatorEntity[VeluxKixDataUpdateCoordinator]):
    def __init__(self, coordinator: VeluxKixDataUpdateCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def available(self) -> bool:
        # If we never had a successful update, mark unavailable.
        if self.coordinator.last_success_ts is None:
            return False

        # If updates fail continuously for > 1 hour, mark unavailable.
        if not self.coordinator.last_update_success:
            if (time.time() - self.coordinator.last_success_ts) > FAIL_UNAVAILABLE_AFTER_SECONDS:
                return False

        return True

    def _get_home(self, home_id: str) -> dict[str, Any] | None:
        return (self.coordinator.data or {}).get("homes", {}).get(str(home_id))

    @staticmethod
    def _to_bool01(value: Any) -> int:
        return 1 if bool(value) else 0


def gateway_device_info(home_id: str, home_name: str, gateway_id: str, model: str | None = None) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{home_id}_gateway_{gateway_id}")},
        name="Velux Gateway",
        manufacturer="Velux",
        model=model,
    )


def room_device_info(
    home_id: str,
    home_name: str,
    room_id: str,
    room_name: str,
    gateway_id: str | None = None,
) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{home_id}_room_{room_id}")},
        name=f"Velux {home_name} {room_name} Sensor",
        manufacturer="Velux",
        model="Velux Room Sensor",
        suggested_area=room_name,
        via_device=(DOMAIN, f"{home_id}_gateway_{gateway_id}") if gateway_id else None,
    )


def module_device_info(
    home_id: str,
    home_name: str,
    module_id: str,
    module_name: str,
    gateway_id: str | None = None,
    model: str | None = None,
) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{home_id}_module_{module_id}")},
        name=f"Velux {home_name} {module_name}",
        manufacturer="Velux",
        model=model,
        via_device=(DOMAIN, f"{home_id}_gateway_{gateway_id}") if gateway_id else None,
    )
