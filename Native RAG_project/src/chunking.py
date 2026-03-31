# chunking.py
from typing import List

def chunk_text(
    text: str,
    target_words: int = 220, # target number of words per chunk to set semantically meaningful size/scope
    overlap_words: int = 30  # number of overlapping words between chunks to maintain context
    ) -> List[str]:

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        words = para.split()
        para_len = len(words)

        # If adding this paragraph doesn't exceed target, add it (semantic coherence)
        if current_len + para_len <= target_words:
            current_chunk.append(para) # add paragraph to current chunk (semantic grouping)
            current_len += para_len
        else:
            # finalize current chunk
            chunks.append(" ".join(current_chunk))

            # overlap handling
            overlap = " ".join(
                " ".join(current_chunk).split()[-overlap_words:]
            ) # get last 'overlap_words' from current chunk for context preservation

            current_chunk = [overlap, para] # start new chunk with overlap
            current_len = len(overlap.split()) + para_len

    if current_chunk:
        chunks.append(" ".join(current_chunk)) # add last chunk

    return chunks
