# Architecture

## App summary

SoundPad is a PyQt5 desktop pad launcher for the Novation Launchkey MK3 49.
FluidSynth (via pyFluidSynth + PulseAudio/PipeWire) renders audio for 8 pads.
Practice Mode (in progress) adds a separate `QMainWindow` for Midiano-style MIDI song learning on the keyboard half of the device.

## Data flow

### Pad mode (existing)
```
Launchkey pad → rtmidi callback → MidiHandler._on_midi_message
                                       │
                                       ▼
                          MidiSignals.pad_toggled.emit(idx)
                                       │
                                       ▼
                          MainWindow._on_pad_toggle
                                       │
                                       ▼
                          SynthEngine.toggle_pad → FluidSynth channel `idx`
```

### Practice mode (new)
```
QTimer (16ms)  →  MidiFilePlayer._tick  →  playback_tick/waiting_for/note_on/off signals
                                                       │
                                                       ▼
                                          PracticeWindow._on_tick / _on_waiting_for
                                                       │
                                       ┌───────────────┼───────────────┐
                                       ▼               ▼               ▼
                            PianoRollWidget    SynthEngine.practice_note_on (ch 15)
                            .set_state(...)

Launchkey key → rtmidi → MidiHandler → MidiSignals.key_pressed → PracticeWindow → MidiFilePlayer.note_pressed
                                                                                          │
                                                                                          ▼
                                                                                  NoteMatcher.check → HIT/MISS/NOT_YET
```

## Major boundaries

- **`core/`** is Qt-free for pure logic modules: `config`, `note_matcher`, parsing half of `midi_file_player`. Other `core/` modules use PyQt5 signals for thread-safe communication with the UI.
- **`ui/`** depends on `core/` but never the reverse.
- **MIDI thread** (rtmidi callback) emits Qt signals only; never touches widgets directly.
- **FluidSynth**: channel allocation — pads use 0–7, practice mode reserves channel 15.

## External / local deps

| Dep | Purpose | Local mac dev | Linux target |
|---|---|---|---|
| PyQt5 | UI | pip in venv | `python3-pyqt5` apt |
| pyFluidSynth | Audio | pip + brew `fluid-synth` (DYLD_LIBRARY_PATH) | `libfluidsynth3` apt |
| python-rtmidi | MIDI input | pip wheel | apt or pip |
| mido | MIDI file parsing (Practice Mode) | pip | pip |
| pytest, pytest-qt | tests | pip | pip |
