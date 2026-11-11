"""address.py — модуль извлечения адрезов из текста."""

from __future__ import annotations

import re
from collections import Counter
from typing import Optional, List, Union


def extract_address(texts: list[str], config: dict) -> str:
    """
    Возвращает самый вероятный адрес из объединённых текстов.
    Пустая строка, если адрес не найден.
    """
    patterns = config.get("address", {}).get("patterns", [])
    # Приводим к списку, если передан кортеж
    if isinstance(patterns, tuple):
        patterns = list(patterns)
    min_length = config.get("address", {}).get("min_length", 3)
    max_candidates = config.get("address", {}).get("max_candidates", 10)

    if not patterns:
        return ""

    # Дополнительные паттерны для различных форматов адресов
    all_patterns = patterns + [
        # Pattern: "обл. City, г. Street, ul. Street, d Number"
        r"обл\.\s*([А-Я][а-яё]+)\s*,\s*г\.?\s*([А-Я][а-яё]+)\s*,\s*ул\.?\s*([А-Я][а-яё]+)\s*,?\s*д\.?\s*(\d+)",
        # Pattern: "г. City, пр-т Street, d Number"
        r"г\.?\s*([А-Я][а-яё]+)\s*,?\s*пр-т\s*([А-Я][а-яё]+)\s*,?\s*д\.?\s*(\d+)",
        # Pattern: "г. City, пл. д. Number"
        r"г\.?\s*([А-Я][а-яё]+)\s*,?\s*пл\.\s*д\.?\s*(\d+)",
        # Pattern: abbrev city like СПб, г. Moscow
        r"(\b[А-Я]{2,3}\.\s*[А-Я][а-яё]+)\s*,?\s*ул\.?\s*([А-Я][а-яё]+)\s*,?\s*д\.?\s*(\d+)",
        # Pattern: "City, ul. Street, d Number" без г.
        r"([А-Я][а-яё]+)\s*,\s*ул\.?\s*([А-Я][а-яё]+)\s*,?\s*д\.?\s*(\d+)",
    ]

    candidates = []

    for text in texts:
        for pattern in all_patterns:
            for match in re.findall(pattern, text, re.UNICODE):
                # re.findall с группами возвращает tuple, берем первый элемент
                candidate = match[0] if isinstance(match, tuple) else match
                candidate = candidate.strip()
                candidate = re.sub(r"\s+", " ", candidate)
                if len(candidate) >= min_length:
                    candidates.append(candidate)

    if not candidates:
        return ""

    counter = Counter(candidates)
    top_candidates = counter.most_common(max_candidates)

    if not top_candidates:
        return ""

    best = max(top_candidates, key=lambda x: (x[1], len(x[0])))[0]

    return best