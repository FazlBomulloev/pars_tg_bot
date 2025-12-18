from typing import List, Optional


def find_keyword_in_text(text: str, keywords: List[str]) -> Optional[str]:
    if not text or not keywords:
        return None

    text_lower = text.lower()

    for keyword in keywords:
        if keyword.lower() in text_lower:
            return keyword

    return None