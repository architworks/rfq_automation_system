from __future__ import annotations

from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def validate_document_name(file_name: str) -> tuple[str, str]:
    extension = Path(file_name).suffix.lower()
    mime_type = SUPPORTED_EXTENSIONS.get(extension)
    if mime_type is None:
        allowed = ", ".join(extension.lstrip(".") for extension in sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Allowed extensions: {allowed}.")
    return extension, mime_type


def build_visual_fidelity_warnings(extension: str) -> list[str]:
    if extension == ".pdf":
        return []
    if extension in {".xls", ".xlsx"}:
        return [
            "Native file input is used for this spreadsheet. OpenAI processes spreadsheets through a spreadsheet-specific augmentation flow, so chart fidelity and full workbook layout may not fully carry through.",
        ]
    return [
        "Native file input is used for this document. OpenAI processes non-PDF office files as text-only input, so embedded charts, diagrams, images, and layout-heavy cues may not fully carry through.",
    ]
