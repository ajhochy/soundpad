"""
conftest.py — pytest fixtures shared across the test suite.

pytest-qt provides the `qtbot` fixture automatically once installed.
QApplication is created automatically by pytest-qt for widget tests.
This file exists to mark tests/ as a package and to document that
no manual QApplication setup is needed.
"""
