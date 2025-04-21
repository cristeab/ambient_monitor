#!/usr/bin/env python3

import os
os.environ["BLINKA_FT232H"] = "1"
try:
    import board
except ValueError as e:
    print(e)
    import sys
    sys.exit(1)
import adafruit_bme680
import time
from datetime import datetime, timezone


class AmbientMonitor:
    GAS_BASELINE_OHMS = 180000
    HUMIDITY_BASELINE = 40.0
    HUMIDITY_WEIGHT = 0.25

    def __init__(self):
        self.elapsed_time = "N/A"
        self._start_time = None
        i2c = board.I2C()  # Automatically uses FT232H as I2C if BLINKA_FT232H=1 is set
        self._sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)
        self._sensor.sea_level_pressure = 1013.25
        self._sensor.humidity_oversample = 2
        self._sensor.pressure_oversample = 4
        self._sensor.temperature_oversample = 8
        self._sensor.filter_size = 3
        self._sensor.set_gas_heater(320, 150)  # 320 degrees C for 150 ms

    def _calculate_iaq(self, gas_resistance, humidity):

        # Humidity score (0-25)
        hum_offset = humidity - self.HUMIDITY_BASELINE
        if hum_offset > 0:
            # Humidity is above optimal -> too humid
            hum_score = ((100.0 - self.HUMIDITY_BASELINE) - hum_offset) / (100.0 - self.HUMIDITY_BASELINE)
        else:
            # Humidity is below optimal -> too dry
            hum_score = (self.HUMIDITY_BASELINE + hum_offset) / self.HUMIDITY_BASELINE
        hum_score = max(0.0, min(1.0, hum_score))  # clamp between 0 and 1
        hum_score *= (self.HUMIDITY_WEIGHT * 100.0)  # now scale to 0-25 range

        # Calculate gas contribution (scaled 0 to 75)
        gas_offset = self.GAS_BASELINE_OHMS - gas_resistance
        if gas_offset > 0:
            # Gas resistance dropped -> air quality degraded
            gas_score = (gas_resistance / self.GAS_BASELINE_OHMS)
            gas_score = max(0.0, min(1.0, gas_score))  # ratio between 0 and 1
            gas_score *= (100.0 - self.HUMIDITY_WEIGHT * 100.0)  # scale to 0-75 range
        else:
            # gas_resistance is higher than baseline (very clean air)
            gas_score = 100.0 - (self.HUMIDITY_WEIGHT * 100.0)   # = 75, i.e. no gas contribution to "bad" score

        # Combine humidity and gas scores
        air_quality_score = hum_score + gas_score  # 0 (clean) to 100 (dirty) percentage

        return air_quality_score

    def _update_elapsed_time(self, current_time):
        if self._start_time is None:
            self._start_time = current_time

        etime = current_time - self._start_time
        total_seconds = int(etime.total_seconds())

        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        self.elapsed_time = "Elapsed time: "
        if days > 0:
            self.elapsed_time += f"{days} days, {hours:02d}:{minutes:02d}:{seconds:02d}"
        elif hours > 0:
            self.elapsed_time += f"{hours}:{minutes:02d}:{seconds:02d}"
        elif minutes > 0:
            self.elapsed_time += f"{minutes}:{seconds:02d}"
        else:
            self.elapsed_time += f"{int(etime.total_seconds())} sec."

    def get_data(self):
        timestamp = datetime.now(timezone.utc)
        temperature = self._sensor.temperature
        humidity = self._sensor.relative_humidity
        pressure = self._sensor.pressure
        gas_resistance = self._sensor.gas
        if temperature is None or gas_resistance == 0:
            return None
        iaq = self._calculate_iaq(gas_resistance, humidity)
        self._update_elapsed_time(timestamp)
        return {
            'timestamp': timestamp,
            'temperature': temperature,
            'humidity': humidity,
            'pressure': pressure,
            'gas': gas_resistance,
            'iaq': iaq if iaq is not None else 0
        }


if __name__ == "__main__":
    monitor = AmbientMonitor()
    while True:
        data = monitor.get_data()
        if data is not None:
            print(f"{monitor.elapsed_time}, "
                f"Temperature: {data['temperature']:.1f} °C, "
                f"Humidity: {data['humidity']:.1f} %, "
                f"Pressure: {data['pressure']:.1f} hPa, "
                f"Gas: {data['gas']} ohms, "
                f"IAQ: {data['iaq']:.1f} %",
                flush=True)
        time.sleep(1)
