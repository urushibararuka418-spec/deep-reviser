"""Gradio Web UI。"""

from __future__ import annotations

import html
import json

import gradio as gr

from src.api.services import get_app_service


def _pretty_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _get_analysis_choices() -> list[str]:
    return [item["novel_title"] for item in get_app_service().list_analyses()]


def _build_analysis_summary(analysis: dict) -> str:
    return (
        f"作品：{analysis.get('novel_title', '未命名小说')}\n"
        f"章节数：{len(analysis.get('chapters', []))}\n"
        f"段落数：{len(analysis.get('segments', []))}\n"
        f"角色数：{len(analysis.get('characters', []))}\n"
        f"剧情事件数：{len(analysis.get('events', []))}\n"
        f"设定数：{len(analysis.get('lore_entries', []))}"
    )


def _build_chapter_choices(analysis: dict | None) -> list[tuple[str, int]]:
    if not analysis:
        return []
    choices = []
    for chapter in analysis.get("chapters", []):
        chapter_index = int(chapter.get("index", 0))
        chapter_title = chapter.get("title", f"第 {chapter_index + 1} 章")
        choices.append((f"{chapter_index}: {chapter_title}", chapter_index))
    return choices


def _build_diff_panel(diff_html: str) -> str:
    if not diff_html:
        return "<div>暂无对比结果。</div>"
    return f"<div style='overflow:auto; max-height: 720px;'>{diff_html}</div>"


def _build_history_rows(items: list[dict]) -> list[list]:
    """将历史记录转换为表格行。"""
    rows = []
    for index, item in enumerate(items, start=1):
        rows.append(
            [
                index,
                item.get("id"),
                item.get("segment_id", ""),
                item.get("original_preview", ""),
                item.get("rewritten_preview", ""),
                item.get("instruction", ""),
                item.get("created_at", ""),
            ]
        )
    return rows


def _build_history_detail(detail: dict) -> str:
    """构建历史详情展示文本。"""
    return (
        f"记录 ID：{detail.get('id', '')}\n"
        f"段落 ID：{detail.get('segment_id', '')}\n"
        f"时间：{detail.get('created_at', '')}\n"
        f"指令：{detail.get('instruction', '')}\n\n"
        f"原文：\n{detail.get('original_text', '')}\n\n"
        f"改写后：\n{detail.get('rewritten_text', '')}"
    )


def _build_batch_summary(result: dict) -> str:
    stats = result.get("stats", {})
    return (
        f"批量改写完成\n"
        f"章节数：{stats.get('chapter_count', 0)}\n"
        f"改写段数：{stats.get('rewrite_count', 0)}\n"
        f"章节索引：{stats.get('chapter_indices', [])}"
    )


def _build_chapter_preview(chapter_indices, chapters_json):
    try:
        chapters = get_app_service().parse_json_field(chapters_json, [])
    except json.JSONDecodeError as exc:
        raise gr.Error(f"章节 JSON 解析失败: {exc}") from exc

    selected = []
    chapter_set = {int(index) for index in (chapter_indices or [])}
    for chapter in chapters:
        if int(chapter.get("index", -1)) not in chapter_set:
            continue
        title = chapter.get("title", "未命名章节")
        content = chapter.get("content", "")
        selected.append(f"【{title}】\n{content}")

    return "\n\n".join(selected)


def _handle_upload(file_obj):
    if file_obj is None:
        raise gr.Error("请选择要上传的文件。")

    file_path = getattr(file_obj, "name", file_obj)
    result = get_app_service().upload_file(file_path)
    summary = (
        f"作品：{result['novel_title']}\n"
        f"文件：{result['filename']}\n"
        f"章节数：{result['chapter_count']}\n"
        f"段落数：{result['segment_count']}"
    )
    chapter_choices = _build_chapter_choices(result)
    return (
        summary,
        result["text"],
        _pretty_json(result["chapters"]),
        _pretty_json(result["segments"]),
        gr.Dropdown(choices=_get_analysis_choices(), value=result["novel_title"]),
        gr.CheckboxGroup(choices=chapter_choices, value=[]),
        "",
    )


def _handle_extract(text):
    if not text or not text.strip():
        raise gr.Error("请先上传或粘贴小说文本。")
    result = get_app_service().extract(text)
    chapter_choices = _build_chapter_choices(result)
    return (
        _pretty_json(result["characters"]),
        _pretty_json(result["events"]),
        _pretty_json(result["lore_entries"]),
        _pretty_json(result["style"]),
        gr.Dropdown(choices=_get_analysis_choices(), value=result["novel_title"]),
        gr.CheckboxGroup(choices=chapter_choices, value=[]),
        _build_analysis_summary(result),
    )


