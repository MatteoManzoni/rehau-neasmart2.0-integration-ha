"""Hub and device models for the Rehau Neasmart 2.0 integration."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import requests

from homeassistant.core import HomeAssistant

from .const import (
    BINARY_STATUSES,
    ENDPOINT_CACHE_TTL_SECONDS,
    MAX_REASONABLE_TEMPERATURE,
    MIN_REASONABLE_TEMPERATURE,
    REQUEST_TIMEOUT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class RehauNeasmart2ClimateControlSystem:
    """Representation of the Neasmart gateway and attached devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        sysname: str,
        shim_host: str,
        shim_port: int,
        zones: str,
        mixg: int,
        pumps: str,
        dehumidifiers: str,
    ) -> None:
        self.hass = hass
        self.shim_host = shim_host
        self.shim_port = shim_port
        self.shim_base_url = f"http://{self.shim_host}:{self.shim_port}"
        self.name = f"{sysname} Climate Control System"
        self.model = "Neasmart 2.0 Base Station"
        self.manufacturer = "Rehau"
        self.online = True
        self._id = sysname
        self.hub = self
        self.mixgs = []
        self.zones = []
        self.pumps = []
        self.dehumidifiers = []
        self._endpoint_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._endpoint_locks: dict[str, asyncio.Lock] = {}
        self._last_gateway_error: str | None = None

        dehumidifiers_topology = dehumidifiers.split(",") if dehumidifiers != "" else []
        pumps_topology = pumps.split(",") if pumps != "" else []
        zones_name_array = zones.split(",")

        self.mixgs = [RehauNeasmart2MixedGroup(m, self) for m in range(1, mixg + 1)]
        self.dehumidifiers = [
            RehauNeasmart2Dehumidifier(int(dehumidifiers_topology[d]), self)
            for d in range(0, len(dehumidifiers_topology))
        ]
        self.pumps = [
            RehauNeasmart2Pump(int(pumps_topology[p]), self)
            for p in range(0, len(pumps_topology))
        ]
        for z, entry in enumerate(zones_name_array):
            entry = entry.strip()
            if ":" in entry:
                addr, name = entry.split(":", 1)
                base_str, channel_str = addr.split(".")
                self.zones.append(RehauNeasmart2Zone(int(base_str), int(channel_str), name.strip(), self))
            else:
                self.zones.append(RehauNeasmart2Zone((z // 12) + 1, z - (12 * (z // 12)) + 1, entry, self))

    @property
    def id(self) -> str:
        """Return the unique identifier of the hub."""
        return self._id

    async def test_connection(self) -> bool:
        """Test the connection to the shim server."""
        return await self.hass.async_add_executor_job(self._check_shim_online)

    def _check_shim_online(self) -> bool:
        """Check if the shim server itself is reachable."""
        try:
            response = requests.get(
                f"{self.shim_base_url}/health",
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as err:
            self._set_gateway_online(False, f"Error calling {self.shim_base_url}/health: {err}")
            return False

        if response.status_code != 200:
            self._set_gateway_online(
                False, f"Error calling {self.shim_base_url}/health, code {response.status_code}"
            )
            return False

        self._set_gateway_online(True)
        return True

    def _set_gateway_online(self, online: bool, reason: str | None = None) -> None:
        """Update gateway reachability state and deduplicate log noise."""
        if online:
            if not self.online:
                _LOGGER.info("Gateway %s is reachable again", self.shim_base_url)
            self.online = True
            self._last_gateway_error = None
            return

        self.online = False
        if reason is not None and reason != self._last_gateway_error:
            _LOGGER.warning(reason)
        self._last_gateway_error = reason

    def _response_has_fresh_data(self, response: requests.Response, endpoint: str) -> bool:
        """Validate freshness metadata if the gateway exposes it."""
        registers_stale = response.headers.get("X-Rehau-Registers-Stale")
        if registers_stale is None:
            self._set_gateway_online(True)
            return True
        if registers_stale.lower() != "true":
            self._set_gateway_online(True)
            return True

        last_write = response.headers.get("X-Rehau-Last-Register-Write", "never")
        age_seconds = response.headers.get("X-Rehau-Registers-Age-Seconds", "unknown")
        self._set_gateway_online(
            False,
            (
                f"Gateway {self.shim_base_url} is reachable but its register data is stale "
                f"while calling /{endpoint} (last write: {last_write}, age: {age_seconds}s)"
            ),
        )
        return False

    def _request_json(self, endpoint: str) -> dict[str, Any] | None:
        """Perform a single GET request to the gateway."""
        url = f"{self.shim_base_url}/{endpoint}"
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as err:
            self._set_gateway_online(False, f"Error calling {url}: {err}")
            return None

        if response.status_code != 200:
            self._set_gateway_online(False, f"Error calling {url}, code {response.status_code}")
            return None

        if not self._response_has_fresh_data(response, endpoint):
            return None

        try:
            return response.json()
        except ValueError as err:
            self._set_gateway_online(False, f"Error decoding JSON from {url}: {err}")
            return None

    async def async_get_endpoint_json(self, endpoint: str) -> dict[str, Any] | None:
        """Fetch endpoint data with a short cache to collapse duplicate entity updates."""
        cached_response = self._endpoint_cache.get(endpoint)
        if cached_response and (time.monotonic() - cached_response[0]) < ENDPOINT_CACHE_TTL_SECONDS:
            return cached_response[1]

        lock = self._endpoint_locks.setdefault(endpoint, asyncio.Lock())
        async with lock:
            cached_response = self._endpoint_cache.get(endpoint)
            if cached_response and (time.monotonic() - cached_response[0]) < ENDPOINT_CACHE_TTL_SECONDS:
                return cached_response[1]

            json_response = await self.hass.async_add_executor_job(self._request_json, endpoint)
            if json_response is None:
                self._endpoint_cache.pop(endpoint, None)
                return None

            self._endpoint_cache[endpoint] = (time.monotonic(), json_response)
            return json_response

    async def async_get_endpoint_value(self, endpoint: str, key: str, default: Any) -> Any:
        """Fetch a single value from a gateway endpoint."""
        json_response = await self.async_get_endpoint_json(endpoint)
        if json_response is None:
            return default

        if key not in json_response:
            self._set_gateway_online(
                False,
                (
                    f"Error retrieving data from {self.shim_base_url}/{endpoint}, "
                    f"cannot access {key} in response: {json_response}"
                ),
            )
            return default

        data = json_response[key]
        if data is None:
            return default

        return data

    def _normalize_temperature(self, value: Any, endpoint: str, key: str) -> float | None:
        """Reject invalid DPT9 sentinel values and implausible temperatures."""
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self._set_gateway_online(
                False,
                f"Invalid temperature from {self.shim_base_url}/{endpoint} for {key}: {value}",
            )
            return None
        if value < MIN_REASONABLE_TEMPERATURE or value > MAX_REASONABLE_TEMPERATURE:
            self._set_gateway_online(
                False,
                f"Implausible temperature from {self.shim_base_url}/{endpoint} for {key}: {value}",
            )
            return None
        return float(value)

    async def async_get_temperature_value(self, endpoint: str, key: str) -> float | None:
        """Fetch and validate a temperature value from a gateway endpoint."""
        value = await self.async_get_endpoint_value(endpoint, key, None)
        return self._normalize_temperature(value, endpoint, key)

    async def get_outside_temperature(self) -> float | None:
        """Retrieve the outside temperature."""
        return await self.async_get_temperature_value("outsidetemperature", "outside_temperature")

    async def get_filtered_outside_temperature(self) -> float | None:
        """Retrieve the filtered outside temperature."""
        return await self.async_get_temperature_value(
            "outsidetemperature",
            "filtered_outside_temperature",
        )

    async def get_notification_hints(self) -> bool | None:
        """Retrieve notification hints."""
        return await self.async_get_endpoint_value("notifications", "hints_present", None)

    async def get_notification_warnings(self) -> bool | None:
        """Retrieve notification warnings."""
        return await self.async_get_endpoint_value("notifications", "warnings_present", None)

    async def get_notification_errors(self) -> bool | None:
        """Retrieve notification errors."""
        return await self.async_get_endpoint_value("notifications", "error_present", None)

    async def get_global_state(self) -> int | None:
        """Retrieve the global state of the climate control system."""
        return await self.async_get_endpoint_value("state", "state", None)

    async def set_global_state(self, state: int) -> bool:
        """Set the global state of the climate control system."""
        return await self.hass.async_add_executor_job(
            self.data_setter_helper,
            "state",
            {"state": state},
        )

    async def get_global_mode(self) -> int | None:
        """Retrieve the global mode of the climate control system."""
        return await self.async_get_endpoint_value("mode", "mode", None)

    async def set_global_mode(self, mode: int) -> bool:
        """Set the global mode of the climate control system."""
        return await self.hass.async_add_executor_job(
            self.data_setter_helper,
            "mode",
            {"mode": mode},
        )

    def data_setter_helper(self, endpoint: str, payload: dict[str, Any]) -> bool:
        """Send data to the gateway."""
        url = f"{self.shim_base_url}/{endpoint}"
        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as err:
            self._set_gateway_online(False, f"Error sending {payload} to {url}: {err}")
            return False

        if response.status_code != 202:
            self._set_gateway_online(
                False,
                f"Error sending {payload} to {url}, code {response.status_code}",
            )
            return False

        if not self._response_has_fresh_data(response, endpoint):
            return False

        self._endpoint_cache.pop(endpoint, None)
        return True


class RehauNeasmart2MixedGroup:
    """Rehau Neasmart 2.0 controlled mixed group."""

    def __init__(self, mixedgroup_id: int, hub: RehauNeasmart2ClimateControlSystem) -> None:
        self._id = f"{hub.id}_{mixedgroup_id}"
        self.name = f"Mixed Group #{mixedgroup_id}"
        self.hub = hub
        self.model = "Mixed Group w/ 24/230 Pump and 0-10v controlled mixing valve"
        self.manufacturer = "Rehau"
        self.mixg_id = mixedgroup_id

    @property
    def id(self) -> str:
        """Return the unique identifier of the mixed group."""
        return self._id

    async def get_flow_temperature(self) -> float | None:
        """Retrieve the flow temperature for the mixed group."""
        return await self.hub.async_get_temperature_value(
            f"mixedgroups/{self.mixg_id}",
            "flow_temperature",
        )

    async def get_return_temperature(self) -> float | None:
        """Retrieve the return temperature for the mixed group."""
        return await self.hub.async_get_temperature_value(
            f"mixedgroups/{self.mixg_id}",
            "return_temperature",
        )

    async def get_valve_opening_percentage(self) -> int | None:
        """Retrieve the valve opening percentage for the mixed group."""
        return await self.hub.async_get_endpoint_value(
            f"mixedgroups/{self.mixg_id}",
            "mixing_valve_opening_percentage",
            None,
        )

    async def get_pump_state(self) -> int | None:
        """Retrieve the pump state for the mixed group."""
        return await self.hub.async_get_endpoint_value(
            f"mixedgroups/{self.mixg_id}",
            "pump_state",
            None,
        )


class RehauNeasmart2Dehumidifier:
    """Rehau Neasmart 2.0 controlled dehumidifier."""

    def __init__(self, dehumidifier_id: int, hub: RehauNeasmart2ClimateControlSystem) -> None:
        self._id = f"{hub.id}_{dehumidifier_id}"
        self.name = f"Dehumidifier #{dehumidifier_id}"
        self.hub = hub
        self.model = "Dehumidifier with optional hydronic battery"
        self.manufacturer = "Rehau"
        self.dehumidifier_id = dehumidifier_id

    @property
    def id(self) -> str:
        """Return the unique identifier of the dehumidifier."""
        return self._id

    async def get_dehumidifier_state(self) -> str | None:
        """Retrieve the state of the dehumidifier."""
        dehumidifier_state = await self.hub.async_get_endpoint_value(
            f"dehumidifiers/{self.dehumidifier_id}",
            "dehumidifier_state",
            None,
        )
        if dehumidifier_state is None:
            return None
        return BINARY_STATUSES.get(dehumidifier_state)


class RehauNeasmart2Pump:
    """Rehau Neasmart 2.0 controlled extra pump."""

    def __init__(self, pump_id: int, hub: RehauNeasmart2ClimateControlSystem) -> None:
        self._id = f"{hub.id}_{pump_id}"
        self.name = f"Extra Pump #{pump_id}"
        self.hub = hub
        self.model = "On-Off 24/230v Pump"
        self.manufacturer = "Rehau"
        self.pump_id = pump_id

    @property
    def id(self) -> str:
        """Return the unique identifier of the pump."""
        return self._id

    async def get_pump_state(self) -> int | None:
        """Retrieve the state of the pump."""
        return await self.hub.async_get_endpoint_value(
            f"pumps/{self.pump_id}",
            "pump_state",
            None,
        )


class RehauNeasmart2Zone:
    """Rehau Neasmart 2.0 controlled zone."""

    def __init__(
        self,
        base_id: int,
        zone_id: int,
        name: str,
        hub: RehauNeasmart2ClimateControlSystem,
    ) -> None:
        self._id = f"{hub.id}_{base_id}_{zone_id}"
        self.name = f"{name}"
        self.hub = hub
        self.zone_id = zone_id
        self.base_id = base_id
        self.model = "Neasmart 2.0 Room Thermostat"
        self.manufacturer = "Rehau"

    @property
    def id(self) -> str:
        """Return the unique identifier of the zone."""
        return self._id

    async def get_zone_data(self) -> dict[str, Any] | None:
        """Retrieve the data for the zone."""
        endpoint = f"zones/{self.base_id}/{self.zone_id}"
        zone_data = await self.hub.async_get_endpoint_json(endpoint)
        if zone_data is None:
            return None

        for key in ("temperature", "setpoint"):
            if key in zone_data:
                zone_data[key] = self.hub._normalize_temperature(zone_data[key], endpoint, key)
        return zone_data

    async def set_zone_setpoint(self, setpoint: float) -> bool:
        """Set the setpoint temperature for the zone."""
        return await self.hub.hass.async_add_executor_job(
            self.hub.data_setter_helper,
            f"zones/{self.base_id}/{self.zone_id}",
            {"setpoint": setpoint},
        )

    async def set_zone_state(self, state: int) -> bool:
        """Set the state for the zone."""
        return await self.hub.hass.async_add_executor_job(
            self.hub.data_setter_helper,
            f"zones/{self.base_id}/{self.zone_id}",
            {"state": state},
        )
