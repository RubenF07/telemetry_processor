# Live CAN Telemetry Pipeline

Virginia Tech Motorsports recruit project (EPT): **Grafana Telemetry Dashboard**.

This project takes raw CAN frames coming off the car (over a USB serial port), decodes them into human-readable signals (e.g. `Pack_SOC`, `D2_Motor_Speed`), stores them in a time-series database, and displays them live in Grafana.

---

## The Short Version

1. **The car's CAN bus** broadcasts tiny packets of raw numbers, like `0x0A0: 12 34 56 78 ...`. On their own these are meaningless.
2. **`can_bridge.py`** (the heart of this project) reads those packets from a USB serial port and uses a **DBC file**, a "dictionary" that has the instruction to turn the raw bytes into real values.
3. **Telegraf** is a small program that catches those values and hands them to the database.
4. **InfluxDB** is a database built for timestamped data (a "time-series" database). It stores every reading with the moment it arrived.
5. **Grafana** reads from the database and draws live visualizations.


---

## What's in This Repo

| File | Role | What it does |
|---|---|---|
| **`can_bridge.py`** | **Main program** | Reads CAN frames from the serial port, decodes them using the DBC, and forwards them to Telegraf. Automatically reconnects if the serial port or Telegraf drops. |
| `csv_can_sim.py` | Secondary tool | Replays a recorded MoTeC i2 CSV export in real time so you can develop and test dashboards without a car. Also documents the **real signal names** used on the car (see the commented field list at the bottom of the file). |
| `telegraf_format.py` | Shared helper | Converts a dict of signals into InfluxDB *line protocol* (the text format the database understands). Used by both programs above. |
| `serial_test.py` | Utility | Lists the serial ports on your computer so you can find the right one for `SERIAL_PORT`. |
| `EV_Test.dbc` | Config *(required)* | The DBC file describing the vehicle's CAN network. |
| `requirements.txt` | Config | Python dependencies. (it is referenced in setup below). |

---

## Quick Start

