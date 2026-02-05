from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import VeluxKixApiClient
from .const import (
    CONF_ACCOUNT,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_TOKEN_TIME,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
)


class VeluxKixDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.api = VeluxKixApiClient(
            hass,
            entry.data[CONF_ACCOUNT],
            entry.data[CONF_PASSWORD],
            entry.entry_id,
            token=entry.data.get(CONF_TOKEN),
            token_time=entry.data.get(CONF_TOKEN_TIME),
        )

        self.last_success_ts: float | None = None
        self.last_http_status: int | None = None  # last request overall

        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            await self.api.async_ensure_token()
            homesdata = await self.api.async_get_homesdata()
            self.last_http_status = self.api.last_http_status

            homes = homesdata.get("body", {}).get("homes", []) or []
            combined: dict[str, Any] = {"homes": {}}

            for home in homes:
                home_id = str(home.get("id"))
                homestatus = await self.api.async_get_homestatus(home_id)
                self.last_http_status = self.api.last_http_status

                combined["homes"][home_id] = {
                    "meta": home,
                    "status": homestatus.get("body", {}).get("home", {}),
                }

            self.last_success_ts = time.time()
            return combined

        except Exception as err:
            # keep last_http_status as "last request overall"
            self.last_http_status = self.api.last_http_status
            raise UpdateFailed(str(err)) from err
