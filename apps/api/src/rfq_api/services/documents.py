from __future__ import annotations

import base64
from pathlib import Path

from ..models import VendorDocument


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
            "Spreadsheet uploads are processed with spreadsheet augmentation, but embedded charts and layout-heavy visuals may not carry through exactly.",
        ]
    return [
        "Non-PDF uploads are sent as text-first file inputs to the model, so embedded charts, diagrams, and visual layout cues may be missed.",
    ]


def build_file_data_url(document: VendorDocument, content: bytes) -> str:
    base64_string = base64.b64encode(content).decode("utf-8")
    return f"data:{document.mime_type};base64,{base64_string}"
