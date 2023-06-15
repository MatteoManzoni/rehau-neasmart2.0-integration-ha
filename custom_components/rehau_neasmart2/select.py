import logging
from .const import DOMAIN, PRESET_STATES_MAPPING, PRESET_CLIMATE_MODES_MAPPING, \
    PRESET_STATES_MAPPING_REVERSE, PRESET_CLIMATE_MODES_MAPPING_REVERSE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.select import SelectEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]
    devices = [RehauNeasmart2MasterGlobalModeSelect(hub), RehauNeasmart2MasterGlobalStateSelect(hub)]

    if devices:
        async_add_entities(devices)


class RehauNeasmart2GenericSelect(SelectEntity, RestoreEntity):
    _attr_has_entity_name = False

    def __init__(self, device):
        self._device = device
        self._state = None

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.id)},
            name=self._device.name,
            manufacturer=self._device.manufacturer,
            model=self._device.model,
        )

    @property
    def available(self) -> bool:
        return self._device.hub.online


class RehauNeasmart2MasterGlobalModeSelect(RehauNeasmart2GenericSelect):
    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_global_climate_mode"
        self._attr_name = f"{self._device.name} Global Climate Mode"
        self._attr_options = list(PRESET_CLIMATE_MODES_MAPPING.keys())
        self._attr_current_option = None

    async def async_select_option(self, option: str) -> None:
        if not await self._device.set_global_mode(PRESET_CLIMATE_MODES_MAPPING[option]):
            _LOGGER.error(f"Error configuring {option} global climate mode")

    async def async_update(self) -> None:
        mode = await self._device.get_global_mode()
        if mode is not None:
            self._attr_current_option = PRESET_CLIMATE_MODES_MAPPING_REVERSE[mode]
        else:
            _LOGGER.error(f"Error updating global climate mode")


class RehauNeasmart2MasterGlobalStateSelect(RehauNeasmart2GenericSelect):
    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_global_climate_state"
        self._attr_name = f"{self._device.name} Global Climate State"
        self._attr_options = list(PRESET_STATES_MAPPING.keys())
        self._attr_current_option = None

    async def async_select_option(self, option: str) -> None:
        if not await self._device.set_global_state(PRESET_STATES_MAPPING[option]):
            _LOGGER.error(f"Error configuring {option} global climate state")

    async def async_update(self) -> None:
        state = await self._device.get_global_state()
        if state is not None:
            self._attr_current_option = PRESET_STATES_MAPPING_REVERSE[state]
        else:
            _LOGGER.error(f"Error updating global climate state")
