"""Gradio Web UI。"""

from __future__ import annotations

import json

import gradio as gr

from src.api.services import get_app_service


def _pretty_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _handle_upload(file_obj):
    if file_obj is None:
        raise gr.Error("请选择要上传的文件。")

    file_path = getattr(file_obj, "name", file_obj)
    result = get_app_service().upload_file(file_path)
    summary = (
        f"文件：{result['filename']}\n"
        f"章节数：{result['chapter_count']}\n"
        f"段落数：{result['segment_count']}"
    )
    return (
        summary,
        result["text"],
        _pretty_json(result["chapters"]),
        _pretty_json(result["segments"]),
    )


def _handle_extract(text):
    if not text or not text.strip():
        raise gr.Error("请先上传或粘贴小说文本。")
    result = get_app_service().extract(text)
    return (
        _pretty_json(result["characters"]),
        _pretty_json(result["events"]),
        _pretty_json(result["lore_entries"]),
        _pretty_json(result["style"]),
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


def build_app() -> gr.Blocks:
    """构建 Gradio Blocks 应用。"""
    with gr.Blocks(title="Deep Reviser") as demo:
        gr.Markdown("# Deep Reviser\n上传小说，提取结构化信息，并按段落执行改写。")

        with gr.Tab("Upload"):
            upload_file = gr.File(label="小说文件", file_types=[".txt", ".md", ".docx", ".epub"])
            upload_btn = gr.Button("上传并预处理", variant="primary")
            upload_summary = gr.Textbox(label="处理结果", lines=4)
            uploaded_text = gr.Textbox(label="原文文本", lines=18)
            chapters_json = gr.Code(label="章节 JSON", language="json")
            segments_json = gr.Code(label="段落 JSON", language="json")
            extract_btn = gr.Button("提取角色/剧情/设定/风格")
            characters_json = gr.Code(label="角色 JSON", language="json")
            events_json = gr.Code(label="剧情 JSON", language="json")
            lore_json = gr.Code(label="设定 JSON", language="json")
            style_json = gr.Code(label="风格 JSON", language="json")

        with gr.Tab("Rewrite"):
            segment_input = gr.Textbox(label="待改写段落", lines=14)
            instruction_input = gr.Textbox(label="改写指令", lines=4, value="保持剧情不变，增强画面感和情绪张力。")
            similar_json = gr.Code(label="相似片段 JSON（可留空）", language="json", value="[]")
            export_title = gr.Textbox(label="导出文件名", value="rewritten_segment")
            rewrite_btn = gr.Button("执行改写", variant="primary")
            rewritten_text = gr.Textbox(label="改写结果", lines=14)
            context_json = gr.Code(label="注入上下文", language="json")
            consistency_json = gr.Code(label="一致性检查", language="json")
            download_file = gr.File(label="下载改写结果")

        upload_btn.click(
            _handle_upload,
            inputs=[upload_file],
            outputs=[upload_summary, uploaded_text, chapters_json, segments_json],
        )
        extract_btn.click(
            _handle_extract,
            inputs=[uploaded_text],
            outputs=[characters_json, events_json, lore_json, style_json],
        )
        rewrite_btn.click(
            _handle_rewrite,
            inputs=[segment_input, instruction_input, characters_json, lore_json, similar_json, export_title],
            outputs=[rewritten_text, context_json, consistency_json, download_file],
        )

    return demo


app = build_app()


if __name__ == "__main__":
    app.launch()
