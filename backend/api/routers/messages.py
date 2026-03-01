from typing import List

from api.deps import get_current_user_id
from api.schemas import (AddMessageRequest, AddMessageResponse,
                         MessageRatingRequest, MessageResponse)
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from utils.db import (get_conversation, get_latest_messages,
                      get_message_with_conversation, list_messages,
                      update_message_rating)

router = APIRouter(
    prefix="/conversations/{conversation_id}/messages", tags=["messages"]
)


def _msg_to_response(m: dict) -> MessageResponse:
    return MessageResponse(
        id=m["id"],
        conversation_id=m["conversation_id"],
        role=m["role"],
        content=m["content"],
        created_at=m.get("created_at"),
        ambiguous=m.get("ambiguous", False),
        bot_trace=m.get("bot_trace"),
        rating=m.get("rating"),
        rated_at=m.get("rated_at"),
    )


@router.get("", response_model=List[MessageResponse])
def list_messages_endpoint(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    limit: int = Query(100, ge=1, le=500),
):
    """Load messages of a conversation (oldest first)."""
    conv = get_conversation(conversation_id, user_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    rows = list_messages(conversation_id, limit=limit)
    return [_msg_to_response(m) for m in rows]


@router.post("", response_model=AddMessageResponse)
def add_message(
    conversation_id: str,
    body: AddMessageRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Send a user message; run the behavior tree and return user + assistant messages."""
    conv = get_conversation(conversation_id, user_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )

    tree = getattr(request.app.state, "tree", None)
    bb = getattr(request.app.state, "bb", None)
    if not tree or not bb:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Behavior tree not initialized",
        )

    bb.clear_for_new_question()
    bb.conversation_id = conversation_id
    bb.user_id = user_id
    bb.user_question = body.content
    tree.tick()

    latest = get_latest_messages(conversation_id, limit=2)
    if len(latest) < 2:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save or retrieve messages",
        )
    user_msg = next((m for m in latest if m["role"] == "user"), None)
    assistant_msg = next((m for m in latest if m["role"] == "assistant"), None)
    if not user_msg or not assistant_msg:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing user or assistant message",
        )
    return AddMessageResponse(
        user_message=_msg_to_response(user_msg),
        assistant_message=_msg_to_response(assistant_msg),
    )


@router.patch("/{message_id}/rating")
def rate_message(
    conversation_id: str,
    message_id: str,
    body: MessageRatingRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Set per-message rating (1-5) for an assistant message."""
    msg = get_message_with_conversation(message_id)
    if (
        not msg
        or msg["conversation_user_id"] != user_id
        or msg["conversation_id"] != conversation_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        )
    ok = update_message_rating(message_id, user_id, body.rating)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found, not an assistant message, or not in this conversation",
        )
    return {"ok": True}
