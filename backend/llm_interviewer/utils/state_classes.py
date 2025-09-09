from typing import List, Dict, Optional
from enum import Enum
from pydantic import BaseModel, Field

class TopicSummary(BaseModel):
    score: int = Field(description="Общая оценка по теме от 1 до 100", ge=1, le=100)
    strengths: List[str] = Field(description="Список сильных сторон с примерами")
    red_flags: List[str] = Field(description="Критические красные флаги - серьезные риски для вакансии")

class HardTopicSummary(TopicSummary):
    practical_experience: str = Field(description="Анализ практического опыта")
    honesty_analysis: str = Field(description="Анализ честности ответов")

class SoftTopicSummary(TopicSummary):
    behavioral_patterns: List[str] = Field(description="Выявленные поведенческие паттерны и привычки")
    consistency_analysis: str = Field(description="Анализ согласованности и искренности ответов") 

class QuestionType(Enum):
    FIRST = "first"
    ADAPTIVE = "adaptive"

class TopicType(Enum):
    GREETING = "greeting"
    VACANCY_INFO = "vacancy_info"
    HARD_SKILL = "hard_skill"
    SOFT_SKILL = "soft_skill"

class TopicState(BaseModel):
    topic_type: TopicType
    questions_asked: int = 0
    conversation_history: List[Dict[str, str]] = []

class InterviewState(BaseModel):
    verification_plan: List[Dict]
    current_topic_index: int = 0
    topic_states: Dict[str, TopicState] = {}
    candidate_profile: Dict = {}
    final_report: Optional[str] = None

    def __init__(self, verification_plan: List[str]):
        super().__init__(
            verification_plan=verification_plan,
            topic_states={topic["name"]: TopicState(topic_type=topic["type"])
                         for topic in verification_plan}
        )

    @property
    def current_topic(self) -> Dict:
        return self.verification_plan[self.current_topic_index]

    @property
    def current_topic_state(self) -> TopicState:
        return self.topic_states[self.current_topic["name"]]

    def move_to_next_topic(self):
        if self.current_topic_index < len(self.verification_plan) - 1:
            self.current_topic_index += 1
            return True
        return False

    def is_last_topic(self):
        return self.current_topic_index == len(self.verification_plan) - 1

    def is_finished(self):
        return self.current_topic_index >= len(self.verification_plan)