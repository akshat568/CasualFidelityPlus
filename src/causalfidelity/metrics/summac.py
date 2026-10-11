"""SummaCConv metric adapter implementation for CausalFidelity+."""

import logging
from typing import Any, Dict, List, Optional

from causalfidelity.config import SummaCMetricConfig
from causalfidelity.metrics.base import BaseMetric

logger = logging.getLogger(__name__)


class SummaCConvMetric(BaseMetric):
    """Adapter wrapping SummaCConv for summary consistency scoring.

    Exposes the underlying SummaCConv model native score semantics without
    artificially forcing extra normalization.
    """

    def __init__(self, config: Optional[SummaCMetricConfig] = None):
        """Initialize SummaCConv metric adapter.

        Args:
            config: Optional SummaCMetricConfig instance. If None, default settings are used.
        """
        self.config = config or SummaCMetricConfig()
        self._model = None

    @property
    def name(self) -> str:
        return "SummaCConv"

    @property
    def version(self) -> str:
        return "summac-0.0.4"

    def _get_model(self):
        """Lazy load SummaCConv model instance."""
        if self._model is None:
            try:
                from summac.model_summac import SummaCConv

                logger.info(
                    "Initializing SummaCConv model with models=%s, granularity=%s, device=%s",
                    self.config.models,
                    self.config.granularity,
                    self.config.device,
                )
                self._model = SummaCConv(
                    models=self.config.models,
                    granularity=self.config.granularity,
                    device=self.config.device,
                )
            except Exception as e:
                logger.error("Failed to initialize SummaCConv model: %s", e)
                raise RuntimeError(f"Could not load SummaCConv model: {e}") from e
        return self._model

    def score(self, source_text: str, summary_text: str) -> float:
        """Compute SummaCConv score for a single document/summary pair.

        Args:
            source_text: Full source document text.
            summary_text: Claim or summary text to score.

        Returns:
            Native SummaCConv score float.
        """
        model = self._get_model()
        res = model.score([source_text], [summary_text])
        if "scores" in res and len(res["scores"]) > 0:
            return float(res["scores"][0])
        raise ValueError(f"SummaCConv output missing expected 'scores' key: {res}")

    def score_batch(self, source_texts: List[str], summary_texts: List[str]) -> List[float]:
        """Compute SummaCConv scores for a batch of document/summary pairs.

        Args:
            source_texts: List of source document texts.
            summary_texts: List of summary texts.

        Returns:
            List of native SummaCConv score floats.
        """
        if len(source_texts) != len(summary_texts):
            raise ValueError(
                f"Mismatch in length: source_texts ({len(source_texts)}) vs summary_texts ({len(summary_texts)})"
            )
        if not source_texts:
            return []

        model = self._get_model()
        res = model.score(source_texts, summary_texts)
        if "scores" in res:
            return [float(s) for s in res["scores"]]
        raise ValueError(f"SummaCConv output missing expected 'scores' key: {res}")

    def get_metadata(self) -> Dict[str, Any]:
        """Return configuration and metadata for the SummaCConv metric adapter."""
        base_meta = super().get_metadata()
        base_meta.update(
            {
                "model_type": self.config.model_type,
                "models": self.config.models,
                "granularity": self.config.granularity,
                "device": self.config.device,
            }
        )
        return base_meta
