"""Platform for sensor integration."""

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from homeassistant.const import (
    TEMPERATURE,
    UnitOfTemperature,
    PERCENTAGE,
    DEVICE_CLASS_HUMIDITY,
)
from .const import DOMAIN, PRESENCE_STATES, BINARY_STATUSES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]
    devices = [
        RehauNeasmart2OutsideTemperatureSensor(hub),
        RehauNeasmart2FilteredOutsideTemperatureSensor(hub),
        RehauNeasmart2ErrorsPresentSensor(hub),
        RehauNeasmart2WarningsPresentSensor(hub),
        RehauNeasmart2HintsPresentSensor(hub)
    ]

    for mixg in hub.mixgs:
        devices.append(RehauNeasmart2MixedGroupFlowTemperatureSensor(mixg))
        devices.append(RehauNeasmart2MixedGroupReturnTemperatureSensor(mixg))
        devices.append(RehauNeasmart2MixedGroupValveOpeningSensor(mixg))
        devices.append(RehauNeasmart2MixedGroupPumpStateSensor(mixg))

    for extra_pump in hub.pumps:
        devices.append(RehauNeasmart2ExtraPumpStateSensor(extra_pump))

    for dehumidifier in hub.dehumidifiers:
        devices.append(RehauNeasmart2DehumidifierStateSensor(dehumidifier))

    for zone in hub.zones:
        devices.append(RehauNeasmart2ZoneHumidity(zone))

    if devices:
        async_add_entities(devices)


class RehauNeasmart2GenericSensor(SensorEntity, RestoreEntity):
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

    @property
    def native_value(self) -> float | None:
        return self._state


class RehauNeasmart2OutsideTemperatureSensor(RehauNeasmart2GenericSensor):
    device_class = TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_outside_temperature"
        self._attr_name = f"{self._device.name} Outside Temperature"

    async def async_update(self) -> None:
        outside_temperature = await self._device.get_outside_temperature()
        if outside_temperature is not None:
            self._state = outside_temperature
        else:
            _LOGGER.error(f"Error updating {self._device.id}_outside_temperature")


class RehauNeasmart2FilteredOutsideTemperatureSensor(RehauNeasmart2GenericSensor):
    device_class = TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_filtered_outside_temperature"
        self._attr_name = f"{self._device.name} Filtered Outside Temperature"

    async def async_update(self) -> None:
        filtered_outside_temperature = await self._device.get_filtered_outside_temperature()
        if filtered_outside_temperature is not None:
            self._state = filtered_outside_temperature
        else:
            _LOGGER.error(f"Error updating {self._device.id}_filtered_outside_temperature")


class RehauNeasmart2ErrorsPresentSensor(RehauNeasmart2GenericSensor):
    device_class = "enum"
    _attr_options = list(PRESENCE_STATES.values())
    _state = PRESENCE_STATES[False]

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_errors_presence"
        self._attr_name = f"{self._device.name} Errors"

    async def async_update(self) -> None:
        errors_present = await self._device.get_notification_errors()
        if errors_present is not None:
            self._state = PRESENCE_STATES[errors_present]
        else:
            _LOGGER.error(f"Error updating {self._device.id}_errors_presence")


class RehauNeasmart2WarningsPresentSensor(RehauNeasmart2GenericSensor):
    device_class = "enum"
    _attr_options = list(PRESENCE_STATES.values())
    _state = PRESENCE_STATES[False]

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_warnings_presence"
        self._attr_name = f"{self._device.name} Warnings"

    async def async_update(self) -> None:
        warnings_present = await self._device.get_notification_warnings()
        if warnings_present is not None:
            self._state = PRESENCE_STATES[warnings_present]
        else:
            _LOGGER.error(f"Error updating {self._device.id}_warnings_presence")


