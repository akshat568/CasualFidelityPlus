"""Deterministic sampling utilities for constructing development subsets."""

import random
from typing import List, TypeVar

T = TypeVar("T")


class DeterministicSampler:
    """Provides reproducible sampling over dataset records given a fixed random seed."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def sample(self, items: List[T], sample_size: int) -> List[T]:
        """Sample up to `sample_size` items deterministically from `items`.

        Args:
            items: List of items to sample from.
            sample_size: Number of items requested in sample.

        Returns:
            Deterministically sampled list of items.
        """
        if sample_size <= 0:
            return []

        if len(items) <= sample_size:
            return list(items)

        # Copy list to avoid mutating original order
        items_copy = list(items)
        rng = random.Random(self.seed)
        rng.shuffle(items_copy)
        return items_copy[:sample_size]
