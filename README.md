# Ambient Monitor
Read environmental data from the BME688 sensor. The sensor is connected to the USB port using an FT232H USB-to-I2C adapter.

The Indoor Air Quality (IAQ) is computed from the gas resistance and humidity using a simplified version of the algorithm provided by Bosch Sensortec Environmental Cluster (BSEC) Software.

BSEC software is closed source and cannot be used in this setup because the sensor is connected via the USB port.

An usage example can be found [here](https://github.com/cristeab/aq_dashboard).

## Sample output

```console
Elapsed time: 3:35, Temperature: 23.4 °C, Humidity: 37.7 %, Pressure: 1001.7 hPa, Gas: 82901 ohms, IAQ: 174.9
```
