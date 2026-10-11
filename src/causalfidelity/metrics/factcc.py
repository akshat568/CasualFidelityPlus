"""FactCC metric adapter implementation for CausalFidelity+."""

import logging
from typing import Any, Dict, List, Optional

import torch

from causalfidelity.config import FactCCMetricConfig
from causalfidelity.metrics.base import BaseMetric

logger = logging.getLogger(__name__)


class FactCCMetric(BaseMetric):
    """Adapter wrapping FactCC for summary factual consistency scoring.

    Exposes native FactCC score semantics (probability of label 'CORRECT')
    without applying arbitrary extra transformations or calibrations.
    """

    def __init__(self, config: Optional[FactCCMetricConfig] = None):
        """Initialize FactCC metric adapter.

        Args:
            config: Optional FactCCMetricConfig instance. If None, default settings are used.
        """
        self.config = config or FactCCMetricConfig()
        self._tokenizer = None
        self._model = None
        self._correct_idx = None

    @property
    def name(self) -> str:
        return "FactCC"

    @property
    def version(self) -> str:
        return "factcc-manueldeprada"

    def _load_model_and_tokenizer(self):
        """Lazy load FactCC model and tokenizer instances."""
        if self._model is None or self._tokenizer is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                model_path = self.config.model_path
                logger.info("Initializing FactCC tokenizer and model from %s", model_path)
                self._tokenizer = AutoTokenizer.from_pretrained(model_path)
                self._model = AutoModelForSequenceClassification.from_pretrained(model_path)
                
                device = self.config.device
                if device != "cpu" and torch.cuda.is_available():
                    self._model.to(device)
                self._model.eval()

                # Determine index corresponding to 'CORRECT' / consistent label
                correct_idx = 0
                if hasattr(self._model.config, "label2id") and "CORRECT" in self._model.config.label2id:
                    correct_idx = self._model.config.label2id["CORRECT"]
                elif hasattr(self._model.config, "id2label"):
                    for idx, lbl in self._model.config.id2label.items():
                        if str(lbl).upper() in ["CORRECT", "CONSISTENT", "ENTAILED"]:
                            correct_idx = int(idx)
                            break
                self._correct_idx = correct_idx
                logger.info("FactCC loaded successfully. Target label index ('CORRECT'): %d", correct_idx)
            except Exception as e:
                logger.error("Failed to initialize FactCC model/tokenizer: %s", e)
                raise RuntimeError(f"Could not load FactCC model from {self.config.model_path}: {e}") from e

    def score(self, source_text: str, summary_text: str) -> float:
        """Compute FactCC consistency score (probability of CORRECT) for a single document/summary pair.

        Args:
            source_text: Full source document text.
            summary_text: Summary text to score.

        Returns:
            Native FactCC score float (probability of factual consistency in range [0, 1]).
        """
        results = self.score_batch([source_text], [summary_text])
        return results[0]

    def score_batch(self, source_texts: List[str], summary_texts: List[str]) -> List[float]:
        """Compute FactCC consistency scores for a batch of document/summary pairs.

        Args:
            source_texts: List of source document texts.
            summary_texts: List of summary texts.

        Returns:
            List of native FactCC score floats.
        """
        if len(source_texts) != len(summary_texts):
            raise ValueError(
                f"Mismatch in length: source_texts ({len(source_texts)}) vs summary_texts ({len(summary_texts)})"
            )
        if not source_texts:
            return []

        self._load_model_and_tokenizer()

        device = next(self._model.parameters()).device
        max_length = self.config.max_length

        inputs = self._tokenizer(
            source_texts,
            summary_texts,
            max_length=max_length,
            padding=True,
            truncation="only_first",
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            outputs = self._model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)

        scores = probs[:, self._correct_idx].cpu().tolist()
        return [float(s) for s in scores]

    def get_metadata(self) -> Dict[str, Any]:
        """Return configuration and metadata for the FactCC metric adapter."""
        base_meta = super().get_metadata()
        base_meta.update(
            {
                "implementation": "manueldeprada/FactCC via HuggingFace transformers BertForSequenceClassification",
                "model_path": self.config.model_path,
                "device": self.config.device,
                "max_length": self.config.max_length,
            }
        )
        return base_meta
