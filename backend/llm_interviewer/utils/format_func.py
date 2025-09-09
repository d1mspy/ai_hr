from typing import List, Dict

# Функция для форматирования истории диалога
def format_history(history: List[Dict[str, str]]) -> str:

    formatted = []
    for i, exchange in enumerate(history, 1):
        formatted.append(f"Вопрос {i}: {exchange['question']}")
        formatted.append(f"Ответ {i}: {exchange['answer']}")
        
    return "\n".join(formatted)

# Функция для форматирования вывода по теме
def format_dict_for_prompt(topic_name: str, data: Dict):

    lines = []
    lines.append(f"НАЗВАНИЕ ТЕМЫ: {topic_name}")
    for key, value in data.items():
        if isinstance(value, list):
            formatted_value = " ".join(str(item) for item in value)
        else:
            formatted_value = str(value)
        lines.append(f"{key}: {formatted_value}")
    
    return "\n".join(lines)