"""
Embedding generation using Ollama nomic-embed-text (768-dim).
Used after OCR to index prescription chunks for RAG search.
"""

from core.db import save_document_embedding


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Sliding-window chunker. Returns list of text chunks."""
    if not text.strip():
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


def _embed(text: str) -> list[float]:
    """Generate a 768-dim embedding for a single text chunk via Ollama."""
    import ollama

    response = ollama.embeddings(model="nomic-embed-text", prompt=text)
    return list(response["embedding"])


async def generate_and_save_embeddings(doc_id: str, user_id: str, text: str) -> int:
    """
    Chunk text, embed each chunk, and persist to document_embeddings.
    Returns number of chunks saved.
    """
    chunks = chunk_text(text)
    if not chunks:
        return 0

    for idx, chunk in enumerate(chunks):
        try:
            embedding = _embed(chunk)
        except Exception as e:
            print(f"[embeddings] Failed to embed chunk {idx} for doc {doc_id}: {e}")
            continue

        await save_document_embedding(
            document_id=doc_id,
            user_id=user_id,
            chunk_text=chunk,
            chunk_index=idx,
            embedding=embedding,
        )

    return len(chunks)
