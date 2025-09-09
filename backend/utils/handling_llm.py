#ОБЩАЯ ЛОГИКА: Грише через вебсокет отпарвляем кучу чанков - чанки преобразованы в текст -
#кидаем этот текст в ЛЛМ - ЛЛМ генерит ответ - кидаем в модель для озвучки - по вебсокету даем фронту
from llm_interviewer.interviewer_model import llm as imported_llm
from llm_interviewer.interviewer import AIInterviewer, ResponseStatus
llm = AIInterviewer(llm=imported_llm, vacancy_name="example", hr_name="Даша", vacancy_general="example", resume_context="example",verification_plan=[])