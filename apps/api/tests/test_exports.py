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
                    "rows": [["Alice Example", "alice", 5], ["حسین", "hosein", 2]],
                }
            ],
            "notes": ["AI recommendations never authorize a merge."],
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")
    assert len(response.content) > 500
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
