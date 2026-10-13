"""Inference utilities for DermaPred models."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dermapred.inference.predictor import Prediction, Predictor

__all__ = ["Prediction", "Predictor"]


def __getattr__(name: str) -> object:
    """Import the image API on demand, keeping metadata downloads lightweight."""
    if name in __all__:
        from dermapred.inference.predictor import Prediction, Predictor

        return {"Prediction": Prediction, "Predictor": Predictor}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
