# Vicon4Epic — EPIC Group Guide

This repository builds on the Vicon Tracker project by Maneesha Wickramasuriya (upstream: `ManeeshW/vicon`). See [README.md](README.md) for the original project documentation and dependency installation notes.

This guide covers our configuration and two added Python scripts:

- [`test_vicon_listen.py`](test_vicon_listen.py): display incoming poses and average message rates.
- [`record_vicon.py`](record_vicon.py): display incoming poses and save them to CSV.

Both scripts use the added `vicon_tracker.vicon.listen(callback)` API. Output is triggered by received VRPN pose messages, rather than repeatedly sampling the latest stored pose. Identical positions may still appear when separate messages report a stationary object. Receiving every camera frame is not guaranteed.

## 1. Configure the tracked object

The current [`config.cfg`](config.cfg) contains:

```yaml
VICON:
 object: "visio@192.168.11.2"
```

| Value | Meaning |
| --- | --- |
| `visio` | The VRPN tracker/object name exported by the Vicon server. Match the server's configured name exactly, including capitalization. |
| `192.168.11.2` | The address of the computer serving Vicon data over VRPN. Replace it if the lab server address changes. |
| `visio@192.168.11.2` | The complete connection string passed to VRPN. |

Before running either script, ensure that the Vicon server is running, VRPN output is enabled, the object is being tracked, and your computer can reach the server on the lab network.

Both scripts default to `config.cfg` beside the script, regardless of your working directory. You can select another configuration with `--config`, or override the configuration entirely with `--object`. Keep the `object:` value on its own line as shown above; these scripts use a simple line parser, not a full YAML parser.

## 2. Build the updated Python module

Run the commands below from the repository root, using the Python environment you intend to use for recording. You need CMake, a C++17 compiler, Eigen3, VRPN headers/libraries, and Quat installed (see the original README). Use Python 3.7 or newer for these scripts; the recorder uses `time.time_ns()`.

```bash
python -m pip install pybind11 numpy
cmake -S . -B build \
  -DPython_EXECUTABLE="$(python -c 'import sys; print(sys.executable)')" \
  -Dpybind11_DIR="$(python -m pybind11 --cmakedir)"
cmake --build build --parallel
```

Check that Python loads the newly built extension and that it provides `listen`:

```bash
PYTHONPATH="$PWD/build" python -c 'import vicon_tracker; print(vicon_tracker.__file__); print("listen available:", hasattr(vicon_tracker.vicon, "listen"))'
```

The module path should point into this repository's `build` directory, and the check should print `listen available: True`. Rebuild after changing the C++ implementation or bindings. The commands below use this build directly; installing the module with pip is not required for this workflow.

## 3. Monitor live data: test_vicon_listen.py

From the repository root:

```bash
PYTHONPATH="$PWD/build" python test_vicon_listen.py
```

Optional overrides:

```bash
PYTHONPATH="$PWD/build" python test_vicon_listen.py --object "visio@192.168.11.2"
PYTHONPATH="$PWD/build" python test_vicon_listen.py --config ./config.cfg
```

Each received pose prints:

| Output | Meaning |
| --- | --- |
| `frame` | Local received-message count for this sensor, starting at 1; not a Vicon hardware frame number. |
| `sensor` | Sensor ID supplied by VRPN. |
| `timestamp` | Source timestamp from the VRPN message, in seconds. |
| `source_avg_hz` | `(count - 1)` divided by the source timestamp span since this sensor's first message. |
| `received_avg_hz` | `(count - 1)` divided by the local monotonic time span since this sensor's first message. |
| `position` | Three position components: `x`, `y`, `z`. |
| `rotation` | A 3 × 3 rotation matrix, printed row by row. |

Rates are cumulative averages per sensor, not instantaneous rates or guaranteed camera capture rates. They show `--` until enough messages and a positive time span are available. This script does not save a data file. Press **Ctrl+C** to stop.

## 4. Record data: record_vicon.py

From the repository root:

```bash
PYTHONPATH="$PWD/build" python record_vicon.py
```

By default, the script creates a timestamped file under `records/` beside the script, for example `records/vicon_20261027_143000_123456.csv`. It prints the resolved output path at startup.

To choose a filename and object explicitly:

```bash
PYTHONPATH="$PWD/build" python record_vicon.py \
  --object "visio@192.168.11.2" \
  --output records/epic_trial_001.csv
```

To use another configuration:

```bash
PYTHONPATH="$PWD/build" python record_vicon.py \
  --config ./config.cfg \
  --output records/epic_trial_002.csv
```

Relative `--config` and `--output` paths are resolved from your current working directory. Missing output directories are created automatically. **An existing output file is never overwritten**; choose a new filename for each trial.

Each received pose is printed and written as one CSV row. The file is flushed after each row. Press **Ctrl+C** to stop, close the connection and file, and print the saved pose count.

### CSV columns

| Column | Meaning |
| --- | --- |
| `frame` | Local row counter starting at 1, shared across all sensors in this recording. |
| `object` | Connection string used for the recording. |
| `sensor` | VRPN sensor ID. |
| `source_timestamp_s` | VRPN message timestamp in seconds, written to six decimal places. |
| `received_unix_ns` | Local wall-clock time in Unix nanoseconds when the Python callback runs. |
| `elapsed_s` | Local monotonic time since recording setup began, including connection/waiting time. |
| `x`, `y`, `z` | Position components passed through from VRPN without unit conversion. |
| `r00` … `r22` | Rotation matrix entries in row-major order: `r00,r01,r02,r10,r11,r12,r20,r21,r22`. |

Confirm position units, axes, and coordinate conventions against the lab's Vicon setup before analysis. The rotation matrix is computed from the received quaternion; it is not Euler angles. Source and receive timestamps come from different clocks, so their difference should not be interpreted as network latency without clock synchronization.

## 5. Troubleshooting

- **`ModuleNotFoundError: vicon_tracker`**: build the extension, run from the repository root with the `PYTHONPATH` prefix shown above, and use the same Python environment used for compilation.
- **`Old module loaded`**: rebuild and run the module check in section 2. A previously installed extension may not include `listen`.
- **Waiting message but no poses**: verify the exact object name (`visio`), server IP, VRPN output, network access, and tracking visibility. An "object opened" message alone does not confirm that data is arriving. The recorder creates a CSV header before receiving poses, so a file with only a header means no poses were saved.
- **Output file already exists**: choose another `--output` filename or omit the option to generate a timestamped name.
- **Unexpected rates**: inspect both averages in the listener. Terminal printing and per-row file flushing can affect receive performance; these scripts do not verify lossless capture.

For this workflow, use the two scripts documented here. The older `test_vicon.py` remains in the repository and currently has a separate fallback name (`visio1@192.168.11.2`); that fallback does not control either script above.
