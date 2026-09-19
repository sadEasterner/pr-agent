import pytest
from tests.conftest import seed_pr


@pytest.mark.asyncio
async def test_export_pdf_returns_a_pdf(app_client) -> None:
    client, *_ = app_client
    response = await client.post(
        "/api/exports/pdf",
        json={
            "title": "People",
            "subtitle": "PR authors and findings",
            "metrics": [{"label": "PRs", "value": 4}, {"label": "Findings", "value": 5}],
            "tables": [
                {
                    "title": "Authors",
                    "headers": ["Name", "Login", "Findings"],
                    "rows": [["Alice Example", "alice", 5], ["José García", "jose", 2]],
                }
            ],
            "notes": ["AI recommendations never authorize a merge."],
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert "charset" not in response.headers["content-type"]
    assert response.content.startswith(b"%PDF")
    assert b"%%EOF" in response.content
    assert len(response.content) > 500
    assert response.headers.get("content-length") == str(len(response.content))
    assert "filename=" in response.headers.get("content-disposition", "")


@pytest.mark.asyncio
async def test_export_pdf_handles_empty_tables(app_client, session) -> None:
    client, *_ = app_client
    await seed_pr(session)
    response = await client.post(
        "/api/exports/pdf",
        json={"title": "Overview", "tables": [{"title": "Empty", "headers": ["A", "B"], "rows": []}]},
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert b"%%EOF" in response.content


@pytest.mark.asyncio
async def test_export_pdf_handles_wide_tables(app_client) -> None:
    client, *_ = app_client
    response = await client.post(
        "/api/exports/pdf",
        json={
            "title": "Pull Requests",
            "tables": [
                {
                    "headers": [
                        "PR",
                        "Repository",
                        "Author",
                        "Login",
                        "Risk",
                        "Findings",
                        "Recommendation",
                        "Review status",
                        "Updated",
                    ],
                    "rows": [
                        [
                            "#42 Add user endpoint",
                            "acme/demo",
                            "José García",
                            "jose",
                            "low",
                            1,
                            "ready_for_human_review",
                            "Waiting for human",
                            "2026-09-19",
                        ]
                    ],
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert b"%%EOF" in response.content
