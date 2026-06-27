# HAB Tracker

Ground-station tools for tracking a **High Altitude Balloon (HAB)**.

There are two programs in this folder:

| Script | What it does |
| --- | --- |
| `track.py` | Listens to your LoRa radio board over USB, shows live balloon telemetry, tells you where to point your antenna, and (optionally) uploads positions to SondeHub. |
| `point.py` | A simple calculator. You type in a balloon position by hand and it tells you where to point your antenna. No radio hardware needed. |

This guide assumes you have **never used Python before**. Follow it step by step.

---

## 1. Install Python

You need **Python 3.12 or newer**. Older versions will not run these scripts.

Check what you have by opening a terminal (Command Prompt on Windows, Terminal on
macOS/Linux) and typing:

```bash
python3 --version
```

You should see something like `Python 3.12.0` or higher. If the number is lower than
3.12, or you get an error, download and install the latest Python from
<https://www.python.org/downloads/> and try again.

> **Windows tip:** when installing, tick the box that says **"Add Python to PATH"** on the
> first screen of the installer. If you skip this, the `python` and `pip` commands will not
> work in your terminal.

---

## 2. Download the code

Before anything else, you need a copy of these scripts on your own computer.

- **Easiest way:** on the project's GitHub page, click the green **Code** button, choose
  **Download ZIP**, then unzip it. This gives you a folder containing `track.py`, `point.py`,
  and `requirements.txt`.
- **If you use git:** `git clone <repository-url>`.

Then open a terminal and **go into that folder** with the `cd` ("change directory") command,
for example:

```bash
cd Downloads/HAB-tracker
```

Everything in the rest of this guide must be run from **inside this folder** — that is where
`requirements.txt` and the scripts live, and the commands below will not find them otherwise.
To check you are in the right place, list the files and confirm you can see them:

```bash
ls          # macOS / Linux
dir         # Windows
```

You should see `track.py`, `point.py`, and `requirements.txt` in the list.

---

## 3. Install the required dependencies

These scripts rely on four free add-on packages, listed in the `requirements.txt` file.
From inside the project folder (see section 2), install all of them in one command.

**On macOS and Linux**, use `pip3`:

```bash
pip3 install -r requirements.txt
```

**On Windows**, use `pip`:

```bash
pip install -r requirements.txt
```

> **Tip:** `pip` and `pip3` are the same tool, but on macOS the plain `pip` command is often
> missing or points at the wrong Python — so if `pip` gives a "command not found" error, use
> `pip3`.

(This is the same as installing `pymap3d pygeomag pyserial requests` by hand.)

