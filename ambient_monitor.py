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
    CALIBRATION_SAMPLES = 60
    CALIBRATION_DELAY_SEC = 5
    HUMIDITY_BASELINE = 40.0
    HUMIDITY_WEIGHT = 0.25

    def __init__(self):
        self.elapsed_time = "N/A"
        self._start_time = None
        i2c = board.I2C()  # Automatically uses FT232H as I2C if BLINKA_FT232H=1 is set
        self._sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c)
        self._sensor.humidity_oversample = 2
        self._sensor.pressure_oversample = 4
        self._sensor.temperature_oversample = 8
        self._sensor.filter_size = 3
        self._sensor.set_gas_heater(320, 150)  # 320 degrees C for 150 ms
        self._gas_baseline = None

    def _calibrate_baseline(self, timestamp, gas_resistance):
        if self._gas_baseline is not None:
            return
        # Calibrate the gas baseline
        if not hasattr(self, "_calibration_data"):
            # Initialize calibration state
            self._calibration_data = {
                "last_timestamp": timestamp,
                "total_gas": 0,
                "count": 0
            }
        elapsed_time = (timestamp - self._calibration_data["last_timestamp"]).total_seconds()
        if elapsed_time >= self.CALIBRATION_DELAY_SEC:
            self._calibration_data["last_timestamp"] = timestamp
            self._calibration_data["total_gas"] += gas_resistance
            self._calibration_data["count"] += 1
            if self._calibration_data["count"] == self.CALIBRATION_SAMPLES:
                self._gas_baseline = self._calibration_data["total_gas"] / self.CALIBRATION_SAMPLES
                del self._calibration_data

    def _calculate_iaq(self, gas_resistance, humidity):
        # Humidity score (0-25)
        hum_offset = humidity - self.HUMIDITY_BASELINE
        if hum_offset > 0:
            hum_score = ((100 - self.HUMIDITY_BASELINE - hum_offset) / (100 - self.HUMIDITY_BASELINE)) * self.HUMIDITY_WEIGHT * 100
        else:
            hum_score = ((self.HUMIDITY_BASELINE + hum_offset) / self.HUMIDITY_BASELINE) * self.HUMIDITY_WEIGHT * 100

        # Gas score (0-75)
        if self._gas_baseline is not None:
            gas_ratio = gas_resistance / self._gas_baseline
            if (self._gas_baseline - gas_resistance) > 0:
                gas_score = gas_ratio * (100 * (1 - self.HUMIDITY_WEIGHT))
            else:
                gas_score = 70 + (5 * (gas_ratio - 1))
                if gas_score > 75:
                    gas_score = 75
        else:
            # If no baseline provided, use the default scaling
            # Assuming gas resistance ranges from 50 (bad) to 50000 (good)
            gas_resistance = min(max(gas_resistance, 50), 50000)
            gas_percent = (gas_resistance - 50) / (50000 - 50) * 100
            gas_score = (100 - gas_percent) * 0.75

        # Combined IAQ index (0-100, higher = cleaner air)
        iaq_percent = hum_score + gas_score
        # Convert to IAQ scale (0-500, where 0 is excellent and 500 is hazardous)
        iaq = 500 - (iaq_percent * 5)
        iaq = max(0, min(500, iaq)) 

        return iaq

    def _update_elapsed_time(self, current_time):
        if self._start_time is None:
            self._start_time = current_time

        elapsed_time = current_time - self._start_time
        total_seconds = int(elapsed_time.total_seconds())

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
            self.elapsed_time += f"{int(elapsed_time.total_seconds())} sec."

    def get_data(self):
        timestamp = datetime.now(timezone.utc)
        temperature = self._sensor.temperature
        humidity = self._sensor.relative_humidity
        pressure = self._sensor.pressure
        gas_resistance = self._sensor.gas
        self._calibrate_baseline(timestamp, gas_resistance)
        iaq = self._calculate_iaq(gas_resistance, humidity)
        self._update_elapsed_time(timestamp)
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
        print(
            f"{monitor.elapsed_time}, "
            f"Temperature: {data['temperature']:.1f} °C, "
            f"Humidity: {data['humidity']:.1f} %, "
            f"Pressure: {data['pressure']:.1f} hPa, "
            f"Gas: {data['gas']:.1f} ohms, "
            f"IAQ: {data['iaq']:.1f}",
            flush=True
        )
        time.sleep(1)
