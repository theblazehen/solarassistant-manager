import datetime
import math
import time
from enum import Enum
import paho.mqtt.client as mqtt

"""
This script controls the charging logic based on the state of charge (SOC) and
other factors like time. The charging states and conditions are abstracted using the State Enum
and associated configuration.
"""

class State(Enum):
    MANUAL = 1
    UTILITY_CHARGE_AND_SUB = 2
    SUB_AND_SOLAR_ONLY = 3
    # Assuming SBU stands for Solar/Battery/Utility. Please modify if incorrect.
    SBU_AND_SOLAR_ONLY = 4

CONFIG = {
    "desired_soc": 60,
    "state_offsets": {
        State.UTILITY_CHARGE_AND_SUB: (None, -4),
        State.SUB_AND_SOLAR_ONLY: (-6, 1),
        State.SBU_AND_SOLAR_ONLY: (0, None),
    },
    "hysteresis_duration": 300,
}

def calculate_limits():
    """Calculate the state limits based on the desired SOC and offsets."""
    limits = {}
    for state, (lower_offset, upper_offset) in CONFIG["state_offsets"].items():
        lower_limit = CONFIG["desired_soc"] + lower_offset if lower_offset is not None else 0
        upper_limit = CONFIG["desired_soc"] + upper_offset if upper_offset is not None else 100
        limits[state] = (lower_limit, upper_limit)

    # Validate that limits are between 0 and 100
    for state, (lower, upper) in limits.items():
        if not (0 <= lower < 100) or not (0 < upper <= 100):
            raise ValueError(f"Invalid state limits for {state}. Values should be between 0 and 100.")

    # Validate ordering of the states for forward transition
    states_ordered = [State.UTILITY_CHARGE_AND_SUB, State.SUB_AND_SOLAR_ONLY, State.SBU_AND_SOLAR_ONLY]
    for i in range(len(states_ordered) - 1):
        current_state_upper = limits[states_ordered[i]][1]
        next_state_lower = limits[states_ordered[i + 1]][0]
        if current_state_upper < next_state_lower:
            raise ValueError(f"Invalid ordering. Upper limit of {states_ordered[i]} should be greater than or equal to the lower limit of {states_ordered[i + 1]}.")

    # Validate ordering of the states for reverse transition
    for i in range(len(states_ordered) - 1, 0, -1):
        current_state_lower = limits[states_ordered[i]][0]
        previous_state_upper = limits[states_ordered[i - 1]][1]
        if current_state_lower > previous_state_upper:
            raise ValueError(f"Invalid ordering. Lower limit of {states_ordered[i]} should be less than or equal to the upper limit of {states_ordered[i - 1]}.")

    return limits


CONFIG["state_limits"] = calculate_limits()

cur_state = None
last_state_change_time = 0

def is_manual_charge_time():
    current_time = datetime.datetime.now()

    if current_time.weekday() == 2 and 17 <= current_time.hour and current_time.hour <= 21:  # 2 is Wednesday
        return True
    return False



def set_priority(client, state):
    if state == State.UTILITY_CHARGE_AND_SUB:
        client.publish("solar_assistant/inverter_1/output_source_priority/set", "Utility first")
        client.publish("solar_assistant/inverter_1/charger_source_priority/set", "Solar and utility simultaneously")
    elif state == State.SUB_AND_SOLAR_ONLY:
        client.publish("solar_assistant/inverter_1/output_source_priority/set", "Solar/Utility/Battery")
        client.publish("solar_assistant/inverter_1/charger_source_priority/set", "Solar only")
    elif state == State.SBU_AND_SOLAR_ONLY:
        client.publish("solar_assistant/inverter_1/output_source_priority/set", "Solar/Battery/Utility")
        client.publish("solar_assistant/inverter_1/charger_source_priority/set", "Solar only")
    elif state == State.MANUAL:
        client.publish("solar_assistant/inverter_1/output_source_priority/set", "Utility first")
        client.publish("solar_assistant/inverter_1/charger_source_priority/set", "Utility first")

def handle_charge_logic(client, soc):
    global cur_state, last_state_change_time

    # Hysteresis time check
    if time.time() - last_state_change_time < CONFIG["hysteresis_duration"]:
        return
    last_state_change_time = time.time()

    # Manual charge time logic
    if is_manual_charge_time():
        if cur_state != State.MANUAL:
            print(f"\n{datetime.datetime.now()} Manual Full Charge Mode")
            set_priority(client, State.MANUAL)
            cur_state = State.MANUAL

    # Regular SOC-based logic
    else:
        for state, (lower_limit, upper_limit) in CONFIG["state_limits"].items():
            if lower_limit <= soc <= upper_limit and cur_state != state:
                cur_state = state
                print(f"\n{datetime.datetime.now()} {soc=} Changing to state {state}")
                set_priority(client, state)
                return

def on_message(client, userdata, msg):
    try:
        soc = math.ceil(float(msg.payload))
        if 0 <= soc <= 100:
            print(f"\r{datetime.datetime.now()} SOC: {soc}   \r", end="")
            handle_charge_logic(client, soc)
        else:
            print(f"\nReceived invalid SOC value: {soc}")
    except ValueError:
        print(f"\nError parsing SOC message: {msg.payload}")

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("solar_assistant/battery_1/state_of_charge/state")
    print("subscribed")

client = mqtt.Client(client_id="SolarChargerController")
client.on_connect = on_connect
client.on_message = on_message

client.connect("solar-assistant")
client.loop_forever()
