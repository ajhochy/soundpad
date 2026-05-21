"""Tests for ui/piano_roll_widget.py — piano key layout and widget."""
import pytest
from ui.piano_roll_widget import compute_key_layout

# Test with a widget width that gives clean numbers:
# white_w = 580 / 29 = 20.0 exactly
WIDGET_W = 580
PIANO_H = 100


def test_returns_all_49_keys():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    # MIDI 36 (C2) to MIDI 84 (C6) inclusive
    assert len(layout) == 49
    for note in range(36, 85):
        assert note in layout


def test_white_key_count():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    white_keys = [k for k, v in layout.items() if not v['is_black']]
    assert len(white_keys) == 29


def test_black_key_count():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    black_keys = [k for k, v in layout.items() if v['is_black']]
    assert len(black_keys) == 20


def test_c2_starts_at_x_zero():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[36]['x'] == pytest.approx(0.0)


def test_white_key_width():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    expected_w = WIDGET_W / 29  # 20.0
    assert layout[36]['w'] == pytest.approx(expected_w)


def test_black_key_width_is_62_5_percent():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    white_w = WIDGET_W / 29
    expected_bw = white_w * 0.625
    assert layout[37]['w'] == pytest.approx(expected_bw)  # C#2


def test_black_key_height_is_63_5_percent():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[37]['h'] == pytest.approx(PIANO_H * 0.635)  # C#2


def test_white_key_height_equals_piano_height():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[36]['h'] == pytest.approx(float(PIANO_H))


def test_c_sharp_2_is_black():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[37]['is_black'] is True


def test_d2_is_white():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[38]['is_black'] is False


def test_c_sharp_position_neothesia_algorithm():
    # white_w=20, cde_block = 3*20/5 = 12, black_w = 12.5
    # C#2 x = 0 + 1*12 - 12.5/2 = 5.75
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[37]['x'] == pytest.approx(5.75)


def test_d_sharp_position_neothesia_algorithm():
    # D#2 x = 0 + 3*12 - 6.25 = 29.75
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[39]['x'] == pytest.approx(29.75)


def test_f_sharp_position_neothesia_algorithm():
    # F is at x=60 (3 white keys × 20), fgab_block=4*20/7
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    white_w = 20.0
    f_x = 3 * white_w
    fgab_block = 4 * white_w / 7
    black_w = white_w * 0.625
    expected_x = f_x + fgab_block - black_w / 2
    assert layout[42]['x'] == pytest.approx(expected_x)


def test_g_sharp_position_neothesia_algorithm():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    white_w = 20.0
    f_x = 3 * white_w
    fgab_block = 4 * white_w / 7
    black_w = white_w * 0.625
    expected_x = f_x + 3 * fgab_block - black_w / 2
    assert layout[44]['x'] == pytest.approx(expected_x)


def test_a_sharp_position_neothesia_algorithm():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    white_w = 20.0
    f_x = 3 * white_w
    fgab_block = 4 * white_w / 7
    black_w = white_w * 0.625
    expected_x = f_x + 5 * fgab_block - black_w / 2
    assert layout[46]['x'] == pytest.approx(expected_x)


def test_c6_is_last_key_and_white():
    layout = compute_key_layout(WIDGET_W, PIANO_H)
    assert layout[84]['is_black'] is False
    # C6 is the 29th white key, 0-indexed position 28
    white_w = WIDGET_W / 29
    assert layout[84]['x'] == pytest.approx(28 * white_w)
