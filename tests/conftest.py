"""
conftest.py — pytest fixtures shared across the test suite.

pytest-qt provides the `qtbot` fixture automatically once installed.
QApplication is created automatically by pytest-qt for widget tests.
This file exists to mark tests/ as a package and to document that
no manual QApplication setup is needed.

Qt platform selection
----------------------
The Linux target box runs the headless suite under
``QT_QPA_PLATFORM=offscreen`` (the documented command in
``docs/ai/testing-guide.md``). On macOS dev boxes, however, the Qt
``offscreen`` plugin segfaults (Bus error) when a ``QMainWindow`` is
shown or grabbed — this hits the PracticeWindow screenshot/open smoke
tests. It is a Qt-on-macOS platform bug, not a SoundPad defect: the
exact same tests pass cleanly under the ``minimal`` platform.

To keep the suite runnable on both platforms with identical logic
coverage, on macOS we transparently fall back from ``offscreen`` to
``minimal`` before any QApplication is created. Linux is left
untouched so the target box keeps using ``offscreen`` as documented.
Set ``SOUNDPAD_KEEP_QT_PLATFORM=1`` to disable this fallback.
"""

import os
import sys

if sys.platform == "darwin" and not os.environ.get("SOUNDPAD_KEEP_QT_PLATFORM"):
    _platform = os.environ.get("QT_QPA_PLATFORM")
    if _platform in (None, "", "offscreen"):
        os.environ["QT_QPA_PLATFORM"] = "minimal"
        sys.stderr.write(
            "[conftest] macOS detected: QT_QPA_PLATFORM forced to 'minimal' "
            "(the 'offscreen' plugin segfaults on QMainWindow.show()/grab() "
            "on macOS; 'minimal' runs the identical test logic). "
            "Set SOUNDPAD_KEEP_QT_PLATFORM=1 to override.\n"
        )
