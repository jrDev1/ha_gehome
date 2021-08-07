import logging
from typing import Any, List, Optional

from homeassistant.components.climate import ClimateEntity
from homeassistant.const import (
    ATTR_TEMPERATURE,
    TEMP_FAHRENHEIT,
    TEMP_CELSIUS,
)
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_FAN_MODE,
    HVAC_MODE_OFF
)
from gehomesdk import ErdCode, ErdCodeType, ErdMeasurementUnits, ErdOnOff
from ...const import DOMAIN
from ...devices import ApplianceApi
from .ge_erd_entity import GeEntity
from .options_converter import OptionsConverter

_LOGGER = logging.getLogger(__name__)

#by default, we'll support target temp and fan mode (derived classes can override)
GE_CLIMATE_SUPPORT = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE

class GeClimate(GeEntity, ClimateEntity):
    """GE Climate Base Entity (Window AC, Portable AC, etc)"""
    def __init__(
        self, 
        api: ApplianceApi,
        hvac_mode_converter: OptionsConverter,
        fan_mode_converter: OptionsConverter,        
        power_status_erd_code: ErdCodeType = ErdCode.AC_POWER_STATUS,
        current_temperature_erd_code: ErdCodeType = ErdCode.AC_AMBIENT_TEMPERATURE,
        target_temperature_erd_code: ErdCodeType = ErdCode.AC_TARGET_TEMPERATURE,
        hvac_mode_erd_code: ErdCodeType = ErdCode.AC_OPERATION_MODE,
        fan_mode_erd_code: ErdCodeType = ErdCode.AC_FAN_SETTING

    ):
        super().__init__(api)
        self._hvac_mode_converter = hvac_mode_converter
        self._fan_mode_converter = fan_mode_converter
        self._power_status_erd_code = api.appliance.translate_erd_code(power_status_erd_code)
        self._current_temperature_erd_code = api.appliance.translate_erd_code(current_temperature_erd_code)
        self._target_temperature_erd_code = api.appliance.translate_erd_code(target_temperature_erd_code)
        self._hvac_mode_erd_code = api.appliance.translate_erd_code(hvac_mode_erd_code)
        self._fan_mode_erd_code = api.appliance.translate_erd_code(fan_mode_erd_code)

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_{self.serial_or_mac}_climate"

    @property
    def name(self) -> Optional[str]:
        return f"{self.serial_or_mac} Climate"

    @property
    def power_status_erd_code(self):
        return self._power_status_erd_code

    @property
    def target_temperature_erd_code(self):
        return self._target_temperature_erd_code

    @property
    def current_temperature_erd_code(self):
        return self._current_temperature_erd_code
    
    @property
    def hvac_mode_erd_code(self):
        return self._hvac_mode_erd_code

    @property
    def fan_mode_erd_code(self):
        return self._fan_mode_erd_code

    @property
    def temperature_unit(self):
        measurement_system = self.appliance.get_erd_value(ErdCode.TEMPERATURE_UNIT)
        if measurement_system == ErdMeasurementUnits.METRIC:
            return TEMP_CELSIUS
        return TEMP_FAHRENHEIT

    @property
    def supported_features(self):
        return GE_CLIMATE_SUPPORT

    @property
    def is_on(self) -> bool:
        return self.appliance.get_erd_value(self.power_status_erd_code) == ErdOnOff.ON

    @property
    def target_temperature(self) -> Optional[float]:
        return float(self.appliance.get_erd_value(self.target_temperature_erd_code))

    @property
    def current_temperature(self) -> Optional[float]:
        return float(self.appliance.get_erd_value(self.current_temperature_erd_code))

    @property
    def hvac_mode(self):
        if not self.is_on:
            return HVAC_MODE_OFF

        return self._hvac_mode_converter.to_option_string(self.appliance.get_erd_value(self.hvac_mode_erd_code))

    @property
    def hvac_modes(self) -> List[str]:
        return [HVAC_MODE_OFF] + self._hvac_mode_converter.options

    @property
    def fan_mode(self):
        return self._fan_mode_converter.to_option_string(self.appliance.get_erd_value(self.fan_mode_erd_code))

    @property
    def fan_modes(self) -> List[str]:
        return self._fan_mode_converter.options

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        _LOGGER.debug(f"Setting HVAC mode from {self.hvac_mode} to {hvac_mode}")
        if hvac_mode != self.hvac_mode:
            if hvac_mode == HVAC_MODE_OFF:
                await self.appliance.async_set_erd_value(self.power_status_erd_code, ErdOnOff.OFF)
            else:
                await self.appliance.async_set_erd_value(
                    self.hvac_mode_erd_code, 
                    self._hvac_mode_converter.from_option_string(hvac_mode)
                )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        _LOGGER.debug(f"Setting Fan mode from {self.fan_mode} to {fan_mode}")
        if fan_mode != self.fan_mode:
            await self.appliance.async_set_erd_value(
                self.fan_mode_erd_code, 
                self._fan_mode_converter.from_option_string(fan_mode)
            )

    async def async_set_temperature(self, **kwargs) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        _LOGGER.debug(f"Setting temperature from {self.target_temperature} to {temperature}")
        if self.target_temperature != temperature:
            await self.appliance.async_set_erd_value(self.target_temperature_erd_code, temperature)