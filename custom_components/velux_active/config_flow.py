from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import VeluxKixApiClient
from .const import DOMAIN, CONF_ACCOUNT, CONF_PASSWORD, CONF_TOKEN, CONF_TOKEN_TIME


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class VeluxKixConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            account = user_input[CONF_ACCOUNT].strip()
            password = user_input[CONF_PASSWORD]

            # Validate by attempting a login
            api = VeluxKixApiClient(self.hass, account, password, entry_id="__flow__")
            try:
                await api.async_login_password_grant()
            except Exception:
                errors["base"] = "auth"
            else:
                # Use account as unique id to avoid duplicates
                await self.async_set_unique_id(f"{DOMAIN}:{account.lower()}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Velux Active KIX 300 ({account})",
                    data={
                        CONF_ACCOUNT: account,
                        CONF_PASSWORD: password,
                        CONF_TOKEN: api.token,
                        CONF_TOKEN_TIME: api.token_time,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
