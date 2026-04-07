#!/bin/bash
# download_soundfonts.sh — download free soundfont packs into /usr/share/sounds/sf2/
#
# Run as:  sudo bash download_soundfonts.sh
#
# Downloads are non-fatal: a failed download prints a warning and the script
# continues. The app works with whatever soundfonts are already installed
# (fluid-soundfont-gm from apt is enough to get started).

set -e

SF_DIR="/usr/share/sounds/sf2"
mkdir -p "$SF_DIR"

_dl() {
    local name="$1"
    local url="$2"
    local dest="$SF_DIR/$3"
    if [[ -f "$dest" ]]; then
        echo "  already exists, skipping: $3"
        return
    fi
    echo "  Downloading $name..."
    if wget -q --timeout=30 --tries=2 -O "$dest" "$url"; then
        echo "  ✓ $name"
    else
        rm -f "$dest" 2>/dev/null || true
        echo "  ✗ $name — download failed (skipping)"
    fi
}

echo "==> Downloading soundfonts to $SF_DIR ..."

_dl "TimGM6mb" \
    "https://github.com/musescore/MuseScore/raw/master/share/sound/TimGM6mb.sf2" \
    "TimGM6mb.sf2"

_dl "Arachno SoundFont 1.0" \
    "https://www.arachnosoft.com/main/soundfont/Arachno%20SoundFont%20-%20Version%201.0.sf2" \
    "Arachno SoundFont - Version 1.0.sf2"

_dl "SGM-v2.01" \
    "https://archive.org/download/SGM-V2.01/SGM-v2.01-NicePianosGuitarsBass-V1.2.sf2" \
    "SGM-v2.01-NicePianosGuitarsBass-V1.2.sf2"

_dl "Timbres of Heaven 4.0" \
    "https://hammersound.com/TimbreSound/Timbres%20of%20Heaven%20(XGM)%204.00(G).sf2" \
    "Timbres of Heaven (XGM) 4.00(G).sf2"

_dl "OPL-3 FM 128M" \
    "https://archive.org/download/opl3_fm_sf2/OPL-3_FM_128M.sf2" \
    "OPL-3_FM_128M.sf2"

echo ""
echo "Done. Soundfonts in $SF_DIR:"
ls "$SF_DIR"/*.sf2 2>/dev/null | xargs -I{} basename {} || echo "  (none)"
