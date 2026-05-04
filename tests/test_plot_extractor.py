"""PlotExtractor 测试套件 — TDD Step 1: 先写测试，预期全部 FAIL"""

from unittest.mock import MagicMock, patch

from src.extractor.plot_extractor import PLOT_EXTRACTION_PROMPT, PlotExtractor


# ============================================================
# test_prompt_is_chinese — 确认提示词包含中文字段名
# ============================================================
def test_prompt_is_chinese():
    """确认提示词包含剧情事件相关的中文/英文关键词"""
    assert "剧情" in PLOT_EXTRACTION_PROMPT or "plot" in PLOT_EXTRACTION_PROMPT.lower()
    assert "event_id" in PLOT_EXTRACTION_PROMPT
    assert "chapter" in PLOT_EXTRACTION_PROMPT
    assert "summary" in PLOT_EXTRACTION_PROMPT
    assert "participants" in PLOT_EXTRACTION_PROMPT
    assert "location" in PLOT_EXTRACTION_PROMPT
    assert "cause_events" in PLOT_EXTRACTION_PROMPT
    assert "consequence_events" in PLOT_EXTRACTION_PROMPT
    assert "events" in PLOT_EXTRACTION_PROMPT


# ============================================================
# test_extract_plot_events — mock DeepSeekClient，验证提取结果
# ============================================================
@patch("src.extractor.plot_extractor.DeepSeekClient")
def test_extract_plot_events(mock_ds_class):
    """extract() 应调用 client.extract_json 并返回剧情事件列表"""
    mock_client = MagicMock()
    mock_ds_class.return_value = mock_client
    mock_client.extract_json.return_value = {
        "events": [
            {
                "event_id": "E001",
                "chapter": "第二章",
                "summary": "李明在山门试炼中击败对手，正式拜入青云宗。",
                "participants": ["李明", "长老", "赵峰"],
                "location": "青云宗山门",
                "cause_events": ["E000"],
                "consequence_events": ["E002"],
            }
        ]
    }

    extractor = PlotExtractor()
    result = extractor.extract("测试小说全文...")

    assert len(result["events"]) == 1
    assert result["events"][0]["event_id"] == "E001"
    assert result["events"][0]["participants"][0] == "李明"

    mock_client.extract_json.assert_called_once_with(
        PLOT_EXTRACTION_PROMPT, "测试小说全文..."
    )


# ============================================================
# test_extract_empty_plot — 空剧情列表场景
# ============================================================
@patch("src.extractor.plot_extractor.DeepSeekClient")
def test_extract_empty_plot(mock_ds_class):
    """无明显剧情推进时，应返回空的 events 列表"""
    mock_client = MagicMock()
    mock_ds_class.return_value = mock_client
    mock_client.extract_json.return_value = {"events": []}

    extractor = PlotExtractor()
    result = extractor.extract("短文本")

    assert result["events"] == []
    assert len(result["events"]) == 0


# ============================================================
# test_extractor_with_injected_client — 验证可注入自定义 client
# ============================================================
def test_extractor_with_injected_client():
    """通过构造函数注入 client，避免依赖真实 API"""
    mock_client = MagicMock()
    mock_client.extract_json.return_value = {
        "events": [
            {
                "event_id": "E099",
                "chapter": "终章",
                "summary": "主角完成复仇并离开故土。",
                "participants": ["主角"],
                "location": "皇城",
                "cause_events": ["E050"],
                "consequence_events": [],
            }
        ]
    }

    extractor = PlotExtractor(client=mock_client)
    result = extractor.extract("任意小说文本")

    assert result["events"][0]["location"] == "皇城"
    mock_client.extract_json.assert_called_once()
