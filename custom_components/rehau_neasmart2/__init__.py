"""The Rehau Neasmart 2.0 integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from . import hub

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.CLIMATE, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rehau Neasmart 2.0 from a config entry."""

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub.RehauNeasmart2ClimateControlSystem(
        hass,
        entry.data["climate_system_name"],
        entry.data["neasmart_gw_server_host"],
        entry.data["neasmart_gw_server_port"],
        entry.data["zones"],
        entry.data.get("mixed_groups", 0),
        entry.data.get("pumps_regs_mapping", ""),
        entry.data.get("dehumidificators_regs_mapping", "")
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