class RehauNeasmart2HintsPresentSensor(RehauNeasmart2GenericSensor):
    device_class = "enum"
    _attr_options = list(PRESENCE_STATES.values())
    _state = PRESENCE_STATES[False]

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_hints_presence"
        self._attr_name = f"{self._device.name} Hints"

    async def async_update(self) -> None:
        hints_present = await self._device.get_notification_hints()
        if hints_present is not None:
            self._state = PRESENCE_STATES[hints_present]
        else:
            _LOGGER.error(f"Error updating {self._device.id}_hints_presence")


class RehauNeasmart2MixedGroupFlowTemperatureSensor(RehauNeasmart2GenericSensor):
    device_class = TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_mixedgroup_flow_temperature"
        self._attr_name = f"{self._device.name} Flow Temperature"

    async def async_update(self) -> None:
        flow_temperature = await self._device.get_flow_temperature()
        if flow_temperature is not None:
            self._state = flow_temperature
        else:
            _LOGGER.error(f"Error updating {self._device.id}_mixedgroup_flow_temperature")


class RehauNeasmart2MixedGroupReturnTemperatureSensor(RehauNeasmart2GenericSensor):
    device_class = TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_mixedgroup_return_temperature"
        self._attr_name = f"{self._device.name} Return Temperature"

    async def async_update(self) -> None:
        return_temperature = await self._device.get_return_temperature()
        if return_temperature is not None:
            self._state = return_temperature
        else:
            _LOGGER.error(f"Error updating {self._device.id}_mixedgroup_return_temperature")


class RehauNeasmart2MixedGroupValveOpeningSensor(RehauNeasmart2GenericSensor):
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_valve_opening"
        self._attr_name = f"{self._device.name} Valve Opening"

    async def async_update(self) -> None:
        valve_opening = await self._device.get_valve_opening_percentage()
        if valve_opening is not None:
            self._state = valve_opening
        else:
            _LOGGER.error(f"Error updating {self._device.id}_valve_opening")


class RehauNeasmart2MixedGroupPumpStateSensor(RehauNeasmart2GenericSensor):
    device_class = "enum"
    _attr_options = list(BINARY_STATUSES.values())
    _state = BINARY_STATUSES[0]

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_mixedgroup_pump_state"
        self._attr_name = f"{self._device.name} Pump State"

    async def async_update(self) -> None:
        pump_status = await self._device.get_pump_state()
        if pump_status is not None:
            self._state = BINARY_STATUSES[pump_status]
        else:
            _LOGGER.error(f"Error updating {self._device.id}_mixedgroup_pump_state")


class RehauNeasmart2ExtraPumpStateSensor(RehauNeasmart2GenericSensor):
    device_class = "enum"
    _attr_options = list(BINARY_STATUSES.values())
    _state = BINARY_STATUSES[0]

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_extra_pump_state"
        self._attr_name = f"{self._device.name} Pump State"

    async def async_update(self) -> None:
        pump_status = await self._device.get_pump_state()
        if pump_status is not None:
            self._state = BINARY_STATUSES[pump_status]
        else:
            _LOGGER.error(f"Error updating {self._device.id}_extra_pump_state")


class RehauNeasmart2DehumidifierStateSensor(RehauNeasmart2GenericSensor):

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_dehumidifier_state"
        self._attr_name = f"{self._device.name} Dehumidifiers State"

    async def async_update(self) -> None:
        dehumidifier_status = await self._device.get_dehumidifier_state()
        if dehumidifier_status is not None:
            self._state = dehumidifier_status
        else:
            _LOGGER.error(f"Error updating {self._device.id}_dehumidifier_state")


class RehauNeasmart2ZoneHumidity(RehauNeasmart2GenericSensor):

    device_class = DEVICE_CLASS_HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, device):
        super().__init__(device)
        self._attr_unique_id = f"{self._device.id}_zone_humidity"
        self._attr_name = f"{self._device.name} Humidity"

    async def async_update(self) -> None:
        zone_data = await self._device.get_zone_data()
        if zone_data is not None and zone_data.get("relative_humidity") is not None:
            self._state = zone_data["relative_humidity"]
        else:
            _LOGGER.error(f"Error updating {self._attr_unique_id} thermostat")
