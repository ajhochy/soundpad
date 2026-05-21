"""Tests for core/note_matcher.py — Linthesia waiting-mode logic port."""
import pytest
from core.note_matcher import MatchResult, NOTE_WINDOW_LENGTH_MS, check, all_required_pressed


def test_hit_when_note_in_required():
    assert check(60, {60}) == MatchResult.HIT


def test_hit_one_of_chord():
    # Pressing one note of a two-note chord is still a HIT for that note
    assert check(60, {60, 64}) == MatchResult.HIT


def test_miss_when_wrong_note():
    assert check(61, {60}) == MatchResult.MISS


def test_miss_wrong_note_in_chord():
    assert check(59, {60, 64}) == MatchResult.MISS


def test_not_yet_when_no_required_notes():
    assert check(60, set()) == MatchResult.NOT_YET


def test_not_yet_empty_required():
    assert check(0, set()) == MatchResult.NOT_YET


def test_all_required_pressed_single_note():
    assert all_required_pressed({60}, {60}) is True


def test_all_required_pressed_chord_complete():
    assert all_required_pressed({60, 64, 67}, {60, 64, 67}) is True


def test_all_required_pressed_chord_incomplete():
    assert all_required_pressed({60}, {60, 64}) is False


def test_all_required_pressed_superset():
    # Extra pressed notes are fine — the chord is still satisfied
    assert all_required_pressed({60, 64, 67, 72}, {60, 64, 67}) is True


def test_all_required_pressed_empty_required():
    assert all_required_pressed({60}, set()) is True


def test_note_window_length_is_400ms():
    assert NOTE_WINDOW_LENGTH_MS == 400
