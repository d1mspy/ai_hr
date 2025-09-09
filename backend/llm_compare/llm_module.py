import time
import requests
import json
from settings.settings import settings

"""
Пример использования. 
analyzer = LLMAnalyzer(api_key=API_KEY)
analyzer.set_data(resume, vacancy)

if analyzer.analyze(): // Отображение результата в формате json. Можно просто обращаться к полям объекта класса
  results = analyzer.get_results()
  print(json.dumps(results, ensure_ascii=False, indent=2))
"""

class LLMAnalyzer:
    
    # поля модели
    api_key: str = settings.analyzer.api_key, 
    model_name: str = settings.analyzer.model_name, 
    temperature: float = settings.analyzer.temperature

    def __init__(self):
        """
        Инициализация анализатора.
        """
        
        # Поля для хранения данных
        self.resume_text = None
        self.vacancy_text = None


        # Поля для хранения сокращенных копий данных
        self.compressed_data = None # Для Гриши
        self.vacancy_meta = None # Для Гриши
        
        # Поля для результатов
        self.decision = None # True / False
        self.match_percentage = None # Проценты
        self.reasoning_report = None # Обоснование решения (не берем)
        self.candidate_feedback = None # Фидбек
        self.hard_interview_topics = [] # Для Гриши
        self.soft_interview_topics = [] # Для Гриши
        
        # Поля для метрик - в продакт не идут
        self.response_time_seconds = 0
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.speed_tokens_per_second = 0
        
        # Системный промт 
        self.SYSTEM_PROMPT = """
# ROLE
Ты — AI-рекрутер. Твоя задача — проанализировать текст резюме и текст вакансии, чтобы принять обоснованное решение о допуске кандидата на собеседование.

# ИНСТРУКЦИИ
1.  **АНАЛИЗ:** Внимательно прочитай оба текста. Выдели все ключевые требования вакансии (обязанности, навыки, опыт, образование) и сопоставь их с данными из резюме.
2.  **ВЕСА КРИТЕРИЕВ:** При оценке руководствуйся следующими весами:
    -   Технические (Hard) навыки: 60% (навыки и опыт считается соответствующими **ТОЛЬКО если они релевантны** требованиям вакансии, присутствует **ПРЯМОЙ опыт работы по специальности**; опыт в смежных областях учитывается, но вносит вдвое меньше очков в общий зачет навыка)
    -   Софт-скилы и личные качества: 20%
    -   Опыт работы: 10%
    -   Образование: 5% (наличие у кандидата образования уровня **выше требуемого** считается за **ПОЛНОЕ соответствие**)
    -   Прочие условия (формат работы, командировки и т.д.): 5%
    -  *ВАЖНО*: не жалей кандидата, будь **ОБЪЕКТИВЕН**. Не старайся натянуть его умения и навыки на требования вакансии, но и не занижай их. Будь строг, но справедлив.
3.  **РЕШЕНИЕ:** Рассчитай общий процент соответствия.
    -   Если процент >= 75% -> доступ на собеседование **TRUE**.
    -   Если процент < 75% -> доступ **FALSE**.
4.  **ФИДБЕК:** Сгенерируй два текста:
    -   **Аргументация:** Детальный отчет для рекрутера с ходом мыслей.
    -   **Видбек:** Краткая, вежливая и конструктивная выжимка для кандидата (3-4 предложения).
5.   **ТЕМЫ ДЛЯ СОБЕСЕДОВАНИЯ:**
    -   Если решение "Доступ на собеседование предоставлен" -> сгенерируй 20 тем для обсуждения на интервью.
    -   **Формат:** 10 тем по hard skills + 10 тем по soft skills.
    -   **Hard skills вопросы:** Должны проверять общие профессиональные компетенции и умения.
    -   **Soft skills вопросы:** Должны оценивать личностные качества, коммуникативные навыки и teamwork.
    -   **Баланс тем для Hard skills:**
        -   5 тем на обнаружение  **наиболее слабых мест или пробелов** кандидата, выявленных во время анализа.
        -   2 темы на выявление *противоречий с резюме и красных флагов* в процессе собеседования.\
        -   3 общих темы, соответствующих вакансии.
     -   **Баланс тем для Soft skills:**
        -   3 тем на обнаружение  **наиболее слабых мест или пробелов** кандидата, выявленных во время анализа.
        -   7 общих темы, соответствующих вакансии.
    -   **Конкретность:** Темы должны быть конкретными и проверяемыми, охватывать разные аспекты резюме и требований вакансии.
6.  **ОСНОВНАЯ ИНФОРМАЦИЯ О ВАКАНСИИ:**
    -   Извлеки основные атрибуты вакансии в структурированном виде. Вот *ЧЕТКИЙ И ОГРАНИЧЕННЫЙ* список полей, которые нужно *ДОСЛОВНО* извлечь: Название, Регион, Город, Адрес, Тип трудового, График работы, Доход, Оклад макс., Оклад мин., Годовая премия, Тип премирования, Уровень образования, Требуемый опыт работы, Навыки работы на компьютере, Знание иностранных языков, Уровень владения языками, Наличие командировок, Дополнительная информация
    -   **Формат:** "Ключ: Значение". Ячейки, где данные отсутсвуют, заполняй в формате: "Ключ: null".
    -   **Фокус:** *НЕ АНАЛИЗИРУЙ И НЕ ФАНТАЗРУЙ*, строго извлекай данные из соответсвующих ячеек. 
7.  **СЖАТЫЕ КОПИИ РЕЗЮМЕ И ВАКАНСИИ ДЛЯ СЛЕДУЮЩЕГО ЭТАПА:**
    -   Подготовь сжатые представления РЕЗЮМЕ и ВАКАНСИИ для этапа собеседования.
    -   **Степень сжатия:** Адаптивная. Определи на основе богатства опыта (для РЕЗЮМЕ) и списка требований (для ВАКАНСИИ).
    -   **При обработке РЕЗЮМЕ обрати внимание**:
        -   Для плотных, насыщенных резюме -> сохрани больше деталей (сжатие на 15 - 25 %)
        -   Для простых или коротких резюме -> более сильное сжатие (сжатие на 30 - 40 %)
        -   РЕЗЮМЕ *ПОСЛЕ* сжатия должно содержать *НЕ МЕНЕЕ 30%* символов от *ИЗНАЧАЛЬНОЙ* версии.
    -   **Формат:** Текст в формате структурированного списка. 
    -   **Фокус:** Сохрани всё, что важно для оценки квалификации и проведения собеседования. Обращай внимание на *ключевые навыки, опыт и технологии, важные для собеседования* (для РЕЗЮМЕ) и *основные требования и обязанности* (для ВАКАНСИИ). Делай акцент на том, что ты *посчитал важным на этапе резюме и вакансии*.

# ФОРМАТ ОТВЕТА
Верни ответ ТОЛЬКО в виде JSON-объекта со следующей структурой. Никакого другого текста.
"""
       # Пользовательский промт
        self.USER_PROMPT_TEMPLATE = """
Проведи анализ и сгенерируй отчет на основе предоставленных текстов.

**ТЕКСТ ВАКАНСИИ:**
{vacancy_text}

**ТЕКСТ РЕЗЮМЕ:**
{resume_text}

**СГЕНЕРИРУЙ ОТЧЕТ СЛЕДУЮЩЕГО ВИДА:**
{{
  "decision": "True", // Или "False"
  "match_percentage": 75, // Рассчитанный процент соответствия (целое число)
  "reasoning_report": "Детальный развернутый текст на 5-10 предложений. Аргументируй решение. Укажи: 1) Главные strengths кандидата, соотнесенные с требованиями. 2) Ключевые пробелы (gaps), которые повлияли на решение. 3) Как были применены веса критериев при оценке. 4) Общую логику вывода процента.",
  "candidate_feedback": "Краткий видбек для кандидата (3-4 предложения). Вежливый и конструктивный. Если доступ предоставлен — сообщи об этом и укажи сильные стороны. Если нет — вежливо откажи, укажи ДВЕ - ТРИ главных причины и дай рекомендацию для улучшения (например, 'Рекомендуем обратить внимание на изучение Kubernetes')."
  "hard_interview_topics": ["Название темы"]. // ЗАПОЛНЯТЬ ТОЛЬКО ЕСЛИ ДОСТУП ПРЕДОСТАВЛЕН. Иначе - пустой массив [].
  "soft_interview_topics":["Назвернутое название темы"]. // ЗАПОЛНЯТЬ ТОЛЬКО ЕСЛИ ДОСТУП ПРЕДОСТАВЛЕН. Иначе - пустой массив [].
  "vacancy_meta":"Ключ1: Значение1\n Ключ2: Значение2",
  "compressed_data": "РЕЗЮМЕ\n- Ключевой навык 1 с контекстом\n- Ключевой навык 2 с контекстом\n- Основной опыт работы\ВАКАНСИЯ\n- Основное требование 1\n- Основное требование 2\n- Ключевая обязанность"".
"""
    def set_data(self, resume_text: str, vacancy_text: str):
        """
        Установка данных для анализа.

        Args:
            resume_text (str): Текст резюме кандидата
            vacancy_text (str): Текст описания вакансии
        """
        self.resume_text = resume_text
        self.vacancy_text = vacancy_text
    
    def analyze(self) -> bool:
        """
        Запуск анализа соответствия резюме и вакансии.

        Returns:
            bool: True если анализ успешен, False если произошла ошибка
        """
        if not self.resume_text or not self.vacancy_text:
            raise ValueError("Не установлены текст резюме или вакансии")

        # Формируем пользовательский промт
        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            vacancy_text=self.vacancy_text,
            resume_text=self.resume_text
        )

        # Отправляем запрос к LLM
        result = self._send_to_llm(user_prompt)
        
        if not result['success']:
            return False

        # Парсим результат
        return self._parse_result(result['content'])

    def _send_to_llm(self, user_prompt: str, max_tokens: int = 100000) -> dict:
        """
        Отправляет запрос к LLM через OpenRouter API.

        Args:
            user_prompt (str): Пользовательский промт с данными
            max_tokens (int): Максимальное количество токенов в ответе

        Returns:
            dict: Результат запроса
        """
        url = settings.analyzer.url
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens
        }

        start_time = time.time()

        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()
            end_time = time.time()

            # Извлекаем информацию
            content = result['choices'][0]['message']['content']
            usage = result.get('usage', {})

            # Сохраняем метрики
            self.response_time_seconds = round(end_time - start_time, 2)
            self.prompt_tokens = usage.get('prompt_tokens', 0)
            self.completion_tokens = usage.get('completion_tokens', 0)
            self.total_tokens = usage.get('total_tokens', 0)
            self.speed_tokens_per_second = round(
                usage.get('completion_tokens', 0) / (end_time - start_time), 2
            ) if (end_time - start_time) > 0 else 0

            return {
                'success': True,
                'content': content,
                'model_used': result.get('model', self.model_name)
            }

        except Exception as e:
            self.response_time_seconds = round(time.time() - start_time, 2)
            return {
                'success': False,
                'error': str(e)
            }

    def _parse_result(self, content: str) -> bool:
        """
        Парсит результат от LLM.
        """
        try:
            data = json.loads(content)
            
            self.decision = data.get('decision')
            self.match_percentage = data.get('match_percentage')
            self.reasoning_report = data.get('reasoning_report')
            self.candidate_feedback = data.get('candidate_feedback')
            self.hard_interview_topics = data.get('hard_interview_topics', [])
            self.soft_interview_topics = data.get('soft_interview_topics', [])
            self.vacancy_meta = data.get('vacancy_meta')
            self.compressed_data = data.get('compressed_data')

            return True
            
        except json.JSONDecodeError:
            # Если не JSON, пробуем извлечь из текста
            return False

    def get_results(self) -> dict:
        """
        Возвращает результаты анализа.

        Returns:
            dict: Словарь с результатами и метриками
        """
        return {
            'decision': self.decision,
            'match_percentage': self.match_percentage,
            'reasoning_report': self.reasoning_report,
            'candidate_feedback': self.candidate_feedback,
            'hard_interview_topics': self.hard_interview_topics,
            'soft_interview_topics':self.soft_interview_topics,
            'metrics': {
                'response_time_seconds': self.response_time_seconds,
                'total_tokens': self.total_tokens,
                'prompt_tokens': self.prompt_tokens,
                'completion_tokens': self.completion_tokens,
                'speed_tokens_per_second': self.speed_tokens_per_second
            },
            'compressed_data': self.compressed_data,
            'vacancy_meta': self.vacancy_meta
        }
    def clear_results(self):
        """
        Очищает результаты предыдущего анализа.
        """
        self.resume_text = None
        self.vacancy_text = None


        # Поля для хранения сокращенных копий данных
        self.compressed_data = None
        self.vacancy_meta = None
        
        # Поля для результатов
        self.decision = None
        self.match_percentage = None
        self.reasoning_report = None
        self.candidate_feedback = None
        self.hard_interview_topics = []
        self.soft_interview_topics = []

        # Поля для метрик
        self.response_time_seconds = 0
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.speed_tokens_per_second = 0
