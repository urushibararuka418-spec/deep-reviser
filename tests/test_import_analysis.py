"""导入分析记录相关测试。"""

from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.services import AppService


def _build_service_stub():
    service = AppService.__new__(AppService)
    service.saved_payload = None
    service.used_title = None

    def _save_analysis(analysis):
        service.saved_payload = AppService._normalize_analysis(service, analysis)
        return AppService._clone_analysis(service.saved_payload)

    def _use_analysis(novel_title):
        service.used_title = novel_title
        return AppService._clone_analysis(service.saved_payload)

    service.save_analysis = _save_analysis
    service.use_analysis = _use_analysis
    service._now_iso = lambda: "2026-05-05T00:00:00"
    return service


def test_import_analysis_merges_per_type_payloads(tmp_path):
    """服务层应支持按类型合并导入。"""
    service = _build_service_stub()

    result = service.import_analysis(
        title="分类型导入",
        chapters=[{"index": 0, "title": "第一章", "content": "章节内容"}],
        segments=[{"chapter_index": 0, "content": "段落内容"}],
        characters=[{"name": "主角"}],
        events=[{"summary": "事件"}],
        lore_entries=[{"key": "设定", "value": "世界观"}],
        style={"tone": "冷峻"},
    )

    assert result["novel_title"] == "分类型导入"
    assert result["chapters"] == [{"index": 0, "title": "第一章", "content": "章节内容"}]
    assert result["segments"] == [{"chapter_index": 0, "content": "段落内容"}]
    assert result["characters"] == [{"name": "主角"}]
    assert result["events"] == [{"summary": "事件"}]
    assert result["lore_entries"] == [{"key": "设定", "value": "世界观"}]
    assert result["style"] == {"tone": "冷峻"}


def test_import_analysis_fills_missing_fields_with_empty_values(tmp_path):
    """未上传的类型应保留为空值。"""
    service = _build_service_stub()

    result = service.import_analysis(
        title="仅角色",
        characters=[{"name": "配角"}],
    )

    assert result["novel_title"] == "仅角色"
    assert result["chapters"] == []
    assert result["segments"] == []
    assert result["characters"] == [{"name": "配角"}]
    assert result["events"] == []
    assert result["lore_entries"] == []
    assert result["style"] == {}


def test_import_analysis_api_accepts_split_json_uploads(monkeypatch):
    """API 应读取多个分类型 JSON 文件并合并导入。"""
    captured = {}

    class StubService:
        def import_analysis(self, **kwargs):
            captured.update(kwargs)
            return {
                "novel_title": kwargs["title"],
                "chapters": kwargs.get("chapters", []),
                "segments": kwargs.get("segments", []),
                "characters": kwargs.get("characters", []),
                "events": kwargs.get("events", []),
                "lore_entries": kwargs.get("lore_entries", []),
                "style": kwargs.get("style", {}),
            }

    monkeypatch.setattr("src.api.routes.get_app_service", lambda: StubService())
    client = TestClient(app)

    response = client.post(
        "/api/import-analysis",
        data={"title": "接口导入"},
        files={
            "chapters_json": ("chapters.json", io.BytesIO(json.dumps({"chapters": [{"index": 0}]}).encode("utf-8")), "application/json"),
            "characters_json": ("characters.json", io.BytesIO(json.dumps([{"name": "主角"}]).encode("utf-8")), "application/json"),
            "style_json": ("style.json", io.BytesIO(json.dumps({"style": {"tone": "克制"}}).encode("utf-8")), "application/json"),
        },
    )

    assert response.status_code == 200
    assert captured == {
        "title": "接口导入",
        "chapters": [{"index": 0}],
        "characters": [{"name": "主角"}],
        "style": {"tone": "克制"},
    }


def test_import_analysis_api_rejects_empty_upload(monkeypatch):
    """API 未上传任何 JSON 文件时应返回 400。"""

    class StubService:
        def import_analysis(self, **kwargs):  # pragma: no cover
            raise AssertionError("不应调用服务层")

    monkeypatch.setattr("src.api.routes.get_app_service", lambda: StubService())
    client = TestClient(app)

    response = client.post("/api/import-analysis", data={"title": "空导入"})

    assert response.status_code == 400
    assert response.json()["detail"] == "请至少上传一个 JSON 文件。"