What each package is for (you don't need to understand these, just install them):

- **pymap3d** and **pygeomag** – do the antenna-pointing maths.
- **pyserial** – talks to the radio board over the USB cable.
- **requests** – uploads data to the internet (SondeHub).

> **"Permission denied" or "externally-managed-environment" error?**
> On macOS and Linux you may need to add `--user` to install just for your account:
> ```bash
> pip3 install --user -r requirements.txt
> ```

You only have to do this installation **once**.

---

## 4. Editing settings (important background)

Both scripts have a block of settings near the top of the file that you must edit before
running. To change them:

1. Open the `.py` file in any plain-text editor (Notepad on Windows, TextEdit on macOS, or
   a code editor like VS Code).
2. Find the section marked `CONFIGURATION SETTINGS (Edit these before running)`.
3. Change the values, keeping the format exactly as shown (numbers stay numbers, text stays
   inside the `"quote marks"`).
4. **Save the file** before running it.

The most important settings are your **station location** – your own fixed position on the
ground. This is the spot the antenna pointing is calculated *from*, so get it right.

```python
STATION_LAT = -41.212121     # Your Latitude  (negative = South)
STATION_LON = 174.920222     # Your Longitude (negative = West)
STATION_ALT = 0.00           # Your Altitude in metres
```

You can find your latitude and longitude by right-clicking your location in Google Maps.

---

## 5. `point.py` – the pointing calculator

Use this when you know roughly where the balloon is and just want to know which way to aim
your antenna. It needs no radio and no internet.

### Settings to change

In addition to the **station location** (see section 4), set the **balloon location**:

```python
HAB_LAT = -41.180036     # Balloon Latitude
HAB_LON = 175.002708     # Balloon Longitude
HAB_ALT = 5000.0         # Balloon Altitude in metres
```

Get these numbers from a separate source such as a Garmin tracker or a prediction website.

### How to run it

In your terminal, go to the folder containing the scripts, then run:

```bash
python3 point.py
```

It prints the answer once and exits. The line to read is **Magnetic Azimuth** – that is the
compass bearing to point your antenna. It also shows the **Elevation Angle** (how far up to
tilt) and the **Direct Distance** to the balloon.

### Troubleshooting

| Problem | Fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'pymap3d'` (or similar) | The dependencies aren't installed. Go back to **section 3**. |
| `python3: command not found` | Try `python point.py` instead, or re-install Python with "Add to PATH" ticked. |
| The numbers look wrong / point the wrong way | Double-check the sign of your latitude/longitude. South latitude and West longitude must be **negative**. |
| `SyntaxError` mentioning f-strings | You're on an old Python. Install **3.12 or newer** (section 1). |

---

## 6. `track.py` – the live tracker

This is the main program. It reads live telemetry from your **Lilygo T3S3 LoRa board**
plugged in over USB, shows a live dashboard, and saves everything to a log file.

### Settings to change

Set your **station location** (section 4), then review these:

```python
STATION_CALLSIGN = "ZL2HV-S1"    # Your amateur radio callsign
PAYLOAD_CALLSIGN = "ZL2HV-HAB"   # The balloon's name/callsign

SERIAL_PORT = "auto"             # Leave as "auto" to find the board automatically
BAUD_RATE   = 115200             # Leave this as-is unless you know otherwise

SONDEHUB_ENABLED = False         # Set to True to upload positions to SondeHub
```

- **`SERIAL_PORT`** – leave it as `"auto"` and the script will try to find your board by
  itself. If that fails, set it to the exact port name instead:
  - Windows: `"COM3"`, `"COM4"`, etc.
  - Linux: `"/dev/ttyUSB0"` or `"/dev/ttyACM0"`
  - macOS: `"/dev/tty.usbserial-1410"` or similar
- **`SONDEHUB_ENABLED`** – keep it `False` while testing. Set it to `True` only when you
  want to share live balloon positions on the SondeHub Amateur map (this needs an internet
  connection).

### How to run it

1. Plug the Lilygo board into your computer with a USB cable.
2. In your terminal, go to the script folder and run:

   ```bash
   python3 track.py
   ```

3. The program runs continuously. Each time the balloon sends data, a dashboard appears
   showing the balloon's position, temperatures, pressure, signal strength, and the antenna
   pointing angles. Point your antenna to the **Magnetic Azimuth** shown.
4. To stop the program, press **Ctrl + C**.

Every run also saves the raw incoming data to a file named `telemetry_log_1.txt`,
`telemetry_log_2.txt`, and so on. A new numbered file is created each run, so your old logs
are never overwritten.

### Troubleshooting

| Problem | Fix |
| --- | --- |
| `Error: No serial ports found` | The board isn't detected. Check the USB cable is plugged in and is a **data** cable (some cables are charge-only). You may also need a USB driver (CP210x or CH340) for your board. |
| It connects to the wrong port, or picks the wrong device | Don't use `"auto"`. Set `SERIAL_PORT` to the exact port name (see list above). |
| `Error opening serial port ... Access is denied / Permission denied` | The port is in use by another program (e.g. Arduino IDE) – close it. On Linux you may need to add yourself to the `dialout` group: `sudo usermod -a -G dialout $USER`, then log out and back in. |
| Dashboard never appears, only `[Lilygo Message] ...` lines | The board is talking but not sending valid telemetry yet. Wait for the balloon to transmit, and confirm the board's firmware and `BAUD_RATE` (115200) match. |
| Shows "No GPS Lock" | The balloon hasn't got a GPS fix yet – this is normal at startup. Pointing angles only appear once GPS is locked. |
| SondeHub upload says "Error" or "Network Error" | Check your internet connection and that `STATION_CALLSIGN` is filled in correctly. Uploads are skipped until the balloon has a GPS lock. |
| `ModuleNotFoundError` | Dependencies aren't installed – see **section 3**. |
