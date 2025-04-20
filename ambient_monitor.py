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
    CALIBRATION_SAMPLES = 120
    HUMIDITY_BASELINE = 40.0
    HUMIDITY_WEIGHT = 0.25

    def __init__(self):
        i2c = board.I2C()  # Automatically uses FT232H as I2C if BLINKA_FT232H=1 is set
        self._sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)
        self._sensor.humidity_oversample = 2
        self._sensor.pressure_oversample = 4
        self._sensor.temperature_oversample = 8
        self._sensor.filter_size = 3
        self._sensor.set_gas_heater(320, 150)  # 320 degrees C for 150 ms
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

    def _calculate_iaq(self, gas_resistance, humidity):
        # Humidity score (0-25)
        hum_offset = humidity - self.HUMIDITY_BASELINE
        if hum_offset > 0:
            hum_score = ((100 - self.HUMIDITY_BASELINE - hum_offset) / (100 - self.HUMIDITY_BASELINE)) * self.HUMIDITY_WEIGHT * 100
        else:
            hum_score = ((self.HUMIDITY_BASELINE + hum_offset) / self.HUMIDITY_BASELINE) * self.HUMIDITY_WEIGHT * 100

        # Gas score (0-75)
        gas_ratio = gas_resistance / self._gas_baseline
        if (self._gas_baseline - gas_resistance) > 0:
            gas_score = gas_ratio * (100 * (1 - self.HUMIDITY_WEIGHT))
        else:
            gas_score = 70 + (5 * (gas_ratio - 1))
            if gas_score > 75:
                gas_score = 75

        # Combined IAQ index (0-100, higher = cleaner air)
        iaq_percent = hum_score + gas_score
        return iaq_percent
    
    def get_data(self):
        timestamp = datetime.now(timezone.utc)
        temperature = self._sensor.temperature
        humidity = self._sensor.relative_humidity
        pressure = self._sensor.pressure
        gas_resistance = self._sensor.gas
        iaq = self._calculate_iaq(gas_resistance, humidity)
        return {
            'timestamp': timestamp,
            'temperature': temperature,
            'humidity': humidity,
            'pressure': pressure,
            'gas': gas_resistance,
            'iaq': iaq
        }


if __name__ == "__main__":
    monitor = AmbientMonitor()
    while True:
        data = monitor.get_data()
        print(f"Timestamp: {data['timestamp']}")
        print(f"Temperature: {data['temperature']} °C")
        print(f"Humidity: {data['humidity']} %")
        print(f"Pressure: {data['pressure']} hPa")
        print(f"IAQ: {data['iaq']} %")
        time.sleep(1)
