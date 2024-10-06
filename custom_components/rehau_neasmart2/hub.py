"""A demonstration 'hub' that connects several devices."""
from __future__ import annotations

from typing import Any

import requests

from homeassistant.core import HomeAssistant
from .const import (
    BINARY_STATUSES
)
import logging

# Initialize a logger for this module.
_LOGGER = logging.getLogger(__name__)

# Class representing the Rehau Neasmart 2.0 Climate Control System hub.
class RehauNeasmart2ClimateControlSystem:
    def __init__(self,
                 hass: HomeAssistant,
                 sysname: str,
                 shim_host: str,
                 shim_port: int,
                 zones: str,
                 mixg: int,
                 pumps: str,
                 dehumidifiers: str) -> None:
        """Initialize the Rehau Neasmart 2.0 Climate Control System hub."""
        self.hass = hass  # Home Assistant instance.
        self.shim_host = shim_host  # Host address of the shim server.
        self.shim_port = shim_port  # Port number of the shim server.
        self.shim_base_url = f"http://{self.shim_host}:{self.shim_port}"  # Base URL for the shim server.
        self.name = "{} Climate Control System".format(sysname)  # Name of the climate control system.
        self.model = "Neasmart 2.0 Base Station"  # Model of the base station.
        self.manufacturer = "Rehau"  # Manufacturer of the base station.
        self.online = True  # Online status of the hub.
        self._id = sysname  # Unique identifier for the hub.
        self.hub = self  # Reference to the hub itself.
        self.mixgs = []  # List to store mixed groups.
        self.zones = []  # List to store zones.
        self.pumps = []  # List to store pumps.
        self.dehumidifiers = []  # List to store dehumidifiers.

        # Parse the topology of dehumidifiers, pumps, and zones.
        dehumidifiers_topology = dehumidifiers.split(",") if dehumidifiers != "" else []
        pumps_topology = pumps.split(",") if pumps != "" else []
        zones_name_array = zones.split(",")

        # Initialize mixed groups, dehumidifiers, pumps, and zones.
        self.mixgs = [RehauNeasmart2MixedGroup(m, self) for m in range(1, mixg + 1)]
        self.dehumidifiers = [RehauNeasmart2Dehumidifier(int(dehumidifiers_topology[d]), self)
                              for d in range(0, len(dehumidifiers_topology))]
        self.pumps = [RehauNeasmart2Pump(int(pumps_topology[p]), self) for p in range(0, len(pumps_topology))]
        self.zones = [RehauNeasmart2Zone((z // 12) + 1, z - (12 * (z // 12)) + 1, zones_name_array[z], self)
                      for z in range(0, len(zones_name_array))]

    @property
    def id(self) -> str:
        """Return the unique identifier of the hub."""
        return self._id

    # Asynchronously test the connection to the shim server.
    async def test_connection(self) -> bool:
        """Test the connection to the shim server."""
        return await self.hass.async_add_executor_job(self._check_shim_online)

    # Check if the shim server is online.
    def _check_shim_online(self) -> bool:
        """Check if the shim server is online by sending a health check request."""
        r = requests.get(f"{self.shim_base_url}/health")
        return r.status_code == 200

    # Asynchronously get the outside temperature.
    async def get_outside_temperature(self) -> float | None:
        """Retrieve the outside temperature."""
        outside_temperature = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "outsidetemperature",
            "outside_temperature",
            None
        )
        return outside_temperature

    # Asynchronously get the filtered outside temperature.
    async def get_filtered_outside_temperature(self) -> float | None:
        """Retrieve the filtered outside temperature."""
        filtered_outside_temperature = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "outsidetemperature",
            "filtered_outside_temperature",
            None
        )
        return filtered_outside_temperature

    # Asynchronously get notification hints.
    async def get_notification_hints(self) -> bool | None:
        """Retrieve notification hints."""
        hints_present = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "notifications",
            "hints_present",
            None
        )
        return hints_present

    # Asynchronously get notification warnings.
    async def get_notification_warnings(self) -> bool | None:
        """Retrieve notification warnings."""
        warnings_present = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "notifications",
            "warnings_present",
            None
        )
        return warnings_present

    # Asynchronously get notification errors.
    async def get_notification_errors(self) -> bool | None:
        """Retrieve notification errors."""
        errors_present = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "notifications",
            "error_present",
            None
        )
        return errors_present

    # Asynchronously get the global state.
    async def get_global_state(self) -> int | None:
        """Retrieve the global state of the climate control system."""
        state = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "state",
            "state",
            None
        )
        return state

    # Asynchronously set the global state.
    async def set_global_state(self, state: int) -> bool:
        """Set the global state of the climate control system."""
        payload = {"state": state}
        return await self.hass.async_add_executor_job(
            self.data_setter_helper,
            "state",
            payload
        )

    # Asynchronously get the global mode.
    async def get_global_mode(self) -> int | None:
        """Retrieve the global mode of the climate control system."""
        mode = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "mode",
            "mode",
            None
        )
        return mode

    # Asynchronously set the global mode.
    async def set_global_mode(self, mode: int) -> bool:
        """Set the global mode of the climate control system."""
        payload = {"mode": mode}
        return await self.hass.async_add_executor_job(
            self.data_setter_helper,
            "mode",
            payload
        )

    # Helper function to set data on the shim server.
    def data_setter_helper(self, endpoint, payload) -> bool:
        """Helper function to send data to the shim server."""
        r = requests.post(f"{self.shim_base_url}/{endpoint}", json=payload)
        if r.status_code != 202:
            _LOGGER.error(f"Error sending {payload} to {self.shim_base_url}/{endpoint}, code {r.status_code}")
            return False
        return True

    # Helper function to get data from the shim server.
    def data_getter_helper(self, endpoint, key, default):
        """Helper function to retrieve data from the shim server."""
        r = requests.get(f"{self.shim_base_url}/{endpoint}")
        if r.status_code != 200:
            _LOGGER.error(f"Error calling {self.shim_base_url}/{endpoint}, code {r.status_code}")
            return default
        json_response = r.json()
        data = json_response.get(key)
        if data is None:
            _LOGGER.error(f"Error retrieving data from {self.shim_base_url}/{endpoint}, "
                          f"cannot access {key} in response: {json_response}")
            return default
        return data

