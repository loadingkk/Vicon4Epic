"""Record and display each received VRPN pose; stop with Ctrl+C."""
import argparse
import csv
from datetime import datetime
from pathlib import Path
import time

import vicon_tracker


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object", help="VRPN name, e.g. visio@192.168.11.2")
    parser.add_argument("--config", type=Path, default=root / "config.cfg")
    parser.add_argument("--output", type=Path, help="Output CSV (must not already exist)")
    args = parser.parse_args()
    object_name = args.object
    if not object_name:
        try:
            for line in args.config.read_text().splitlines():
                key, separator, value = line.strip().partition(":")
                if separator and key == "object":
                    object_name = value.strip().strip('"')
                    break
        except OSError as exc:
            parser.error(str(exc))
    if not object_name:
        parser.error("No object in config; specify --object")
    if not hasattr(vicon_tracker.vicon, "listen"):
        parser.error('Old module loaded. Run with PYTHONPATH="$PWD/build"')

    output = args.output or root / "records" / (
        "vicon_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".csv"
    )
    output = output.resolve()
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        file = output.open("x", newline="", encoding="utf-8")
    except OSError as exc:
        parser.error(str(exc))

    count = 0
    started = time.monotonic()
    tracker = vicon_tracker.vicon()
    with file:
        writer = csv.writer(file)
        writer.writerow([
            "frame", "object", "sensor", "source_timestamp_s",
            "received_unix_ns", "elapsed_s", "x", "y", "z",
            "r00", "r01", "r02", "r10", "r11", "r12", "r20", "r21", "r22",
        ])
        file.flush()

        def on_pose(position, rotation, timestamp, sensor):
            nonlocal count
            received_ns = time.time_ns()
            elapsed = time.monotonic() - started
            writer.writerow([
                count + 1, object_name, sensor, f"{timestamp:.6f}",
                received_ns, f"{elapsed:.9f}",
                *[float(value) for value in position],
                *[float(value) for row in rotation for value in row],
            ])
            # Flush each received frame; no timer-based sampling or duplicate poses.
            file.flush()
            count += 1
            p = ", ".join(f"{value:.6f}" for value in position)
            r = "; ".join(
                ", ".join(f"{value:.6f}" for value in row) for row in rotation
            )
            print(
                f"frame={count} sensor={sensor} timestamp={timestamp:.6f} "
                f"position=[{p}] rotation=[{r}]",
                flush=True,
            )

        try:
            tracker.open(object_name)
            print(f"Recording {object_name}\nFile: {output}\nWaiting for poses; Ctrl+C to stop.", flush=True)
            tracker.listen(on_pose)
        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            tracker.close()
            print(f"Saved {count} poses to {output}", flush=True)


if __name__ == "__main__":
    main()
