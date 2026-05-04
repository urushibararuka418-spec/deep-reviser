"""剧情提取器 — 从小说全文中提取关键剧情事件"""

from src.extractor.ds_client import DeepSeekClient


PLOT_EXTRACTION_PROMPT = """你是一位专业的小说剧情分析助手。请从以下小说全文中提取关键剧情事件。

对每个事件提取以下字段：
- event_id: 事件唯一标识，建议使用简短且稳定的编号
- chapter: 事件发生的章节/位置
- summary: 事件摘要，概括发生了什么
- participants: 参与该事件的角色列表
- location: 事件发生地点
- cause_events: 导致当前事件发生的前置事件 event_id 列表
- consequence_events: 由当前事件引发的后续事件 event_id 列表

要求：
1. 只提取推动剧情发展的关键事件，忽略重复或无关紧要的日常片段。
2. 如果因果关系不明确，对应列表可为空。
3. 若文本中没有明显剧情主线，可返回空列表。

以严格 JSON 格式输出：{"events": [{"event_id": "", "chapter": "", "summary": "", "participants": [], "location": "", "cause_events": [], "consequence_events": []}]}"""


class PlotExtractor:
    """剧情提取器。"""

    def __init__(self, client=None):
        """初始化提取器，可注入自定义 client 以便测试。"""
        self.client = client or DeepSeekClient()

    def extract(self, full_text: str) -> dict:
        """从小说全文中提取剧情事件，返回 {"events": [...]}。"""
        return self.client.extract_json(PLOT_EXTRACTION_PROMPT, full_text)
