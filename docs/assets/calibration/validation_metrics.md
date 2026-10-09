Validation samples: **1003** (196 positive, 807 negative).

Calibrated probability threshold: **0.5**; selected checkpoint epoch: **31**.

| Metric | Before calibration | After calibration (out-of-fold) |
| --- | ---: | ---: |
| ROC AUC | 0.8793 | 0.8715 |
| Average precision | 0.6483 | 0.6024 |
| Accuracy | 0.7537 | 0.8395 |
| Balanced accuracy | 0.7852 | 0.7013 |
| Sensitivity | 0.8367 | 0.4745 |
| Specificity | 0.7336 | 0.9281 |
| Precision | 0.4327 | 0.6159 |
| Negative predictive value | 0.9487 | 0.8791 |
| F1 score | 0.5704 | 0.5360 |
| Brier score | 0.1523 | 0.1074 |
| Expected calibration error | 0.1676 | 0.0128 |
