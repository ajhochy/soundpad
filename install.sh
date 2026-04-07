#!/bin/bash
# install.sh — deploy SoundPad to a target Ubuntu machine
#
# Usage:
#   bash install.sh [user@host] [desktop-user]
#
# Examples:
#   bash install.sh aj@192.168.0.50 kids    # deploy to kids account on remote machine
#   bash install.sh pi@raspberrypi.local pi # Raspberry Pi
#
# Requirements on this machine: ssh, rsync
# Requirements on target:       Ubuntu 22.04+, PipeWire with PulseAudio support
#
# The script will prompt for sudo password on the target machine.
# SSH key auth is recommended — set up with: ssh-copy-id user@host

set -e

# --------------------------------------------------------------------------
# Configuration — override via arguments or environment variables
# --------------------------------------------------------------------------

TARGET_HOST="${1:-${SOUNDPAD_HOST:-}}"
DESKTOP_USER="${2:-${SOUNDPAD_USER:-}}"

if [[ -z "$TARGET_HOST" ]]; then
    echo "Usage: bash install.sh user@host [desktop-user]"
    echo ""
    echo "  user@host     SSH target (e.g. aj@192.168.0.50)"
    echo "  desktop-user  Linux user who will run SoundPad (default: same as SSH user)"
    echo ""
    echo "  Or set SOUNDPAD_HOST and SOUNDPAD_USER environment variables."
    exit 1
fi

# If no desktop user specified, use the SSH user
if [[ -z "$DESKTOP_USER" ]]; then
    DESKTOP_USER="${TARGET_HOST%@*}"
    # If TARGET_HOST has no @, use it directly
    [[ "$DESKTOP_USER" == "$TARGET_HOST" ]] && DESKTOP_USER="$USER"
fi

TARGET_DIR="/opt/soundpad"
AUTOSTART_DIR="/home/$DESKTOP_USER/.config/autostart"
APP_DIR="/home/$DESKTOP_USER/.local/share/applications"

SSH_OPTS="-o StrictHostKeyChecking=no -o BatchMode=no"

_ssh() { ssh $SSH_OPTS "$TARGET_HOST" "$@"; }

# Try passwordless sudo first, fall back to prompting
_sudo() {
    _ssh "sudo -n $* 2>/dev/null || sudo $*"
}

echo ""
echo "========================================="
echo "  SoundPad Installer"
echo "========================================="
echo "  Target host   : $TARGET_HOST"
echo "  Desktop user  : $DESKTOP_USER"
echo "  Install dir   : $TARGET_DIR"
echo "========================================="
echo ""

# --------------------------------------------------------------------------
# 1. Copy app files
# --------------------------------------------------------------------------

echo "==> Copying app files..."
_sudo "mkdir -p $TARGET_DIR"
rsync -av -e "ssh $SSH_OPTS" \
    --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.venv' --exclude='venv' --exclude='install.sh' \
    --exclude='.claude' --exclude='.DS_Store' --exclude='*.md' \
    ./ "$TARGET_HOST:/tmp/soundpad_src/"
_sudo "cp -r /tmp/soundpad_src/. $TARGET_DIR/ && rm -rf /tmp/soundpad_src"

# --------------------------------------------------------------------------
# 2. Install system dependencies
# --------------------------------------------------------------------------

echo "==> Installing system dependencies..."
_sudo "apt-get update -qq"
_sudo "apt-get install -y \
    python3-pyqt5 python3-pip libfluidsynth-dev \
    fluid-soundfont-gm fluid-soundfont-gs \
    fonts-noto fonts-noto-color-emoji \
    wget curl"

# --------------------------------------------------------------------------
# 3. Python venv + packages
# --------------------------------------------------------------------------

echo "==> Setting up Python environment..."
_sudo "python3 -m venv $TARGET_DIR/venv"
_sudo "$TARGET_DIR/venv/bin/pip install --quiet pyFluidSynth python-rtmidi PyQt5"

# --------------------------------------------------------------------------
# 4. Download soundfonts
# --------------------------------------------------------------------------

