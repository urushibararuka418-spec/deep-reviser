"""风格基线提取器 — 从小说全文中提取写作风格信息"""

from src.extractor.ds_client import DeepSeekClient


STYLE_EXTRACTION_PROMPT = """你是一位专业的小说文风分析助手。请从以下小说全文中提取可复用的写作风格基线信息。

请输出以下字段：
- pace: 叙事节奏偏好（如 快节奏、中快节奏、舒缓、张弛有度 等）
- sentence_length_preference: 句长偏好（如 短句为主、中长句较多、长短句结合 等）
- dialogue_ratio: 对话占比特征（如 对话偏多、对话适中、对话偏少，或给出大致比例描述）
- tone: 整体语气/氛围标签列表（如 冷峻、热烈、克制、幽默、压抑、诗性 等）
- common_rhetoric: 常见修辞或表达手法列表（如 排比、反问、环境烘托、动作描写、心理独白、象征、留白 等）
- forbidden_patterns: 应避免的表达模式列表（如 现代网络口语、过度解释、出戏的旁白、重复口头禅 等）

要求：
1. 基于全文整体风格总结，不要只看局部片段。
2. 字段内容应简洁、可执行，便于后续仿写。
3. 若某项不明显，可填写空字符串或空列表。

以严格 JSON 格式输出：{"pace": "", "sentence_length_preference": "", "dialogue_ratio": "", "tone": [], "common_rhetoric": [], "forbidden_patterns": []}"""


class StyleExtractor:
    """风格基线提取器。"""

    def __init__(self, client=None):
        """初始化提取器，可注入自定义 client 以便测试。"""
        self.client = client or DeepSeekClient()

    def extract(self, full_text: str) -> dict:
        """从小说全文中提取风格基线，返回风格字段字典。"""
        return self.client.extract_json(STYLE_EXTRACTION_PROMPT, full_text)
