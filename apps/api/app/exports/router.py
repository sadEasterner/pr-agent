from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import Response

from app.api.schemas import PdfReportIn
from app.exports.pdf import render_pdf

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("/pdf")
async def create_pdf(payload: PdfReportIn) -> Response:
    content = render_pdf(payload)
    filename = _filename(payload.title)
    disposition = f"inline; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": disposition,
            "Content-Length": str(len(content)),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _filename(title: str) -> str:
    slug = re.sub(r"[^\w]+", "-", title, flags=re.UNICODE).strip("-")
    return f"{(slug or 'report')[:80]}.pdf"