def _handle_rewrite(segment, instruction, characters_json, lore_json, similar_json, export_title):
    if not segment or not segment.strip():
        raise gr.Error("请输入要改写的段落。")
    if not instruction or not instruction.strip():
        raise gr.Error("请输入改写指令。")

    try:
        service = get_app_service()
        characters = service.parse_json_field(characters_json, [])
        lore_entries = service.parse_json_field(lore_json, [])
        similar_segments = service.parse_json_field(similar_json, [])
    except json.JSONDecodeError as exc:
        raise gr.Error(f"JSON 解析失败: {exc}") from exc

    result = service.rewrite(
        segment,
        instruction,
        characters=characters,
        lore_entries=lore_entries,
        similar_segments=similar_segments,
    )
    download_path = service.export_rewrites_to_tempfile(
        [{"rewritten_text": result["rewritten_text"]}],
        title=export_title or "rewritten_segment",
    )
    return (
        result["rewritten_text"],
        _pretty_json(result["context"]),
        _pretty_json(result["consistency"]),
        download_path,
    )


def _handle_analysis_select(novel_title):
    if not novel_title:
        return (
            "",
            "",
            "[]",
            "[]",
            "[]",
            "{}",
            gr.CheckboxGroup(choices=[], value=[]),
            "",
        )

    analysis = get_app_service().use_analysis(novel_title)
    return (
        _build_analysis_summary(analysis),
        get_app_service().get_analysis_text(analysis),
        _pretty_json(analysis["chapters"]),
        _pretty_json(analysis["segments"]),
        _pretty_json(analysis["characters"]),
        _pretty_json(analysis["lore_entries"]),
        gr.CheckboxGroup(choices=_build_chapter_choices(analysis), value=[]),
        _pretty_json(analysis["style"]),
    )


