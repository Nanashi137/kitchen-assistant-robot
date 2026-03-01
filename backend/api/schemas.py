from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ---- Auth ----
class SignUpRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=6)
    email: Optional[str] = Field(None, max_length=255)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None


# ---- Conversations ----
class CreateConversationRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255)


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    name: Optional[str] = None
    created_at: Optional[str] = None
    rating: Optional[int] = None
    rated_at: Optional[str] = None


class ConversationRatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)


# ---- Messages ----
class AddMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: Optional[str] = None
    ambiguous: bool = False
    bot_trace: Optional[List[Any]] = None
    rating: Optional[int] = None
    rated_at: Optional[str] = None


class AddMessageResponse(BaseModel):
    """User message + assistant message after running the tree."""

    user_message: MessageResponse
    assistant_message: MessageResponse


class MessageRatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
