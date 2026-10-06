# RC4R

A template for reproducible code in research

The `dermapred` Python package provides a CPU image-inference API and command:

```python
from dermapred.inference import Predictor

predictor = Predictor.from_manifest("model-release.json")
result = predictor.predict("image.jpg")
print(result.to_dict())
```

```bash
dermapred predict image.jpg --manifest model-release.json
```

The model manifest selects a verified weights/calibrator bundle. Runtime
dependencies are PyTorch, NumPy, and Pillow; training tools and private dataset
access are unnecessary for inference. See [the inference guide](docs/dermapred/inference.md)
for installation, local model files, legacy image sizes, and release preparation.

This repository is an educational template for reproducible research workflows.
DermaMNIST provides an illustrative example; the model is not intended for
clinical use or medical decision-making.
