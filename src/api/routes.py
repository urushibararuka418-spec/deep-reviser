"""FastAPI 路由定义。"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.api.schemas import ExportRequest, ExtractRequest, RewriteRequest, SegmentsRequest
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


@router.post("/export")
def export(payload: ExportRequest):
    """导出改写文本。"""
    return get_app_service().export_rewrites(payload.rewrites, title=payload.title)
