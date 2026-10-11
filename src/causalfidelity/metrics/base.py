"""Base abstract class for faithfulness metric evaluators in CausalFidelity+."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseMetric(ABC):
    """Abstract base class defining the common interface for external faithfulness metrics."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique name identifier of the metric."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Return the version string of the metric wrapper or underlying model."""
        pass

    @abstractmethod
    def score(self, source_text: str, summary_text: str) -> float:
        """Compute faithfulness score for a single source document and summary pair.

        Args:
            source_text: Full source document text.
            summary_text: Claim / summary text to evaluate.

        Returns:
            Native metric score float.
        """
        pass

    def score_batch(self, source_texts: List[str], summary_texts: List[str]) -> List[float]:
        """Compute faithfulness scores for a batch of source and summary pairs.

        Default implementation loops over score(); subclasses can override for batching.

        Args:
            source_texts: List of full source document texts.
            summary_texts: List of claim / summary texts to evaluate.

        Returns:
            List of native metric score floats.
        """
        if len(source_texts) != len(summary_texts):
            raise ValueError(
                f"Mismatch in length: source_texts ({len(source_texts)}) vs summary_texts ({len(summary_texts)})"
            )
        return [self.score(src, smm) for src, smm in zip(source_texts, summary_texts)]

    def get_metadata(self) -> Dict[str, Any]:
        """Return configuration and metadata dictionary for the metric instance."""
        return {
            "name": self.name,
            "version": self.version,
        }
