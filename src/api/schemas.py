"""API 请求与响应模型。"""

from pydantic import BaseModel, Field


class ExtractRequest(BaseModel):
    """结构化提取请求。"""

    text: str = Field(min_length=1)


class AnalysisImportRequest(BaseModel):
    """分析记录导入请求。"""

    analysis: dict


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


class RewriteChapterRequest(BaseModel):
    """章节改写请求。"""

    chapter_index: int = Field(ge=0)
    instruction: str = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class RewriteBatchRequest(BaseModel):
    """批量章节改写请求。"""

    chapter_indices: list[int] = Field(min_length=1)
    instruction: str = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class ExportRequest(BaseModel):
    """导出请求。"""

    rewrites: list[dict] = Field(default_factory=list)
    title: str = Field(default="rewritten_novel")
