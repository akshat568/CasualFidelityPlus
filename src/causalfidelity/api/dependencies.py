"""Thread-safe dependency injection and lazy model loaders for FastAPI API."""

import logging
import threading
from typing import Dict, Optional

from causalfidelity.api.exceptions import ModelNotAvailableException
from causalfidelity.causal.rule_based import RuleBasedCausalExtractor
from causalfidelity.graph.builder import CausalGraphBuilder
from causalfidelity.perturbation.generator import PerturbationGenerator
from causalfidelity.validation.validator import PerturbationQualityValidator

logger = logging.getLogger(__name__)

# Lightweight singletons
_causal_extractor: Optional[RuleBasedCausalExtractor] = None
_graph_builder: Optional[CausalGraphBuilder] = None
_perturbation_generator: Optional[PerturbationGenerator] = None
_quality_validator: Optional[PerturbationQualityValidator] = None

# Heavy neural metric singletons + locks
_summac_metric = None
_factcc_metric = None
_bertscore_metric = None

_summac_lock = threading.Lock()
_factcc_lock = threading.Lock()
_bertscore_lock = threading.Lock()


def get_causal_extractor() -> RuleBasedCausalExtractor:
    """Get or initialize lightweight RuleBasedCausalExtractor instance."""
    global _causal_extractor
    if _causal_extractor is None:
        _causal_extractor = RuleBasedCausalExtractor()
    return _causal_extractor


def get_graph_builder() -> CausalGraphBuilder:
    """Get or initialize lightweight CausalGraphBuilder instance."""
    global _graph_builder
    if _graph_builder is None:
        _graph_builder = CausalGraphBuilder()
    return _graph_builder


def get_perturbation_generator() -> PerturbationGenerator:
    """Get or initialize lightweight PerturbationGenerator instance."""
    global _perturbation_generator
    if _perturbation_generator is None:
        _perturbation_generator = PerturbationGenerator()
    return _perturbation_generator


def get_quality_validator() -> PerturbationQualityValidator:
    """Get or initialize lightweight PerturbationQualityValidator instance."""
    global _quality_validator
    if _quality_validator is None:
        _quality_validator = PerturbationQualityValidator()
    return _quality_validator


def get_summac_metric():
    """Thread-safe lazy singleton loader for SummaCConvMetric."""
    global _summac_metric
    if _summac_metric is None:
        with _summac_lock:
            if _summac_metric is None:
                try:
                    logger.info("Lazy loading SummaCConvMetric...")
                    from causalfidelity.metrics.summac import SummaCConvMetric

                    _summac_metric = SummaCConvMetric()
                    logger.info("SummaCConvMetric loaded successfully.")
                except Exception as err:
                    logger.error("Failed to load SummaCConvMetric: %s", err)
                    raise ModelNotAvailableException("summac", str(err))
    return _summac_metric


def get_factcc_metric():
    """Thread-safe lazy singleton loader for FactCCMetric."""
    global _factcc_metric
    if _factcc_metric is None:
        with _factcc_lock:
            if _factcc_metric is None:
                try:
                    logger.info("Lazy loading FactCCMetric...")
                    from causalfidelity.metrics.factcc import FactCCMetric

                    _factcc_metric = FactCCMetric()
                    logger.info("FactCCMetric loaded successfully.")
                except Exception as err:
                    logger.error("Failed to load FactCCMetric: %s", err)
                    raise ModelNotAvailableException("factcc", str(err))
    return _factcc_metric


def get_bertscore_metric():
    """Thread-safe lazy singleton loader for BERTScoreMetric."""
    global _bertscore_metric
    if _bertscore_metric is None:
        with _bertscore_lock:
            if _bertscore_metric is None:
                try:
                    logger.info("Lazy loading BERTScoreMetric...")
                    from causalfidelity.metrics.bertscore import BERTScoreMetric

                    _bertscore_metric = BERTScoreMetric()
                    logger.info("BERTScoreMetric loaded successfully.")
                except Exception as err:
                    logger.error("Failed to load BERTScoreMetric: %s", err)
                    raise ModelNotAvailableException("bertscore", str(err))
    return _bertscore_metric


def check_models_loaded() -> Dict[str, bool]:
    """Check currently loaded status of neural models without triggering model initialization."""
    return {
        "summac": _summac_metric is not None,
        "factcc": _factcc_metric is not None,
        "bertscore": _bertscore_metric is not None,
    }
