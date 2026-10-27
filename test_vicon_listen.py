"""Display each received VRPN pose once. Stop with Ctrl+C."""
import argparse
from pathlib import Path
import time

import vicon_tracker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object", help="VRPN name, e.g. visio@192.168.11.2")
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).resolve().with_name("config.cfg"))
    args = parser.parse_args()
    object_name = args.object
    if not object_name:
        for line in args.config.read_text().splitlines():
            key, separator, value = line.strip().partition(":")
            if separator and key == "object":
                object_name = value.strip().strip('"')
                break
    if not object_name:
        parser.error("No object in config; specify --object")
    if not hasattr(vicon_tracker.vicon, "listen"):
        parser.error('Old module loaded. Run with PYTHONPATH="$PWD/build"')

    # Track each sensor independently; source rate uses VRPN message timestamps.
    stats = {}

    def on_pose(position, rotation, timestamp, sensor):
        now = time.monotonic()
        state = stats.setdefault(sensor, [timestamp, now, 0])
        state[2] += 1
        count = state[2]
        source_dt = timestamp - state[0]
        receive_dt = now - state[1]
        source_hz = f"{(count - 1) / source_dt:.2f}" if source_dt > 0 and count > 1 else "--"
        receive_hz = f"{(count - 1) / receive_dt:.2f}" if receive_dt > 0 and count > 1 else "--"
        p = ", ".join(f"{v:.6f}" for v in position)
        r = "; ".join(", ".join(f"{v:.6f}" for v in row) for row in rotation)
        print(f"frame={count} sensor={sensor} timestamp={timestamp:.6f} "
              f"source_avg_hz={source_hz} received_avg_hz={receive_hz} "
              f"position=[{p}] rotation=[{r}]", flush=True)

    tracker = vicon_tracker.vicon()
    tracker.open(object_name)
    try:
        print(f"Listening to {object_name}; one line per received pose. Ctrl+C to stop.", flush=True)
        tracker.listen(on_pose)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        tracker.close()


if __name__ == "__main__":
    main()
