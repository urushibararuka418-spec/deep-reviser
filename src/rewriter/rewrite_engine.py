"""分段改写引擎。"""

from src.extractor.ds_client import DeepSeekClient


REWRITE_SYSTEM_PROMPT = """你是专业的中文小说改写助手。
请根据角色信息、世界设定、相似片段和用户指令改写段落。
改写时必须保持角色身份与行为逻辑一致，不能违背已有设定，并尽量延续原文风格。
只输出改写后的正文，不要附加解释。"""


class RewriteEngine:
    """封装基于 DeepSeek 的段落改写能力。"""

    def __init__(self, client=None):
        """初始化改写引擎。"""
        self.client = client or DeepSeekClient()

    def rewrite(self, segment, instruction, context, **kwargs):
        """根据指令和上下文改写段落。"""
        messages = [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": self._build_user_prompt(segment, instruction, context)},
        ]
        return self.client.chat(messages, **kwargs)

    def _build_user_prompt(self, segment, instruction, context):
        """构造给模型的用户提示。"""
        parts = [f"改写指令：{instruction}", f"待改写段落：\n{segment}"]

        if context.character_context:
            parts.append(f"角色上下文：\n{context.character_context}")

        if context.lorebook_context:
            parts.append(f"设定上下文：\n{context.lorebook_context}")

        if context.similar_context:
            parts.append(f"相似片段：\n{context.similar_context}")

        return "\n\n".join(parts)
