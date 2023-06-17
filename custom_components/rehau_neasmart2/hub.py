"""A demonstration 'hub' that connects several devices."""
from __future__ import annotations

from typing import Any

import requests

from homeassistant.core import HomeAssistant
from .const import (
    BINARY_STATUSES
)
import logging

_LOGGER = logging.getLogger(__name__)


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
        self.hass = hass
        self.shim_host = shim_host
        self.shim_port = shim_port
        self.shim_base_url = f"http://{self.shim_host}:{self.shim_port}"
        self.name = "{} Climate Control System".format(sysname)
        self.model = "Neasmart 2.0 Base Station"
        self.manufacturer = "Rehau"
        self.online = True
        self._id = sysname
        self.hub = self
        self.mixgs = []
        self.zones = []
        self.pumps = []
        self.dehumidifiers = []

        dehumidifiers_topology = dehumidifiers.split(",") if dehumidifiers != "" else []
        pumps_topology = pumps.split(",") if pumps != "" else []
        zones_name_array = zones.split(",")

        self.mixgs = [RehauNeasmart2MixedGroup(m, self) for m in range(1, mixg + 1)]
        self.dehumidifiers = [RehauNeasmart2Dehumidifier(int(dehumidifiers_topology[d]), self)
                              for d in range(0, len(dehumidifiers_topology))]
        self.pumps = [RehauNeasmart2Pump(int(pumps_topology[p]), self) for p in range(0, len(pumps_topology))]
        self.zones = [RehauNeasmart2Zone((z // 12) + 1, z - (12 * (z // 12)) + 1, zones_name_array[z], self)
                      for z in range(0, len(zones_name_array))]

    @property
    def id(self) -> str:
        return self._id

    async def test_connection(self) -> bool:
        return await self.hass.async_add_executor_job(self._check_shim_online)

    def _check_shim_online(self) -> bool:
        r = requests.get(f"{self.shim_base_url}/health")
        return r.status_code == 200

    async def get_outside_temperature(self) -> float | None:
        outside_temperature = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "outsidetemperature",
            "outside_temperature",
            None
        )
        return outside_temperature

    async def get_filtered_outside_temperature(self) -> float | None:
        filtered_outside_temperature = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "outsidetemperature",
            "filtered_outside_temperature",
            None
        )
        return filtered_outside_temperature

    async def get_global_state(self) -> int | None:
        state = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "state",
            "state",
            None
        )
        return state

    async def set_global_state(self, state: int) -> bool:
        payload = {"state": state}
        return await self.hass.async_add_executor_job(
            self.data_setter_helper,
            "state",
            payload
        )

    async def get_global_mode(self) -> int | None:
        mode = await self.hass.async_add_executor_job(
            self.data_getter_helper,
            "mode",
            "mode",
            None
        )
        return mode

    async def set_global_mode(self, mode: int) -> bool:
        payload = {"mode": mode}
        return await self.hass.async_add_executor_job(
            self.data_setter_helper,
            "mode",
            payload
        )

    def data_setter_helper(self, endpoint, payload) -> bool:
        r = requests.post(f"{self.shim_base_url}/{endpoint}", json=payload)
        if r.status_code != 202:
            _LOGGER.error(f"Error sending {payload} to {self.shim_base_url}/{endpoint}, code {r.status_code}")
            return False
        return True

    def data_getter_helper(self, endpoint, key, default):
        r = requests.get(f"{self.shim_base_url}/{endpoint}")
        if r.status_code != 200:
            _LOGGER.error(f"Error calling {self.shim_base_url}/{endpoint}, code {r.status_code}")
            return default
        json_response = r.json()
        data = json_response.get(key)
        if data is None:
            _LOGGER.error(f"Error retrieving data from, {self.shim_base_url}/{endpoint}, "
                          f"cannot access {key} in response: {json_response}")
            return default
        return data


