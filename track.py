import os
import sys
import json
import time
import requests
from datetime import datetime, timezone
import serial
import serial.tools.list_ports
import pymap3d as pm
from pygeomag import GeoMag

# ==============================================================================
# CONFIGURATION SETTINGS (Edit these before running)
# ==============================================================================

# --- Station / Observer Location (Your current stationary position) ---
STATION_CALLSIGN = "ZL2HV-S1"  # Your amateur radio callsign (used as the uploader ID)
STATION_LAT = -41.212121     # Your stationary Latitude (e.g. Lower Hutt)
STATION_LON = 174.920222     # Your stationary Longitude
STATION_ALT = 0.00           # Your stationary Altitude in meters

# --- Balloon / Payload Details ---
PAYLOAD_CALLSIGN = "ZL2HV-HAB"  # The callsign or name of the balloon payload

# --- Serial Port Configuration ---
# Set to "auto" to let the script search and pick the serial port of your Lilygo board.
# Alternatively, specify the port explicitly based on your Operating System:
#   - Windows: 'COM3', 'COM4', etc.
#   - Linux:   '/dev/ttyUSB0', '/dev/ttyACM0', etc.
#   - macOS:   '/dev/tty.usbserial-1410', '/dev/cu.usbserial-1410', etc.
SERIAL_PORT = "auto"
BAUD_RATE = 115200

# --- Sondehub Amateur Settings ---
SONDEHUB_ENABLED = False
SOFTWARE_NAME = "TEST-T3S3-LoRa"
SOFTWARE_VERSION = "1.0.0"

# --- Logging Settings ---
LOG_FILE_PREFIX = "telemetry_log"

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_next_log_filename(prefix=LOG_FILE_PREFIX, ext=".txt"):
    """
    Finds the next available log file name to avoid overwriting existing data.
    e.g., telemetry_log_1.txt, telemetry_log_2.txt, etc.
    """
    i = 1
    while True:
        filename = f"{prefix}_{i}{ext}"
        if not os.path.exists(filename):
            return filename
        i += 1


def init_serial():
    """
    Configures and opens the serial port, automatically detecting the Lilygo board if requested.
    """
    port = SERIAL_PORT
    if port.lower() == "auto":
        print("Searching for serial port...")
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("Error: No serial ports found. Please connect your Lilygo T3S3.")
            return None
        
        # Keywords commonly associated with USB-to-UART bridge chips
        usb_keywords = ["usb", "uart", "serial", "cp210", "ch340", "ch910", "ftdi", "silicon labs", "lilygo"]
        selected_port = None
        for p in ports:
            desc = p.description.lower()
            hwid = p.hwid.lower()
            name = p.device.lower()
            if any(kw in desc or kw in hwid or kw in name for kw in usb_keywords):
                selected_port = p.device
                print(f"Auto-detected port: {p.device} ({p.description})")
                break
        
        if not selected_port:
            selected_port = ports[0].device
            print(f"Could not confirm UART driver description. Trying first available port: {selected_port}")
        
        port = selected_port

    try:
        ser = serial.Serial(port=port, baudrate=BAUD_RATE, timeout=1)
        print(f"Successfully connected to serial port: {port}")
        return ser
    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")
        return None


def calculate_pointing_angles(balloon_lat, balloon_lon, balloon_alt):
    """
    Calculates True Azimuth, Magnetic Declination, Magnetic Azimuth,
    Elevation, and Slant Range from the station to the balloon.
    """
    # 1. Calculate True Azimuth, Elevation, and Range
    true_az, elevation, slant_range = pm.geodetic2aer(
        balloon_lat, balloon_lon, balloon_alt,
        STATION_LAT, STATION_LON, STATION_ALT
    )

    # 2. Calculate local Magnetic Declination
    current_date = datetime.now()
    decimal_year = current_date.year + (current_date.timetuple().tm_yday - 1) / 365.25

    geo_mag = GeoMag()  # Automatically defaults to the WMM-2025 model (valid through 2029)
    mag_result = geo_mag.calculate(
        glat=STATION_LAT, glon=STATION_LON, alt=STATION_ALT, time=decimal_year
    )
    declination = mag_result.d  # Declination in degrees (Positive/East, Negative/West)

    # 3. Convert True Azimuth to Magnetic Azimuth
    magnetic_az = (true_az - declination) % 360.0

    return {
        "true_az": true_az,
        "declination": declination,
        "magnetic_az": magnetic_az,
        "elevation": elevation,
        "slant_range_km": slant_range / 1000.0
    }