You need four things running, in this order: **InfluxDB → Telegraf → Grafana → `can_bridge.py`**.
(`can_bridge.py` will keep retrying until Telegraf is up, so a wrong order isn't fatal, just noisy.)

### 1. Python environment (Windows)

> Serial port reading did **not** work from WSL, so run the Python scripts on Windows directly. The database stack (Section 2) runs in WSL.

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

To leave the virtual environment later: `deactivate`

### 2. Database stack (WSL)

Install each of these first by following the official docs:

- [InfluxDB 3](https://docs.influxdata.com/influxdb3/enterprise/install/)
- [Telegraf](https://docs.influxdata.com/telegraf/v1/get-started/)
- Grafana (installed so that `grafana-server` runs as a systemd service)

**Start InfluxDB** (with its web UI):

```bash
influxdb3 serve --mode all,webui --webui-session-secret local-dev-only --without-auth \
  --node-id host01 --cluster-id cluster01 --object-store file --data-dir ~/.influxdb3
```

- Web UI: [http://localhost:8181](http://localhost:8181)
- ⚠️ `--without-auth` and the placeholder session secret are **for local development only**. Never expose this instance to a network.

**Start Telegraf:**

```bash
sudo systemctl start telegraf
```

Telegraf must be configured with a **TCP socket listener on port `7654`** that accepts InfluxDB line protocol, and an **output to your InfluxDB instance**. These must match `TELEGRAF_HOST` / `TELEGRAF_PORT` in the Python scripts.

Telegraf also **buffers incoming data and writes it to the database in batches every 200 ms** instead of once per frame (see [Design Decisions](#design-decisions)). This interval is adjustable in the Telegraf config: shorter means fresher dashboards, longer means less database load.


**Start Grafana:**

```bash
sudo systemctl daemon-reload
sudo systemctl start grafana-server
```

- Open [http://localhost:3000](http://localhost:3000)
- Add InfluxDB as a data source.


### 3. Run the pipeline

**Option A. Live from the car (main use):**

1. Plug in the telemetry board over USB. (During development this was a **mock CAN board streaming random values** as a proof of concept, so graphs from it won't look like real car data. Use Option B for realistic data.)
2. Find the port name:
   ```powershell
   python serial_test.py
   ```
3. Edit the config block at the top of `can_bridge.py`:
   ```python
   SERIAL_PORT = "COM3"        # <-- change to YOUR port
   BAUD_RATE   = 921600
   DBC_FILE    = "EV_Test.dbc" # path to your DBC
   ```
4. Run it from the folder containing the DBC:
   ```powershell
   python can_bridge.py
   ```
5. Stop with `Ctrl+C`.

**Option B. Replay a recorded session (no car needed):**

This is how the example dashboard was developed and demonstrated. The dataset is a **real session from the VT Motorsports 24 EV car at the Michigan competition**, so it has realistic values and timing. The simulator streams it to Telegraf exactly as if it were coming from the CAN bus.

1. Export a session from MoTeC i2 as CSV and set `CSV_FILE` at the top of `csv_can_sim.py`.
2. Run:
   ```powershell
   python csv_can_sim.py
   ```
3. Press Enter when prompted. The script replays the data at the original speed and prints progress. At the end it reports how many rows it couldn't keep real-time pace on.

---

## Reference

### Dashboard Design

Before building anything, I talked with members of both the IC and EV teams about what they need from live telemetry. Shared takeaway: **prioritize the key engineering signals on the live view** and leave secondary or driver-facing data to post-session logs, so the vital data can be polled faster.

| Team | Priority | Requested fields (examples) |
|---|---|---|
| IC | Engine health, especially thermals (if oil/coolant climbs, the driver can be told to back off) | Engine speed, oil and coolant temperature, gear state, oil pressure, PDM current, lambda, air-fuel ratio, battery voltage |
| EV | Battery and powertrain health, including single-cell problems (e.g. one cell's voltage dropping fast) | State of charge, average cell temperature, max cell voltage delta, inverter temperature, motor temperature |
| Both | General | Throttle %, front/rear brake pressure, sector times, g-force, track map |

Only the **EV dashboard** was built (time constraints), but the design keeps IC needs in mind. Some requested fields (inverter temperature, individual cell temperatures) have **no sensors on the car yet**, so they are not in the dashboard.

### Design Decisions

| Choice | Why |
|---|---|
| **Python** | Fast to write, huge library ecosystem, and fast enough here: the ingester's work is light and keeps up with the CAN stream. A compiled language would only matter if throughput grows a lot. |
| **`cantools` + DBC** | The DBC describes every frame's layout, scaling and offsets, so decoding is data-driven. A CAN network change means updating the DBC, not the code. |
| **TCP socket to Telegraf** (not HTTP requests) | A socket stays open and authenticates once; HTTP adds per-message overhead. Locally everything is on `127.0.0.1`; in production only the address changes. |
| **Telegraf as a buffer** | Thousands of tiny writes per second would overload the database. Batching every 200 ms means fewer, larger writes. Data arrives slightly later, but the dashboard refreshes much more smoothly. |
| **InfluxDB (time-series DB)** | Built for high write throughput and fast time-range queries, which is what CAN data looks like. A relational database is more flexible but slower for this job. Also integrates easily with Telegraf. |
| **Grafana** | Free and open source, reads InfluxDB natively, and has gauges, refresh-rate switching, time-range viewing and an in-browser editor, so almost no software time goes to the front end. |

### Serial input format

The board sends one text line per CAN frame:

```
B:<bus id>|C:0x<frame id in hex>|D:<up to 8 data bytes, hex, space separated>
```

Example: `B:0|C:0x0A0|D:12 34 56 78 9A BC DE F0`

Lines that can't be parsed, belong to a frame ID that isn't in the DBC, or have the wrong payload length are logged and skipped. They will not crash the program.

### What gets written to the database

| Source | Measurement (table) | Tag | Fields |
|---|---|---|---|
| `can_bridge.py` | `can_frame` | `can_id` (hex, e.g. `0xA0`) | One field per signal in the DBC |
| `csv_can_sim.py` | `simulated_can_frame` | `can_id=0x0` (placeholder) | One field per CSV column |

The simulator writes to a **separate measurement** so replayed data never mixes with real car data. Build dashboards against `can_frame` for live data and `simulated_can_frame` for testing.

### Reliability behaviour

- If the serial port disappears (unplugged board), `can_bridge.py` closes it and retries every 1 s.
- If the Telegraf socket drops, it reconnects automatically.
- Non-finite numbers (`NaN`, `inf`) are rejected before they reach InfluxDB, which would otherwise refuse the write.

---

## Local-Only Settings (change these for your machine)

These values are specific to the original developer's setup and **will not work as-is for you**:

| Setting | Where | Notes |
|---|---|---|
| `SERIAL_PORT = "COM3"` | `can_bridge.py` | Varies by computer, OS, and which USB port you use. Use `serial_test.py`. macOS looks like `/dev/cu.usbmodemXXXXXXXX`; Linux like `/dev/ttyACM0`. |
| `CSV_FILE = "testData4.csv"` | `csv_can_sim.py` | Points to a local recording that may not be in the repo. |
| `skiprows=14` | `csv_can_sim.py` | Tied to the MoTeC i2 CSV header length. Adjust if your export differs. |
| `--webui-session-secret local-dev-only`, `--without-auth` | InfluxDB start command | Development convenience only. |
| `ngrok` URL (below) | README | A personal ngrok domain. Use your own. |

### Optional: sharing your dashboard with ngrok

To let someone outside your network view your **local** Grafana temporarily:

```bash
ngrok http 3000 --url https://chaffing-subdued-feline.ngrok-free.dev
```

This is a convenience for demos only. The domain used during development belongs to the original developer and won't work for you. You'll need your own (free) [ngrok](https://ngrok.com) account and domain.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Cannot open COM3...Retrying` | Wrong port, board unplugged, or another program (serial monitor, etc.) already has the port open. |
| `Cannot connect to Telegraf...Retrying` | Telegraf isn't running, or its socket listener isn't on `127.0.0.1:7654`. If Telegraf is in WSL and the script is on Windows, confirm `localhost` forwarding works. |
| `Could not parse CAN frame ...` | Frame ID isn't in your DBC, payload length doesn't match, or the line is malformed. |
| `Ahead of the game, waiting on serial...` | Not an error. No data arrived within the 1 s read timeout. |
| Serial doesn't work in WSL | Known issue. Run the Python scripts on Windows. |

---

## Credits

- Project author: Ruben Finkel
- `serial_test.py` by Cooper
- Team members consulted for dashboard needs: 
    EV - Dillon Lewallen
    IC - Nikolay Bychkov