from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import models
from .auth import (
    create_access_token,
    find_user_by_email,
    get_current_user,
    get_password_hash,
    verify_password,
)
from .database import Base, engine, get_db
from .schemas import (
    ConversationCreate,
    ConversationResponse,
    LoginRequest,
    MessageCreate,
    MessagePairResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
)

app = FastAPI(title="Private Conversations API")
Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> models.User:
    email = str(payload.email).lower()
    if find_user_by_email(db, email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = models.User(email=email, password_hash=get_password_hash(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = find_user_by_email(db, str(payload.email).lower())
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.id))


def owned_conversation(
    conversation_id: int, user: models.User, db: Session
) -> models.Conversation:
    conversation = db.scalar(
        select(models.Conversation)
        .options(selectinload(models.Conversation.messages))
        .where(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == user.id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@app.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> models.Conversation:
    conversation = models.Conversation(user_id=user.id, title=payload.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@app.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    user: models.User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[models.Conversation]:
    return list(
        db.scalars(
            select(models.Conversation)
            .options(selectinload(models.Conversation.messages))
            .where(models.Conversation.user_id == user.id)
            .order_by(models.Conversation.created_at.desc())
        ).all()
    )


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> models.Conversation:
    return owned_conversation(conversation_id, user, db)


@app.post("/conversations/{conversation_id}/messages", response_model=MessagePairResponse)
def add_message(
    conversation_id: int,
    payload: MessageCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessagePairResponse:
    conversation = owned_conversation(conversation_id, user, db)
    user_message = models.Message(
        conversation=conversation, role="user", content=payload.content
    )
    assistant_message = models.Message(
        conversation=conversation, role="assistant", content=payload.assistant_response
    )
    db.add_all([user_message, assistant_message])
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    return MessagePairResponse(
        user_message=user_message, assistant_message=assistant_message
    )
