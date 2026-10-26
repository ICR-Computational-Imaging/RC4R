"""PyQt6 workspace with a Matplotlib image and a replaceable red selection."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from matplotlib.backend_bases import MouseButton, MouseEvent
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.widgets import RectangleSelector
from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dermapred.inference.predictor import Predictor
from dermapred.ui.images import load_example_image, load_image, selection_bounds, square_crop


class Task(QThread):
    """Run one blocking operation; only the GUI thread handles its signals."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, operation: Callable[[], Any], parent: QWidget) -> None:
        super().__init__(parent)
        self.operation = operation

    def run(self) -> None:
        """Keep errors within the worker and report them to the interface."""
        try:
            result = self.operation()
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.succeeded.emit(result)


class InferenceWindow(QMainWindow):
    """Select a region in an original-resolution image and infer on its crop."""

    def __init__(self, predictor_factory: Callable[[], Predictor]) -> None:
        super().__init__()
        self.predictor_factory = predictor_factory
        self.predictor: Predictor | None = None
        self.image: Image.Image | None = None
        self.bounds: tuple[int, int, int, int] | None = None
        self.selector: RectangleSelector | None = None
        self.task: Task | None = None
        self._closing = False
        self._callback: Callable[[Any], None] | None = None
        self.setWindowTitle("DermaPred — image inference")
        self.resize(1000, 700)
        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.addWidget(QLabel("Educational example — not intended for clinical use."))
        controls = QHBoxLayout()
        self.open_button = QPushButton("Open image")
        self.example_button = QPushButton("Load example")
        self.infer_button = QPushButton("Infer")
        self.cancel_button = QPushButton("Cancel")
        for button in (
            self.open_button,
            self.example_button,
            self.infer_button,
            self.cancel_button,
        ):
            controls.addWidget(button)
        layout.addLayout(controls)
        panels = QHBoxLayout()
        # Matplotlib's Qt backend constructor and draw_idle lack annotations.
        self.canvas = FigureCanvasQTAgg(Figure(layout="constrained"))  # type: ignore[no-untyped-call]
        self.axes = self.canvas.figure.add_subplot()
        self.axes.set_axis_off()
        self.axes.set_title("Open an image, then left-click and drag around the mole")
        panels.addWidget(self.canvas, stretch=3)
        self.result = QLabel("No prediction yet.")
        self.result.setWordWrap(True)
        self.result.setMinimumWidth(220)
        panels.addWidget(self.result, stretch=1)
        layout.addLayout(panels)
        self.status = QLabel("Open an image or click Load example to begin.")
        layout.addWidget(self.status)
        self.setCentralWidget(workspace)
        self.open_button.clicked.connect(self.choose_image)
        self.example_button.clicked.connect(self.open_example)
        self.infer_button.clicked.connect(self.infer)
        self.cancel_button.clicked.connect(self.close)
        # Register before RectangleSelector so a fresh press clears the old result.
        self.canvas.mpl_connect("button_press_event", self._begin_selection)

    def choose_image(self) -> None:
        """Ask for a supported image path; decode it in a background worker."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open image", "", "Images (*.jpg *.jpeg *.tif *.tiff *.png *.bmp)"
        )
        if filename:
            self.open_image(Path(filename))

    def open_image(self, path: Path) -> None:
        """Load a user-selected file in the background."""
        self._load_image(lambda: load_image(path), "Loading image…")

    def open_example(self) -> None:
        """Load the example shipped with the installed Python package."""
        self._load_image(load_example_image, "Loading example image…")

    def _load_image(self, loader: Callable[[], Image.Image], message: str) -> None:
        """Clear stale evidence before attempting to load another image."""
        if self.task is not None:
            return
        self.image = None
        self.bounds = None
        self.result.setText("No prediction yet.")
        if self.selector is not None:
            self.selector.disconnect_events()
            self.selector = None
        self.axes.clear()
        self.axes.set_axis_off()
        self.canvas.draw_idle()  # type: ignore[no-untyped-call]
        self._start(loader, self._show_image, message)

    def _show_image(self, image: Image.Image) -> None:
        self.image = image
        width, height = image.size
        # Explicit edge coordinates align Matplotlib selection with Pillow pixels.
        self.axes.imshow(image, extent=(0, width, height, 0), origin="upper")
        self.axes.set_xlim(0, width)
        self.axes.set_ylim(height, 0)
        self.axes.set_title("Left-click and drag; release to finish the red box")
        self.selector = RectangleSelector(
            self.axes,
            self._select,
            button=[MouseButton.LEFT],
            minspanx=0,
            minspany=0,
            useblit=True,
            interactive=False,
            props={"edgecolor": "red", "facecolor": "none", "linewidth": 2},
        )
        self.canvas.draw_idle()  # type: ignore[no-untyped-call]

    def _begin_selection(self, event: MouseEvent) -> None:
        if (
            event.inaxes is self.axes
            and event.button == MouseButton.LEFT
            and self.image is not None
            and self.task is None
        ):
            self.bounds = None
            self.result.setText("No prediction yet.")
            if self.selector is not None:
                self.selector.clear()

    def _select(self, press: MouseEvent, release: MouseEvent) -> None:
        if self.image is None:
            return
        x_start, y_start = press.xdata, press.ydata
        x_end, y_end = release.xdata, release.ydata
        if x_start is None or y_start is None or x_end is None or y_end is None:
            return
        coordinates = (x_start, y_start, x_end, y_end)
        try:
            self.bounds = selection_bounds(coordinates, self.image.size)
        except ValueError:
            self.bounds = None
        if self.selector is not None:
            self.selector.set_visible(self.bounds is not None)
        self.result.setText("No prediction yet.")

    def infer(self) -> None:
        """Crop the original pixels, then reuse calibrated Predictor inference."""
        if self.task is not None:
            return
        if self.image is None or self.bounds is None:
            QMessageBox.information(self, "Select a region", "Draw a bounding box first.")
            return
        cropped = square_crop(self.image, self.bounds)
        self.result.setText("No prediction yet.")

        def predict() -> tuple[Predictor, Any]:
            predictor = self.predictor if self.predictor is not None else self.predictor_factory()
            if predictor.calibrator is None:
                raise ValueError("This interface requires a matching probability calibrator.")
            prediction = predictor.predict(cropped)
            if not prediction.calibrated:
                raise ValueError("Inference did not return a calibrated probability.")
            return predictor, prediction

        self._start(predict, self._show_prediction, "Loading model / running inference…")

    def _show_prediction(self, value: tuple[Predictor, Any]) -> None:
        self.predictor, prediction = value
        self.result.setText(
            "Calibrated probability of clinically_concerning:\n"
            f"{prediction.probability:.1%}\n\n"
            f"Predicted class: {prediction.label}\n"
            f"Threshold: {prediction.threshold:g}"
        )

    def _start(
        self, operation: Callable[[], Any], callback: Callable[[Any], None], message: str
    ) -> None:
        self._callback = callback
        self.task = Task(operation, self)
        self.open_button.setEnabled(False)
        self.example_button.setEnabled(False)
        self.infer_button.setEnabled(False)
        if self.selector is not None:
            self.selector.set_active(False)
        self.status.setText(message)
        self.task.succeeded.connect(self._succeeded)
        self.task.failed.connect(self._failed)
        self.task.finished.connect(self._finished)
        self.task.start()

    def _succeeded(self, value: Any) -> None:
        if not self._closing and self._callback is not None:
            self._callback(value)

    def _failed(self, message: str) -> None:
        if not self._closing:
            self.status.setText("Operation failed. Check the files and try again.")
            QMessageBox.warning(self, "Unable to complete operation", message)

    def _finished(self) -> None:
        task = self.task
        self.task = None
        self._callback = None
        if task is not None:
            task.deleteLater()
        if self._closing:
            self.close()
            return
        self.open_button.setEnabled(True)
        self.example_button.setEnabled(True)
        self.infer_button.setEnabled(True)
        if self.selector is not None:
            self.selector.set_active(True)
        self.status.setText("Ready. Draw a region and click Infer.")

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Never destroy a running QThread or terminate a model operation unsafely."""
        if event is None:
            return
        if self.task is not None:
            self._closing = True
            self.hide()
            event.ignore()
        else:
            if self.selector is not None:
                self.selector.disconnect_events()
            event.accept()


def run(predictor_factory: Callable[[], Predictor]) -> int:
    """Start a standalone Qt application without loading a model on launch."""
    app = QApplication.instance() or QApplication([sys.argv[0]])
    window = InferenceWindow(predictor_factory)
    window.show()
    return app.exec()
