"""BERTScore metric adapter implementation for CausalFidelity+ semantic similarity control."""

import logging
from typing import Any, Dict, List, Optional, Tuple

import bert_score

from causalfidelity.config import BERTScoreMetricConfig
from causalfidelity.metrics.base import BaseMetric

logger = logging.getLogger(__name__)


class BERTScoreMetric(BaseMetric):
    """Adapter wrapping official bert_score library for summary semantic similarity scoring.

    Calculates token-level contextual precision, recall, and F1 between reference
    (original summary) and candidate (perturbed summary).
    """

    def __init__(self, config: Optional[BERTScoreMetricConfig] = None):
        """Initialize BERTScore metric adapter.

        Args:
            config: Optional BERTScoreMetricConfig instance. If None, default settings are used.
        """
        self.config = config or BERTScoreMetricConfig()
        self._scorer = None

    @property
    def name(self) -> str:
        return "BERTScore"

    @property
    def version(self) -> str:
        return f"bert-score-{getattr(bert_score, '__version__', '0.3.13')}"

    def _get_scorer(self):
        """Lazy load BERTScorer instance."""
        if self._scorer is None:
            try:
                logger.info(
                    "Initializing BERTScorer with model_type=%s, device=%s, batch_size=%d",
                    self.config.model_type,
                    self.config.device,
                    self.config.batch_size,
                )
                self._scorer = bert_score.BERTScorer(
                    model_type=self.config.model_type,
                    device=self.config.device,
                    batch_size=self.config.batch_size,
                    lang="en",
                    rescale_with_baseline=False,
                )
            except Exception as e:
                logger.error("Failed to initialize BERTScorer: %s", e)
                raise RuntimeError(f"Could not load BERTScorer model '{self.config.model_type}': {e}") from e
        return self._scorer

    def score(self, source_text: str, summary_text: str) -> float:
        """Compute primary scalar metric (BERTScore F1) for reference and candidate pair.

        Args:
            source_text: Reference text (e.g., original summary).
            summary_text: Candidate text (e.g., perturbed summary).

        Returns:
            BERTScore F1 float score in range [0, 1].
        """
        detailed = self.score_detailed(source_text, summary_text)
        return detailed["f1"]

    def score_detailed(self, reference_text: str, candidate_text: str) -> Dict[str, float]:
        """Compute detailed Precision, Recall, and F1 scores for reference and candidate pair.

        Args:
            reference_text: Reference text (original summary).
            candidate_text: Candidate text (perturbed summary).

        Returns:
            Dictionary containing 'precision', 'recall', and 'f1' floats.
        """
        batch_results = self.score_detailed_batch([reference_text], [candidate_text])
        return batch_results[0]

    def score_batch(self, source_texts: List[str], summary_texts: List[str]) -> List[float]:
        """Compute BERTScore F1 floats for a batch of reference and candidate pairs.

        Args:
            source_texts: List of reference texts (original summaries).
            summary_texts: List of candidate texts (perturbed summaries).

        Returns:
            List of BERTScore F1 floats.
        """
        detailed_batch = self.score_detailed_batch(source_texts, summary_texts)
        return [item["f1"] for item in detailed_batch]

    def score_detailed_batch(self, reference_texts: List[str], candidate_texts: List[str]) -> List[Dict[str, float]]:
        """Compute detailed Precision, Recall, and F1 scores for a batch of pairs.

        Args:
            reference_texts: List of reference texts.
            candidate_texts: List of candidate texts.

        Returns:
            List of dictionaries, each containing 'precision', 'recall', and 'f1' floats.
        """
        if len(reference_texts) != len(candidate_texts):
            raise ValueError(
                f"Mismatch in length: reference_texts ({len(reference_texts)}) vs candidate_texts ({len(candidate_texts)})"
            )
        if not reference_texts:
            return []

        # Handle empty/invalid string inputs gracefully
        clean_refs = [r if r and r.strip() else " " for r in reference_texts]
        clean_cands = [c if c and c.strip() else " " for c in candidate_texts]

        scorer = self._get_scorer()
        P, R, F1 = scorer.score(cands=clean_cands, refs=clean_refs)

        results = []
        for p_val, r_val, f1_val in zip(P.tolist(), R.tolist(), F1.tolist()):
            results.append({
                "precision": round(float(p_val), 4),
                "recall": round(float(r_val), 4),
                "f1": round(float(f1_val), 4),
            })
        return results

    def get_metadata(self) -> Dict[str, Any]:
        """Return configuration and metadata for the BERTScore metric adapter."""
        base_meta = super().get_metadata()
        base_meta.update(
            {
                "implementation": "official bert-score package",
                "model_type": self.config.model_type,
                "device": self.config.device,
                "batch_size": self.config.batch_size,
            }
        )
        return base_meta
