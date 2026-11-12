import os
import re
from collections import Counter


def summarize(texts: list[str], config: dict) -> str:
    """Создает описание проекта на основе текстов (LLM или умный fallback)."""
    if not texts:
        return ""

    combined_text = " ".join(texts)
    
    # --- Очистка от мусора PDF и LISP ---
    # Убираем служебные теги PDF (obj, endobj, stream и т.д.)
    clean_text = re.sub(r'\b(obj|endobj|stream|endstream|xref|trailer|startxref)\b', '', combined_text, flags=re.IGNORECASE)
    # Убираем LISP-команды (если это AutoCAD)
    clean_text = re.sub(r'\b(defun|setq|vlax|vla-|command|entget|ssget)\b.*?\n', '', clean_text, flags=re.IGNORECASE)
    
    # --- Ветка LLM (если включена и есть ключ) ---
    llm_config = config.get("llm", {})
    api_key = os.getenv("LLM_API_KEY")
    
    if llm_config.get("enabled") and api_key:
        try:
            import openai
            client = openai.OpenAI(
                base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
                api_key=api_key
            )
            prompt = llm_config.get("system_prompt", "Сформируй краткое техническое описание объекта (2-4 предложения): тип, этажность, конструктив, материалы, стиль.")
            
            # Обрезаем текст для отправки
            max_chars = llm_config.get("max_total_chars", 20000)
            content_to_send = clean_text[:max_chars]
            
            response = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content_to_send}
                ],
                temperature=llm_config.get("temperature", 0.2),
                max_tokens=llm_config.get("max_tokens", 400)
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM Error: {e}. Переход на fallback.")
            # Если ошибка LLM, идем в fallback

    # --- Ветка Fallback (если LLM выключена или упала) ---
    # Ищем предложения с архитектурными/строительными терминами
    keywords = ["площад", "этаж", "конструкт", "фасад", "жил", "дом", "материал", "кв.м", "м2", "корпус", "строительств", "помещен", "здание"]
    sentences = re.split(r'(?<=[.!?])\s+', clean_text)
    
    good_sentences = []
    for s in sentences:
        s = s.strip()
        # Берем предложения от 20 до 200 символов, где есть ключевые слова
        if 20 < len(s) < 200 and any(kw in s.lower() for kw in keywords):
            good_sentences.append(s)
            
    # Если нашли хорошие предложения, берем первые 3
    if good_sentences:
        # Убираем дубликаты, сохраняя порядок
        seen = set()
        unique_sentences = [x for x in good_sentences if not (x in seen or seen.add(x))]
        return " ".join(unique_sentences[:3])
        
    # Если предложений с терминами нет, берем самые частые слова (исключая мусор)
    words = re.findall(r'\b[а-яА-ЯёЁ]{4,}\b', clean_text.lower())
    bad_words = {"который", "которая", "также", "более", "менее", "после", "перед", "между", "через", "чтобы", "этого", "этому", "будет", "может"}
    filtered_words = [w for w in words if w not in bad_words]
    
    if filtered_words:
        top_words = [w[0] for w in Counter(filtered_words).most_common(7)]
        return "Ключевые темы: " + ", ".join(top_words).capitalize()
        
    return "Описание не сформировано (текст не содержит архитектурных терминов)."