def _load_optional_json_file(file_obj, field_name):
    if file_obj is None:
        return None

    file_path = getattr(file_obj, "name", file_obj)
    try:
        with open(file_path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise gr.Error(f"{field_name} 导入失败: {exc}") from exc

    return payload.get(field_name) if isinstance(payload, dict) and field_name in payload else payload


def _handle_import_analysis(
    title,
    chapters_file,
    segments_file,
    characters_file,
    events_file,
    lore_file,
    style_file,
):
    payload = {
        "chapters": _load_optional_json_file(chapters_file, "chapters"),
        "segments": _load_optional_json_file(segments_file, "segments"),
        "characters": _load_optional_json_file(characters_file, "characters"),
        "events": _load_optional_json_file(events_file, "events"),
        "lore_entries": _load_optional_json_file(lore_file, "lore_entries"),
        "style": _load_optional_json_file(style_file, "style"),
    }
    if not any(value is not None for value in payload.values()):
        raise gr.Error("请至少选择一个 JSON 文件。")

    analysis = get_app_service().import_analysis(title=title, **payload)
    return (
        f"已导入分析记录：{analysis['novel_title']}",
        gr.Dropdown(choices=_get_analysis_choices(), value=analysis["novel_title"]),
        _build_analysis_summary(analysis),
        get_app_service().get_analysis_text(analysis),
        _pretty_json(analysis["chapters"]),
        _pretty_json(analysis["segments"]),
        _pretty_json(analysis["characters"]),
        _pretty_json(analysis["events"]),
        _pretty_json(analysis["lore_entries"]),
        _pretty_json(analysis["style"]),
        gr.CheckboxGroup(choices=_build_chapter_choices(analysis), value=[]),
    )


def _handle_batch_rewrite(chapter_indices, instruction, export_title):
    if not chapter_indices:
        raise gr.Error("请至少选择一个章节。")
    if not instruction or not instruction.strip():
        raise gr.Error("请输入全局改写指令。")

    result = get_app_service().rewrite_batch(chapter_indices, instruction)
    rewrites = []
    for chapter in result["chapters"]:
        rewrites.append({
            "rewritten_text": f"{chapter['chapter_title']}\n{chapter['rewritten_text']}".strip()
        })
    download_path = get_app_service().export_rewrites_to_tempfile(
        rewrites,
        title=export_title or "rewritten_chapters",
    )
    return (
        result["rewritten_text"],
        _build_diff_panel(result["diff_html"]),
        _build_batch_summary(result),
        download_path,
    )


def _load_rewrite_history(page, page_size):
    """加载改写历史分页列表。"""
    try:
        result = get_app_service().get_rewrite_history(int(page), int(page_size))
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc

    summary = (
        f"当前第 {result['page']} 页 / 共 {result['total_pages']} 页\n"
        f"每页 {result['page_size']} 条，共 {result['total']} 条记录"
    )
    return _build_history_rows(result["items"]), summary


def _show_rewrite_history_detail(history_table):
    """根据表格选中行展示完整历史详情。"""
    if not history_table:
        raise gr.Error("当前没有可查看的历史记录。")

    record_id = history_table[0][1] if history_table and len(history_table[0]) > 1 else None
    if record_id is None:
        raise gr.Error("请选择有效的历史记录。")

    try:
        detail = get_app_service().get_rewrite_detail(int(record_id))
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc

    return _build_history_detail(detail), _build_diff_panel(detail["diff_html"])


def _export_rewrite_history(export_title):
    """导出全部改写历史并生成下载文件。"""
    result = get_app_service().export_rewrite_history(export_title or "改写历史导出")
    download_path = get_app_service()._write_temp_txt(result["content"])
    summary = f"已导出 {result['record_count']} 条历史记录：{result['title']}"
    return download_path, summary


def build_app() -> gr.Blocks:
    """构建 Gradio Blocks 应用。"""
    with gr.Blocks(title="Deep Reviser") as demo:
        gr.Markdown("# Deep Reviser\n上传小说，提取结构化信息，并按段落执行改写。")

        with gr.Tab("Upload"):
            with gr.Row():
                with gr.Column(scale=3):
                    upload_file = gr.File(label="小说文件", file_types=[".txt", ".md", ".docx", ".epub"])
                    upload_btn = gr.Button("上传并预处理", variant="primary")
                with gr.Column(scale=2):
                    analysis_selector = gr.Dropdown(
                        label="已有分析记录",
                        choices=_get_analysis_choices(),
                        allow_custom_value=False,
                    )
                    import_title = gr.Textbox(label="导入标题", value="未命名导入")
                    import_chapters_file = gr.File(label="章节 JSON（可选）", file_types=[".json"])
                    import_segments_file = gr.File(label="段落 JSON（可选）", file_types=[".json"])
                    import_characters_file = gr.File(label="角色 JSON（可选）", file_types=[".json"])
                    import_events_file = gr.File(label="剧情 JSON（可选）", file_types=[".json"])
                    import_lore_file = gr.File(label="设定 JSON（可选）", file_types=[".json"])
                    import_style_file = gr.File(label="风格 JSON（可选）", file_types=[".json"])
                    import_btn = gr.Button("导入分析记录")
                    import_status = gr.Textbox(label="导入状态", lines=2)

            upload_summary = gr.Textbox(label="处理结果", lines=5)
            analysis_summary = gr.Textbox(label="分析摘要", lines=6)
            uploaded_text = gr.Textbox(label="原文文本", lines=18)
            chapters_json = gr.Code(label="章节 JSON", language="json")
            segments_json = gr.Code(label="段落 JSON", language="json")
            extract_btn = gr.Button("提取角色/剧情/设定/风格")
            characters_json = gr.Code(label="角色 JSON", language="json")
            events_json = gr.Code(label="剧情 JSON", language="json")
            lore_json = gr.Code(label="设定 JSON", language="json")
            style_json = gr.Code(label="风格 JSON", language="json")

        with gr.Tab("Rewrite"):
            with gr.Tabs():
                with gr.Tab("段落模式"):
                    segment_input = gr.Textbox(label="待改写段落", lines=14)
                    instruction_input = gr.Textbox(label="改写指令", lines=4, value="保持剧情不变，增强画面感和情绪张力。")
                    similar_json = gr.Code(label="相似片段 JSON（可留空）", language="json", value="[]")
                    export_title = gr.Textbox(label="导出文件名", value="rewritten_segment")
                    rewrite_btn = gr.Button("执行改写", variant="primary")
                    rewritten_text = gr.Textbox(label="改写结果", lines=14)
                    context_json = gr.Code(label="注入上下文", language="json")
                    consistency_json = gr.Code(label="一致性检查", language="json")
                    download_file = gr.File(label="下载改写结果")

                with gr.Tab("章节选择模式"):
                    chapter_selector = gr.CheckboxGroup(label="选择章节", choices=[])
                    selected_chapter_preview = gr.Textbox(label="已选章节预览", lines=12)
                    batch_instruction = gr.Textbox(
                        label="全局改写指令",
                        lines=4,
                        value="保持剧情不变，统一增强叙事张力与画面感。",
                    )
                    batch_export_title = gr.Textbox(label="批量导出文件名", value="rewritten_chapters")
                    batch_rewrite_btn = gr.Button("一键批量改写", variant="primary")
                    batch_stats = gr.Textbox(label="改写统计", lines=4)
                    batch_rewritten_text = gr.Textbox(label="批量改写结果", lines=16)
                    batch_diff = gr.HTML(label="Diff 对比")
                    batch_download_file = gr.File(label="下载批量改写结果")

        with gr.Tab("改写历史"):
            with gr.Row():
                history_page = gr.Number(label="页码", value=1, precision=0)
                history_page_size = gr.Number(label="每页条数", value=20, precision=0)
                history_refresh_btn = gr.Button("加载历史", variant="primary")
            history_summary = gr.Textbox(label="分页信息", lines=2)
            history_table = gr.Dataframe(
                label="历史记录列表",
                headers=["序号", "记录ID", "段落ID", "原文前50字", "改写后前50字", "指令", "时间"],
                datatype=["number", "number", "str", "str", "str", "str", "str"],
                row_count=(0, "dynamic"),
                column_count=(7, "fixed"),
                interactive=False,
                wrap=True,
            )
            view_history_btn = gr.Button("查看首条记录详情")
            history_detail = gr.Textbox(label="完整对比详情", lines=18)
            history_diff = gr.HTML(label="Diff 对比")
            history_export_title = gr.Textbox(label="导出文件名", value="改写历史导出")
            export_history_btn = gr.Button("导出全部历史")
            history_download_file = gr.File(label="下载改写历史")
            history_export_status = gr.Textbox(label="导出状态", lines=2)

        upload_btn.click(
            _handle_upload,
            inputs=[upload_file],
            outputs=[
                upload_summary,
                uploaded_text,
                chapters_json,
                segments_json,
                analysis_selector,
                chapter_selector,
                analysis_summary,
            ],
        )
        extract_btn.click(
            _handle_extract,
            inputs=[uploaded_text],
            outputs=[
                characters_json,
                events_json,
                lore_json,
                style_json,
                analysis_selector,
                chapter_selector,
                analysis_summary,
            ],
        )
        rewrite_btn.click(
            _handle_rewrite,
            inputs=[segment_input, instruction_input, characters_json, lore_json, similar_json, export_title],
            outputs=[rewritten_text, context_json, consistency_json, download_file],
        )
        analysis_selector.change(
            _handle_analysis_select,
            inputs=[analysis_selector],
            outputs=[
                analysis_summary,
                uploaded_text,
                chapters_json,
                segments_json,
                characters_json,
                lore_json,
                chapter_selector,
                style_json,
            ],
        )
        import_btn.click(
            _handle_import_analysis,
            inputs=[
                import_title,
                import_chapters_file,
                import_segments_file,
                import_characters_file,
                import_events_file,
                import_lore_file,
                import_style_file,
            ],
            outputs=[
                import_status,
                analysis_selector,
                analysis_summary,
                uploaded_text,
                chapters_json,
                segments_json,
                characters_json,
                events_json,
                lore_json,
                style_json,
                chapter_selector,
            ],
        )
        chapter_selector.change(
            _build_chapter_preview,
            inputs=[chapter_selector, chapters_json],
            outputs=[selected_chapter_preview],
        )
        batch_rewrite_btn.click(
            _handle_batch_rewrite,
            inputs=[chapter_selector, batch_instruction, batch_export_title],
            outputs=[batch_rewritten_text, batch_diff, batch_stats, batch_download_file],
        )
        history_refresh_btn.click(
            _load_rewrite_history,
            inputs=[history_page, history_page_size],
            outputs=[history_table, history_summary],
        )
        view_history_btn.click(
            _show_rewrite_history_detail,
            inputs=[history_table],
            outputs=[history_detail, history_diff],
        )
        export_history_btn.click(
            _export_rewrite_history,
            inputs=[history_export_title],
            outputs=[history_download_file, history_export_status],
        )

    return demo


app = build_app()


if __name__ == "__main__":
    app.launch()
