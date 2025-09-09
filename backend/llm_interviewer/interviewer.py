from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


from .utils.prompts import *
from .utils.state_classes import HardTopicSummary, SoftTopicSummary, QuestionType, TopicType, InterviewState
from .utils.format_func import format_dict_for_prompt, format_history
from .utils.some_llm_func import should_end_topic_llm_based, generate_structured_output


class ResponseStatus(str, Enum):
    QUESTION = "question"  # Система задает вопрос
    REPORT = "report"  # Финальный отчет
    ERROR = "error"  # Ошибка

class InterviewResponse(BaseModel):
    status: ResponseStatus
    text: str
    current_topic: Optional[str] = None

class AIInterviewer:
    def __init__(self, llm, vacancy_name: str, hr_name: str, vacancy_general: str,
                 resume_context: str, verification_plan: List[Dict]):
        self.llm = llm
        self.vacancy_name = vacancy_name
        self.hr_name = hr_name
        self.vacancy_general = vacancy_general
        self.resume_context = resume_context
        self.state = InterviewState(verification_plan)
        self.is_interview_started = False

    def process_message(self, user_message: str = None) -> InterviewResponse:
        """
        Основной метод для обработки сообщений пользователя
        """
        # try:
            # Если интервью еще не начато, инициируем приветствие
        if not self.is_interview_started:
            self.is_interview_started = True
            return self._generate_greeting()

        # Обрабатываем ответ пользователя
        return self._process_user_response(user_message)

        # except Exception as e:
        #     return InterviewResponse(
        #         status=ResponseStatus.ERROR,
        #         text=f"Произошла ошибка при обработке сообщения: {str(e)}"
        #     )

    def _generate_greeting(self) -> InterviewResponse:
        """Генерирует приветственное сообщение"""
        greeting = f"Здравствуйте! Меня зовут {self.hr_name} и Я проведу с вами собеседование на позицию {self.vacancy_name}. "
        greeting += "Готовы ли вы начать?"

        topic_state = self.state.current_topic_state
        topic_state.conversation_history.append({
            "question": greeting,
            "answer": ""  # Ответ будет добавлен при обработке ответа пользователя
        })
        topic_state.questions_asked += 1

        return InterviewResponse(
            status=ResponseStatus.QUESTION,
            text=greeting,
            current_topic="Приветствие",
        )

    def _process_user_response(self, user_message: str) -> InterviewResponse:
        """Обрабатывает ответ пользователя и генерирует следующий вопрос или отчет"""
        current_topic = self.state.current_topic
        topic_state = self.state.current_topic_state

        if topic_state.questions_asked > 0:
            topic_state.conversation_history[-1]["answer"] = user_message

        # Определяем, нужно ли завершить текущую тему
        if self._should_end_topic():
            return self._complete_topic_and_move_next()

        # Генерируем следующий вопрос
        question_type = QuestionType.FIRST if topic_state.questions_asked == 0 else QuestionType.ADAPTIVE
        next_question = self._generate_question(question_type)

        # Сохраняем вопрос в историю
        topic_state.conversation_history.append({
            "question": next_question,
            "answer": ""  # Ответ будет добавлен при следующем вызове
        })
        topic_state.questions_asked += 1

        # Проверяем, не завершено ли интервью
        if self.state.is_finished():
            return self._generate_final_report()
        print(ResponseStatus.QUESTION)
        print(next_question)
        print(current_topic["name"])
        return InterviewResponse(
            status=ResponseStatus.QUESTION,
            text=next_question,
            current_topic=current_topic["name"],
        )

    def _should_end_topic(self) -> bool:
        """Определяет, нужно ли завершить текущую тему"""
        current_topic = self.state.current_topic
        topic_state = self.state.current_topic_state

        if current_topic["type"] == TopicType.GREETING:
            # Для приветствия проверяем, готов ли кандидат начать
            last_answer = topic_state.conversation_history[-1]["answer"].lower()
            positive_keywords = ["да", "готов", "конечно", "начали", "поехали"]
            if any(keyword in last_answer for keyword in positive_keywords):
                return True

        if current_topic["type"] == TopicType.VACANCY_INFO:
            if topic_state.questions_asked > 1:
                last_answer = topic_state.conversation_history[-1]["answer"].lower()
                negative_keywords = ["нет", "все понятно", "пока нет", "спасибо"]
                if any(keyword in last_answer for keyword in negative_keywords):
                    return True

        return should_end_topic_llm_based(
                        self.llm,
                        current_topic['type'],
                        current_topic["name"],
                        self.vacancy_name,
                        topic_state.conversation_history
                    )


    def _generate_question(self, question_type: QuestionType) -> str:
        current_topic = self.state.current_topic
        topic_state = self.state.current_topic_state
        topic_name = current_topic["name"]
        topic_type = current_topic["type"]

        if topic_type == TopicType.GREETING:
            if question_type == QuestionType.FIRST:
                pass
            else:
                prompt = greeting_adaptive_prompt.format(
                    hr_name=self.hr_name,
                    last_answer=topic_state.conversation_history[-1]["answer"],
                    history=format_history(topic_state.conversation_history)
                )

        elif topic_type == TopicType.VACANCY_INFO:
            if question_type == QuestionType.FIRST:
                vacancy_question = self.vacancy_general + ' У вас остались какие-то вопросы?'
                return vacancy_question
            else:
                prompt = vacancy_info_adaptive_prompt.format(
                    hr_name=self.hr_name,
                    last_question=topic_state.conversation_history[-1]["answer"],
                    history=format_history(topic_state.conversation_history)
                )
        

        elif topic_type == TopicType.HARD_SKILL: 
            if question_type == QuestionType.FIRST:
                prompt = first_hard_prompt.format(
                    vacancy_name=self.vacancy_name,
                    current_topic=topic_name,
                    resume_context=self.resume_context
                )
            else:
                prompt = adaptive_hard_prompt.format(
                    hr_name=self.hr_name,
                    vacancy_name=self.vacancy_name,
                    current_topic=topic_name,
                    history=format_history(topic_state.conversation_history)
                )
        elif topic_type == TopicType.SOFT_SKILL:
            if question_type == QuestionType.FIRST:
                prompt = first_soft_prompt.format(
                    vacancy_name=self.vacancy_name,
                    current_topic=topic_name,
                    resume_context=self.resume_context
                )
            else:
                prompt = adaptive_soft_prompt.format(
                    hr_name=self.hr_name,
                    vacancy_name=self.vacancy_name,
                    current_topic=topic_name,
                    history=format_history(topic_state.conversation_history)
                )

        response = self.llm.invoke(prompt)
        return response.content.strip()

    def _complete_topic_and_move_next(self) -> InterviewResponse: # , user_message: str
        """Завершает текущую тему, генерирует анализ и переходит к следующей"""
        try:
            current_topic = self.state.current_topic
            topic_state = self.state.current_topic_state
            topic_type = current_topic['type']
            
            # Генерируем структурированный анализ темы
            if topic_type == TopicType.HARD_SKILL or topic_type == TopicType.SOFT_SKILL:

                topic_summary = self.generate_topic_summary(current_topic["name"], topic_type)
                self.state.candidate_profile[current_topic["name"]] = topic_summary.dict()
            
            # Переходим к следующей теме
            if self.state.move_to_next_topic():
                next_question = self._generate_question(QuestionType.FIRST)
                
                next_topic_state = self.state.current_topic_state
                next_topic_state.conversation_history.append({
                    "question": next_question,
                    "answer": ""
                })
                next_topic_state.questions_asked += 1
                

                return InterviewResponse(
                    status=ResponseStatus.QUESTION,
                    text=next_question,
                    current_topic=self.state.current_topic["name"],
                )
            else:
                return self._generate_final_report()
            
        except Exception as e:
            error_message = f"Ошибка при завершении темы: {str(e)}"
            return InterviewResponse(
                status=ResponseStatus.ERROR,
                text=error_message
            )

    def generate_topic_summary(self, topic_name: str, topic_type: str) -> HardTopicSummary | SoftTopicSummary:
        """Генерирует структурированный анализ темы используя JSON output"""
        topic_state = self.state.topic_states[topic_name]

        if topic_type == TopicType.HARD_SKILL:
            prompt_template = hard_topic_summary_prompt
            output_model = HardTopicSummary
        elif topic_type == TopicType.SOFT_SKILL:
            prompt_template = soft_topic_summary_prompt
            output_model = SoftTopicSummary

        prompt_params = {
            "current_topic": topic_name,
            "vacancy_name": self.vacancy_name,
            "resume_context": self.resume_context,
            "history": format_history(topic_state.conversation_history)
        }  
          
        return generate_structured_output(
            llm=self.llm,
            prompt_template=prompt_template,
            output_model=output_model,
            **prompt_params
        )

    def _generate_final_report(self) -> InterviewResponse:
        """Генерирует финальный отчет на основе готовых выводов по темам"""
        try:
            # Собираем выводы по всем темам
            topic_summaries = []
            candidate_profile = self.state.candidate_profile 
            for topic in candidate_profile.keys():
                topic_summary = format_dict_for_prompt(
                    topic_name=topic,
                    data=candidate_profile[topic]
                )
                topic_summaries.append(topic_summary)
            
            # Форматируем выводы для включения в промпт
            summaries_text = "\n".join(topic_summaries)
            
            # Генерируем финальный отчет
            prompt = final_report_prompt.format(
                vacancy_name=self.vacancy_name,
                topic_evaluations=summaries_text
            )
            
            response = self.llm.invoke(prompt)
            report = response.content.strip()
            
            # Сохраняем отчет в состоянии
            self.state.final_report = report
            
            return InterviewResponse(
                status=ResponseStatus.REPORT,
                text=report,
            )
        
        except Exception as e:
            error_message = f"Ошибка при генерации финального отчета: {str(e)}"
            return InterviewResponse(
                status=ResponseStatus.ERROR,
                text=error_message
            )