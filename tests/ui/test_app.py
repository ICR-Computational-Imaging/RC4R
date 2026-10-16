"""Exercise the actual Qt workspace using synthetic images and mocked inference."""

import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from matplotlib.backend_bases import MouseEvent
from PIL import Image
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from dermapred.inference.predictor import Prediction
from dermapred.ui import app


@pytest.fixture(scope="module")
def qt():
    application = QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    return application


def wait_for_idle(window, qt):
    deadline = time.monotonic() + 10
    while window.task is not None and time.monotonic() < deadline:
        qt.processEvents()
        QTest.qWait(10)
    assert window.task is None, "Background task did not finish"
    qt.processEvents()


@pytest.fixture
def workspace(qt, monkeypatch):
    prediction = Prediction("clinically_concerning", 1, 0.8, 0.7, 0.5, True)
    predictor = SimpleNamespace(calibrator=object(), predict=Mock(return_value=prediction))
    factory = Mock(return_value=predictor)
    window = app.InferenceWindow(factory)
    monkeypatch.setattr(app.QMessageBox, "information", Mock())
    monkeypatch.setattr(app.QMessageBox, "warning", Mock())
    window.show()
    qt.processEvents()
    yield window, factory, predictor
    wait_for_idle(window, qt)
    window.close()
    qt.processEvents()


def drag(window, start, end, qt):
    window.canvas.draw()
    for name, xy in [("button_press_event", start), ("motion_notify_event", end),
                     ("button_release_event", end)]:
        x, y = window.axes.transData.transform(xy)
        event = MouseEvent(name, window.canvas, x, y, button=1)
        window.canvas.callbacks.process(name, event)
        qt.processEvents()


def test_real_mouse_drag_replaces_selection_and_clears_result(workspace, qt):
    window, _, _ = workspace
    window._show_image(Image.new("RGB", (100, 60)))
    drag(window, (10, 10), (60, 40), qt)
    assert window.bounds is not None
    assert window.bounds[0] == pytest.approx(10, abs=1)
    assert window.selector.artists[0].get_visible()
    window.result.setText("Old prediction")
    drag(window, (80, 50), (20, 15), qt)
    assert window.bounds[2] == pytest.approx(80, abs=1)
    assert window.result.text() == "No prediction yet."
    assert len(window.axes.patches) == 1


def test_infer_requires_selection(workspace):
    window, factory, _ = workspace
    window.infer_button.click()
    app.QMessageBox.information.assert_called_once()
    factory.assert_not_called()


def test_inference_crops_original_and_reuses_predictor(workspace, qt):
    window, factory, predictor = workspace
    window._show_image(Image.new("RGB", (100, 80)))
    window.bounds = (10, 10, 70, 50)
    window.infer_button.click()
    assert not window.open_button.isEnabled()
    assert not window.infer_button.isEnabled()
    wait_for_idle(window, qt)
    assert predictor.predict.call_args.args[0].size == (40, 40)
    assert "80.0%" in window.result.text()
    assert "clinically_concerning" in window.result.text()
    assert window.open_button.isEnabled()
    window.infer()
    wait_for_idle(window, qt)
    factory.assert_called_once()
    assert predictor.predict.call_count == 2


@pytest.mark.parametrize("failure", ["load", "predict", "calibrator", "uncalibrated"])
def test_inference_failures_show_dialog_without_result(workspace, qt, failure):
    window, factory, predictor = workspace
    window._show_image(Image.new("RGB", (20, 20)))
    window.bounds = (0, 0, 10, 10)
    if failure == "load":
        factory.side_effect = OSError("Cannot retrieve model")
    elif failure == "predict":
        predictor.predict.side_effect = RuntimeError("Model failed")
    elif failure == "calibrator":
        predictor.calibrator = None
    else:
        predictor.predict.return_value = SimpleNamespace(calibrated=False)
    window.infer()
    wait_for_idle(window, qt)
    app.QMessageBox.warning.assert_called_once()
    assert window.result.text() == "No prediction yet."
    assert window.infer_button.isEnabled()


def test_open_new_image_resets_selection_and_errors_are_reported(workspace, qt, tmp_path):
    window, _, _ = workspace
    path = tmp_path / "image.png"
    Image.new("RGB", (80, 40)).save(path)
    window._show_image(Image.new("RGB", (20, 20)))
    window.bounds = (0, 0, 5, 5)
    window.result.setText("Old prediction")
    window.open_image(path)
    wait_for_idle(window, qt)
    assert window.image.size == (80, 40)
    assert window.bounds is None
    assert window.result.text() == "No prediction yet."
    window.open_image(tmp_path / "missing.png")
    wait_for_idle(window, qt)
    assert window.image is None
    app.QMessageBox.warning.assert_called_once()


def test_file_dialog_selection_and_cancel(workspace, qt, monkeypatch, tmp_path):
    window, factory, _ = workspace
    path = tmp_path / "image.bmp"
    Image.new("RGB", (40, 30)).save(path)
    monkeypatch.setattr(app.QFileDialog, "getOpenFileName", lambda *args: (str(path), ""))
    window.choose_image()
    wait_for_idle(window, qt)
    assert window.image.size == (40, 30)
    monkeypatch.setattr(app.QFileDialog, "getOpenFileName", lambda *args: ("", ""))
    window.choose_image()
    assert window.image.size == (40, 30)
    window.cancel_button.click()
    assert not window.isVisible()
    factory.assert_not_called()


def test_close_during_work_waits_safely_and_ignores_result(workspace, qt):
    window, _, _ = workspace
    release = threading.Event()
    callback = Mock()
    try:
        window._start(lambda: release.wait(5), callback, "Working")
        window.open_image(None)  # Busy: do not start another task.
        window.infer()
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        assert not window.isVisible()
        window._failed("Late error")
        release.set()
        wait_for_idle(window, qt)
        callback.assert_not_called()
        app.QMessageBox.warning.assert_not_called()
    finally:
        release.set()


def test_invalid_selection_callbacks(workspace):
    window, _, _ = workspace
    press = SimpleNamespace(xdata=1, ydata=1)
    window._select(press, press)  # No image.
    window._show_image(Image.new("RGB", (20, 20)))
    window._select(press, SimpleNamespace(xdata=None, ydata=None))
    window._select(press, press)
    assert window.bounds is None


def test_run_starts_event_loop(qt, monkeypatch):
    monkeypatch.setattr(app.QApplication, "exec", lambda self: 0)
    window = Mock()
    monkeypatch.setattr(app, "InferenceWindow", Mock(return_value=window))
    assert app.run(Mock()) == 0
    window.show.assert_called_once()
