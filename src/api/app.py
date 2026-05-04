"""FastAPI 应用入口。"""

from fastapi import FastAPI

from src.api.routes import router


app = FastAPI(title="Deep Reviser API")
app.include_router(router)


@app.get("/health")
def health():
    """健康检查。"""
    return {"status": "ok"}