def parse_line(line):
    """
    Parses a line received from the Lilygo T3S3.
    If it is JSON containing 'payload', 'rssi', and 'snr', parse those.
    Then, parses the comma-separated payload values.
    Returns a dict with parsed fields if successful, otherwise None.
    """
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None  # Not a JSON string (likely a system startup message)
        
    payload_str = data.get("payload")
    if not payload_str:
        return None
        
    rssi = data.get("rssi")
    snr = data.get("snr")
    
    parts = [p.strip() for p in payload_str.split(",")]
    if len(parts) < 7:
        return None
        
    try:
        frame = int(parts[0])
        
        # Check for invalid GPS readings ("N")
        has_gps = (parts[1] != "N" and parts[2] != "N" and parts[3] != "N")
        lat = float(parts[1]) if has_gps else None
        lon = float(parts[2]) if has_gps else None
        alt = float(parts[3]) if has_gps else None
        
        # Check for invalid sensor readings ("E")
        int_temp = float(parts[4]) if parts[4] != "E" else None
        pressure = float(parts[5]) if parts[5] != "E" else None
        ext_temp = float(parts[6]) if parts[6] != "E" else None
        
        return {
            "frame": frame,
            "has_gps": has_gps,
            "lat": lat,
            "lon": lon,
            "alt": alt,
            "int_temp": int_temp,
            "pressure": pressure,
            "ext_temp": ext_temp,
            "rssi": rssi,
            "snr": snr
        }
    except ValueError:
        return None


