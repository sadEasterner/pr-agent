import pytest
from app.policy.engine import AutomationAction, PolicyEngine
from app.rules.loader import AutomationConfig


def test_policy_never_allows_merge_or_approve() -> None:
    policy = PolicyEngine(
        AutomationConfig(
            mode="review_only",
            allowed_actions=["read_pr", "post_review", "merge_pr", "approve_pr"],
            forbidden_actions=[],
        )
    )
    assert policy.can(AutomationAction.POST_REVIEW) is True
    assert policy.can(AutomationAction.MERGE_PR) is False
    assert policy.can(AutomationAction.APPROVE_PR) is False
    assert policy.can(AutomationAction.CLOSE_PR) is False
    assert policy.assert_not_merge_authority("approved") == "waiting_for_human"
    assert policy.human_label("ready_for_human_review") == "READY FOR HUMAN REVIEW"
    assert policy.human_label("changes_requested") == "CHANGES REQUESTED"
    assert policy.human_label("high_risk") == "HIGH RISK"


@pytest.mark.asyncio
async def test_settings_endpoint_states_human_authority(app_client) -> None:
    client, *_ = app_client
    response = await client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    assert body["merge_authority"] == "human"
    assert "merge_pr" in body["forbidden_actions"]
    assert "approve_pr" in body["forbidden_actions"]