class RehauNeasmart2MixedGroup:
    """Rehau Neasmart 2.0 controlled Mixed Group"""

    def __init__(self, mixedgroup_id: int, hub: RehauNeasmart2ClimateControlSystem) -> None:
        self._id = f"{hub.id}_{mixedgroup_id}"
        self.name = f"Mixed Group #{mixedgroup_id}"
        self.hub = hub
        self.model = "Mixed Group w/ 24/230 Pump and 0-10v controlled mixing valve"
        self.manufacturer = "Rehau"
        self.mixg_id = mixedgroup_id

    @property
    def id(self) -> str:
        return self._id

    async def get_flow_temperature(self) -> float | None:
        flow_temperature = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"mixedgroups/{self.mixg_id}",
            "flow_temperature",
            None
        )
        return flow_temperature

    async def get_return_temperature(self) -> float | None:
        return_temperature = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"mixedgroups/{self.mixg_id}",
            "return_temperature",
            None
        )
        return return_temperature

    async def get_valve_opening_percentage(self) -> int | None:
        valve_opening_percentage = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"mixedgroups/{self.mixg_id}",
            "mixing_valve_opening_percentage",
            None
        )
        return valve_opening_percentage

    async def get_pump_state(self) -> str | None:
        pump_state = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"mixedgroups/{self.mixg_id}",
            "pump_state",
            None
        )

        return pump_state


class RehauNeasmart2Dehumidifier:
    """Rehau Neasmart 2.0 controlled Dehumidifier."""

    def __init__(self, dehumidifier_id: int, hub: RehauNeasmart2ClimateControlSystem) -> None:
        self._id = f"{hub.id}_{dehumidifier_id}"
        self.name = f"Dehumidifier #{dehumidifier_id}"
        self.hub = hub
        self.model = "Dehumidifier with optional hydronic battery"
        self.manufacturer = "Rehau"
        self.dehumidifier_id = dehumidifier_id

    @property
    def id(self) -> str:
        """Return ID of the dehumidifier."""
        return self._id

    async def get_dehumidifier_state(self) -> str | None:
        dehumidifier_state = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"dehumidifiers/{self.dehumidifier_id}",
            "dehumidifier_state",
            None
        )

        return BINARY_STATUSES[dehumidifier_state]


class RehauNeasmart2Pump:
    """Rehau Neasmart 2.0 controlled Extra Pump."""

    def __init__(self, pump_id: int, hub: RehauNeasmart2ClimateControlSystem) -> None:
        self._id = f"{hub.id}_{pump_id}"
        self.name = f"Extra Pump #{pump_id}"
        self.hub = hub
        self.model = "On-Off 24/230v Pump"
        self.manufacturer = "Rehau"
        self.pump_id = pump_id

    @property
    def id(self) -> str:
        """Return ID of the pump."""
        return self._id

    async def get_pump_state(self) -> str | None:
        pump_state = await self.hub.hass.async_add_executor_job(
            self.hub.data_getter_helper,
            f"pumps/{self.pump_id}",
            "pump_state",
            None
        )

        return pump_state


class RehauNeasmart2Zone:
    """Rehau Neasmart 2.0 controlled Mixed Group"""

    def __init__(self, base_id: int, zone_id: int, name: str, hub: RehauNeasmart2ClimateControlSystem) -> None:
        self._id = f"{hub.id}_{base_id}_{zone_id}"
        self.name = f"{name}"
        self.hub = hub
        self.zone_id = zone_id
        self.base_id = base_id
        self.model = "Neasmart 2.0 Room Thermostat"
        self.manufacturer = "Rehau"

    @property
    def id(self) -> str:
        """Return ID of the zone."""
        return self._id

    async def get_zone_data(self) -> dict | None:
        r = await self.hub.hass.async_add_executor_job(
            requests.get, f"{self.hub.shim_base_url}/zones/{self.base_id}/{self.zone_id}")
        if r.status_code != 200:
            _LOGGER.error(f"Error calling {self.hub.shim_base_url}/zones/{self.base_id}/{self.zone_id}, "
                          f"code {r.status_code}")
            return None
        json_response = r.json()
        return json_response

    async def set_zone_setpoint(self, setpoint: float) -> bool:
        payload = {"setpoint": setpoint}
        return await self.hub.hass.async_add_executor_job(
            self.hub.data_setter_helper,
            f"zones/{self.base_id}/{self.zone_id}",
            payload
        )

    async def set_zone_state(self, state: int) -> bool:
        payload = {"state": state}
        return await self.hub.hass.async_add_executor_job(
            self.hub.data_setter_helper,
            f"zones/{self.base_id}/{self.zone_id}",
            payload
        )


