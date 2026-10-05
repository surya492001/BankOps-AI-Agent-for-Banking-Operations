import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set in .env")


# "openrouter/free" lets OpenRouter pick any free model, so answers can
# vary in style between requests. Set LLM_MODEL to pin a specific model.
LLM_MODEL = os.getenv("LLM_MODEL", "openrouter/free")


llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=0,
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)
