# cybersec002

Small Linux wireless-security and software-defined-radio utilities for
authorized lab use. The scripts use local Wi-Fi interfaces, HackRF, or a USRP
B210; they do not provide a general-purpose network attack framework.

## Contents

| File | Purpose |
| --- | --- |
| [`nist_codes.py`](./nist_codes.py) | Audit visible Wi-Fi networks with NetworkManager and optionally measure receive-only B210 signal energy. |
| [`nist_wlan_profile_audit.sh`](./nist_wlan_profile_audit.sh) | Check saved NetworkManager Wi-Fi profiles for open/WEP security and missing enterprise CA configuration. |
| [`nist_b210_passive_monitor.grc`](./nist_b210_passive_monitor.grc) | GNU Radio Companion GUI for live, receive-only B210 spectrum and power monitoring. |
| [`NIST_B210_GUI.md`](./NIST_B210_GUI.md) | B210 GUI prerequisites, controls, and run instructions. |
| [`engage_telco_b200.py`](./engage_telco_b200.py) | GNU Radio/UHD B200/B210 receive flowgraph that filters and records IQ samples to `usrp_filtered_output.iq`. |
| [`engage_telco_hackrf.sh`](./engage_telco_hackrf.sh) | HackRF receive utility for a spectrum sweep or IQ capture. |
| [`engage_wifi.sh`](./engage_wifi.sh) | Linux wireless-interface monitor-mode and scanning helper. |

## Requirements

Install only the dependencies for the utility you intend to run:

- **Wi-Fi profile audit and `nist_codes.py --backend nmcli`:** NetworkManager's
  `nmcli` and Python 3.
- **B210 command-line measurement or GUI:** UHD, a GNU Radio installation
  with UHD support, and an accessible USRP B210.
- **B200/B210 IQ capture script:** GNU Radio Python modules with UHD and a
  compatible USRP.
- **HackRF utility:** `hackrf_info`, `hackrf_sweep`, and `hackrf_transfer`
  from HackRF tools.
- **Wi-Fi monitor-mode helper:** `iw`, `ip`, and optionally `airodump-ng`.

The wireless scripts change interface state or capture local RF data. Review
each script before running it, run only against equipment and signals you own
or are authorized to assess, and follow applicable radio and privacy rules.
The HackRF and `engage_telco_b200.py` utilities write capture data to disk.
The NIST B210 GUI and B210 CLI energy measurement do not save IQ samples.

## Wi-Fi posture tools

List visible networks and summarize their advertised security:

```sh
python3 nist_codes.py --backend nmcli
```

Inspect stored NetworkManager wireless profiles:

```sh
bash nist_wlan_profile_audit.sh
```

The WLAN profile audit is read-only. It reports findings; it does not change
connection settings.

## B210 receive-only energy measurement

Check that UHD can see the B210:

```sh
uhd_find_devices
```

Take a bounded energy measurement at the default 2412 MHz:

```sh
python3 nist_codes.py --backend b210
```

Set frequency in MHz, sample rate in samples per second, duration in seconds,
and receive gain in dB:

```sh
python3 nist_codes.py --backend b210 \
  --frequency-mhz 2412 \
  --sample-rate 1000000 \
  --duration 0.5 \
  --gain 20
```

Use `--backend both` to run the NetworkManager scan and B210 measurement in
one invocation. The B210 CLI currently accepts 70–6000 MHz, rates up to
2 MS/s, durations up to 2 seconds, a maximum of 1,000,000 samples per
measurement, and gain values from 0 to 76 dB. Actual device capabilities may
be narrower.

## B210 GNU Radio Companion GUI

Open the flowgraph:

```sh
gnuradio-companion nist_b210_passive_monitor.grc
```

Press **Run** in GNU Radio Companion. GUI controls change center frequency,
sample rate, RX gain, and antenna port while the flowgraph is running. The
flowgraph plots the received spectrum and linear power; it does not decode
Wi-Fi frames, transmit, or write IQ files. See
[`NIST_B210_GUI.md`](./NIST_B210_GUI.md) for further details.

## Other SDR and wireless helpers

`engage_telco_b200.py` is a receive flowgraph that writes filtered IQ samples
to `usrp_filtered_output.iq`. Run it only when you intend to make and retain a
local recording:

```sh
python3 engage_telco_b200.py
```

`engage_telco_hackrf.sh` offers a HackRF sweep or receive capture. It writes
sweep output to `sweep_data.csv` or I/Q data to `raw_capture.iq`:

```sh
bash engage_telco_hackrf.sh
```

`engage_wifi.sh` changes the selected wireless interface to monitor mode and
starts a scan. It requires root privileges and may disrupt the interface's
normal network connection:

```sh
sudo bash engage_wifi.sh
```

Restore the interface to managed mode and reconnect it when finished, using
the network tools appropriate to your Linux distribution.