def upload_to_sondehub(packet):
    """
    Uploads a parsed packet to SondeHub Amateur.
    API accepts a JSON list of telemetry objects via HTTP PUT.
    """
    url = "https://api.v2.sondehub.org/amateur/telemetry"
    
    headers = {
        "Content-Type": "application/json",
        "accept": "text/plain",
        "User-Agent": f"{SOFTWARE_NAME}/{SOFTWARE_VERSION} ({STATION_CALLSIGN})"
    }
    
    # Generate current ISO-8601 UTC time
    now_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    # Build standard SondeHub Amateur JSON fields
    telemetry_data = {
        "software_name": SOFTWARE_NAME,
        "software_version": SOFTWARE_VERSION,
        "uploader_callsign": STATION_CALLSIGN,
        "uploader_position": [STATION_LAT, STATION_LON, STATION_ALT],
        "time_received": now_utc_str,
        "datetime": now_utc_str,
        "payload_callsign": PAYLOAD_CALLSIGN,
        "frame": packet["frame"],
        "lat": packet["lat"],
        "lon": packet["lon"],
        "alt": packet["alt"]
    }
    
    # Optional fields
    if packet.get("ext_temp") is not None:
        telemetry_data["temp"] = packet["ext_temp"]
    if packet.get("pressure") is not None:
        telemetry_data["pressure"] = packet["pressure"]
    if packet.get("rssi") is not None:
        telemetry_data["rssi"] = packet["rssi"]
    if packet.get("snr") is not None:
        telemetry_data["snr"] = packet["snr"]
    
    # SondeHub expects a list of objects
    payload = [telemetry_data]
    
    try:
        response = requests.put(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return True, f"Success (HTTP 200: {response.text.strip()})"
        else:
            return False, f"Error {response.status_code}: {response.text.strip()}"
    except requests.exceptions.RequestException as e:
        return False, f"Network Error: {e}"


def display_packet(parsed, pointing_info, upload_status):
    """
    Prints a readable dashboard to the terminal.
    """
    print("\n" + "=" * 60)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Telemetry Packet Received")
    print("=" * 60)
    
    print("--- Balloon Status ---")
    print(f"  Frame (Packet #): {parsed['frame']}")
    
    if parsed['has_gps']:
        print(f"  Latitude:         {parsed['lat']:.6f} °")
        print(f"  Longitude:        {parsed['lon']:.6f} °")
        print(f"  Altitude:         {parsed['alt']:.1f} m")
    else:
        print("  Latitude:         No GPS Lock (N)")
        print("  Longitude:        No GPS Lock (N)")
        print("  Altitude:         No GPS Lock (N)")
        
    print(f"  Ext Temp:         {f'{parsed['ext_temp']:.2f} °C' if parsed['ext_temp'] is not None else 'No reading (E)'}")
    print(f"  Int Temp:         {f'{parsed['int_temp']:.2f} °C' if parsed['int_temp'] is not None else 'No reading (E)'}")
    print(f"  Pressure:         {f'{parsed['pressure']:.1f} hPa' if parsed['pressure'] is not None else 'No reading (E)'}")
    print(f"  LoRa RSSI:        {parsed['rssi']:.1f} dBm" if parsed['rssi'] is not None else "  LoRa RSSI:        N/A")
    print(f"  LoRa SNR:         {parsed['snr']:.2f} dB" if parsed['snr'] is not None else "  LoRa SNR:         N/A")
    
    print("\n--- Antenna Pointing Angles ---")
    if pointing_info:
        print(f"  True Azimuth:         {pointing_info['true_az']:.2f}°")
        direction_label = "East" if pointing_info['declination'] >= 0 else "West"
        print(f"  Magnetic Declination: {abs(pointing_info['declination']):.2f}° {direction_label}")
        print(f"  Magnetic Azimuth:     {pointing_info['magnetic_az']:.2f}° <-- Point your antenna here")
        print(f"  Elevation Angle:      {pointing_info['elevation']:.2f}°")
        print(f"  Direct Distance:      {pointing_info['slant_range_km']:.2f} km")
    else:
        print("  Status:               Cannot calculate pointing (no GPS lock).")
        
    print("\n--- SondeHub Upload ---")
    print(f"  Status:               {upload_status}")
    print("=" * 60)


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def main():
    # Identify a safe log filename sequentially
    log_filename = get_next_log_filename()
    print(f"Initializing logger. Saving raw serial feeds to: {log_filename}")
    
    # Open log file
    log_file = open(log_filename, "a", encoding="utf-8")
    
    # Establish connection to serial device
    ser = init_serial()
    if not ser:
        print("Critical Error: Unable to configure or open the serial interface. Exiting.")
        log_file.close()
        sys.exit(1)
        
    print("Listening for incoming telemetry...")
    last_uploaded_frame = -1
    
    try:
        while True:
            if ser.in_waiting > 0:
                # Read line from the serial port
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                # Append line to raw text file with local timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"[{timestamp}] {line}\n")
                log_file.flush()
                
                # Check if it is valid telemetry
                parsed = parse_line(line)
                
                if parsed is not None:
                    pointing_info = None
                    if parsed["has_gps"]:
                        try:
                            # Calculate physical antenna direction coordinates
                            pointing_info = calculate_pointing_angles(
                                parsed["lat"], parsed["lon"], parsed["alt"]
                            )
                        except Exception as e:
                            print(f"[Internal pointing calculation warning: {e}]")
                            pointing_info = None
                    
                    # SondeHub amateur API routing
                    upload_status = "Disabled in settings."
                    if SONDEHUB_ENABLED:
                        if not parsed["has_gps"]:
                            # Prevent sending dirty data without coordinate locks to SondeHub
                            upload_status = "Skipped (SondeHub requires a valid coordinate lock)."
                        elif parsed["frame"] == last_uploaded_frame:
                            upload_status = "Skipped (Duplicate frame number already processed)."
                        else:
                            success, msg = upload_to_sondehub(parsed)
                            upload_status = msg
                            if success:
                                last_uploaded_frame = parsed["frame"]
                                
                    display_packet(parsed, pointing_info, upload_status)
                else:
                    # Print raw non-JSON content (system startup logs, messages etc.)
                    print(f"[Lilygo Message] {line}")
            else:
                time.sleep(0.05)
                
    except KeyboardInterrupt:
        print("\nScript terminated by user.")
    finally:
        # Clean resources on exit
        if ser and ser.is_open:
            ser.close()
        if log_file and not log_file.closed:
            log_file.close()
        print("Cleaned up serial ports and saved log file successfully.")


if __name__ == "__main__":
    main()
