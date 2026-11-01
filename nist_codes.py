#!/usr/bin/env python3
"""Passive WLAN posture scanner with an optional B210 energy-only monitor.

The B210 backend measures received signal power at one tuned frequency. It does
not decode frames or write IQ samples. For live GUI spectrum monitoring, open
the accompanying nist_b210_passive_monitor.grc in GNU Radio Companion.
"""

import argparse
import csv
import io
import math
import shutil
import subprocess
import sys


def scan_wireless_environment():
    """Return visible access points reported by NetworkManager."""
    if not shutil.which("nmcli"):
        raise RuntimeError("'nmcli' binary not found; install NetworkManager.")

    cmd = [
        "nmcli",
        "-t",
        "-f",
        "BSSID,SSID,CHAN,FREQ,SIGNAL,SECURITY",
        "dev",
        "wifi",
        "list",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or str(exc)
        raise RuntimeError(f"Error querying wireless interfaces: {detail}") from exc

    aps = []
    for row in csv.reader(io.StringIO(result.stdout), delimiter=":"):
        if len(row) < 6:
            continue

        bssid = ":".join(row[:-5])
        ssid, channel, frequency, signal, security = row[-5:]
        aps.append(
            {
                "bssid": bssid,
                "ssid": ssid if ssid else "<Hidden SSID>",
                "channel": channel,
                "freq": frequency,
                "signal": signal,
                "security": security if security else "OPEN",
            }
        )

    return aps


def evaluate_compliance(ap_list):
    """Summarize visible AP security against the scanner's configured baseline."""
    print(f"\nDiscovered {len(ap_list)} visible Access Points.\n")
    print(f"{'BSSID':<20} {'SSID':<25} {'CHAN':<6} {'SIGNAL':<8} {'STATUS':<10} {'DETAILS'}")
    print("-" * 90)

    findings = 0

    for ap in ap_list:
        sec = ap["security"].upper()
        status = "COMPLIANT"
        details = sec

        if sec == "OPEN":
            status = "FAIL"
            details = "Unencrypted network (No authentication/encryption)"
            findings += 1
        elif "WEP" in sec:
            status = "FAIL"
            details = "Legacy WEP cipher (Deprecated by NIST)"
            findings += 1
        elif "WPA1" in sec or "TKIP" in sec:
            status = "WARNING"
            details = "Weak encryption / TKIP suite"
            findings += 1
        elif "WPA2" in sec or "WPA3" in sec:
            status = "PASS"
            details = sec
        else:
            status = "UNKNOWN"

        print(
            f"{ap['bssid']:<20} {ap['ssid'][:24]:<25} {ap['channel']:<6} "
            f"{ap['signal']:<8} {status:<10} {details}"
        )

    print("-" * 90)
    print(f"Total non-compliant or warning APs observed: {findings}\n")


def measure_b210_energy(frequency_mhz, sample_rate, duration, gain):
    """Measure mean and peak received power without retaining raw IQ samples."""
    try:
        from gnuradio import blocks, gr, uhd
    except ImportError as exc:
        raise RuntimeError(
            "GNU Radio Python modules with UHD support are required for --backend b210."
        ) from exc

    sample_count = int(sample_rate * duration)
    flowgraph = gr.top_block("B210 receive-only energy monitor")
    source = uhd.usrp_source(
        "type=b200",
        uhd.stream_args(cpu_format="fc32", channels=[0]),
    )
    source.set_samp_rate(sample_rate)
    source.set_center_freq(frequency_mhz * 1_000_000, 0)
    source.set_gain(gain, 0)
    source.set_antenna("RX2", 0)

    limit = blocks.head(gr.sizeof_gr_complex, sample_count)
    power = blocks.complex_to_mag_squared(1)
    sink = blocks.vector_sink_f()
    flowgraph.connect(source, limit, power, sink)
    flowgraph.run()

    powers = sink.data()
    if not powers:
        raise RuntimeError("The B210 returned no samples.")

    mean_power = sum(powers) / len(powers)
    peak_power = max(powers)

    def to_dbfs(value):
        return 10 * math.log10(value) if value > 0 else float("-inf")

    print(
        f"B210 receive-only energy at {frequency_mhz:.3f} MHz "
        f"({len(powers)} samples): mean {to_dbfs(mean_power):.2f} dBFS, "
        f"peak {to_dbfs(peak_power):.2f} dBFS"
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        choices=("nmcli", "b210", "both"),
        default="nmcli",
        help="Use NetworkManager AP scanning, B210 energy monitoring, or both.",
    )
    parser.add_argument(
        "--frequency-mhz",
        type=float,
        default=2412.0,
        help="B210 receive center frequency in MHz (default: 2412).",
    )
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=1_000_000,
        help="B210 sample rate in samples/second (maximum: 2,000,000).",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.5,
        help="B210 measurement duration in seconds (maximum: 2; total samples capped).",
    )
    parser.add_argument(
        "--gain",
        type=float,
        default=20.0,
        help="B210 receive gain in dB (range: 0-76).",
    )
    args = parser.parse_args(argv)

    if args.backend in ("b210", "both"):
        if not 70 <= args.frequency_mhz <= 6000:
            parser.error("--frequency-mhz must be between 70 and 6000.")
        if not 1 <= args.sample_rate <= 2_000_000:
            parser.error("--sample-rate must be between 1 and 2,000,000.")
        if not 0 < args.duration <= 2:
            parser.error("--duration must be greater than 0 and no more than 2.")
        if args.sample_rate * args.duration > 1_000_000:
            parser.error("--sample-rate multiplied by --duration must not exceed 1,000,000 samples.")
        if not 0 <= args.gain <= 76:
            parser.error("--gain must be between 0 and 76.")

    return args


def main(argv=None):
    args = parse_args(argv)

    try:
        if args.backend in ("nmcli", "both"):
            evaluate_compliance(scan_wireless_environment())
        if args.backend in ("b210", "both"):
            measure_b210_energy(
                args.frequency_mhz,
                args.sample_rate,
                args.duration,
                args.gain,
            )
    except (OSError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
