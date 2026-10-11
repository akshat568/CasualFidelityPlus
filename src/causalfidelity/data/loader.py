"""Dataset acquisition and loading utilities for XSum."""

from typing import Any, Dict, Iterator, List, Optional

from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class XSumLoader:
    """Loader for XSum dataset using HuggingFace datasets or local synthetic records."""

    def __init__(
        self,
        dataset_path: str = "EdinburghNLP/xsum",
        split: str = "train",
        streaming: bool = True,
    ):
        self.dataset_path = dataset_path
        self.split = split
        self.streaming = streaming

    def stream_raw_records(self, limit: Optional[int] = None) -> Iterator[Dict[str, Any]]:
        """Stream raw XSum records from HuggingFace hub.

        Yields:
            Dict containing raw original_id, source_text, reference_summary, and split.
        """
        try:
            from datasets import load_dataset
        except ImportError as err:
            raise ImportError(
                "The 'datasets' package is required to load XSum. Please install it via requirements.txt."
            ) from err

        logger.info(
            f"Accessing XSum dataset '{self.dataset_path}' (split='{self.split}', streaming={self.streaming})"
        )

        dataset = load_dataset(self.dataset_path, split=self.split, streaming=self.streaming)

        count = 0
        for item in dataset:
            raw_record = {
                "original_id": str(item.get("id", f"xsum_raw_{count}")),
                "source_text": item.get("document", ""),
                "reference_summary": item.get("summary", ""),
                "split": self.split,
            }
            yield raw_record
            count += 1
            if limit is not None and count >= limit:
                break

    @staticmethod
    def load_from_list(raw_records: List[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        """Yield records from a provided in-memory list (useful for synthetic testing)."""
        for item in raw_records:
            yield item
