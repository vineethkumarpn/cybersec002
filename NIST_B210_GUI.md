# GNU Radio Companion B210 monitor

`nist_b210_passive_monitor.grc` is a receive-only GNU Radio Companion flowgraph for a USRP B210. It displays the received spectrum and instantaneous linear power; it does not decode Wi-Fi frames, transmit, or write IQ samples.

## Requirements

- GNU Radio Companion with the UHD blocks and Python bindings installed.
- UHD drivers and a connected, accessible USRP B210.

Check that UHD detects the radio before starting the flowgraph:

```sh
uhd_find_devices
```

## Run

From this directory, open the flowgraph:

```sh
gnuradio-companion nist_b210_passive_monitor.grc
```

In GNU Radio Companion, press **Run**. Use the GUI controls to adjust:

- Center frequency: 70 MHz to 6 GHz, in 1 MHz steps.
- Sample rate: 1 to 2 MS/s, in 100 kS/s steps.
- Receive gain: 0 to 76 dB.
- RX antenna port: RX2, TX/RX, or RX1.

The spectrum and power plots update while the flowgraph runs. UHD may reject a frequency, sample rate, gain, or antenna that is not supported by the attached device or its current configuration; check the GNU Radio console for the reported error.

The existing command-line scanner remains available separately:

```sh
python3 nist_codes.py --backend nmcli
python3 nist_codes.py --backend b210
```

The B210 command reports bounded mean/peak power statistics; the Companion flowgraph is for live GUI monitoring.
