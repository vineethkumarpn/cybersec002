#!/usr/bin/env bash
#
# Audits local NetworkManager wireless profiles against NIST SP 800-153 baselines.

set -euo pipefail

echo "=================================================="
echo " NIST SP 800-153 Client Wireless Profile Audit"
echo "=================================================="

if ! command -v nmcli &>/dev/null; then
    echo "Error: nmcli utility is required to inspect connection profiles." >&2
    exit 1
fi

mapfile -t WIFI_CONNS < <(nmcli -t -f UUID,TYPE connection show | awk -F: '$2=="802-11-wireless" {print $1}')

if [ ${#WIFI_CONNS[@]} -eq 0 ]; then
    echo "No stored wireless profiles found."
    exit 0
fi

findings=0

for uuid in "${WIFI_CONNS[@]}"; do
    name=$(nmcli -t -f connection.id connection show "$uuid" | cut -d: -f2)
    key_mgmt=$(nmcli -t -f 802-11-wireless-security.key-mgmt connection show "$uuid" | cut -d: -f2)
    autoconnect=$(nmcli -t -f connection.autoconnect connection show "$uuid" | cut -d: -f2)

    echo ""
    echo "Checking Profile: '$name' (UUID: $uuid)"

    if [[ -z "$key_mgmt" || "$key_mgmt" == "none" ]]; then
        echo "  [FAIL] Open / Unencrypted network profile detected."
        findings=$((findings + 1))
    elif [[ "$key_mgmt" =~ "wep" ]]; then
        echo "  [FAIL] Legacy WEP encryption detected (prohibited by NIST 800-153)."
        findings=$((findings + 1))
    else
        echo "  [PASS] Key management: $key_mgmt"
    fi

    if [[ "$autoconnect" == "yes" && ( -z "$key_mgmt" || "$key_mgmt" == "none" ) ]]; then
        echo "  [FAIL] Autoconnect is ENABLED on an unencrypted profile."
        findings=$((findings + 1))
    fi

    if [[ "$key_mgmt" =~ "802-1x" || "$key_mgmt" =~ "wpa-eap" ]]; then
        ca_cert=$(nmcli -t -f 802-1x.ca-cert connection show "$uuid" | cut -d: -f2)
        if [[ -z "$ca_cert" ]]; then
            echo "  [WARNING] Enterprise connection lacks server CA validation."
            findings=$((findings + 1))
        fi
    fi
done

echo ""
echo "=================================================="
echo "Audit complete: $findings issue(s) identified."
echo "=================================================="
