"""FastAPI 路由定义。"""

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.api.schemas import (
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


async def _read_optional_json_file(file: UploadFile | None, field_name: str):
    """读取可选 JSON 文件；未上传时返回 None。"""
    if file is None:
        return None

    try:
        content = await file.read()
        return json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{field_name} JSON 解析失败: {exc}") from exc


@router.post("/import-analysis")
async def import_analysis(
    title: str = Form("未命名导入"),
    chapters_json: UploadFile | None = File(default=None),
    segments_json: UploadFile | None = File(default=None),
    characters_json: UploadFile | None = File(default=None),
    events_json: UploadFile | None = File(default=None),
    lore_json: UploadFile | None = File(default=None),
    style_json: UploadFile | None = File(default=None),
):
    """按类型导入分析记录 JSON 文件。"""
    try:
        field_payloads = {
            "chapters": await _read_optional_json_file(chapters_json, "章节"),
            "segments": await _read_optional_json_file(segments_json, "段落"),
            "characters": await _read_optional_json_file(characters_json, "角色"),
            "events": await _read_optional_json_file(events_json, "剧情"),
            "lore_entries": await _read_optional_json_file(lore_json, "设定"),
            "style": await _read_optional_json_file(style_json, "风格"),
        }
        if not any(value is not None for value in field_payloads.values()):
            raise ValueError("请至少上传一个 JSON 文件。")

        normalized_payload = {}
        for field_name, value in field_payloads.items():
            if value is None:
                continue

            # 兼容直接上传列表/对象，或包裹在同名字段中的 JSON。
            if isinstance(value, dict) and field_name in value:
                normalized_payload[field_name] = value[field_name]
            else:
                normalized_payload[field_name] = value

        return get_app_service().import_analysis(title=title, **normalized_payload)
    except ValueError as exc:
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
