"""API 请求与响应模型。"""

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    """结构化提取请求。"""

    text: str = Field(min_length=1)


class SegmentsRequest(BaseModel):
    """分段请求。"""

    text: str = Field(min_length=1)
    chunk_size: int = Field(default=1500, ge=100, le=10000)


class RewriteRequest(BaseModel):
    """改写请求。"""

    segment: str = Field(min_length=1)
    instruction: str = Field(min_length=1)
    characters: list[dict] = Field(default_factory=list)
    lore_entries: list[dict] = Field(default_factory=list)
    similar_segments: list[dict | str] = Field(default_factory=list)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class ExportRequest(BaseModel):
    """导出请求。"""

    rewrites: list[dict] = Field(default_factory=list)
    title: str = Field(default="rewritten_novel")
