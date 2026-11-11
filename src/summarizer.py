"""summarizer.py — модуль суммаризации текста.

Содержит функции для создания кратких суммар текста с использованием
LLM и fallback-стратегии на основе TF-IDF.

Примечание: Полноценная работа требует установки OpenAI API ключа и
библиотеки scikit-learn для TF-IDF fallback.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Optional, List, Dict, Any

import numpy as np

# Попытка импорта библиотек
try:
    from sklearn.feature.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    warnings.warn("scikit-learn not available. TF-IDF fallback disabled.")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    warnings.warn("openai not available. LLM summarization disabled.")


def summarize_with_llm(
    text: str,
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
    max_tokens: int = 1000,
    temperature: float = 0.3,
) -> Optional[str]:
    """Создать суммарный текст с помощью LLM.

    Args:
        text: Исходный текст для суммаризации.
        model: Название модели OpenAI.
        base_url: URL базы OpenAI API.
        max_tokens: Максимальное количество токенов в ответе.
        temperature: Температура генерации.

    Returns:
        Краткая суммаризация текста или None если LMM недоступен.
    """
    if not OPENAI_AVAILABLE:
        print("OpenAI not available. LLM summarization disabled.")
        return None

    if not text or len(text.strip()) < 100:
        print("Text too short for summarization.")
        return None

    try:
        # Формируем промпт для суммаризации
        prompt = f"""
        Сделай краткую суммаризацию следующего текста на русском языке. 
        Результат должен быть кратким (1-2 параграфа), содержать основные мысли.
        
        Текст:
        {text[:5000]}  # Ограничиваем длину входного текста
        
        Краткая суммаризация:
        """

        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        summary = response.choices[0].message.content.strip()
        return summary

    except Exception as e:
        print(f"Error in LLM summarization: {e}")
        return None


def summarize_with_tfidf(
    text: str,
    summary_ratio: float = 0.3,
) -> Optional[str]:
    """Создать суммарный текст с помощью TF-IDF fallback.

    Args:
        text: Исходный текст для суммаризации.
        summary_ratio: Доля текста, которую нужно оставить (от 0 до 1).

    Returns:
        Краткая суммаризация текста или None если TF-IDF недоступен.
    """
    if not SKLEARN_AVAILABLE:
        print("scikit-learn not available. TF-IDF fallback disabled.")
        return None

    if not text or len(text.strip()) < 100:
        print("Text too short for summarization.")
        return None

    try:
        # Подготовка текста
        sentences = [s.strip() for s in text.split(". ") if s.strip()]
        
        if len(sentences) <= 2:
            return text

        # Создаем TF-IDF векторы
        vectorizer = TfidfVectorizer(stop_words="russian", min_df=1, max_df=0.9)
        tfidf_matrix = vectorizer.fit_transform(sentences)

        # Вычисляем сходство каждого предложения с 전체 текстом
        cosine_similarities = cosine_similarity(tfidf_matrix, tfidf_matrix).diagonal()

        # Сортируем предложения по важности
        ranked_indices = cosine_similarities.argsort()[::-1]

        # Выбираем топ-N предложений
        n_summary = max(1, int(len(sentences) * summary_ratio))
        summary_indices = sorted(ranked_indices[:n_summary])

        # Формируем суммаризацию в оригинальном порядке
        summary_sentences = [sentences[i] for i in summary_indices]
        summary = ". ".join(summary_sentences)

        # Добавляем точку в конце если её нет
        if not summary.endswith("."):
            summary += "."

        return summary

    except Exception as e:
        print(f"Error in TF-IDF summarization: {e}")
        return None


def summarize_text(
    text: str,
    use_llm: bool = True,
    use_tfidf: bool = True,
    **kwargs: Any,
) -> Optional[str]:
    """Основная функция суммаризации текста.

    Пытается использовать LLM, если недоступен — падает back на TF-IDF.

    Args:
        text: Исходный текст для суммаризации.
        use_llm: Попытаться ли использовать LLM.
        use_tfidf: Попытаться ли использовать TF-IDF fallback.
        **kwargs: Дополнительные аргументы для функций суммаризации.

    Returns:
        Краткая суммаризация текста.
    """
    # Попытка LLM
    if use_llm and OPENAI_AVAILABLE:
        llm_summary = summarize_with_llm(text, **kwargs)
        if llm_summary:
            return llm_summary

    # Fallback на TF-IDF
    if use_tfidf and SKLEARN_AVAILABLE:
        tfidf_summary = summarize_with_tfidf(text, **kwargs)
        if tfidf_summary:
            return tfidf_summary

    # Если ничего не получилось
    print("Both LLM and TF-IDF summarization failed.")
    # Возвращаем первые предложения как fallback
    sentences = [s.strip() for s in text.split(". ") if s.strip()]
    if sentences:
        return ". ".join(sentences[:min(3, len(sentences))]) + "."
    return text[:200] + "..." if len(text) > 200 else text