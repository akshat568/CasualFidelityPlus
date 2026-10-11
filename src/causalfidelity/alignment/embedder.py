"""Local sentence embedding generator using sentence-transformers."""

from typing import List, Union
import numpy as np

from causalfidelity.utils.logging import get_logger

logger = get_logger(__name__)


class SemanticEmbedder:
    """Local, deterministic sentence embedder using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None

    def _load_model(self):
        """Lazy loader for sentence transformer model with clear error reporting."""
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading local sentence-transformer model '{self.model_name}' on device '{self.device}'...")
            self._model = SentenceTransformer(self.model_name, device=self.device)
            return self._model
        except Exception as e:
            err_msg = f"Failed to load sentence-transformer model '{self.model_name}' on device '{self.device}': {str(e)}"
            logger.error(err_msg)
            raise RuntimeError(err_msg) from e

    def embed(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """Generate L2-normalized embeddings for input text or list of texts.

        Args:
            texts: Single string or list of strings.
            batch_size: Batch size for model encoding.

        Returns:
            2D numpy array of shape (N, D) containing normalized embeddings.
        """
        model = self._load_model()
        is_single = isinstance(texts, str)
        text_list = [texts] if is_single else texts

        # Handle empty strings gracefully with zero vectors
        non_empty_indices = [i for i, t in enumerate(text_list) if t and t.strip()]
        
        if hasattr(model, "get_embedding_dimension"):
            dim = model.get_embedding_dimension()
        else:
            dim = model.get_sentence_embedding_dimension()

        embeddings = np.zeros((len(text_list), dim), dtype=np.float32)

        if non_empty_indices:
            valid_texts = [text_list[i] for i in non_empty_indices]
            # Encode with normalize_embeddings=True for unit length vectors
            encoded = model.encode(
                valid_texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            for idx, orig_i in enumerate(non_empty_indices):
                embeddings[orig_i] = encoded[idx]

        return embeddings

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two 1D normalized embedding vectors.

        Args:
            vec1: 1D numpy array.
            vec2: 1D numpy array.

        Returns:
            Float cosine similarity score in [-1.0, 1.0].
        """
        if vec1 is None or vec2 is None or len(vec1) == 0 or len(vec2) == 0:
            return 0.0

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        dot = np.dot(vec1, vec2)
        sim = dot / (norm1 * norm2)
        return float(np.clip(sim, -1.0, 1.0))
