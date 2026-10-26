"""A compact binary classifier based on the LeNet architecture."""

from typing import cast

import torch
import torch.nn as nn
import torch.nn.functional as F


class LeNetBinary(nn.Module):
    """Classify RGB lesion images as benign or clinically concerning.

    Args:
        input_channels: Number of channels in each input image. DermaMNIST RGB
            images use three channels.

    Raises:
        ValueError: If ``input_channels`` is not a positive integer.
    """

    def __init__(self, input_channels: int = 3) -> None:
        """Initialise the convolutional and fully connected layers.

        Args:
            input_channels: Number of channels in each input image.

        Returns:
            None.

        Raises:
            ValueError: If ``input_channels`` is not a positive integer.
        """
        if isinstance(input_channels, bool) or not isinstance(input_channels, int):
            raise ValueError("input_channels must be a positive integer.")
        if input_channels <= 0:
            raise ValueError("input_channels must be a positive integer.")

        super().__init__()
        self.conv1 = nn.Conv2d(input_channels, 6, kernel_size=5)
        self.conv2 = nn.Conv2d(6, 16, kernel_size=5)
        self.adaptive_pool = nn.AdaptiveAvgPool2d((4, 4))  # This layer ensures output 4 x 4.
        self.fc1 = nn.Linear(16 * 4 * 4, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 2)
        self.fc4 = nn.Linear(2, 1)

    def featurize(self, x: torch.Tensor) -> torch.Tensor:
        """Extract a two-value feature representation from each image.

        Args:
            x: Image batch with shape ``(N, C, H, W)``. ``C`` must match the
                ``input_channels`` supplied to the constructor.

        Returns:
            Tensor with shape ``(N, 2)`` containing the learned features.

        Raises:
            RuntimeError: If the input shape or channel count is incompatible
                with the network.
        """
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2)
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2)
        x = self.adaptive_pool(x)
        x = torch.flatten(x, start_dim=1)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return cast(torch.Tensor, self.fc3(x))

    def classify(self, x: torch.Tensor) -> torch.Tensor:
        """Convert learned features into raw classification logits.

        Args:
            x: Learned feature tensor with shape ``(N, 2)``.

        Returns:
            Tensor with shape ``(N, 1)`` containing unbounded logits.

        Raises:
            RuntimeError: If the final dimension of ``x`` is not two.
        """
        return cast(torch.Tensor, self.fc4(x))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Run an image batch through the complete classifier.

        Args:
            x: Image batch with shape ``(N, C, H, W)``.

        Returns:
            Tensor with shape ``(N, 1)`` containing raw classification logits.

        Raises:
            RuntimeError: If the input is incompatible with the network.
        """
        return self.classify(self.featurize(x))

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """Predict clinically concerning class probabilities.

        Args:
            x: Image batch with shape ``(N, C, H, W)``.

        Returns:
            Tensor with shape ``(N, 1)`` containing probabilities in
            ``[0, 1]``.

        Raises:
            RuntimeError: If the input is incompatible with the network.
        """
        return torch.sigmoid(self.forward(x))
