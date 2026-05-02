"""DeepSeek API 客户端封装 — 统一的聊天和 JSON 提取接口"""
import json
import re
from openai import OpenAI
from src.config import settings


class DeepSeekClient:
    """DeepSeek API 客户端封装，提供 chat 和 extract_json 两个核心方法。"""

    def __init__(self, api_key=None, base_url=None):
        """
        初始化 DeepSeek 客户端。

        Args:
            api_key: DeepSeek API 密钥，不传则使用 settings.deepseek_api_key
            base_url: API 基础地址，不传则使用 settings.deepseek_base_url
        """
        self.client = OpenAI(
            api_key=api_key or settings.deepseek_api_key,
            base_url=base_url or settings.deepseek_base_url,
        )
        self.model = settings.deepseek_model

    def chat(self, messages, **kwargs) -> str:
        """
        调用 DeepSeek chat API 并返回回复文本。

        Args:
            messages: OpenAI 格式的消息列表
            **kwargs: 传递给 chat.completions.create 的额外参数（如 temperature）

        Returns:
            模型回复的文本内容
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content

    def extract_json(self, system_prompt, user_content) -> dict:
        """
        调用 DeepSeek API 并返回解析后的 JSON 字典。

        使用 response_format={"type": "json_object"} 引导模型输出 JSON，
        并对返回结果调用 _parse_json 进行容错解析。

        Args:
            system_prompt: 系统提示词
            user_content: 用户输入内容

        Returns:
            解析后的字典

        Raises:
            ValueError: 当返回内容无法解析为 JSON 时
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        raw = self.chat(messages, response_format={"type": "json_object"})
        return self._parse_json(raw)

    def _parse_json(self, text) -> dict:
        """
        容错 JSON 解析器。

        解析策略：
        1. 直接 json.loads 解析
        2. 尝试提取 ```json...``` 代码块后再解析
        3. 尝试提取 ```...``` （无语言标记）代码块后再解析
        4. 以上均失败则抛出 ValueError

        Args:
            text: 原始响应文本

        Returns:
            解析后的字典

        Raises:
            ValueError: 无法解析为 JSON
        """
        # 策略 1: 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 策略 2: 提取 ```json ... ``` 代码块
        json_block = self._extract_code_block(text, "json")
        if json_block is not None:
            try:
                return json.loads(json_block)
            except json.JSONDecodeError:
                pass

        # 策略 3: 提取 ``` ... ``` 代码块（无语言标记）
        generic_block = self._extract_code_block(text)
        if generic_block is not None:
            try:
                return json.loads(generic_block)
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法解析 JSON: {text[:200]}")

    @staticmethod
    def _extract_code_block(text, language=None):
        """
        从文本中提取 Markdown 代码块内容。

        Args:
            text: 包含代码块的文本
            language: 可选，指定代码块语言标记（如 "json"）

        Returns:
            代码块内容字符串，未找到则返回 None
        """
        if language:
            pattern = rf"```{re.escape(language)}\s*\n(.*?)```"
        else:
            pattern = r"```\s*\n(.*?)```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
