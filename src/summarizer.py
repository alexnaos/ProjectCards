import re


def summarize(texts: list[str], config: dict) -> str:
    if not texts: return "Описание не сформировано."

    full_text = "\n".join(texts)
    
    # Ищем "Наименование объекта: ..."
    name_match = re.search(r'Наименование\s+объекта\s*[:\|]?\s*([^\n]+)', full_text, re.IGNORECASE)
    if name_match:
        res = name_match.group(1).strip()
        res = re.split(r'\s+(?:по\s+адресу|расположенный|\(далее)', res, flags=re.IGNORECASE)[0]
        if len(res) > 3: 
            return f"Объект: {res}"

    # Ищем в кавычках «Здание торговли»
    quotes = re.findall(r'«([^»\n]{3,100})»', full_text)
    for q in quotes:
        if any(bad in q.lower() for bad in ["ооо", "зао", "ип", "ао", "пао", "договор"]): continue
        if re.search(r'\d{4}', q): continue
        return f"Объект: «{q}»"

    return "Описание не сформировано."