# Class representing a mixed group controlled by Rehau Neasmart 2.0.
class RehauNeasmart2MixedGroup:
    """Rehau Neasmart 2.0 controlled Mixed Group"""

    def __init__(self, mixedgroup_id: int, hub: RehauNeasmart2ClimateControlSystem) -> None:
        """Initialize the mixed group with its ID and associated hub."""
        self._id = f"{hub.id}_{mixedgroup_id}"  # Unique identifier for the mixed group.
        self.name = f"Mixed Group #{mixedgroup_id}"  # Human-readable name for the mixed group.
        self.hub = hub  # Reference to the associated hub.
        self.model = "Mixed Group w/ 24/230 Pump and 0-10v controlled mixing valve"  # Model of the mixed group.
        self.manufacturer = "Rehau"  # Manufacturer of the mixed group.
        self.mixg_id = mixedgroup_id  # ID of the mixed group.

    @property
    def id(self) -> str:
        """Return the unique identifier of the mixed group."""
        return self._id

    # Asynchronously get the flow temperature of the mixed group.
    async def get_flow_temperature(self) -> float | None:
        """Retrieve the flow temperature for the mixed group."""
        flow_temperature = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"mixedgroups/{self.mixg_id}",
            "flow_temperature",
            None
        )
        return flow_temperature

    # Asynchronously get the return temperature of the mixed group.
    async def get_return_temperature(self) -> float | None:
        """Retrieve the return temperature for the mixed group."""
        return_temperature = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"mixedgroups/{self.mixg_id}",
            "return_temperature",
            None
        )
        return return_temperature

    # Asynchronously get the valve opening percentage of the mixed group.
    async def get_valve_opening_percentage(self) -> int | None:
        """Retrieve the valve opening percentage for the mixed group."""
        valve_opening_percentage = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"mixedgroups/{self.mixg_id}",
            "mixing_valve_opening_percentage",
            None
        )
        return valve_opening_percentage

    # Asynchronously get the pump state of the mixed group.
    async def get_pump_state(self) -> str | None:
        """Retrieve the pump state for the mixed group."""
        pump_state = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"mixedgroups/{self.mixg_id}",
            "pump_state",
            None
        )
        return pump_state

