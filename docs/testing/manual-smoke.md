# Manual smoke — Practice Mode v1

Run on the Ubuntu target (`aj@192.168.0.50`, desktop account `kids`) after `bash install.sh aj@192.168.0.50 kids`.

## Pre-flight

- [ ] Launchkey MK3 49 is plugged in and showing up in `aconnect -l`.
- [ ] At least one `.sf2` soundfont is installed in `/usr/share/sounds/sf2/`.
- [ ] `python3 soundpad.py` launches without errors; main window appears.
- [ ] Existing pad/knob/fader bindings still work (toggle a pad on, hear sound).

## Practice Mode entry

- [ ] 🎹 Practice button is visible in the main window, between pad grid and master bar.
- [ ] Clicking it opens a separate window titled "SoundPad — Practice 🎹".
- [ ] Closing and re-clicking re-shows the same window (instance is reused).

## Toolbar

- [ ] 📂 Open prompts for a `.mid` file.
- [ ] Loading a known file shows note bars scrolling above the piano on ▶ Play.
- [ ] Speed slider moves 25–150; label updates live with the value.
- [ ] Mode combo has "Waiting" and "Free".
- [ ] 🔇 Mute toggle suppresses audio but visuals continue.

## Free mode

- [ ] Plays at 100% by default; notes hit the line in sync with audio.
- [ ] Speed 50% plays at half speed (audio + visual both slow).
- [ ] ⏹ Stop resets the clock and clears all lit keys.

## Waiting mode

- [ ] Loaded song pauses on the first note; the required key lights up amber.
- [ ] Pressing the correct key on the Launchkey resumes playback (key flashes green).
- [ ] Pressing a wrong key flashes the wrong key red for ~200ms; clock stays paused.
- [ ] Chord (two simultaneous notes) requires both to be pressed before resuming.

## Audio integration

- [ ] Practice channel (15) sounds correct (Grand Piano).
- [ ] Existing pad sounds (channels 0–7) still play simultaneously and aren't disturbed by practice playback.
- [ ] Closing the Practice window does not crash or silence the rest of the app.

## Regression

- [ ] Main pad grid still toggles via physical pads.
- [ ] Knob → pad volume still updates.
- [ ] Fader → master volume still updates.
- [ ] Settings dialog still opens.
- [ ] Scene save/load still works.
