#!/usr/bin/env python3
import sys
import signal
from gnuradio import gr
from gnuradio import blocks
from gnuradio import uhd
from gnuradio import filter as gr_filter
import pmt

class USRPPassiveMonitor(gr.top_block):
    def __init__(self, center_freq=2412000000, sample_rate=10000000):
        gr.top_block.__init__(self, "USRP Passive Monitor")

        # --- Parameters ---
        self.center_freq = center_freq
        self.sample_rate = sample_rate

        # --- Blocks ---
        # 1. UHD USRP Source Block (Configures the B210 Front-End)
        self.uhd_usrp_source = uhd.usrp_source(
            ",".join(("", "")),
            uhd.stream_args(
                cpu_format="fc32", # Complex 32-bit floating point (I/Q)
                channels=list(range(1)),
            ),
        )
        
        # Configure RF parameters on Channel 0
        self.uhd_usrp_source.set_samp_rate(self.sample_rate)
        self.uhd_usrp_source.set_center_freq(self.center_freq, 0)
        self.uhd_usrp_source.set_gain(40, 0) # Adjust RX gain based on noise floor
        self.uhd_usrp_source.set_antenna("RX2", 0) # Select primary receive port

        # 2. Low Pass Filter (Isolates the target channel channel, drops out-of-band noise)
        self.lp_filter = gr_filter.fir_filter_ccf(
            1, # Decimation rate
            gr_filter.firdes.low_pass(
                1.0,               # Gain
                self.sample_rate,  # Input sample rate
                2000000,           # Cut-off frequency (e.g., 2 MHz)
                500000,            # Transition width
                gr_filter.firdes.WIN_HAMMING
            )
        )

        # 3. File Sink (Saves the filtered complex samples for offline software processing)
        self.file_sink = blocks.file_sink(gr.sizeof_gr_complex*1, "usrp_filtered_output.iq", False)
        self.file_sink.set_unbuffered(False)

        # --- Connections ---
        # USRP B210 Output -> Low Pass Filter -> Binary IQ File
        self.connect((self.uhd_usrp_source, 0), (self.lp_filter, 0))
        self.connect((self.lp_filter, 0), (self.file_sink, 0))

    def stop_capture(self):
        self.file_sink.close()

if __name__ == '__main__':
    # Default target: 2.412 GHz (Wi-Fi Channel 1) at 10 Mega-samples per second
    print("[+] Initializing GNU Radio Pipeline for USRP B210...")
    tb = USRPPassiveMonitor(center_freq=2412000000, sample_rate=10000000)

    def handle_shutdown(sig, frame):
        print("\n[-] Shutting down flowgraph and saving remaining samples...")
        tb.stop()
        tb.wait()
        tb.stop_capture()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    
    print(f"[+] Flowgraph running. Capturing passive I/Q data at {tb.center_freq / 1e6} MHz.")
    print("[+] Output logging to 'usrp_filtered_output.iq'. Press Ctrl+C to terminate.")
    tb.start()
    
    # Keep the main thread alive while GNU Radio processes streams asynchronously
    signal.pause()

