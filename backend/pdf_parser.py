"""
PDF Parser for bus schedules
Handles parsing and semantic search in PDF documents
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
from datetime import datetime
import io

import httpx
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import numpy as np

class PDFParser:
    def __init__(self, cache_dir: Path = Path("data/pdf_cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize the sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Cache for parsed content and embeddings
        self.content_cache: Dict[str, List[str]] = {}
        self.embedding_cache: Dict[str, np.ndarray] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load cached content and embeddings"""
        cache_file = self.cache_dir / "content_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.content_cache = json.load(f)
            except Exception as e:
                print(f"Error loading content cache: {e}")
                self.content_cache = {}
                
        embedding_file = self.cache_dir / "embeddings.npz"
        if embedding_file.exists():
            try:
                data = np.load(embedding_file)
                self.embedding_cache = {k: data[k] for k in data.files}
            except Exception as e:
                print(f"Error loading embeddings cache: {e}")
                self.embedding_cache = {}
    
    def _save_cache(self):
        """Save cached content and embeddings"""
        try:
            cache_file = self.cache_dir / "content_cache.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self.content_cache, f)
                
            embedding_file = self.cache_dir / "embeddings.npz"
            if self.embedding_cache:
                np.savez(embedding_file, **self.embedding_cache)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def fetch_pdf(self, url: str) -> Optional[bytes]:
        """Fetch a PDF from a URL (synchronous)"""
        try:
            with httpx.Client() as client:
                response = client.get(url, timeout=15.0)
                response.raise_for_status()
                return response.content
        except Exception as e:
            print(f"Error fetching PDF from {url}: {e}")
            return None

    def parse_pdf_bytes(self, pdf_bytes: bytes, source_url: str) -> List[str]:
        """Parse a PDF from bytes into a list of text chunks"""
        chunks = []
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            reader = PdfReader(pdf_file)
            
            # Extract text from each page
            for page in reader.pages:
                text = page.extract_text()
                
                # Split into smaller chunks (paragraphs or sections)
                page_chunks = [chunk.strip() for chunk in text.split('\n\n') if chunk.strip()]
                chunks.extend(page_chunks)
                
        except Exception as e:
            print(f"Error parsing PDF from {source_url}: {e}")
            return []
            
        return chunks

    def parse_urls(self, urls: List[str]) -> Dict[str, List[str]]:
        """Parse PDFs from a list of URLs (synchronous)"""
        results = {}
        try:
            for url in urls:
                # Check if already cached
                if url in self.content_cache:
                    results[url] = self.content_cache[url]
                    continue

                # Fetch and parse new PDFs
                pdf_bytes = self.fetch_pdf(url)
                if pdf_bytes:
                    chunks = self.parse_pdf_bytes(pdf_bytes, url)
                    if chunks:
                        results[url] = chunks
                        self.content_cache[url] = chunks

                        # Generate and cache embeddings
                        embeddings = self.model.encode(chunks)
                        self.embedding_cache[url] = embeddings

            # Save updated cache
            self._save_cache()

        except Exception as e:
            print(f"Error processing URLs: {e}")

        return results
        try:
            for pdf_file in Path(dir_path).glob(pattern):
                if pdf_file.is_file():
                    file_key = str(pdf_file)
                    
                    # Check if already cached
                    if file_key in self.content_cache:
                        results[file_key] = self.content_cache[file_key]
                        continue
                        
                    # Parse and cache new files
                    chunks = self.parse_pdf(str(pdf_file))
                    if chunks:
                        results[file_key] = chunks
                        self.content_cache[file_key] = chunks
                        
                        # Generate and cache embeddings
                        embeddings = self.model.encode(chunks)
                        self.embedding_cache[file_key] = embeddings
            
            # Save updated cache
            self._save_cache()
            
        except Exception as e:
            print(f"Error processing directory {dir_path}: {e}")
            
        return results
    
    def search(self, query: str, top_k: int = 5, score_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Search parsed PDFs for relevant content"""
        if not self.content_cache or not self.embedding_cache:
            return []
            
        try:
            # Encode query
            query_embedding = self.model.encode(query)
            
            results = []
            
            # Search through each file's content
            for file_path, chunks in self.content_cache.items():
                if file_path not in self.embedding_cache:
                    continue
                    
                chunk_embeddings = self.embedding_cache[file_path]
                
                # Calculate similarities
                similarities = np.dot(chunk_embeddings, query_embedding)
                
                # Get top matches from this file
                top_indices = np.argsort(similarities)[-top_k:][::-1]
                
                for idx in top_indices:
                    score = similarities[idx]
                    if score < score_threshold:
                        continue
                        
                    results.append({
                        "file": str(file_path),
                        "text": chunks[idx],
                        "score": float(score)
                    })
            
            # Sort all results by score
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # Return overall top-k
            return results[:top_k]
            
        except Exception as e:
            print(f"Error during search: {e}")
            return []
            
    def clear_cache(self):
        """Clear the content and embedding caches"""
        self.content_cache.clear()
        self.embedding_cache.clear()
        self._save_cache()