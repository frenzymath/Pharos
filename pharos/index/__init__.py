"""Per-project search service sharing BM25 caches between gateway sessions."""

from .service import build_server, serve

__all__ = ["build_server", "serve"]