echo "==> Downloading soundfonts..."
SF_DIR="/usr/share/sounds/sf2"
_sudo "mkdir -p $SF_DIR"

_dl() {
    local name="$1"
    local url="$2"
    local dest="$SF_DIR/$3"
    echo "  Downloading $name..."
    if _sudo "wget -q --timeout=30 --tries=2 -O '$dest' '$url' 2>&1"; then
        echo "  ✓ $name"
    else
        _sudo "rm -f '$dest'" 2>/dev/null || true
        echo "  ✗ $name — download failed (skipping, app will work without it)"
    fi
}

# TimGM6mb — reliable GitHub release
_dl "TimGM6mb" \
    "https://github.com/musescore/MuseScore/raw/master/share/sound/TimGM6mb.sf2" \
    "TimGM6mb.sf2"

# Arachno SoundFont — arachnosoft.com
_dl "Arachno SoundFont 1.0" \
    "https://www.arachnosoft.com/main/soundfont/Arachno%20SoundFont%20-%20Version%201.0.sf2" \
    "Arachno SoundFont - Version 1.0.sf2"

# SGM-v2.01
_dl "SGM-v2.01" \
    "https://archive.org/download/SGM-V2.01/SGM-v2.01-NicePianosGuitarsBass-V1.2.sf2" \
    "SGM-v2.01-NicePianosGuitarsBass-V1.2.sf2"

# Timbres of Heaven
_dl "Timbres of Heaven 4.0" \
    "https://hammersound.com/TimbreSound/Timbres%20of%20Heaven%20(XGM)%204.00(G).sf2" \
    "Timbres of Heaven (XGM) 4.00(G).sf2"

# OPL-3 FM
_dl "OPL-3 FM 128M" \
    "https://archive.org/download/opl3_fm_sf2/OPL-3_FM_128M.sf2" \
    "OPL-3_FM_128M.sf2"

echo "  (fluid-soundfont-gm and fluid-soundfont-gs already installed via apt)"

# --------------------------------------------------------------------------
# 5. Autostart entry
# --------------------------------------------------------------------------

echo "==> Setting up autostart for $DESKTOP_USER..."
_sudo "mkdir -p $AUTOSTART_DIR"
_ssh "echo celrew | sudo -S tee $AUTOSTART_DIR/soundpad.desktop > /dev/null" << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=SoundPad
Exec=/opt/soundpad/venv/bin/python3 /opt/soundpad/soundpad.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
DESKTOP
_sudo "chown -R $DESKTOP_USER:$DESKTOP_USER $AUTOSTART_DIR"

# --------------------------------------------------------------------------
# 6. App launcher (dock/app-grid icon)
# --------------------------------------------------------------------------

echo "==> Installing app launcher icon..."
_sudo "mkdir -p $APP_DIR"
_ssh "sudo tee $APP_DIR/soundpad.desktop > /dev/null" << 'DESKTOP'
[Desktop Entry]
Type=Application
Name=SoundPad
Comment=Play sounds with your MIDI keyboard
Exec=/opt/soundpad/venv/bin/python3 /opt/soundpad/soundpad.py
Icon=audio-x-generic
Terminal=false
Categories=Audio;Music;Education;
StartupNotify=true
DESKTOP
_sudo "chown -R $DESKTOP_USER:$DESKTOP_USER $APP_DIR"
_sudo "chmod -R 755 $TARGET_DIR"

# --------------------------------------------------------------------------
# Done
# --------------------------------------------------------------------------

echo ""
echo "========================================="
echo "  ✓ SoundPad installed!"
echo "========================================="
echo ""
echo "  SoundPad will auto-launch next time $DESKTOP_USER logs in."
echo ""
echo "  To launch manually now, SSH in and run:"
echo "    sudo -u $DESKTOP_USER DISPLAY=:0 WAYLAND_DISPLAY=wayland-0 \\"
echo "      XDG_RUNTIME_DIR=/run/user/\$(id -u $DESKTOP_USER) \\"
echo "      $TARGET_DIR/venv/bin/python3 $TARGET_DIR/soundpad.py"
echo ""
echo "  Startup log: /tmp/soundpad.log"
echo ""
