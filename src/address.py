import re


def extract_address(texts: list[str], config: dict) -> str:
    if not texts: 
        return "Не определено"

    full_text = " ".join(texts).replace('\n', ' ').replace('\r', ' ')
    
    # 1. Ищем ВСЕ вхождения "по адресу"
    matches = re.finditer(r'(?:по\s+адресам?|адрес\s+объекта|адрес)\s*[:\-]\s*([^;]+(?:;|$))', full_text, re.IGNORECASE)
    
    candidates = []
    for match in matches:
        clean = match.group(1).strip()
        # Обрезаем всё, что идет после точки с запятой или скобки
        clean = re.split(r'[;(]', clean)[0].strip()
        clean = clean.rstrip('.,;:- "\'«»')
        
        if len(clean) > 5:
            candidates.append(clean)
            
    if candidates:
        # Ищем идеальный вариант (где есть и город, и дом/улица)
        best_candidates = [
            c for c in candidates 
            if ("москва" in c.lower() or "зеленоград" in c.lower() or "г." in c.lower() or "город" in c.lower()) 
            and ("ул." in c.lower() or "пр-т" in c.lower() or "проспект" in c.lower() or "д." in c.lower() or "вал" in c.lower())
        ]
        
        if best_candidates:
            return max(best_candidates, key=len)
        
        # Если идеального нет, берем самый длинный из найденных
        return max(candidates, key=len)

    # 2. Если слова "адрес" нет, ищем "Город + Улица + Дом"
    patterns = [
        r'(?:г\.|город)\s*[А-ЯЁ][а-яё\-]+[^\n]{0,120}?(?:ул\.|улица|пр-т|проспект|пер\.|переулок|ш\.|шоссе|проезд|бульвар|наб\.)\s*[А-ЯЁа-яё0-9\-\s]+?(?:д\.|дом|вл\.|владение|стр\.|участок)\s*\d+[А-Яа-я0-9\/\-]*'
    ]
    for pattern in patterns:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            return m.group(0).strip()

    return "Не определено"