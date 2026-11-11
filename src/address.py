"""address.py — модуль извлечения адресов из текста.

Содержит функции для распознавания и извлечения адресной информации
из текстовых документов с использованием regex-паттернов.
ADDRESS_PATTERNS = [
    # Pattern: "г. Москва, ул. Ленина, д. 15"
    r"г\.?\s*([А-Я][а-яё]+\s*(?:г|г\.?|п\.?п\.?|сел)\.?\s*,?\s*)?ул\.?\s*([А-Я][а-яё]+)\s*,?\s*д\.?\s*(\d+)(?:\s*,?\s*к\.?\s*(\d+))?",
    # Pattern: "г Москва ул Ленина д 15 к 1"
    r"г\s+([А-Я][а-яё]+)\s+ул\s+([А-Я][а-яё]+)\s+d\s+(\d+)(?:\s+k\s+(\d+))?",
    # Pattern: "Москва, ул. Ленина, д. 15"
    r"([А-Я][а-яё]+(?:\\s+г\.?)?\s*,?\s*ул\.?\s*([А-Я][а-яё]+)\s*,?\s*д\.?\s*(\d+)(?:\s*,?\s*к\.?\s*(\d+))?)",
    # Pattern: "ул. Ленина, д. 15"
    r"ул\.?\s*([А-Я][а-яё]+)\s*,?\s*д\.?\s*(\d+)(?:\s*,?\s*к\.?\s*(\d+))?",
    # Pattern with index: "197026, г. Санкт-Петербург, ул. Невский проспект, д. 10"
    r"(\d{6})\s*,?\s*г\.?\s*([А-Я][а-яё]+)\s*,?\s*ул\.?\s*([А-Я][а-яё]+)\s*,?\s*д\.?\s*(\d+)(?:\s*,?\s*к\.?\s*(\d+))?",
]


def extract_address(text: str) -> Optional[Dict[str, str]]:
    """Извлечь адрес из текста с использованием regex-паттернов.

    Args:
        text: Текст для поиска адреса.

    Returns:
        Словарь с частями адреса (город, улица, дом, корпус) или None если адрес не найден.
    """
    if not text:
        return None

    for pattern in ADDRESS_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            groups = match.groups()
            address_dict: Dict[str, str] = {}

            if pattern == ADDRESS_PATTERNS[0]:
                city_part = groups[0] if groups[0] else ""
                street = groups[1] if len(groups) > 1 and groups[1] else ""
                house = groups[2] if len(groups) > 2 and groups[2] else ""
                apartment = groups[3] if len(groups) > 3 and groups[3] else ""

                city_match = re.search(r"г\.?\s*([А-Я][а-яё]+)", city_part)
                if city_match:
                    address_dict["city"] = city_match.group(1)

                if street:
                    address_dict["street"] = street

                if house:
                    address_dict["house"] = house

                if apartment:
                    address_dict["apartment"] = apartment

            elif pattern == ADDRESS_PATTERNS[1]:
                if len(groups) >= 3:
                    address_dict["city"] = groups[0] if groups[0] else ""
                    address_dict["street"] = groups[1] if groups[1] else ""
                    address_dict["house"] = groups[2] if groups[2] else ""
                    if len(groups) > 3 and groups[3]:
                        address_dict["apartment"] = groups[3]

            elif pattern == ADDRESS_PATTERNS[2]:
                if len(groups) >= 4:
                    city_part = groups[0] if groups[0] else ""
                    city_match = re.search(r"([А-Я][а-яё]+)(?:\\s+г\.?)?", city_part)
                    if city_match:
                        address_dict["city"] = city_match.group(1)
                    if groups[1]:
                        address_dict["street"] = groups[1]
                    if groups[2]:
                        address_dict["house"] = groups[2]
                    if groups[3]:
                        address_dict["apartment"] = groups[3]

            elif pattern == ADDRESS_PATTERNS[3]:
                if len(groups) >= 2:
                    if groups[0]:
                        address_dict["street"] = groups[0]
                    if groups[1]:
                        address_dict["house"] = groups[1]
                    if len(groups) > 2 and groups[2]:
                        address_dict["apartment"] = groups[2]

            elif pattern == ADDRESS_PATTERNS[4]:
                if len(groups) >= 5:
                    if groups[1]:
                        address_dict["city"] = groups[1]
                    if groups[2]:
                        address_dict["street"] = groups[2]
                    if groups[3]:
                        address_dict["house"] = groups[3]
                    if groups[4]:
                        address_dict["apartment"] = groups[4]

            if "city" in address_dict or "street" in address_dict:
                return address_dict

    return None
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Dict, Any