# Class representing a dehumidifier controlled by Rehau Neasmart 2.0.
class RehauNeasmart2Dehumidifier:
    """Rehau Neasmart 2.0 controlled Dehumidifier."""

    def __init__(self, dehumidifier_id: int, hub: RehauNeasmart2ClimateControlSystem) -> None:
        """Initialize the dehumidifier with its ID and associated hub."""
        self._id = f"{hub.id}_{dehumidifier_id}"  # Unique identifier for the dehumidifier.
        self.name = f"Dehumidifier #{dehumidifier_id}"  # Human-readable name for the dehumidifier.
        self.hub = hub  # Reference to the associated hub.
        self.model = "Dehumidifier with optional hydronic battery"  # Model of the dehumidifier.
        self.manufacturer = "Rehau"  # Manufacturer of the dehumidifier.
        self.dehumidifier_id = dehumidifier_id  # ID of the dehumidifier.

    @property
    def id(self) -> str:
        """Return the unique identifier of the dehumidifier."""
        return self._id

    # Asynchronously get the state of the dehumidifier.
    async def get_dehumidifier_state(self) -> str | None:
        """Retrieve the state of the dehumidifier."""
        dehumidifier_state = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"dehumidifiers/{self.dehumidifier_id}",
            "dehumidifier_state",
            None
        )
        return BINARY_STATUSES[dehumidifier_state]

# Class representing an extra pump controlled by Rehau Neasmart 2.0.
class RehauNeasmart2Pump:
    """Rehau Neasmart 2.0 controlled Extra Pump."""

    def __init__(self, pump_id: int, hub: RehauNeasmart2ClimateControlSystem) -> None:
        """Initialize the pump with its ID and associated hub."""
        self._id = f"{hub.id}_{pump_id}"  # Unique identifier for the pump.
        self.name = f"Extra Pump #{pump_id}"  # Human-readable name for the pump.
        self.hub = hub  # Reference to the associated hub.
        self.model = "On-Off 24/230v Pump"  # Model of the pump.
        self.manufacturer = "Rehau"  # Manufacturer of the pump.
        self.pump_id = pump_id  # ID of the pump.

    @property
    def id(self) -> str:
        """Return the unique identifier of the pump."""
        return self._id

    # Asynchronously get the state of the pump.
    async def get_pump_state(self) -> str | None:
        """Retrieve the state of the pump."""
        pump_state = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"pumps/{self.pump_id}",
            "pump_state",
            None
        )
        return pump_state

# Class representing a zone controlled by Rehau Neasmart 2.0.
class RehauNeasmart2Zone:
    """Rehau Neasmart 2.0 controlled Zone"""

    def __init__(self, base_id: int, zone_id: int, name: str, hub: RehauNeasmart2ClimateControlSystem) -> None:
        """Initialize the zone with its base ID, zone ID, name, and associated hub."""
        self._id = f"{hub.id}_{base_id}_{zone_id}"  # Unique identifier for the zone.
        self.name = f"{name}"  # Human-readable name for the zone.
        self.hub = hub  # Reference to the associated hub.
        self.zone_id = zone_id  # ID of the zone.
        self.base_id = base_id  # Base ID of the zone.
        self.model = "Neasmart 2.0 Room Thermostat"  # Model of the zone.
        self.manufacturer = "Rehau"  # Manufacturer of the zone.

    @property
    def id(self) -> str:
        """Return the unique identifier of the zone."""
        return self._id

    # Asynchronously get the data of the zone.
    async def get_zone_data(self) -> dict | None:
        """Retrieve the data for the zone."""
        r = await self.hub.hass.async_add_executor_job(
            requests.get, f"{self.hub.shim_base_url}/zones/{self.base_id}/{self.zone_id}")
        if r.status_code != 200:
            _LOGGER.error(f"Error calling {self.hub.shim_base_url}/zones/{self.base_id}/{self.zone_id}, "
                          f"code {r.status_code}")
            return None
        json_response = r.json()
        return json_response

    # Asynchronously set the setpoint of the zone.
    async def set_zone_setpoint(self, setpoint: float) -> bool:
        """Set the setpoint temperature for the zone."""
        payload = {"setpoint": setpoint}
        return await self.hub.hass.async_add_executor_job(
            self.hub.data_setter_helper,
            f"zones/{self.base_id}/{self.zone_id}",
            payload
        )

    # Asynchronously set the state of the zone.
    async def set_zone_state(self, state: int) -> bool:
        """Set the state for the zone."""
        payload = {"state": state}
        return await self.hub.hass.async_add_executor_job(
            self.hub.data_setter_helper,
            f"zones/{self.base_id}/{self.zone_id}",
            payload
        )