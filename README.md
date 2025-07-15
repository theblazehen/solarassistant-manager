# Solar Charging Controller

An intelligent MQTT-based solar charging controller that manages battery charging states based on State of Charge (SOC) levels and time-based conditions. This system automatically switches between different charging modes to optimize energy usage and battery health.

## Overview

This Python application monitors battery SOC levels via MQTT and dynamically adjusts inverter charging priorities based on configurable thresholds. It implements a state machine with hysteresis to prevent rapid switching between states and includes special manual charging modes for specific time periods.

## Features

- **Dynamic State Management**: Automatically transitions between 4 distinct charging states based on SOC levels
- **Hysteresis Protection**: Prevents rapid state switching with configurable time delays
- **Manual Override Mode**: Special charging mode activated during Wednesday evenings (5-9 PM)
- **MQTT Integration**: Seamless communication with solar monitoring systems
- **Configurable Thresholds**: Easy adjustment of SOC limits and state transitions
- **Validation Engine**: Built-in validation for configuration parameters and state ordering

## Architecture

### Charging States

The system operates in four distinct states:

1. **MANUAL**: Manual override mode for scheduled charging
2. **UTILITY_CHARGE_AND_SUB**: Utility-first charging with simultaneous solar charging
3. **SUB_AND_SOLAR_ONLY**: Solar-only charging with utility/backup support
4. **SBU_AND_SOLAR_ONLY**: Solar/battery priority with utility as final backup

### State Transitions

State transitions are governed by SOC thresholds with configurable offsets from the desired SOC level:

- **UTILITY_CHARGE_AND_SUB**: SOC range [0, 56] (desired SOC - 4)
- **SUB_AND_SOLAR_ONLY**: SOC range [54, 61] (desired SOC - 6 to +1)
- **SBU_AND_SOLAR_ONLY**: SOC range [60, 100] (desired SOC + 0 to unlimited)

## Configuration

The system is configured through the `CONFIG` dictionary in [`main.py`](main.py:20-28):

```python
CONFIG = {
    "desired_soc": 60,           # Target SOC level (0-100)
    "state_offsets": {
        State.UTILITY_CHARGE_AND_SUB: (None, -4),
        State.SUB_AND_SOLAR_ONLY: (-6, 1),
        State.SBU_AND_SOLAR_ONLY: (0, None),
    },
    "hysteresis_duration": 300,  # Minimum time between state changes (seconds)
}
```

### Configuration Validation

The system performs comprehensive validation on startup:
- Ensures all SOC limits are between 0-100
- Validates proper ordering of state transitions
- Prevents overlapping or invalid state ranges

## MQTT Integration

### Topics

- **Input**: `solar_assistant/battery_1/state_of_charge/state`
  - Receives battery SOC values (0-100)
- **Output**: `solar_assistant/inverter_1/output_source_priority/set`
  - Sets inverter output source priority
- **Output**: `solar_assistant/inverter_1/charger_source_priority/set`
  - Sets inverter charging source priority

### MQTT Settings

- **Broker**: `solar-assistant` (hostname)
- **Client ID**: `SolarChargerController`
- **QoS**: Default (0)

## Installation

### Prerequisites

- Python 3.6+
- `paho-mqtt` library

### Install Dependencies

```bash
pip install paho-mqtt
```

### Docker Deployment

The project includes Docker support:

```bash
docker build -t solar-charger-controller .
docker run -d --name solar-controller --network host solar-charger-controller
```

## Usage

### Basic Usage

1. Ensure your MQTT broker is running and accessible
2. Configure the desired SOC level and state offsets in `main.py`
3. Run the controller:

```bash
python main.py
```

### Environment Setup

The system expects:
- MQTT broker accessible at hostname `solar-assistant`
- Battery SOC published to `solar_assistant/battery_1/state_of_charge/state`
- Inverter control topics available for subscription

## Monitoring

The system provides real-time logging:
- SOC values are displayed continuously
- State changes are logged with timestamps
- Error messages for invalid SOC values or MQTT issues

Example output:
```
2024-01-15 14:30:45 SOC: 65   
2024-01-15 14:30:50 SOC: 64   
2024-01-15 14:30:55 SOC=64 Changing to state State.SUB_AND_SOLAR_ONLY
```

## Troubleshooting

### Common Issues

1. **MQTT Connection Failed**
   - Verify MQTT broker is running at `solar-assistant`
   - Check network connectivity
   - Ensure firewall allows MQTT port (1883)

2. **Invalid SOC Values**
   - Ensure SOC values are numeric and between 0-100
   - Check MQTT topic format matches expected structure

3. **State Validation Errors**
   - Review configuration offsets for valid ranges
   - Ensure state ordering is maintained (no overlapping ranges)

### Debug Mode

Enable verbose logging by modifying the MQTT client settings:

```python
client = mqtt.Client(client_id="SolarChargerController")
client.on_connect = on_connect
client.on_message = on_message
client.on_log = lambda client, userdata, level, buf: print(f"MQTT Log: {buf}")
```

## Configuration Examples

### Conservative Charging (Lower SOC thresholds)
```python
CONFIG = {
    "desired_soc": 50,
    "state_offsets": {
        State.UTILITY_CHARGE_AND_SUB: (None, -5),
        State.SUB_AND_SOLAR_ONLY: (-8, 2),
        State.SBU_AND_SOLAR_ONLY: (-2, None),
    },
    "hysteresis_duration": 600,
}
```

### Aggressive Charging (Higher SOC thresholds)
```python
CONFIG = {
    "desired_soc": 80,
    "state_offsets": {
        State.UTILITY_CHARGE_AND_SUB: (None, -2),
        State.SUB_AND_SOLAR_ONLY: (-4, 1),
        State.SBU_AND_SOLAR_ONLY: (0, None),
    },
    "hysteresis_duration": 180,
}
```

## License

GNU AGPL