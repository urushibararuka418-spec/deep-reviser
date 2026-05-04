"""StyleExtractor 测试套件 — TDD Step 1: 先写测试，预期全部 FAIL"""

from unittest.mock import MagicMock, patch

from src.extractor.style_extractor import STYLE_EXTRACTION_PROMPT, StyleExtractor


# ============================================================
# test_prompt_is_chinese — 确认提示词包含中文字段名
# ============================================================
def test_prompt_is_chinese():
    """确认提示词包含风格分析相关的中文/英文关键词"""
    assert "风格" in STYLE_EXTRACTION_PROMPT or "style" in STYLE_EXTRACTION_PROMPT.lower()
    assert "pace" in STYLE_EXTRACTION_PROMPT
    assert "sentence_length_preference" in STYLE_EXTRACTION_PROMPT
    assert "dialogue_ratio" in STYLE_EXTRACTION_PROMPT
    assert "tone" in STYLE_EXTRACTION_PROMPT
    assert "common_rhetoric" in STYLE_EXTRACTION_PROMPT
    assert "forbidden_patterns" in STYLE_EXTRACTION_PROMPT


# ============================================================
# test_extract_style_profile — mock DeepSeekClient，验证提取结果
# ============================================================
@patch("src.extractor.style_extractor.DeepSeekClient")
def test_extract_style_profile(mock_ds_class):
    """extract() 应调用 client.extract_json 并返回风格基线信息"""
    mock_client = MagicMock()
    mock_ds_class.return_value = mock_client
    mock_client.extract_json.return_value = {
        "pace": "中快节奏",
        "sentence_length_preference": "短句为主，夹杂少量中长句",
        "dialogue_ratio": "对话约占四成",
        "tone": ["克制", "冷峻", "悬疑感"],
        "common_rhetoric": ["环境烘托", "动作描写", "心理独白"],
        "forbidden_patterns": ["现代网络口语", "出戏的解释性旁白"],
    }

    extractor = StyleExtractor()
    result = extractor.extract("测试小说全文...")

    assert result["pace"] == "中快节奏"
    assert result["tone"][0] == "克制"
    assert result["common_rhetoric"] == ["环境烘托", "动作描写", "心理独白"]

    mock_client.extract_json.assert_called_once_with(
        STYLE_EXTRACTION_PROMPT, "测试小说全文..."
    )


# ============================================================
# test_extract_empty_style_profile — 空风格信息场景
# ============================================================
@patch("src.extractor.style_extractor.DeepSeekClient")
def test_extract_empty_style_profile(mock_ds_class):
    """文本过短或风格不明确时，也应返回结构完整的风格字段"""
    mock_client = MagicMock()
    mock_ds_class.return_value = mock_client
    mock_client.extract_json.return_value = {
        "pace": "",
        "sentence_length_preference": "",
        "dialogue_ratio": "",
        "tone": [],
        "common_rhetoric": [],
        "forbidden_patterns": [],
    }

    extractor = StyleExtractor()
    result = extractor.extract("短文本")

    assert result["pace"] == ""
    assert result["tone"] == []
    assert result["forbidden_patterns"] == []


# ============================================================
# test_extractor_with_injected_client — 验证可注入自定义 client
# ============================================================
def test_extractor_with_injected_client():
    """通过构造函数注入 client，避免依赖真实 API"""
    mock_client = MagicMock()
    mock_client.extract_json.return_value = {
        "pace": "慢节奏",
        "sentence_length_preference": "中长句较多",
        "dialogue_ratio": "对话偏少",
        "tone": ["沉郁", "诗性"],
        "common_rhetoric": ["象征", "反复"],
        "forbidden_patterns": ["直白说教"],
    }

    extractor = StyleExtractor(client=mock_client)
    result = extractor.extract("任意小说文本")

    assert result["dialogue_ratio"] == "对话偏少"
    mock_client.extract_json.assert_called_once()
