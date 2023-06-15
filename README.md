# Rehau Neasmart 2.0 Integration
[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/matteomanzoni)

**Integration between Rehau Neasmart 2.0 Climate Control Systems and Homeassistant**

This integration leverages a dedicated add-on to shim the Sysbus protocol (ModbusRTU) of the heating system to something easy to digest with an integration (set of REST APIs) [which you can find here](https://github.com/MatteoManzoni/RehauNeasmart2.0_Gateway)

### How to install

- Add this repository as a HACS custom repository
- Search for `Rehau Neasmart 2.0` and install it
- Restart homeassistant
- Add the `Rehau Neasmart 2.0` integration
- Fill out the requested data:
  - Show name for the Climate Control System eg. *Matteo's Home*
  - Address where the add-on is running
  - Port where the add-on is running
  - Comma separated list of the zones names(only contiguous, single thermostat zones are supported) eg. *Kitchen,Master Bedroom,Living Room,Bathroom* (mapping between zone name and index can be found connecting to the Neasmart base station in AP mode)
  - Number of mixed groups to configure (optional, 1-3)
  - Comma separated list of dehumidifiers id to configure (this will require testing which id contains which dehumidifier as the mapping is based on U/B Modules registers mappings)
  - Comma separated list of pumps id to configure (this will require testing which id contains which pump as the mapping is based on U/R/B Modules registers mappings)

### Architecture

This custom component will install an hub representing the Neasmart Base Station owning the global state, mode of the system and the raw and filtered outside temperature

The hub will own multiple devices:
- one room thermostat for each configured zone describing the zone state (temperature, relative humidity) and able to configure the state and temperature setpoint of said zone
- as many mixed groups as configured, showing the pump status, flow&return temperature and valve opening percentage of the mixed group
- as many dehumidifier and extra pumps as configured, containing their operative status (On, Off)

### Known Issues

- Investigate coordinator to reduce calls per poll to Add-On
- Missing Logos and such
- Improve config flow, avoid comma separated strings

#### Disclaimer: 

Rehau, don't get too pissed, but I'm not buying a 500 Euros KNX GW for something worth 30EUR in hardware and 500 lines of Python.

I'm available to make this something official and spend actual time to improve it, it would be nice for your marketing. You have my email :pray:




MIT Licensed
