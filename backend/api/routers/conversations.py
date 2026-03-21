from api.deps import get_current_user_id
from api.schemas import (ConversationRatingRequest, ConversationResponse,
                         CreateConversationRequest)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from utils.db import (create_conversation, get_conversation,
                      list_conversations, update_conversation_rating)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _conv_to_response(row: dict) -> ConversationResponse:
    raw = row.get("created_at")
    if raw is None:
        created_at = None
    elif hasattr(raw, "isoformat"):
        created_at = raw.isoformat()
    else:
        created_at = str(raw)
    return ConversationResponse(
        id=row["id"],
        user_id=row["user_id"],
        name=row.get("name"),
        created_at=created_at,
        rating=row.get("rating"),
        rated_at=row.get("rated_at"),
    )


@router.get("", response_model=list[ConversationResponse])
def list_conversations_endpoint(
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(100, ge=1, le=500),
):
    """Get all conversations for the current user (newest first)."""
    rows = list_conversations(user_id=user_id, limit=limit)
    return [_conv_to_response(row) for row in rows]


@router.post("", response_model=ConversationResponse)
def create_conversation_endpoint(
    body: CreateConversationRequest = None,
    user_id: str = Depends(get_current_user_id),
):
    """Create a new conversation for the current user."""
    body = body or CreateConversationRequest()
    conv_id = create_conversation(user_id=user_id, name=body.name)
    if not conv_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation",
        )
    row = get_conversation(conv_id, user_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return _conv_to_response(row)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation_endpoint(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get a conversation by id (must belong to current user)."""
    row = get_conversation(conversation_id, user_id)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return _conv_to_response(row)


@router.patch("/{conversation_id}/rating")
def rate_conversation(
    conversation_id: str,
    body: ConversationRatingRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Set per-conversation rating (1-5)."""
    ok = update_conversation_rating(conversation_id, user_id, body.rating)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or not owned by you",
        )
    return {"ok": True}
