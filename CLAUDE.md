# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Ground-station tooling for tracking a High Altitude Balloon (HAB). It receives LoRa
telemetry from a balloon payload, computes where to point a directional antenna, and
optionally relays positions to SondeHub Amateur. Written for an amateur radio operator
(callsign `ZL2HV`).

## Scripts

- **`track.py`** — the live tracker. Reads JSON telemetry lines from a serial-connected
  Lilygo T3S3 LoRa board, parses balloon GPS/sensor data, prints a terminal dashboard
  with antenna pointing angles, appends raw serial output to a sequential log file, and
  (when enabled) uploads each new frame to SondeHub Amateur.
- **`point.py`** — a standalone calculator. Hardcode a balloon lat/lon/alt at the top and
  it prints the azimuth/elevation/range from the station. Useful for testing the pointing
  math without hardware. Its `calculate_pointing_angles` is duplicated verbatim in
  `track.py` — **changes to the pointing math must be made in both files.**

## Running

```bash
# Dependencies (no requirements.txt exists; install from imports)
pip install pymap3d pygeomag pyserial requests

python3 track.py    # live tracking; needs the Lilygo board connected over USB
python3 point.py    # one-shot pointing calculation, no hardware needed
```

There are no tests, build step, or linter configured.

## Configuration

All settings are module-level constants in a `CONFIGURATION SETTINGS` block at the top of
each script — edit them directly before running. Key ones:

- `STATION_LAT/LON/ALT` — the fixed ground-station position (used as the observer origin
  for all pointing math and as `uploader_position` for SondeHub).
- `SERIAL_PORT` — `"auto"` searches `comports()` for a USB-UART bridge by description
  keywords; otherwise set an explicit port (e.g. `/dev/ttyUSB0`, `COM3`).
- `SONDEHUB_ENABLED` — defaults to `False`; gates all network uploads.

## Key behaviors to know

- **Telemetry wire format**: each serial line is JSON `{"payload": "...", "rssi": ..., "snr": ...}`.
  The `payload` is a comma-separated string with at least 7 fields:
  `frame, lat, lon, alt, int_temp, pressure, ext_temp`. A field of `"N"` means no GPS lock
  and `"E"` means a failed sensor reading; `parse_line` maps both to `None`. Non-JSON lines
  are treated as Lilygo system messages and printed raw.
- **Pointing math**: `pymap3d.geodetic2aer` gives *true* azimuth; `pygeomag` (WMM-2025
  model) supplies magnetic declination, which is subtracted to produce the *magnetic*
  azimuth the operator actually dials in. Declination is computed at the station, not the
  balloon.
- **Upload guards**: SondeHub uploads are skipped without a GPS lock and de-duplicated by
  `frame` number (`last_uploaded_frame`); the frame is only marked uploaded on HTTP 200.
- **Logging**: `get_next_log_filename` picks the next unused `telemetry_log_N.txt` so runs
  never overwrite prior data. Raw lines are flushed immediately with a local timestamp.

## Note for editors

`display_packet` in `track.py` uses f-strings with same-quote nesting (e.g.
`f'{parsed['ext_temp']...}'`), which requires Python 3.12+. Keep that in mind when editing
those lines or targeting older interpreters.
