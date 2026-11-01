1 #!/usr/bin/env bash
    2 #
    3 # nist_wlan_profile_audit.sh
    4 # Audits local NetworkManager wireless profiles against NIST SP 800-153 baselines.
    5 #
    6
    7 set -euo pipefail
    8
    9 echo "=================================================="
   10 echo " NIST SP 800-153 Client Wireless Profile Audit"
   11 echo "=================================================="
   12
   13 # Check if NetworkManager CLI is available
   14 if ! command -v nmcli &>/dev/null; then
   15     echo "Error: nmcli utility is required to inspect connection profiles." >&2
   16     exit 1
   17 fi
   18
   19 # Retrieve all stored Wi-Fi connection UUIDs
   20 mapfile -t WIFI_CONNS < <(nmcli -t -f UUID,TYPE connection show | awk -F: '$2=="802-11-wireless" {print $1}')
   21
   22 if [ ${#WIFI_CONNS[@]} -eq 0 ]; then
   23     echo "No stored wireless profiles found."
   24     exit 0
   25 fi
   26
   27 findings=0
   28
   29 for uuid in "${WIFI_CONNS[@]}"; do
   30     name=$(nmcli -t -f connection.id connection show "$uuid" | cut -d: -f2)
   31     key_mgmt=$(nmcli -t -f 802-11-wireless-security.key-mgmt connection show "$uuid" | cut -d: -f2)
   32     autoconnect=$(nmcli -t -f connection.autoconnect connection show "$uuid" | cut -d: -f2)
   33
   34     echo ""
   35     echo "Checking Profile: '$name' (UUID: $uuid)"
   36
   37     # Guideline: Eliminate unencrypted wireless networks
   38     if [[ -z "$key_mgmt" || "$key_mgmt" == "none" ]]; then
   39         echo "  [FAIL] Open / Unencrypted network profile detected."
   40         ((findings++))
   41     elif [[ "$key_mgmt" =~ "wep" ]]; then
   42         echo "  [FAIL] Legacy WEP encryption detected (prohibited by NIST 800-153)."
   43         ((findings++))
   44     else
   45         echo "  [PASS] Key management: $key_mgmt"
   46     fi
   47
   48     # Guideline: Prevent automatic connection to open/untrusted profiles
   49     if [[ "$autoconnect" == "yes" && ( -z "$key_mgmt" || "$key_mgmt" == "none" ) ]]; then
   50         echo "  [FAIL] Autoconnect is ENABLED on an unencrypted profile."
   51         ((findings++))
   52     fi
   53
   54     # Guideline: Verify enterprise certificate settings if 802.1X is used
   55     if [[ "$key_mgmt" =~ "802-1x" || "$key_mgmt" =~ "wpa-eap" ]]; then
   56         ca_cert=$(nmcli -t -f 802-1x.ca-cert connection show "$uuid" | cut -d: -f2)
   57         if [[ -z "$ca_cert" ]]; then
   58             echo "  [WARNING] Enterprise connection lacks server CA validation."
   59             ((findings++))
   60         fi
   61     fi
   62 done
   63
   64 echo ""
   65 echo "=================================================="
   66 echo "Audit complete: $findings issue(s) identified."
   67 echo "=================================================="

  ---

  2. Passive WLAN Posture & Rogue AP Inspector (Python)

  NIST SP 800-153 Section 4 recommends regular monitoring of the local radio frequency space to detect unauthorized (rogue) APs and networks operating without mandatory encryption
  baselines (such as WPA2-AES / WPA3).

  This Python script queries the existing wireless device passively and summarizes visible broadcast beacons to highlight non-compliant access points.

     1 #!/usr/bin/env python3
     2 """
     3 nist_wlan_posture_scanner.py
     4 Passive wireless environment scanner adhering to NIST SP 800-153 monitoring guidelines.
     5 Uses standard administrative tools to audit visible access points.
     6 """
     7
     8 import subprocess
     9 import shutil
    10 import sys
    11 import csv
    12 import io
    13
    14 def check_requirements():
    15     if not shutil.which("nmcli"):
    16         print("Error: 'nmcli' binary not found. This script requires NetworkManager.", file=sys.stderr)
    17         sys.exit(1)
    18
    19 def scan_wireless_environment():
    20     """
    21     Triggers a passive Wi-Fi scan and returns the parsed list of visible access points.
    22     """
    23     # Uses standard passive scan command: nmcli -t -f BSSID,SSID,CHAN,FREQ,SIGNAL,SECURITY dev wifi list
    24     cmd = ["nmcli", "-t", "-f", "BSSID,SSID,CHAN,FREQ,SIGNAL,SECURITY", "dev", "wifi", "list"]
    25     
    26     try:
    27         result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    28     except subprocess.CalledProcessError as e:
    29         print(f"Error querying wireless interfaces: {e.stderr}", file=sys.stderr)
    30         sys.exit(1)
    31
    32     reader = csv.reader(io.StringIO(result.stdout), delimiter=":")
    33     aps = []
    34
    35     for row in reader:
    36         # BSSID contains colons, standard split might create >6 elements
    37         if len(row) < 6:
    38             continue
    39         
    40         bssid = ":".join(row[:-5])
    41         ssid = row[-5]
    42         chan = row[-4]
    43         freq = row[-3]
    44         signal = row[-2]
    45         security = row[-1]
    46
    47         aps.append({
    48             "bssid": bssid,
    49             "ssid": ssid if ssid else "<Hidden SSID>",
    50             "channel": chan,
    51             "freq": freq,
    52             "signal": signal,
    53             "security": security if security else "OPEN"
    54         })
    55
    56     return aps
    57
    58 def evaluate_compliance(ap_list):
    59     """
    60     Evaluates discovered APs against NIST SP 800-153 security requirements:
    61     - No unencrypted networks;
    62     - No deprecated cryptographic suites (WEP, WPA1/TKIP);
    63     - Flagging hidden SSIDs or non-WPA2/WPA3 endpoints;
    64     """
    65     print(f"\nDiscovered {len(ap_list)} visible Access Points.\n")
    66     print(f"{'BSSID':<20} {'SSID':<25} {'CHAN':<6} {'SIGNAL':<8} {'STATUS':<10} {'DETAILS'}")
    67     print("-" * 90)
    68
    69     findings = 0
    70
    71     for ap in ap_list:
    72         sec = ap["security"].upper()
    73         status = "COMPLIANT"
    74         details = sec
    75
    76         if sec == "OPEN":
    77             status = "FAIL"
    78             details = "Unencrypted network (No authentication/encryption)"
    79             findings += 1
    80         elif "WEP" in sec:
    81             status = "FAIL"
    82             details = "Legacy WEP cipher (Deprecated by NIST)"
    83             findings += 1
    84         elif "WPA1" in sec or "TKIP" in sec:
    85             status = "WARNING"
    86             details = "Weak encryption / TKIP suite"
    87             findings += 1
    88         elif "WPA2" in sec or "WPA3" in sec:
    89             status = "PASS"
    90             details = sec
    91         else:
    92             status = "UNKNOWN"
    93
    94         print(f"{ap['bssid']:<20} {ap['ssid'][:24]:<25} {ap['channel']:<6} {ap['signal']:<8} {status:<10} {details}")
    95
    96     print("-" * 90)
    97     print(f"Total non-compliant or warning APs observed: {findings}\n")
    98
    99 if __name__ == "__main__":
   100     check_requirements()
   101     access_points = scan_wireless_environment()
   102     evaluate_compliance(access_points)