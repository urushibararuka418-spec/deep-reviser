"""LoreExtractor 测试套件 — TDD Step 1: 先写测试，预期全部 FAIL"""

from unittest.mock import MagicMock, patch

from src.extractor.lore_extractor import LORE_EXTRACTION_PROMPT, LoreExtractor


# ============================================================
# test_prompt_is_chinese — 确认提示词包含中文字段名
# ============================================================
def test_prompt_is_chinese():
    """确认提示词包含世界观设定相关的中文/英文关键词"""
    assert "设定" in LORE_EXTRACTION_PROMPT or "lore" in LORE_EXTRACTION_PROMPT.lower()
    assert "category" in LORE_EXTRACTION_PROMPT
    assert "name" in LORE_EXTRACTION_PROMPT
    assert "keywords" in LORE_EXTRACTION_PROMPT
    assert "description" in LORE_EXTRACTION_PROMPT
    assert "first_chapter" in LORE_EXTRACTION_PROMPT
    assert "entries" in LORE_EXTRACTION_PROMPT


# ============================================================
# test_extract_lore_entries — mock DeepSeekClient，验证提取结果
# ============================================================
@patch("src.extractor.lore_extractor.DeepSeekClient")
def test_extract_lore_entries(mock_ds_class):
    """extract() 应调用 client.extract_json 并返回设定条目列表"""
    mock_client = MagicMock()
    mock_ds_class.return_value = mock_client
    mock_client.extract_json.return_value = {
        "entries": [
            {
                "category": "组织",
                "name": "青云宗",
                "keywords": ["修仙", "宗门", "正道"],
                "description": "位于东州的名门正派，以剑修闻名。",
                "first_chapter": "第三章",
            }
        ]
    }

    extractor = LoreExtractor()
    result = extractor.extract("测试小说全文...")

    assert len(result["entries"]) == 1
    assert result["entries"][0]["name"] == "青云宗"
    assert result["entries"][0]["category"] == "组织"

    mock_client.extract_json.assert_called_once_with(
        LORE_EXTRACTION_PROMPT, "测试小说全文..."
    )


# ============================================================
# test_extract_empty_lore — 空设定列表场景
# ============================================================
@patch("src.extractor.lore_extractor.DeepSeekClient")
def test_extract_empty_lore(mock_ds_class):
    """无明显世界观设定时，应返回空的 entries 列表"""
    mock_client = MagicMock()
    mock_ds_class.return_value = mock_client
    mock_client.extract_json.return_value = {"entries": []}

    extractor = LoreExtractor()
    result = extractor.extract("短文本")

    assert result["entries"] == []
    assert len(result["entries"]) == 0


# ============================================================
# test_extractor_with_injected_client — 验证可注入自定义 client
# ============================================================
def test_extractor_with_injected_client():
    """通过构造函数注入 client，避免依赖真实 API"""
    mock_client = MagicMock()
    mock_client.extract_json.return_value = {
        "entries": [
            {
                "category": "地理",
                "name": "黑水城",
                "keywords": ["边境", "商路"],
                "description": "一座位于边境要道的贸易城市。",
                "first_chapter": "第一章",
            }
        ]
    }

    extractor = LoreExtractor(client=mock_client)
    result = extractor.extract("任意小说文本")

    assert result["entries"][0]["name"] == "黑水城"
    mock_client.extract_json.assert_called_once()
