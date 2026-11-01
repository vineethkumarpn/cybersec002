#!/bin/bash

# Ensure the script is run with root privileges
if [ "$EUID" -ne 0 ]; then
    echo "[-] Please run this script as root (sudo)."
    exit 1
fi

# Function to list available wireless interfaces
list_interfaces() {
    echo "[+] Available Wireless Interfaces:"
    iw dev | grep Interface | awk '{print $2}'
}

# Function to enable monitor mode safely
enable_monitor_mode() {
    local interface=$1
    if [ -z "$interface" ]; then
        echo "[-] No interface specified."
        return 1
    fi

    echo "[+] Bringing $interface down..."
    ip link set "$interface" down
    
    echo "[+] Setting $interface to monitor mode..."
    iw dev "$interface" set type monitor
    
    echo "[+] Bringing $interface up..."
    ip link set "$interface" up
    
    echo "[+] Interface $interface is now in monitor mode."
}

# Function to execute a passive scan using standard tools
passive_scan() {
    local interface=$1
    if [ -z "$interface" ]; then
        echo "[-] Monitor interface required for scanning."
        return 1
    fi

    echo "[+] Starting passive Wi-Fi scan on $interface..."
    echo "[+] Press Ctrl+C to stop scanning."
    
    # Check if airodump-ng is available from the suite
    if command -v airodump-ng &> /dev/null; then
        airodump-ng "$interface"
    else
        # Fallback to standard iw scanner if specific suites aren't installed
        echo "[-] airodump-ng not found. Falling back to basic iw station scan..."
        # Note: 'iw dev scan' works best in managed mode, but provides a basic alternative
        iw dev "$interface" scan | grep -E "BSS|SSID|DS\ Parameter"
    fi
}

# --- Main Execution Flow (Example Usage) ---
# 1. Show interfaces
list_interfaces

# 2. Prompt user for target interface selection
read -p "Enter the interface name to use (e.g., wlan0): " TARGET_IFACE

# 3. Enable monitor mode and scan
if [ -n "$TARGET_IFACE" ]; then
    enable_monitor_mode "$TARGET_IFACE"
    passive_scan "$TARGET_IFACE"
fi

