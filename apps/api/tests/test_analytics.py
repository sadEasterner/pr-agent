import pytest
from tests.conftest import seed_pr


@pytest.mark.asyncio
async def test_analytics_summary_and_findings(app_client, session) -> None:
    client, *_ = app_client
    await seed_pr(session)
    summary = await client.get("/api/analytics/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["prs_reviewed"] >= 1
    assert "average_pr_size_lines" in body
    assert "developer_score" not in body

    findings = await client.get("/api/analytics/findings")
    assert findings.status_code == 200
    assert findings.json()["by_severity"]

    repos = await client.get("/api/analytics/repositories")
    assert repos.status_code == 200
    assert repos.json()[0]["repository"] == "acme/demo"

    prs = await client.get("/api/analytics/prs")
    assert prs.status_code == 200
    detail = await client.get("/api/analytics/prs/acme/demo/42")
    assert detail.status_code == 200
    assert detail.json()["ai_is_not_approval"] is True

    trends = await client.get("/api/analytics/trends")
    assert trends.status_code == 200
    assert "reviews_over_time" in trends.json()


@pytest.mark.asyncio
async def test_pr_list_filters(app_client, session) -> None:
    client, *_ = app_client
    await seed_pr(session)
    response = await client.get("/api/prs", params={"repository": "acme/demo", "author": "alice"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    empty = await client.get("/api/prs", params={"risk": "critical"})
    assert empty.json() == []
