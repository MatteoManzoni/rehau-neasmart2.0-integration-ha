"""Config flow for Rehau Neasmart 2.0 integration."""
from __future__ import annotations

import logging
from typing import Any

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from . import hub

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("climate_system_name"): str,
        vol.Required("neasmart_gw_server_host"): str,
        vol.Required("neasmart_gw_server_port"): int,
        vol.Required("zones"): str,
        vol.Optional("mixed_groups"): int,
        vol.Optional("dehumidificators_regs_mapping"): str,
        vol.Optional("pumps_regs_mapping"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    if len(data["zones"].split(",")) > 48:
        raise TooManyZones
    if data.get("mixed_groups", 0) > 3:
        raise TooManyMixG
    if len(data.get("dehumidificators_regs_mapping", "").split(",")) > 9:
        raise TooManyDehumidificators
    for dr in data.get("dehumidificators_regs_mapping", "").split(",") \
            if data.get("dehumidificators_regs_mapping", "") != "" else []:
        if not dr.isdecimal() or int(dr) < 1 or int(dr) > 9:
            raise InvalidDehumidificatorIndex
    if len(data.get("pumps_regs_mapping", "").split(",")) > 5:
        raise TooManyExtraPumps
    for pr in data.get("pumps_regs_mapping", "").split(",") \
            if data.get("pumps_regs_mapping", "") != "" else []:
        if not pr.isdecimal() or int(pr) < 1 or int(pr) > 5:
            raise InvalidPumpIndex

    neasmart_climate_control_hub = hub.RehauNeasmart2ClimateControlSystem(
        hass,
        data["climate_system_name"],
        data["neasmart_gw_server_host"],
        data["neasmart_gw_server_port"],
        data["zones"],
        data.get("mixed_groups", 0),
        data.get("dehumidificators_regs_mapping", ""),
        data.get("pumps_regs_mapping", "")
    )

    if not await neasmart_climate_control_hub.test_connection():
        raise CannotConnect

    return {"title": f"{data['climate_system_name']} Climate Control System"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rehau Neasmart 2.0."""

    VERSION = 1

    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except TooManyZones:
                errors["base"] = "too_many_zones"
            except TooManyMixG:
                errors["base"] = "too_many_mixg"
            except TooManyDehumidificators:
                errors["base"] = "too_many_dehumidificators"
            except InvalidDehumidificatorIndex:
                errors["base"] = "invalid_dehumidificator_index"
            except TooManyExtraPumps:
                errors["base"] = "too_many_extra_pump"
            except InvalidPumpIndex:
                errors["base"] = "invalid_pump_index"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class TooManyZones(HomeAssistantError):
    """Error to indicate there are too many zones."""


class TooManyMixG(HomeAssistantError):
    """Error to indicate there are too many mixed group."""


class TooManyDehumidificators(HomeAssistantError):
    """Error to indicate there are too many dehumidificators."""


class InvalidDehumidificatorIndex(HomeAssistantError):
    """Error to indicate there are too many pumps."""


class TooManyExtraPumps(HomeAssistantError):
    """Error to indicate there are too many pumps."""


class InvalidPumpIndex(HomeAssistantError):
    """Error to indicate there are too many pumps."""
