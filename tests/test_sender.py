import serial
import time
import random

# IMPORTANT: Use the OTHER port from the pair
VIRTUAL_PORT = 'COM6' 

print(f"Attempting to open port {VIRTUAL_PORT}")

try:
    # Connect to the second virtual port
    with serial.Serial(VIRTUAL_PORT, 115200, timeout=1) as ser:
        print(f"Port {VIRTUAL_PORT} opened successfully. Sending data...")
        value1 = 50.0
        value2 = 100
        while True:
            # Simulate some sensor data
            value1 += random.uniform(-0.5, 0.5)
            value2 += random.uniform(-5, 5)

            # Format and encode the data to bytes
            data_string = f"Temp: {value1:.2f}, Hum: {value2:.2f}\n"
            ser.write(data_string.encode('utf-8'))

            print(f"Sent: {data_string.strip()}")
            time.sleep(1)

except serial.SerialException as e:
    print(f"Error: Could not open port {VIRTUAL_PORT}. Is it correct? Is the driver installed?")
    print(e)