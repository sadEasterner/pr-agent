from app.gitea.models import GiteaBranchRef, GiteaPullRequest, GiteaUser
from app.jobs.sync import pull_to_event


def test_pull_to_event_maps_open_pr() -> None:
    pull = GiteaPullRequest(
        number=183,
        title="[form]: new version 0.2.85",
        html_url="https://git.example.com/acme/demo/pulls/183",
        state="open",
        user=GiteaUser(login="davoudnasiri"),
        head=GiteaBranchRef(ref="form-dev", sha="abc123"),
        base=GiteaBranchRef(ref="main", sha="def456"),
    )
    event = pull_to_event("hoseinSeifi/modules-monorepo", pull, "opened")
    assert event.action == "opened"
    assert event.repository_name == "hoseinSeifi/modules-monorepo"
    assert event.pr_number == 183
    assert event.head_sha == "abc123"
    assert event.event_type == "opened"
