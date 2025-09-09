from typing import List, Dict
from pydantic import BaseModel
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser

from utils.state_classes import TopicType
from utils.prompts import vacancy_info_completion_prompt, greeting_completion_prompt, soft_topic_completion_prompt, hard_topic_completion_prompt
from utils.format_func import format_history


# Функция для определения необходимости завершения темы
def should_end_topic_llm_based(llm, topic_type: TopicType, topic_name: str, vacancy_name: str, conversation_history: List[Dict]) -> bool:
    """Определяет, можно ли завершить тему на основе решения LLM"""

    candidate_response = conversation_history[-1]["answer"]
    if topic_type == TopicType.GREETING:
        prompt = greeting_completion_prompt.format(
            candidate_response=candidate_response
        )
    elif topic_type == TopicType.VACANCY_INFO:
        prompt = vacancy_info_completion_prompt.format(
            vacancy_name=vacancy_name,
            candidate_response=candidate_response,
            history=format_history(conversation_history)
        )
    elif topic_type == TopicType.HARD_SKILL:
        prompt = hard_topic_completion_prompt.format(
            current_topic=topic_name,
            vacancy_name=vacancy_name,
            history=format_history(conversation_history)
        )
    elif topic_type == TopicType.SOFT_SKILL:
        prompt = soft_topic_completion_prompt.format(
            current_topic=topic_name,
            vacancy_name=vacancy_name,
            history=format_history(conversation_history)
        )
    
    response = llm.invoke(prompt)
    decision = response.content.strip().upper()

    return decision == "ДА"


def generate_structured_output(llm, prompt_template: ChatPromptTemplate, 
                              output_model: BaseModel, **kwargs) -> BaseModel:
    """Генерирует structured output используя Pydantic модель"""
    
    parser = PydanticOutputParser(pydantic_object=output_model)
    
    formatted_prompt = prompt_template.format(**kwargs)
    
    response = llm.invoke(formatted_prompt)
    
    return parser.parse(response.content)