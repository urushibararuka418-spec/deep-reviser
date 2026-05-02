"""CharacterExtractor 测试套件 — TDD Step 1: 先写测试，预期全部 FAIL"""

from unittest.mock import patch, MagicMock
from src.extractor.character_extractor import CharacterExtractor, CHARACTER_EXTRACTION_PROMPT


# ============================================================
# test_prompt_is_chinese — 确认提示词包含中文字段名
# ============================================================
def test_prompt_is_chinese():
    """确认提示词包含角色相关的中文/英文关键词"""
    assert "角色" in CHARACTER_EXTRACTION_PROMPT or "character" in CHARACTER_EXTRACTION_PROMPT.lower()


# ============================================================
# test_extract_characters — mock DeepSeekClient，验证提取结果
# ============================================================
@patch("src.extractor.character_extractor.DeepSeekClient")
def test_extract_characters(mock_ds_class):
    """extract() 应调用 client.extract_json 并返回角色列表"""
    # 构造 mock client
    mock_client = MagicMock()
    mock_ds_class.return_value = mock_client
    mock_client.extract_json.return_value = {
        "characters": [
            {
                "name": "李明",
                "aliases": ["小明", "李兄"],
                "role_type": "主角",
                "personality_traits": ["勇敢", "谨慎"],
                "abilities": ["剑术", "炼丹"],
                "relationships": [
                    {"target": "张伟", "relation": "挚友", "description": "同门师兄弟"}
                ],
                "character_arc": "从普通少年成长为一代宗师",
                "first_appearance": "第一章",
                "quote_examples": ["我不能退！", "这就是我的道！"]
            }
        ]
    }

    # 初始化提取器并执行提取
    extractor = CharacterExtractor()
    result = extractor.extract("测试小说全文...")

    # 验证结果
    assert len(result["characters"]) == 1
    assert result["characters"][0]["name"] == "李明"
    assert "张伟" == result["characters"][0]["relationships"][0]["target"]

    # 验证 client.extract_json 被正确调用
    mock_client.extract_json.assert_called_once_with(
        CHARACTER_EXTRACTION_PROMPT, "测试小说全文..."
    )


# ============================================================
# test_extract_empty_novel — 空角色列表场景
# ============================================================
@patch("src.extractor.character_extractor.DeepSeekClient")
def test_extract_empty_novel(mock_ds_class):
    """短文本/无角色时，应返回空的 characters 列表"""
    mock_client = MagicMock()
    mock_ds_class.return_value = mock_client
    mock_client.extract_json.return_value = {"characters": []}

    extractor = CharacterExtractor()
    result = extractor.extract("短文本")

    assert result["characters"] == []
    assert len(result["characters"]) == 0


# ============================================================
# test_extractor_with_injected_client — 验证可注入自定义 client
# ============================================================
def test_extractor_with_injected_client():
    """通过构造函数注入 client，避免依赖真实 API"""
    mock_client = MagicMock()
    mock_client.extract_json.return_value = {
        "characters": [
            {"name": "测试角色", "role_type": "配角"}
        ]
    }

    extractor = CharacterExtractor(client=mock_client)
    result = extractor.extract("任意小说文本")

    assert result["characters"][0]["name"] == "测试角色"
    mock_client.extract_json.assert_called_once()
