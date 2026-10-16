"""Use Qt's offscreen platform for synthetic desktop tests in CI."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_API", "pyqt6")
