from app.logging import SENSITIVE_KEYS, drop_sensitive_data


def test_logs_redact_secrets() -> None:
    event = drop_sensitive_data(
        None,
        "info",
        {
            "event": "webhook_accepted",
            "gitea_token": "super-secret",
            "openai_api_key": "sk-live",
            "authorization": "Bearer abc",
            "repository": "acme/demo",
        },
    )
    assert event["gitea_token"] == "[redacted]"
    assert event["openai_api_key"] == "[redacted]"
    assert event["authorization"] == "[redacted]"
    assert event["repository"] == "acme/demo"
    assert "gitea_token" in SENSITIVE_KEYS
