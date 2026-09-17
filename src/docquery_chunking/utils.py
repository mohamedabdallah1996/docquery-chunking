"""Small helpers shared across the chunking components."""

from __future__ import annotations

import hashlib

import tiktoken

# A generic encoding, not the embedding model's actual tokenizer -- chunking
# doesn't know (and shouldn't need to know) which embedder will consume its
# output. This is a consistent proxy for "how big is this text", used only
# as a soft sizing target, not a hard limit any API enforces.
_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Return the token count of `text` under the shared reference encoding."""
    return len(_ENCODING.encode(text))


def stable_id(*parts: str) -> str:
    """Generate a deterministic ID from `parts`.

    Re-running the chunker on the same document produces the same IDs.
    """
    value = "::".join(parts)
    return hashlib.sha256(value.encode()).hexdigest()[:16]
