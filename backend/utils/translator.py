from __future__ import annotations

from typing import List, Tuple

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODEL_NAME = "VietAI/envit5-translation"
MAX_CHUNK_TOKENS = 400

_TOKENIZER: AutoTokenizer | None = None
_MODEL: AutoModelForSeq2SeqLM | None = None
_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_pipeline() -> Tuple[AutoTokenizer, AutoModelForSeq2SeqLM]:
    global _TOKENIZER, _MODEL
    if _TOKENIZER is None or _MODEL is None:
        _TOKENIZER = AutoTokenizer.from_pretrained(MODEL_NAME)
        _MODEL = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
        _MODEL.to(_DEVICE)
    return _TOKENIZER, _MODEL


def _prepare_input(text: str, prefix: str = "en:") -> str:
    text = text.strip()
    if not text.startswith(prefix):
        text = f"{prefix} {text}"
    return text


def _translate_chunk(text: str, tokenizer: AutoTokenizer, model: AutoModelForSeq2SeqLM) -> str:
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True).to(_DEVICE)
    outputs = model.generate(**inputs, max_length=512)
    translated = tokenizer.batch_decode(outputs, skip_special_tokens=True)
    return translated[0]


def translate_text(raw_text: str, max_chunk_tokens: int = MAX_CHUNK_TOKENS) -> str:
    """
    Translate English text to Vietnamese. Automatically splits long texts into chunks
    because the seq2seq model struggles with very long sequences.
    """

    tokenizer, model = _load_pipeline()
    text = _prepare_input(raw_text)

    tokens = tokenizer.tokenize(text)
    if len(tokens) <= max_chunk_tokens:
        return _translate_chunk(text, tokenizer, model)

    print(f"Văn bản dài ({len(tokens)} tokens) → chia nhỏ để dịch nhiều lần.")
    translated_parts: List[str] = []
    for idx in range(0, len(tokens), max_chunk_tokens):
        chunk_tokens = tokens[idx : idx + max_chunk_tokens]
        chunk_text = tokenizer.convert_tokens_to_string(chunk_tokens)
        part = _translate_chunk(_prepare_input(chunk_text), tokenizer, model)
        translated_parts.append(part)
        print(f"  ➜ Đã dịch phần {len(translated_parts)}/{(len(tokens) + max_chunk_tokens - 1) // max_chunk_tokens} ({len(chunk_tokens)} tokens)")

    return " ".join(translated_parts).strip()


__all__ = ["translate_text"]

