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
import math
import time
from datetime import datetime, timezone


class AmbientMonitor:
    CALIBRATION_SAMPLES = 50

    def __init__(self):
        i2c = board.I2C()  # Automatically uses FT232H as I2C if BLINKA_FT232H=1 is set
        self._sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)
        self._calibrate_baseline()

    def _calibrate_baseline(self):
        total_gas = 0
        print(f"Calibrating gas baseline. Please wait {self.CALIBRATION_SAMPLES} sec...")
        for s in range(self.CALIBRATION_SAMPLES):
            total_gas += self._sensor.gas
            time.sleep(1)
            print(f"\rElapsed seconds: {s + 1}", end="", flush=True)
        self._gas_baseline = total_gas / self.CALIBRATION_SAMPLES
        print(f"\nDone")

    def get_data(self):
        timestamp = datetime.now(timezone.utc)
        temperature = self._sensor.temperature
        humidity = self._sensor.relative_humidity
        pressure = self._sensor.pressure
        gas_resistance = self._sensor.gas
        iaq = self._calculate_iaq(gas_resistance, humidity, self._gas_baseline)
        tvoc = self._estimate_tvoc(gas_resistance, self._gas_baseline)
        return {
            'timestamp': timestamp,
            'temperature': temperature,
            'humidity': humidity,
            'pressure': pressure,
            'iaq': iaq,
            'tvoc': tvoc
        }

    @staticmethod
    def _calculate_iaq(gas_resistance, humidity, gas_baseline, hum_baseline=40.0):
        hum_weight = 0.25  # Humidity contributes 25%
        gas_weight = 0.75  # Gas contributes 75%

        # Humidity score (0-25)
        hum_offset = humidity - hum_baseline
        if hum_offset > 0:
            hum_score = ((100 - hum_baseline - hum_offset) / (100 - hum_baseline)) * hum_weight * 100
        else:
            hum_score = ((hum_baseline + hum_offset) / hum_baseline) * hum_weight * 100

        # Gas score (0-75)
        gas_score = (gas_resistance / gas_baseline) * gas_weight * 100

        # Combined IAQ index (0-100, higher = cleaner air)
        iaq = hum_score + gas_score
        return max(0, min(iaq, 100))

    @staticmethod
    def _estimate_tvoc(gas_resistance, gas_baseline):
        ratio = gas_baseline / gas_resistance
        tvoc_ppb = 50 * math.exp(4 * (ratio - 1))  # Exponential mapping
        return min(tvoc_ppb, 3000)  # Cap at 3000 ppb


if __name__ == "__main__":
    monitor = AmbientMonitor()
    while True:
        data = monitor.get_data()
        print(f"Timestamp: {data['timestamp']}")
        print(f"Temperature: {data['temperature']} °C")
        print(f"Humidity: {data['humidity']} %")
        print(f"Pressure: {data['pressure']} hPa")
        print(f"IAQ: {data['iaq']}")
        print(f"TVOC: {data['tvoc']} ppb")
        time.sleep(1)
