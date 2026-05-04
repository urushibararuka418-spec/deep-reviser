"""RewriteEngine 测试套件。"""

from unittest.mock import MagicMock, patch

from src.rewriter.context_assembler import Context
from src.rewriter.rewrite_engine import REWRITE_SYSTEM_PROMPT, RewriteEngine


def test_rewrite_prompt_is_chinese():
    """系统提示词应明确要求中文改写。"""
    assert "改写" in REWRITE_SYSTEM_PROMPT
    assert "角色" in REWRITE_SYSTEM_PROMPT
    assert "设定" in REWRITE_SYSTEM_PROMPT
    assert "风格" in REWRITE_SYSTEM_PROMPT


@patch("src.rewriter.rewrite_engine.DeepSeekClient")
def test_rewrite_calls_deepseek_chat_with_context(mock_ds_class):
    """rewrite() 应将指令、段落和上下文传给 client.chat。"""
    mock_client = MagicMock()
    mock_client.chat.return_value = "改写后的段落"
    mock_ds_class.return_value = mock_client

    engine = RewriteEngine()
    context = Context(
        character_context="李明；身份：主角",
        lorebook_context="类别：组织；青云宗；说明：东州宗门。",
        similar_context="前文：李明曾在青云宗修行。",
    )

    result = engine.rewrite("原始段落", "增强紧张感", context)

    assert result == "改写后的段落"
    mock_client.chat.assert_called_once()
    messages = mock_client.chat.call_args.args[0]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == REWRITE_SYSTEM_PROMPT
    assert "增强紧张感" in messages[1]["content"]
    assert "原始段落" in messages[1]["content"]
    assert "李明；身份：主角" in messages[1]["content"]


def test_rewrite_uses_injected_client():
    """应支持通过构造函数注入 client。"""
    mock_client = MagicMock()
    mock_client.chat.return_value = "注入 client 的结果"

    engine = RewriteEngine(client=mock_client)
    result = engine.rewrite("原文", "保持克制语气", Context())

    assert result == "注入 client 的结果"
    mock_client.chat.assert_called_once()


def test_rewrite_omits_empty_context_sections():
    """空上下文字段不应污染用户提示。"""
    mock_client = MagicMock()
    mock_client.chat.return_value = "结果"
    engine = RewriteEngine(client=mock_client)

    engine.rewrite("原文", "精简表达", Context(character_context="角色：李明"))

    user_prompt = mock_client.chat.call_args.args[0][1]["content"]
    assert "角色上下文" in user_prompt
    assert "设定上下文" not in user_prompt
    assert "相似片段" not in user_prompt


def test_rewrite_passes_temperature_override():
    """应允许向 chat 透传 temperature 等参数。"""
    mock_client = MagicMock()
    mock_client.chat.return_value = "结果"
    engine = RewriteEngine(client=mock_client)

    engine.rewrite("原文", "更诗意", Context(), temperature=0.8)

    assert mock_client.chat.call_args.kwargs["temperature"] == 0.8
