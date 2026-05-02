"""DeepSeekClient 测试套件 — TDD Step 1: 先写测试，预期全部 FAIL"""
import pytest
import json
from unittest.mock import MagicMock, patch, ANY


# ============================================================
# test_client_initialization — 验证 api_key/base_url 正确设置
# ============================================================
@patch("src.extractor.ds_client.OpenAI")
def test_client_initialization(mock_openai_class):
    """初始化 DeepSeekClient 时应正确传递 api_key 和 base_url 给 OpenAI"""
    from src.extractor.ds_client import DeepSeekClient

    mock_client_instance = MagicMock()
    mock_openai_class.return_value = mock_client_instance

    # 使用自定义参数初始化
    client = DeepSeekClient(
        api_key="sk-test-key",
        base_url="https://custom.api.com"
    )

    # 验证 OpenAI 被传入正确的参数
    mock_openai_class.assert_called_once_with(
        api_key="sk-test-key",
        base_url="https://custom.api.com"
    )
    assert client.client == mock_client_instance
    assert client.model is not None  # 应从 settings 获取


@patch("src.extractor.ds_client.OpenAI")
def test_client_initialization_defaults(mock_openai_class):
    """不传参数时，应使用 settings 中的默认值"""
    from src.extractor.ds_client import DeepSeekClient, settings

    mock_client_instance = MagicMock()
    mock_openai_class.return_value = mock_client_instance

    client = DeepSeekClient()

    # 应使用 settings 中的值
    mock_openai_class.assert_called_once_with(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url
    )
    assert client.model == settings.deepseek_model


# ============================================================
# test_chat — mock OpenAI client, 验证返回文本
# ============================================================
@patch("src.extractor.ds_client.OpenAI")
def test_chat(mock_openai_class):
    """chat() 应调用 OpenAI chat.completions.create 并返回消息文本"""
    from src.extractor.ds_client import DeepSeekClient

    # 构造 mock client
    mock_client_instance = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="你好，这是一条回复"))
    ]
    mock_client_instance.chat.completions.create.return_value = mock_completion
    mock_openai_class.return_value = mock_client_instance

    client = DeepSeekClient(api_key="sk-test", base_url="https://test.com")
    messages = [{"role": "user", "content": "Hello"}]
    result = client.chat(messages, temperature=0.7)

    # 验证调用参数
    mock_client_instance.chat.completions.create.assert_called_once_with(
        model=client.model,
        messages=messages,
        temperature=0.7,
    )
    assert result == "你好，这是一条回复"


# ============================================================
# test_extract_json — mock 返回 JSON, 验证解析正确
# ============================================================
@patch("src.extractor.ds_client.OpenAI")
def test_extract_json(mock_openai_class):
    """extract_json() 应返回解析后的 dict，且调用时带 response_format"""
    from src.extractor.ds_client import DeepSeekClient

    mock_client_instance = MagicMock()
    mock_completion = MagicMock()
    # 返回纯 JSON 字符串
    mock_completion.choices = [
        MagicMock(message=MagicMock(content='{"name": "Alice", "age": 30}'))
    ]
    mock_client_instance.chat.completions.create.return_value = mock_completion
    mock_openai_class.return_value = mock_client_instance

    client = DeepSeekClient(api_key="sk-test", base_url="https://test.com")
    result = client.extract_json(
        system_prompt="你是一个 JSON 提取器",
        user_content="请提取姓名和年龄"
    )

    assert result == {"name": "Alice", "age": 30}
    # 验证调用时带了 response_format
    mock_client_instance.chat.completions.create.assert_called_once()
    call_kwargs = mock_client_instance.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"] == {"type": "json_object"}


# ============================================================
# test_extract_json_fallback — 测试 ```json 代码块解析
# ============================================================
@patch("src.extractor.ds_client.OpenAI")
def test_extract_json_fallback(mock_openai_class):
    """当返回被 Markdown 代码块包裹时，应能提取并解析 JSON"""
    from src.extractor.ds_client import DeepSeekClient

    mock_client_instance = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content='''```json
{"title": "三体", "author": "刘慈欣"}
```'''))
    ]
    mock_client_instance.chat.completions.create.return_value = mock_completion
    mock_openai_class.return_value = mock_client_instance

    client = DeepSeekClient(api_key="sk-test", base_url="https://test.com")
    result = client.extract_json(
        system_prompt="提取书名和作者",
        user_content="《三体》"
    )

    assert result == {"title": "三体", "author": "刘慈欣"}


# ============================================================
# test_extract_json_invalid — 无效 JSON 抛出 ValueError
# ============================================================
@patch("src.extractor.ds_client.OpenAI")
def test_extract_json_invalid(mock_openai_class):
    """当返回内容无法解析为 JSON 时，应抛出 ValueError"""
    from src.extractor.ds_client import DeepSeekClient

    mock_client_instance = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="这不是 JSON，只是一段普通文本"))
    ]
    mock_client_instance.chat.completions.create.return_value = mock_completion
    mock_openai_class.return_value = mock_client_instance

    client = DeepSeekClient(api_key="sk-test", base_url="https://test.com")

    with pytest.raises(ValueError, match="无法解析 JSON"):
        client.extract_json(
            system_prompt="返回 JSON",
            user_content="任意内容"
        )


# ============================================================
# test__parse_json — 直接测试内部解析方法
# ============================================================
@patch("src.extractor.ds_client.OpenAI")
def test__parse_json_direct(mock_openai_class):
    """_parse_json() 应能直接解析 JSON 字符串"""
    from src.extractor.ds_client import DeepSeekClient

    client = DeepSeekClient(api_key="sk-test", base_url="https://test.com")

    # 直接 JSON
    assert client._parse_json('{"key": "value"}') == {"key": "value"}

    # ```json 代码块
    assert client._parse_json('```json\n{"a": 1}\n```') == {"a": 1}

    # ``` 无语言标记
    assert client._parse_json('```\n{"b": 2}\n```') == {"b": 2}

    # 无效文本
    with pytest.raises(ValueError, match="无法解析 JSON"):
        client._parse_json("not json at all")


# ============================================================
# test__parse_json_with_surrounding_text
# ============================================================
@patch("src.extractor.ds_client.OpenAI")
def test__parse_json_with_surrounding_text(mock_openai_class):
    """JSON 代码块前后有其他文字时也能正确提取"""
    from src.extractor.ds_client import DeepSeekClient

    client = DeepSeekClient(api_key="sk-test", base_url="https://test.com")

    text = '这是前面的说明\n```json\n{"result": "ok"}\n```\n这是后面的文字'
    assert client._parse_json(text) == {"result": "ok"}
