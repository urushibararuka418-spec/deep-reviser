"""FastAPI 路由定义。"""

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.api.schemas import (
    AnalysisImportRequest,
    ExportRequest,
    ExtractRequest,
    RewriteBatchRequest,
    RewriteChapterRequest,
    RewriteRequest,
    SegmentsRequest,
)
from src.api.services import get_app_service


router = APIRouter(prefix="/api")


@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    """上传并预处理小说文件。"""
    try:
        return await get_app_service().upload_fastapi_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/extract")
def extract(payload: ExtractRequest):
    """提取结构化信息。"""
    try:
        return get_app_service().extract(payload.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/analyses")
def analyses():
    """列出所有已保存分析记录。"""
    return {"items": get_app_service().list_analyses()}


@router.post("/import-analysis")
async def import_analysis(
    file: UploadFile | None = File(default=None),
    analysis_json: str | None = Form(default=None),
):
    """导入分析记录 JSON 文件或 JSON 字符串。"""
    try:
        if file is not None:
            content = await file.read()
            payload = json.loads(content.decode("utf-8"))
        elif analysis_json:
            payload = AnalysisImportRequest(analysis=json.loads(analysis_json)).analysis
        else:
            raise ValueError("请提供 analysis_json 或 JSON 文件。")

        return get_app_service().import_analysis(payload)
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/segments")
def segments(payload: SegmentsRequest):
    """按章节和 chunk_size 分段。"""
    return get_app_service().build_segments(payload.text, chunk_size=payload.chunk_size)


@router.post("/rewrite")
def rewrite(payload: RewriteRequest):
    """执行单段改写。"""
    try:
        return get_app_service().rewrite(
            payload.segment,
            payload.instruction,
            characters=payload.characters,
            lore_entries=payload.lore_entries,
            similar_segments=payload.similar_segments,
            temperature=payload.temperature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rewrite/chapter")
def rewrite_chapter(payload: RewriteChapterRequest):
    """执行单章批量改写。"""
    try:
        return get_app_service().rewrite_chapter(
            payload.chapter_index,
            payload.instruction,
            temperature=payload.temperature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rewrite/batch")
def rewrite_batch(payload: RewriteBatchRequest):
    """执行多章批量改写。"""
    try:
        return get_app_service().rewrite_batch(
            payload.chapter_indices,
            payload.instruction,
            temperature=payload.temperature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/export")
def export(payload: ExportRequest):
    """导出改写文本。"""
    return get_app_service().export_rewrites(payload.rewrites, title=payload.title)
