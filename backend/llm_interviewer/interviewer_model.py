from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key='как у Димы',
    model="openai/gpt-oss-20b:free", 
    temperature=0.3,
)