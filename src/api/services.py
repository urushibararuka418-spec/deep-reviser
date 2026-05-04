"""供 API 与 UI 共用的应用服务。"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import delete

from src.config import settings
from src.database.models import (
    Chapter,
    Character,
    PlotEvent,
    RewriteHistory,
    StyleBaseline,
    WorldSetting,
)
from src.database.session import SessionLocal, init_db
from src.database.vector_store import VectorStore
from src.extractor.character_extractor import CharacterExtractor
from src.extractor.lore_extractor import LoreExtractor
from src.extractor.plot_extractor import PlotExtractor
from src.extractor.style_extractor import StyleExtractor
from src.preprocessor.chapter_splitter import ChapterSplitter
from src.preprocessor.file_loader import FileLoader
from src.rewriter.consistency_checker import ConsistencyChecker
from src.rewriter.context_assembler import ContextAssembler
from src.rewriter.rewrite_engine import RewriteEngine


_app_service: "AppService | None" = None


class AppService:
    """封装上传、提取、分段、改写、导出流程。"""

    def __init__(self):
        init_db()
        self.file_loader = FileLoader()
        self.chapter_splitter = ChapterSplitter()
        self.character_extractor = CharacterExtractor()
        self.plot_extractor = PlotExtractor()
        self.lore_extractor = LoreExtractor()
        self.style_extractor = StyleExtractor()
        self.context_assembler = ContextAssembler()
        self.rewrite_engine = RewriteEngine()
        self.consistency_checker = ConsistencyChecker()
        self.vector_store = VectorStore()

    def upload_file(self, file_path: str | Path) -> dict:
        """读取已保存文件并返回预处理结果。"""
        path = Path(file_path)
        text = self.file_loader.load(path)
        chapters = self.chapter_splitter.split_chapters(text)
        segments = self.chapter_splitter.split_segments(text)
        self._save_chapters(chapters)
        self._index_segments(segments)

        return {
            "filename": path.name,
            "path": str(path),
            "text": text,
            "chapters": chapters,
            "segments": segments,
            "chapter_count": len(chapters),
            "segment_count": len(segments),
        }

    async def upload_fastapi_file(self, file: UploadFile) -> dict:
        """保存 FastAPI 上传文件后走统一处理流程。"""
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in FileLoader.SUPPORTED:
            raise ValueError(
                f"不支持的文件格式: {suffix or 'unknown'}。支持的格式: {', '.join(sorted(FileLoader.SUPPORTED))}"
            )

        target_dir = settings.project_root / settings.upload_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{uuid4().hex}{suffix}"

        content = await file.read()
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise ValueError(f"文件过大，超过 {settings.max_upload_size_mb}MB 限制。")

        target_path.write_bytes(content)
        result = self.upload_file(target_path)
        result["original_filename"] = file.filename
        return result

    def extract(self, text: str) -> dict:
        """提取角色、剧情、设定与风格，并写入数据库/向量库。"""
        characters = self.character_extractor.extract(text).get("characters", [])
        events = self.plot_extractor.extract(text).get("events", [])
        lore_entries = self.lore_extractor.extract(text).get("entries", [])
        style = self.style_extractor.extract(text)

        self._save_extractions(characters, events, lore_entries, style)
        self._index_lore_entries(lore_entries)

        return {
            "characters": characters,
            "events": events,
            "lore_entries": lore_entries,
            "style": style,
        }

    def build_segments(self, text: str, chunk_size: int = 1500) -> dict:
        """返回章节与段落切分结果。"""
        chapters = self.chapter_splitter.split_chapters(text)
        segments = self.chapter_splitter.split_segments(text, chunk_size=chunk_size)
        return {
            "chapters": chapters,
            "segments": segments,
            "chapter_count": len(chapters),
            "segment_count": len(segments),
        }

    def rewrite(
        self,
        segment: str,
        instruction: str,
        characters: list[dict] | None = None,
        lore_entries: list[dict] | None = None,
        similar_segments: list[dict | str] | None = None,
        temperature: float | None = None,
    ) -> dict:
        """根据显式上下文执行单段改写。"""
        characters = characters or []
        lore_entries = lore_entries or []
        similar_segments = similar_segments or []

        if not similar_segments:
            similar_segments = self._search_similar_segments(segment)

        context = self.context_assembler.assemble(
            segment,
            characters=characters,
            lore_entries=lore_entries,
            similar_segments=similar_segments,
        )

        rewrite_kwargs = {}
        if temperature is not None:
            rewrite_kwargs["temperature"] = temperature

        rewritten = self.rewrite_engine.rewrite(
            segment,
            instruction,
            context,
            **rewrite_kwargs,
        )
        consistency = self.consistency_checker.check(
            segment,
            rewritten,
            characters=characters,
            settings=lore_entries,
        )

        self._save_rewrite(segment, rewritten, instruction)

        return {
            "rewritten_text": rewritten,
            "context": {
                "character_context": context.character_context,
                "lorebook_context": context.lorebook_context,
                "similar_context": context.similar_context,
            },
            "consistency": consistency,
        }

    def export_rewrites(self, rewrites: list[dict], title: str = "rewritten_novel") -> dict:
        """将改写结果导出为 txt 文件。"""
        safe_title = "".join(ch for ch in title if ch.isalnum() or ch in {"-", "_"}).strip("-_")
        safe_title = safe_title or "rewritten_novel"

        export_dir = settings.project_root / "data" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / f"{safe_title}.txt"

        parts = []
        for index, item in enumerate(rewrites, start=1):
            content = item.get("rewritten_text") or item.get("text") or ""
            if not content:
                continue
            parts.append(f"第 {index} 段\n{content}")

        export_text = "\n\n".join(parts)
        export_path.write_text(export_text, encoding="utf-8")

        return {
            "path": str(export_path),
            "content": export_text,
            "segment_count": len(parts),
        }

    def export_rewrites_to_tempfile(self, rewrites: list[dict], title: str = "rewritten_novel") -> str:
        """为 Gradio 生成临时下载文件。"""
        result = self.export_rewrites(rewrites, title=title)
        with NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
            handle.write(result["content"])
            return handle.name

    @staticmethod
    def parse_json_field(raw: str, default):
        """将 UI 文本框中的 JSON 转成 Python 数据。"""
        if not raw or not raw.strip():
            return default
        return json.loads(raw)

    def _save_chapters(self, chapters: list[dict]) -> None:
        with SessionLocal() as db:
            db.execute(delete(Chapter))
            db.add_all(
                [
                    Chapter(
                        index=chapter["index"],
                        title=chapter["title"],
                        content=chapter["content"],
                        char_count=len(chapter["content"]),
                    )
                    for chapter in chapters
                ]
            )
            db.commit()

    def _save_extractions(self, characters, events, lore_entries, style) -> None:
        with SessionLocal() as db:
            db.execute(delete(Character))
            db.execute(delete(PlotEvent))
            db.execute(delete(WorldSetting))
            db.execute(delete(StyleBaseline))

            db.add_all(
                [
                    Character(
                        name=item.get("name"),
                        aliases=item.get("aliases", []),
                        role_type=item.get("role_type"),
                        personality_traits=item.get("personality_traits", []),
                        abilities=item.get("abilities", []),
                        relationships=item.get("relationships", []),
                        character_arc=item.get("character_arc"),
                        first_appearance=item.get("first_appearance"),
                        quote_examples=item.get("quote_examples", []),
                    )
                    for item in characters
                ]
            )
            db.add_all(
                [
                    PlotEvent(
                        chapter_index=self._coerce_int(item.get("chapter")),
                        summary=item.get("summary"),
                        participants=item.get("participants", []),
                        location=item.get("location"),
                        cause_events=item.get("cause_events", []),
                        consequence_events=item.get("consequence_events", []),
                    )
                    for item in events
                ]
            )
            db.add_all(
                [
                    WorldSetting(
                        category=item.get("category"),
                        name=item.get("name"),
                        keywords=item.get("keywords", []),
                        description=item.get("description"),
                        first_chapter=item.get("first_chapter"),
                    )
                    for item in lore_entries
                ]
            )
            db.add(
                StyleBaseline(
                    pace=style.get("pace", ""),
                    sentence_length_preference=style.get("sentence_length_preference", ""),
                    dialogue_ratio=style.get("dialogue_ratio", ""),
                    tone=",".join(style.get("tone", [])),
                    common_rhetoric=style.get("common_rhetoric", []),
                    forbidden_patterns=style.get("forbidden_patterns", []),
                )
            )
            db.commit()

    def _save_rewrite(self, original: str, rewritten: str, instruction: str) -> None:
        with SessionLocal() as db:
            rewrite_count = db.query(RewriteHistory).count()
            db.add(
                RewriteHistory(
                    segment_id=f"rewrite_{rewrite_count + 1:04d}",
                    original_text=original,
                    rewritten_text=rewritten,
                    instruction=instruction,
                )
            )
            db.commit()

    def _index_segments(self, segments: list[dict]) -> None:
        if not segments:
            return
        texts = [segment["content"] for segment in segments]
        metadatas = [
            {
                "segment_id": segment["id"],
                "chapter_index": segment["chapter_index"],
                "chapter_title": segment["chapter_title"],
            }
            for segment in segments
        ]
        self.vector_store.add_segments(texts, metadatas)

    def _index_lore_entries(self, lore_entries: list[dict]) -> None:
        if not lore_entries:
            return
        texts = [
            " ".join(
                filter(
                    None,
                    [
                        item.get("name", ""),
                        " ".join(item.get("keywords", [])),
                        item.get("description", ""),
                    ],
                )
            )
            for item in lore_entries
        ]
        metadatas = [
            {
                "category": item.get("category", ""),
                "name": item.get("name", ""),
                "first_chapter": item.get("first_chapter", ""),
            }
            for item in lore_entries
        ]
        self.vector_store.add_lore_entries(texts, metadatas)

    def _search_similar_segments(self, segment: str) -> list[dict]:
        try:
            return self.vector_store.search("novel_segments", segment, k=3)
        except Exception:
            return []

    @staticmethod
    def _coerce_int(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


def get_app_service() -> AppService:
    """惰性创建共享服务实例，避免导入时产生外部依赖副作用。"""
    global _app_service
    if _app_service is None:
        _app_service = AppService()
    return _app_service
