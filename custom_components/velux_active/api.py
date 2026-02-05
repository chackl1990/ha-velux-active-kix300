from __future__ import annotations

import asyncio
import time
from typing import Any

from aiohttp import ClientError, ClientResponse
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION


class VeluxKixApiClient:
    """Tiny Velux Active Cloud client mirroring the Ruby script."""

    TOKEN_URL = "https://app.velux-active.com/oauth2/token"
    HOMESDATA_URL = "https://app.velux-active.com/api/homesdata"
    HOMESTATUS_URL = "https://app.velux-active.com/api/homestatus"

    # Values copied from your Ruby script
    CLIENT_ID = "5931426da127d981e76bdd3f"
    CLIENT_SECRET = "6ae2d89d15e767ae5c56b456b452d319"
    USER_PREFIX = "velux"

    def __init__(
        self,
        hass: HomeAssistant,
        account: str,
        password: str,
        entry_id: str,
        token: dict[str, Any] | None = None,
        token_time: float | None = None,
    ) -> None:
        self.hass = hass
        self._session = async_get_clientsession(hass)
        self._account = account
        self._password = password
        self._entry_id = entry_id

        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.token")
        self._token: dict[str, Any] | None = token
        self._token_time: float | None = token_time

        self.last_http_status: int | None = None

    async def async_load_token(self) -> None:
        data = await self._store.async_load()
        if not data:
            return
        self._token = data.get("token")
        self._token_time = data.get("token_time")

    async def async_save_token(self) -> None:
        if self._token is None or self._token_time is None:
            return
        await self._store.async_save({"token": self._token, "token_time": self._token_time})

    @property
    def token(self) -> dict[str, Any] | None:
        return self._token

    @property
    def token_time(self) -> float | None:
        return self._token_time

    def _token_expires_in_seconds(self) -> float | None:
        if not self._token or self._token_time is None:
            return None
        expires_in = float(self._token.get("expires_in", 0) or 0)
        age = time.time() - float(self._token_time)
        return expires_in - age

    async def _post_form(self, url: str, data: dict[str, Any], timeout: float) -> dict[str, Any]:
        try:
            async with asyncio.timeout(timeout):
                resp: ClientResponse
                resp = await self._session.post(url, data=data)
                self.last_http_status = resp.status
                text = await resp.text()
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status} for {url}: {text[:200]}")
                return await resp.json(content_type=None)
        except TimeoutError as err:
            self.last_http_status = None
            raise RuntimeError(f"Timeout calling {url}") from err
        except ClientError as err:
            self.last_http_status = None
            raise RuntimeError(f"Network error calling {url}: {err}") from err

    async def async_login_password_grant(self) -> None:
        payload = {
            "grant_type": "password",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "username": self._account,
            "password": self._password,
            "user_prefix": self.USER_PREFIX,
        }
        token = await self._post_form(self.TOKEN_URL, payload, timeout=20.0)
        self._token = token
        self._token_time = time.time()
        await self.async_save_token()

    async def async_refresh_token(self) -> None:
        if not self._token:
            raise RuntimeError("No token to refresh")
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "refresh_token": self._token.get("refresh_token"),
        }
        token = await self._post_form(self.TOKEN_URL, payload, timeout=20.0)
        self._token = token
        self._token_time = time.time()
        await self.async_save_token()

    async def async_ensure_token(self, forcerefresh: bool = False) -> None:
        if self._token is None:
            await self.async_load_token()

        if self._token is None:
            await self.async_login_password_grant()
            return

        remaining = self._token_expires_in_seconds()
        # Refresh if <10 minutes remaining, or forced.
        if forcerefresh or (remaining is not None and remaining < 600):
            try:
                await self.async_refresh_token()
            except Exception:
                # If refresh fails (invalid/expired refresh token), do password login again
                await self.async_login_password_grant()

    async def async_get_homesdata(self) -> dict[str, Any]:
        if not self._token:
            raise RuntimeError("Missing token")
        return await self._post_form(
            self.HOMESDATA_URL,
            {"access_token": self._token.get("access_token")},
            timeout=8.0,
        )

    async def async_get_homestatus(self, home_id: str) -> dict[str, Any]:
        if not self._token:
            raise RuntimeError("Missing token")
        return await self._post_form(
            self.HOMESTATUS_URL,
            {"access_token": self._token.get("access_token"), "home_id": str(home_id)},
            timeout=8.0,
        )
