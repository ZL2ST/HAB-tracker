from datetime import datetime, timezone
import pymap3d as pm
from pygeomag import GeoMag

# ==============================================================================
# CONFIGURATION SETTINGS (Edit these before running)
# ==============================================================================

# --- Station / Observer Location (Your current stationary position) ---
STATION_LAT = -41.212121     # Your stationary Latitude (e.g. Lower Hutt)
STATION_LON = 174.920222     # Your stationary Longitude
STATION_ALT = 0.00           # Your stationary Altitude in meters

# --- Balloon Location (Determined from Garmin tracker or such) ---
HAB_LAT = -41.180036     # Latitude
HAB_LON = 175.002708     # Longitude
HAB_ALT = 5000.0         # Altitude in meters

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

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

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def main():
    pointing_info = calculate_pointing_angles(HAB_LAT, HAB_LON, HAB_ALT)
    if pointing_info:
        print(f"  True Azimuth:         {pointing_info['true_az']:.2f}°")
        direction_label = "East" if pointing_info['declination'] >= 0 else "West"
        print(f"  Magnetic Declination: {abs(pointing_info['declination']):.2f}° {direction_label}")
        print(f"  Magnetic Azimuth:     {pointing_info['magnetic_az']:.2f}° <-- Point your antenna here")
        print(f"  Elevation Angle:      {pointing_info['elevation']:.2f}°")
        print(f"  Direct Distance:      {pointing_info['slant_range_km']:.2f} km")
    else:
        print("  Status:               Cannot calculate pointing ")

if __name__ == "__main__":
    main()
