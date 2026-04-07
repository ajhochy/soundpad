#!/bin/bash
# install.sh — deploy SoundPad to the target Ubuntu machine
# Run as: sudo bash install.sh
# Run this from your Mac: bash install.sh
#
# What it does:
#   1. Copies the app to /opt/soundpad/ on 192.168.0.50
#   2. Installs Python dependencies
#   3. Sets up the autostart entry for the kids account

set -e

TARGET_HOST="aj@192.168.0.50"
TARGET_DIR="/opt/soundpad"
AUTOSTART_DIR="/home/kids/.config/autostart"

echo "==> Copying app files..."
ssh "$TARGET_HOST" "sudo mkdir -p $TARGET_DIR"
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.venv' --exclude='install.sh' \
  ./ "$TARGET_HOST:/tmp/soundpad_src/"
ssh "$TARGET_HOST" "sudo cp -r /tmp/soundpad_src/. $TARGET_DIR/"

echo "==> Installing Python dependencies..."
ssh "$TARGET_HOST" "sudo apt-get install -y python3-pyqt5 python3-pip libfluidsynth-dev fluid-soundfont-gm"
ssh "$TARGET_HOST" "sudo python3 -m venv /opt/soundpad/venv"
ssh "$TARGET_HOST" "sudo /opt/soundpad/venv/bin/pip install pyFluidSynth python-rtmidi PyQt5"

echo "==> Setting up autostart for kids account..."
ssh "$TARGET_HOST" "sudo mkdir -p $AUTOSTART_DIR"
ssh "$TARGET_HOST" "sudo tee $AUTOSTART_DIR/soundpad.desktop > /dev/null << 'EOF'
[Desktop Entry]
Type=Application
Name=SoundPad
Exec=pw-jack /opt/soundpad/venv/bin/python3 /opt/soundpad/soundpad.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF"
ssh "$TARGET_HOST" "sudo chown -R kids:kids $AUTOSTART_DIR"
ssh "$TARGET_HOST" "sudo chmod -R 755 $TARGET_DIR"

echo ""
echo "✓ SoundPad installed. It will auto-launch next time kids logs in."
echo "  To test now: ssh into the machine and run:"
echo "  sudo -u kids pw-jack /opt/soundpad/venv/bin/python3 /opt/soundpad/soundpad.py"
