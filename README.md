# Ambient Monitor
Read environmental data from BME688 sensor. The sensor is connected on the USB port using a FT232H USB to I2C adapter.

The Indoor Air Quality (IAQ) is computed from the gas resistance and humidity using a simplified version of the algorithm provided by Bosch Sensortec Environmental Cluster (BSEC) Software.

BSEC software is closed source and cannot be used in this setup because the sensor is connected on the USB port.

An usage example can be found [here](https://github.com/cristeab/aq_dashboard).

## Sample output

```console
Elapsed time: 13:25, Temperature: 23.3 °C, Humidity: 38.7 %, Pressure: 1000.6 hPa, Gas: 69584 ohms, IAQ: 53.2 %
```
