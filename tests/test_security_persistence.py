import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register_and_login(client: TestClient, email: str) -> str:
    response = client.post(
        "/auth/register", json={"email": email, "password": "correct horse battery"}
    )
    assert response.status_code == 201
    response = client.post(
        "/auth/login", json={"email": email, "password": "correct horse battery"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_user_cannot_read_or_modify_another_users_conversation(client: TestClient):
    user_a_token = register_and_login(client, "a@example.com")
    user_b_token = register_and_login(client, "b@example.com")

    response = client.post(
        "/conversations",
        headers={"Authorization": f"Bearer {user_a_token}"},
        json={"title": "A private chat"},
    )
    conversation_id = response.json()["id"]

    response = client.get(
        f"/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {user_b_token}"},
    )
    assert response.status_code == 404

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {user_b_token}"},
        json={"content": "intrusion", "assistant_response": "should not save"},
    )
    assert response.status_code == 404

    response = client.get(
        "/conversations", headers={"Authorization": f"Bearer {user_b_token}"}
    )
    assert response.json() == []


def test_messages_and_password_hash_are_persisted(client: TestClient):
    token = register_and_login(client, "persist@example.com")
    response = client.post(
        "/conversations",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Saved chat"},
    )
    conversation_id = response.json()["id"]

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "What is SQLAlchemy?", "assistant_response": "An ORM."},
    )
    assert response.status_code == 200
    assert response.json()["user_message"]["role"] == "user"
    assert response.json()["assistant_message"]["role"] == "assistant"

    response = client.get(
        f"/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert [message["content"] for message in response.json()["messages"]] == [
        "What is SQLAlchemy?",
        "An ORM.",
    ]
