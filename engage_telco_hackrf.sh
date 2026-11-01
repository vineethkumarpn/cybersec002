#!/bin/bash

# Ensure hackrf utilities are installed
if ! command -v hackrf_info &> /dev/null; then
    echo "[-] hackrf-tools package is not installed."
    echo "[*] Install it via: sudo apt install hackrf" # Debian/Ubuntu/BlackArch
    exit 1
fi

# Function to verify hardware connection and operational status
check_sdr_hardware() {
    echo "[+] Checking for connected HackRF devices..."
    if hackrf_info; then
        echo "[+] HackRF hardware detected and initialized successfully."
        return 0
    else
        echo "[-] No HackRF device found. Check your USB connection."
        return 1
    fi
}

# Function to perform a sweep across a specific frequency spectrum
# This tracks signal power levels over time without decoding them (Passive Energy Detection)
passive_spectrum_sweep() {
    local freq_min=$1   # e.g., 2400 (in MHz)
    local freq_max=$2   # e.g., 2480 (in MHz)
    local output_file="sweep_data.csv"

    if [ -z "$freq_min" ] || [ -z "$freq_max" ]; then
        echo "[-] Error: Please define a frequency range (Min and Max in MHz)."
        return 1
    fi

    echo "[+] Starting passive spectrum sweep between ${freq_min}MHz and ${freq_max}MHz..."
    echo "[+] Saving raw FFT bin data to $output_file. Press Ctrl+C to stop."
    
    # hackrf_sweep steps through frequencies rapidly to map out energy density
    hackrf_sweep -f "$freq_min:$freq_max" -w 1000000 > "$output_file"
}

# Function to record raw RF data (I/Q samples) from a targeted channel for offline analysis
passive_signal_capture() {
    local target_freq=$1 # Frequency in Hz (e.g., 915000000 for 915 MHz ISM)
    local sample_rate="10000000" # 10 Msps (Mega-samples per second)
    local capture_file="raw_capture.iq"

    if [ -z "$target_freq" ]; then
        echo "[-] Error: Please specify a target center frequency in Hz."
        return 1
    fi

    echo "[+] Preparing to capture passive I/Q data at $(($target_freq / 1000000)) MHz..."
    echo "[+] Sampling Rate: $(($sample_rate / 1000000)) Msps"
    echo "[+] Recording to '$capture_file'. Press Ctrl+C when finished."
    
    # hackrf_transfer records raw radio data into a binary file
    # -r: receive file path, -f: frequency in Hz, -s: sample rate, -g: VGA gain (0-62)
    hackrf_transfer -r "$capture_file" -f "$target_freq" -s "$sample_rate" -g 16
}

# --- Execution Workflow ---
if check_sdr_hardware; then
    echo "============================================="
    echo "Select an option:"
    echo "1) Run rapid Spectrum Sweep (e.g., 2.4GHz Wi-Fi band)"
    echo "2) Capture raw I/Q samples on a specific frequency"
    read -p "Choice [1-2]: " CHOICE

    case $CHOICE in
        1)
            # Sweep the standard 2.4GHz ISM band space
            passive_spectrum_sweep 2400 2483
            ;;
        2)
            # Example: Tune into a 915 MHz ISM band channel
            passive_signal_capture 915000000
            ;;
        *)
            echo "[-] Invalid option chosen."
            ;;
    esac
fi

