import uuid


def fake_url() -> str:
    return f"https://{uuid.uuid4().hex}.com"
