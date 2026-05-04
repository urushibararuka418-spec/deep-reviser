"""供 API 与 UI 共用的应用服务。"""

from __future__ import annotations

import difflib
import json
from datetime import datetime
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
        self.analyses_dir = settings.project_root / "data" / "analyses"
        self.analyses_dir.mkdir(parents=True, exist_ok=True)
        self.analyses: dict[str, dict] = {}
        self.active_analysis: dict | None = None
        self.current_text = ""
        self.load_analyses()

    def upload_file(self, file_path: str | Path, novel_title: str | None = None) -> dict:
        """读取已保存文件并返回预处理结果。"""
        path = Path(file_path)
        text = self.file_loader.load(path)
        chapters = self.chapter_splitter.split_chapters(text)
        segments = self.chapter_splitter.split_segments(text)
        resolved_title = (novel_title or path.stem or "未命名小说").strip() or "未命名小说"

        self._save_chapters(chapters)
        self._index_segments(segments)
        self._set_active_analysis(
            {
                "novel_title": resolved_title,
                "created_at": self._now_iso(),
                "characters": [],
                "events": [],
                "lore_entries": [],
                "style": {},
                "chapters": chapters,
                "segments": segments,
            },
            text=text,
        )

        return {
            "filename": path.name,
            "path": str(path),
            "novel_title": resolved_title,
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
        original_title = Path(file.filename or "").stem if file.filename else None
        result = self.upload_file(target_path, novel_title=original_title)
        result["original_filename"] = file.filename
        return result

    def extract(self, text: str) -> dict:
        """提取角色、剧情、设定与风格，并写入数据库/向量库。"""
        analysis = self._prepare_analysis_context(text)
        characters = self.character_extractor.extract(text).get("characters", [])
        events = self.plot_extractor.extract(text).get("events", [])
        lore_entries = self.lore_extractor.extract(text).get("entries", [])
        style = self.style_extractor.extract(text)

        self._save_extractions(characters, events, lore_entries, style)
        self._index_lore_entries(lore_entries)
        analysis.update(
            {
                "created_at": self._now_iso(),
                "characters": characters,
                "events": events,
                "lore_entries": lore_entries,
                "style": style,
            }
        )
        analysis = self.save_analysis(analysis)
        self._set_active_analysis(analysis, text=text)

        return analysis

    def save_analysis(self, analysis: dict) -> dict:
        """将分析结果保存到磁盘并刷新内存索引。"""
        normalized = self._normalize_analysis(analysis)
        file_path = self.analyses_dir / f"{self._safe_filename(normalized['novel_title'])}.json"
        file_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.analyses[normalized["novel_title"]] = {
            "data": normalized,
            "file_path": str(file_path),
        }
        return self._clone_analysis(normalized)

    def load_analyses(self) -> list[dict]:
        """扫描分析目录并加载已有记录。"""
        analyses = {}
        for file_path in sorted(self.analyses_dir.glob("*.json")):
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
                normalized = self._normalize_analysis(payload, default_title=file_path.stem)
            except (OSError, json.JSONDecodeError, ValueError):
                continue

            analyses[normalized["novel_title"]] = {
                "data": normalized,
                "file_path": str(file_path),
            }

        self.analyses = analyses
        return self.list_analyses()

    def list_analyses(self) -> list[dict]:
        """返回已保存分析记录的摘要列表。"""
        items = []
        for title, entry in self.analyses.items():
            data = entry["data"]
            items.append(
                {
                    "novel_title": title,
                    "created_at": data.get("created_at", ""),
                    "chapter_count": len(data.get("chapters", [])),
                    "segment_count": len(data.get("segments", [])),
                    "character_count": len(data.get("characters", [])),
                    "event_count": len(data.get("events", [])),
                    "lore_count": len(data.get("lore_entries", [])),
                    "file_path": entry["file_path"],
                }
            )
        return sorted(items, key=lambda item: (item["created_at"], item["novel_title"]), reverse=True)

    def import_analysis(
        self,
        analysis: dict | None = None,
        *,
        title: str | None = None,
        chapters: list[dict] | None = None,
        segments: list[dict] | None = None,
        characters: list[dict] | None = None,
        events: list[dict] | None = None,
        lore_entries: list[dict] | None = None,
        style: dict | None = None,
    ) -> dict:
        """导入外部分析记录，并切换为当前活动分析。"""
        if analysis is None:
            # 按类型文件导入时，将已上传字段合并为统一分析记录。
            analysis = {
                "novel_title": title,
                "chapters": chapters or [],
                "segments": segments or [],
                "characters": characters or [],
                "events": events or [],
                "lore_entries": lore_entries or [],
                "style": style or {},
            }

        saved = self.save_analysis(analysis)
        self.use_analysis(saved["novel_title"])
        return saved

    def use_analysis(self, novel_title: str) -> dict:
        """激活指定分析记录，供 UI 与改写流程复用。"""
        entry = self.analyses.get(novel_title)
        if entry is None:
            raise ValueError(f"未找到分析记录：{novel_title}")

        analysis = self._clone_analysis(entry["data"])
        self._hydrate_analysis(analysis)
        self._set_active_analysis(analysis, text=self._rebuild_text_from_chapters(analysis.get("chapters", [])))
        return self._clone_analysis(analysis)

    def rewrite_chapter(
        self,
        chapter_index: int,
        instruction: str,
        temperature: float | None = None,
    ) -> dict:
        """按章节逐段改写，并返回整章结果。"""
        analysis = self._require_active_analysis()
        chapter = self._get_chapter_by_index(analysis, chapter_index)
        segments = self._get_segments_for_chapter(analysis, chapter_index)
        rewritten_segments = self._rewrite_segments(
            segments,
            instruction,
            characters=analysis.get("characters", []),
            lore_entries=analysis.get("lore_entries", []),
            temperature=temperature,
        )
        original_text = "\n\n".join(segment["content"] for segment in segments if segment.get("content"))
        rewritten_text = "\n\n".join(
            item["rewritten_text"] for item in rewritten_segments if item.get("rewritten_text")
        )

        return {
            "chapter_index": chapter_index,
            "chapter_title": chapter.get("title", f"第 {chapter_index + 1} 章"),
            "original_text": original_text,
            "rewritten_text": rewritten_text,
            "rewritten_segments": rewritten_segments,
            "rewrite_count": len(rewritten_segments),
            "diff_html": self._build_diff_html(
                original_text,
                rewritten_text,
                fromdesc="原文",
                todesc="改写后",
            ),
            "stats": {
                "chapter_count": 1,
                "rewrite_count": len(rewritten_segments),
            },
        }

    def rewrite_batch(
        self,
        chapter_indices: list[int],
        instruction: str,
        temperature: float | None = None,
    ) -> dict:
        """对多个章节执行批量改写。"""
        unique_indices = []
        seen = set()
        for chapter_index in chapter_indices:
            resolved_index = self._coerce_int(chapter_index)
            if resolved_index in seen:
                continue
            seen.add(resolved_index)
            unique_indices.append(resolved_index)

        if not unique_indices:
            raise ValueError("请至少选择一个章节。")

        chapters = [
            self.rewrite_chapter(index, instruction, temperature=temperature)
            for index in unique_indices
        ]
        combined_original = self._combine_chapter_results(chapters, "original_text")
        combined_rewritten = self._combine_chapter_results(chapters, "rewritten_text")
        total_rewrites = sum(item["rewrite_count"] for item in chapters)

        return {
            "chapters": chapters,
            "original_text": combined_original,
            "rewritten_text": combined_rewritten,
            "rewrite_count": total_rewrites,
            "diff_html": self._build_diff_html(
                combined_original,
                combined_rewritten,
                fromdesc="原文",
                todesc="批量改写后",
            ),
            "stats": {
                "chapter_count": len(chapters),
                "rewrite_count": total_rewrites,
                "chapter_indices": unique_indices,
            },
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

    @staticmethod
    def get_analysis_text(analysis: dict) -> str:
        """根据章节信息重建展示用原文。"""
        chapters = analysis.get("chapters", []) if isinstance(analysis, dict) else []
        return "\n\n".join(
            filter(
                None,
                [
                    f"{chapter.get('title', '')}\n{chapter.get('content', '').strip()}".strip()
                    for chapter in chapters
                ],
            )
        )

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

    def _prepare_analysis_context(self, text: str) -> dict:
        if self.active_analysis is not None and self.current_text == text:
            return self._clone_analysis(self.active_analysis)

        chapters = self.chapter_splitter.split_chapters(text)
        segments = self.chapter_splitter.split_segments(text)
        return {
            "novel_title": self._guess_novel_title(),
            "created_at": self._now_iso(),
            "characters": [],
            "events": [],
            "lore_entries": [],
            "style": {},
            "chapters": chapters,
            "segments": segments,
        }

    def _hydrate_analysis(self, analysis: dict) -> None:
        self._save_chapters(analysis.get("chapters", []))
        self._save_extractions(
            analysis.get("characters", []),
            analysis.get("events", []),
            analysis.get("lore_entries", []),
            analysis.get("style", {}),
        )
        self._index_segments(analysis.get("segments", []))
        self._index_lore_entries(analysis.get("lore_entries", []))

    def _set_active_analysis(self, analysis: dict, text: str = "") -> None:
        self.active_analysis = self._normalize_analysis(analysis)
        self.current_text = text or self._rebuild_text_from_chapters(self.active_analysis.get("chapters", []))

    def _require_active_analysis(self) -> dict:
        if self.active_analysis is None:
            raise ValueError("请先上传文本、完成提取，或导入已有分析记录。")
        return self.active_analysis

    def _get_chapter_by_index(self, analysis: dict, chapter_index: int) -> dict:
        for chapter in analysis.get("chapters", []):
            if self._coerce_int(chapter.get("index")) == chapter_index:
                return chapter
        raise ValueError(f"未找到章节索引：{chapter_index}")

    def _get_segments_for_chapter(self, analysis: dict, chapter_index: int) -> list[dict]:
        segments = [
            segment
            for segment in analysis.get("segments", [])
            if self._coerce_int(segment.get("chapter_index")) == chapter_index and segment.get("content")
        ]
        if segments:
            return segments
        return self._build_fallback_segments(self._get_chapter_by_index(analysis, chapter_index))

    def _build_fallback_segments(self, chapter: dict, chunk_size: int = 1500) -> list[dict]:
        content = str(chapter.get("content", "")).strip()
        if not content:
            return []

        segments = []
        current_chunk = ""
        segment_index = 0
        for paragraph in content.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if current_chunk and len(current_chunk) + len(paragraph) + 2 > chunk_size:
                segments.append(
                    {
                        "id": f"chapter_{chapter.get('index', 0)}_{segment_index}",
                        "chapter_index": chapter.get("index", 0),
                        "chapter_title": chapter.get("title", "全文"),
                        "content": current_chunk,
                    }
                )
                current_chunk = ""
                segment_index += 1
            current_chunk = f"{current_chunk}\n\n{paragraph}".strip() if current_chunk else paragraph

        if current_chunk:
            segments.append(
                {
                    "id": f"chapter_{chapter.get('index', 0)}_{segment_index}",
                    "chapter_index": chapter.get("index", 0),
                    "chapter_title": chapter.get("title", "全文"),
                    "content": current_chunk,
                }
            )
        return segments

    def _rewrite_segments(
        self,
        segments: list[dict],
        instruction: str,
        characters: list[dict],
        lore_entries: list[dict],
        temperature: float | None = None,
    ) -> list[dict]:
        rewritten_segments = []
        for segment in segments:
            result = self.rewrite(
                segment.get("content", ""),
                instruction,
                characters=characters,
                lore_entries=lore_entries,
                temperature=temperature,
            )
            rewritten_segments.append(
                {
                    "segment_id": segment.get("id", ""),
                    "original_text": segment.get("content", ""),
                    "rewritten_text": result["rewritten_text"],
                    "context": result["context"],
                    "consistency": result["consistency"],
                }
            )
        return rewritten_segments

    @staticmethod
    def _combine_chapter_results(chapters: list[dict], field_name: str) -> str:
        return "\n\n".join(
            filter(
                None,
                [
                    f"{item.get('chapter_title', '')}\n{item.get(field_name, '').strip()}".strip()
                    for item in chapters
                ],
            )
        )

    @staticmethod
    def _build_diff_html(original_text: str, rewritten_text: str, fromdesc: str, todesc: str) -> str:
        return difflib.HtmlDiff(wrapcolumn=80).make_table(
            original_text.splitlines(),
            rewritten_text.splitlines(),
            fromdesc=fromdesc,
            todesc=todesc,
            context=True,
            numlines=2,
        )

    def _normalize_analysis(self, analysis: dict, default_title: str | None = None) -> dict:
        if not isinstance(analysis, dict):
            raise ValueError("分析记录格式错误，必须是 JSON 对象。")

        novel_title = str(analysis.get("novel_title") or default_title or "未命名小说").strip() or "未命名小说"
        chapters = analysis.get("chapters") if isinstance(analysis.get("chapters"), list) else []
        segments = analysis.get("segments") if isinstance(analysis.get("segments"), list) else []

        return {
            "novel_title": novel_title,
            "created_at": str(analysis.get("created_at") or self._now_iso()),
            "characters": analysis.get("characters") if isinstance(analysis.get("characters"), list) else [],
            "events": analysis.get("events") if isinstance(analysis.get("events"), list) else [],
            "lore_entries": analysis.get("lore_entries") if isinstance(analysis.get("lore_entries"), list) else [],
            "style": analysis.get("style") if isinstance(analysis.get("style"), dict) else {},
            "chapters": chapters,
            "segments": segments,
        }

    @staticmethod
    def _clone_analysis(analysis: dict) -> dict:
        return json.loads(json.dumps(analysis, ensure_ascii=False))

    @staticmethod
    def _safe_filename(title: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        safe_title = "".join("_" if char in invalid_chars else char for char in title).strip().strip(".")
        return safe_title or "未命名小说"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat()

    def _guess_novel_title(self) -> str:
        if self.active_analysis and self.active_analysis.get("novel_title"):
            return self.active_analysis["novel_title"]
        return "未命名小说"

    def _rebuild_text_from_chapters(self, chapters: list[dict]) -> str:
        return self.get_analysis_text({"chapters": chapters})

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
