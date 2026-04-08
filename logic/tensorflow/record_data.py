import serial
import time
import sys

# --- CONFIGURATION ---
# Change these variables before running the script
COM_PORT = 'COM15'      # Replace with your ESP32-S3 COM port
BAUD_RATE = 115200     # Default baud rate for ESP-IDF
FILE_NAME = 'idle.csv' 
# ---------------------

def main():
    try:
        # Open the serial port
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Successfully connected to {COM_PORT} at {BAUD_RATE} baud.")
        print(f"🔴 Recording data to '{FILE_NAME}'... Press Ctrl+C to stop.")
        
        with open(FILE_NAME, 'w', encoding='utf-8') as f:
            # Write the CSV header expected by the training script
            f.write("aX,aY,aZ,gX,gY,gZ\n")
            
            while True:
                if ser.in_waiting > 0:
                    try:
                        # Read the line from serial and decode it cleanly
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        
                        # Filter out ESP-IDF boot logs (Info, Warnings, etc.)
                        # A valid MPU6050 line from your C++ code should have exactly 3 parts separated by commas
                        parts = line.split(',')
                        if len(parts) == 6:
                            # Verify the parts are actually integers (ignores lines like "I (123) main: log")
                            try:
                                [int(p) for p in parts]
                                f.write(line + '\n')
                                # Print to terminal so you can see it working
                                print(f"Recorded: {line}") 
                            except ValueError:
                                # Not an integer data line, skip it
                                pass
                                
                    except Exception as e:
                        print(f"Error parsing line: {e}")
                        
    except serial.SerialException as e:
        print(f"❌ Error opening serial port: {e}")
        print("\n⚠️ IMPORTANT: Make sure the ESP-IDF monitor is CLOSED before running this script.")
        print("Windows only allows one program to use the COM port at a time.")
    except KeyboardInterrupt:
        print(f"\n🛑 Recording stopped by user. All data safely saved to {FILE_NAME}.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == '__main__':
    main()