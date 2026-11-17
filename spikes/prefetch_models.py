# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=4.30", "pyyaml>=6.0", "tiktoken", "numpy", "fastembed>=0.4",
#                 "llama-index-core>=0.12", "openai>=1.40"]
# ///
"""Download the Day 3 packages and local embedding models ahead of time (slow networks). Same deps as retrieval_eval."""

import time
from pathlib import Path

import tiktoken
from fastembed import TextEmbedding

OUT = Path(__file__).resolve().parent / "out" / "models"
tiktoken.get_encoding("cl100k_base")
print("packages + tiktoken ready", flush=True)
for model in ("BAAI/bge-small-en-v1.5", "BAAI/bge-base-en-v1.5"):
    t0 = time.perf_counter()
    TextEmbedding(model, cache_dir=str(OUT))
    print(f"{model} ready in {time.perf_counter() - t0:.0f}s", flush=True)
