import logging
from .const import DOMAIN, PRESET_STATES_MAPPING, PRESET_CLIMATE_MODES_MAPPING, \
    PRESET_STATES_MAPPING_REVERSE, PRESET_CLIMATE_MODES_MAPPING_REVERSE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.select import SelectEntity

# Initialize a logger for this module.
_LOGGER = logging.getLogger(__name__)

# Asynchronously sets up the select entities for the given configuration entry in Home Assistant.
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""
    # Retrieve the hub instance associated with the configuration entry.
    hub = hass.data[DOMAIN][config_entry.entry_id]
    # Create instances of the global mode and state select entities.
    devices = [RehauNeasmart2MasterGlobalModeSelect(hub), RehauNeasmart2MasterGlobalStateSelect(hub)]

    # If there are devices to add, add them to Home Assistant.
    if devices:
        async_add_entities(devices)

# Base class for Rehau Neasmart2 select entities, inheriting from SelectEntity and RestoreEntity.
class RehauNeasmart2GenericSelect(SelectEntity, RestoreEntity):
    _attr_has_entity_name = False  # Indicates that the entity does not have a unique name.

    def __init__(self, device):
        """Initialize the generic select entity."""
        self._device = device  # Store the device instance.
        self._state = None  # Initialize the state to None.

    @property
    def device_info(self):
        """Provide device information for Home Assistant."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.id)},  # Unique identifiers for the device.
            name=self._device.name,  # Human-readable name of the device.
            manufacturer=self._device.manufacturer,  # Manufacturer of the device.
            model=self._device.model,  # Model of the device.
        )

    @property
    def available(self) -> bool:
        """Indicate whether the device is available based on the hub's online status."""
        return self._device.hub.online

# Specific class for Rehau Neasmart2 global climate mode select entities.
class RehauNeasmart2MasterGlobalModeSelect(RehauNeasmart2GenericSelect):
    def __init__(self, device):
        """Initialize the global climate mode select entity."""
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_global_climate_mode"  # Unique identifier for the entity.
        self._attr_name = f"{self._device.name} Global Climate Mode"  # Human-readable name for the entity.
        self._attr_options = list(PRESET_CLIMATE_MODES_MAPPING.keys())  # Available options for the climate mode.
        self._attr_current_option = None  # Current selected option.

    async def async_select_option(self, option: str) -> None:
        """Asynchronously select a global climate mode option."""
        if not await self._device.set_global_mode(PRESET_CLIMATE_MODES_MAPPING[option]):
            _LOGGER.error(f"Error configuring {option} global climate mode")  # Log an error if setting the mode fails.

    async def async_update(self) -> None:
        """Asynchronously update the current global climate mode."""
        mode = await self._device.get_global_mode()
        if mode is not None:
            self._attr_current_option = PRESET_CLIMATE_MODES_MAPPING_REVERSE[mode]  # Update the current option.
        else:
            _LOGGER.error(f"Error updating global climate mode")  # Log an error if updating the mode fails.

# Specific class for Rehau Neasmart2 global climate state select entities.
class RehauNeasmart2MasterGlobalStateSelect(RehauNeasmart2GenericSelect):
    def __init__(self, device):
        """Initialize the global climate state select entity."""
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_global_climate_state"  # Unique identifier for the entity.
        self._attr_name = f"{self._device.name} Global Climate State"  # Human-readable name for the entity.
        self._attr_options = list(PRESET_STATES_MAPPING.keys())  # Available options for the climate state.
        self._attr_current_option = None  # Current selected option.

    async def async_select_option(self, option: str) -> None:
        """Asynchronously select a global climate state option."""
        if not await self._device.set_global_state(PRESET_STATES_MAPPING[option]):
            _LOGGER.error(f"Error configuring {option} global climate state")  # Log an error if setting the state fails.

    async def async_update(self) -> None:
        """Asynchronously update the current global climate state."""
        state = await self._device.get_global_state()
        if state is not None:
            self._attr_current_option = PRESET_STATES_MAPPING_REVERSE[state]  # Update the current option.
        else:
            _LOGGER.error(f"Error updating global climate state")  # Log an error if updating the state fails.