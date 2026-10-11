"""Abstract base class interface for causal relation extractors."""

from abc import ABC, abstractmethod
from typing import List

from causalfidelity.causal.schema import CausalRelation


class CausalExtractor(ABC):
    """Abstract Base Class for causal relation extraction implementations."""

    @abstractmethod
    def extract_relations(self, document_id: str, text: str) -> List[CausalRelation]:
        """Extract structured causal relations from text.

        Args:
            document_id: Canonical document identifier.
            text: Source document or sentence text to inspect.

        Returns:
            List of extracted CausalRelation objects.
        """
        pass
