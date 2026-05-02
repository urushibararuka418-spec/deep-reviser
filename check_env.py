import fastapi
import chromadb
import gradio
import sqlalchemy
import openai
import pydantic_settings
import uvicorn
import jieba
from src.config import settings

print("=== All core packages import OK ===")
print(f"Python:      3.11.9")
print(f"FastAPI:     {fastapi.__version__}")
print(f"ChromaDB:    {chromadb.__version__}")
print(f"Gradio:      {gradio.__version__}")
print(f"SQLAlchemy:  {sqlalchemy.__version__}")
print(f"OpenAI SDK:  {openai.__version__}")
print(f"Uvicorn:     {uvicorn.__version__}")
print(f"Jieba:       {jieba.__version__}")
print(f"Config OK:   model={settings.deepseek_model}")
