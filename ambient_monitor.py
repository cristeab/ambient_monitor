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
    GAS_BASELINE_OHMS = 150000
    HUMIDITY_BASELINE = 40.0 # 40% humidity is considered optimal
    HUMIDITY_WEIGHT = 0.25 # humidity contributes 25% to the IAQ score

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
        # Calculate gas score (75% of total)
        gas_ratio = gas_resistance / self.GAS_BASELINE_OHMS
        gas_offset = self.GAS_BASELINE_OHMS - gas_resistance

        # Calculate humidity score (25% of total)
        hum_offset = humidity - self.HUMIDITY_BASELINE
        hum_score = 0.0

        if hum_offset > 0:
            hum_score = (100 - self.HUMIDITY_BASELINE - hum_offset) / (100 - self.HUMIDITY_BASELINE)
            hum_score *= (self.HUMIDITY_WEIGHT * 100)
        else:
            hum_score = (self.HUMIDITY_BASELINE + hum_offset) / self.HUMIDITY_BASELINE
            hum_score *= (self.HUMIDITY_WEIGHT * 100)

        # Different paths for calculating gas score depending on offset
        if gas_offset > 0:
            gas_score = gas_ratio * (100 * (1 - self.HUMIDITY_WEIGHT))
        else:
            # When air is cleaner than baseline
            gas_score = min(75, 70 + (5 * (gas_ratio - 1)))

        # Calculate IAQ percentage (0-100%, with 100% being cleanest)
        iaq_percent = hum_score + gas_score

        # Convert to 0-500 scale (0 = clean, 500 = very polluted)
        iaq_score = (100 - iaq_percent) * 5

        return iaq_score

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
