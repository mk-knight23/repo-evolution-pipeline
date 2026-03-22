"""
Project Context Manager — builds a dependency graph of source files.
Helps agents find relevant cross-file context (imports, exports, shared constants).
"""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Set, Optional
from collections import Counter
import math

logger = logging.getLogger("pipeline.context")

class ProjectContextManager:
    """Analyzes source files to build a mapping of relationships and enables Search-Augmented Generation (RAG)."""

    def __init__(self, source_files: Dict[str, str]):
        self.source_files = source_files
        self.file_graph: Dict[str, Set[str]] = {}
        self.export_map: Dict[str, str] = {}  # symbol -> filepath
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b\w+\b', text) if len(w) > 2]

    def _build_index(self):
        """Build export map, dependency graph, and TF-IDF search index."""
        self.doc_freqs: Counter = Counter()
        self.tf_index: Dict[str, Counter] = {}
        
        num_docs = 0
        for path, content in self.source_files.items():
            if not path.endswith((".js", ".jsx", ".ts", ".tsx", ".vue", ".dart", ".py")):
                continue

            num_docs += 1
            # Build search index
            tokens = self._tokenize(content)
            tf = Counter(tokens)
            self.tf_index[path] = tf
            for token in tf.keys():
                self.doc_freqs[token] += 1

            # Find exports
            exports = re.findall(r"export\s+(?:function|const|class|type|interface|default)\s+([a-zA-Z0-9_]+)", content)
            for export in exports:
                self.export_map[export] = path

            # Initialize graph node
            self.file_graph[path] = set()

        self.num_docs = num_docs

        # Build dependency edges
        for path, content in self.source_files.items():
            if path not in self.file_graph:
                continue

            imports = re.findall(r"import\s+.*?\{?\s*([a-zA-Z0-9_,\s]+)\s*\}?\s+from\s+['\"](.*?)['\"]", content)
            for symbols, imp_path in imports:
                for symbol in symbols.split(","):
                    symbol = symbol.strip()
                    if symbol in self.export_map:
                        self.file_graph[path].add(self.export_map[symbol])

    def search_context(self, query: str, top_k: int = 3) -> Dict[str, str]:
        """RAG-style retrieval using TF-IDF scoring."""
        query_tokens = self._tokenize(query)
        if not query_tokens or self.num_docs == 0:
            return {}

        scores: Dict[str, float] = {}
        for path, tf in self.tf_index.items():
            score = 0.0
            for token in query_tokens:
                if token in tf:
                    idf = math.log(self.num_docs / (1 + self.doc_freqs[token]))
                    score += tf[token] * idf
            if score > 0:
                scores[path] = score

        top_paths = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return {p: self.source_files[p] for p, _ in top_paths}

    def get_relevant_context(self, target_path: str, max_depth: int = 1) -> Dict[str, str]:
        """Get source content for a file and its direct/indirect dependencies."""
        relevant = {}
        to_visit = [(target_path, 0)]
        visited = set()

        while to_visit:
            current_path, depth = to_visit.pop(0)
            if current_path in visited or depth > max_depth:
                continue
            
            visited.add(current_path)
            if current_path in self.source_files:
                relevant[current_path] = self.source_files[current_path]

            if current_path in self.file_graph:
                for neighbor in self.file_graph[current_path]:
                    to_visit.append((neighbor, depth + 1))

        return relevant

    def find_by_symbol(self, symbol: str) -> Optional[str]:
        """Find the file containing a specific export symbol."""
        path = self.export_map.get(symbol)
        return self.source_files.get(path) if path else None

    def get_summary(self) -> str:
        """Return a statistical summary of the project structure."""
        return (f"Project Analysis: {len(self.source_files)} total files, "
                f"{len(self.export_map)} exported symbols, "
                f"{len(self.file_graph)} indexed source documents, "
                f"ready for RAG.")
