from langchain_openai import ChatOpenAI
from settings.settings import settings

llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.analyzer.api_key,
    model="openai/gpt-oss-20b:free", 
    temperature=0.3,
)