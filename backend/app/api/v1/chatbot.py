import logging
from typing import List
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware
from app.models.chatbot_model import ChatbotModel
from app.schemas.chatbot import (
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    FeedbackRequest,
    SendMessageRequest,
    SendMessageResponse,
)
from app.services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: CreateConversationRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Start a new conversation."""
    return await ChatbotModel(conn).create_conversation(
        current_user["id"], request.title, request.context_type, request.context_reference_id
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """List the current user's conversations, most recent first."""
    return await ChatbotModel(conn).list_conversations(current_user["id"])


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """A conversation with its full message history."""
    model = ChatbotModel(conn)
    conversation = await model.get_conversation(conversation_id, current_user["id"])
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation["messages"] = await model.get_messages(conversation_id)
    return conversation


@router.post("/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Send a message and get the assistant's reply. Both are saved only if the reply succeeds."""
    model = ChatbotModel(conn)
    conversation = await model.get_conversation(conversation_id, current_user["id"])
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    text = request.content.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    history = await model.get_messages(conversation_id, limit=ai_service.HISTORY_LIMIT)
    try:
        reply = await ai_service.generate_reply(conn, history, text)
    except httpx.HTTPError as e:
        logger.error(f"AI provider error: {e}")
        raise HTTPException(status_code=502, detail="The AI service is unavailable. Please try again.")

    user_msg, assistant_msg = await model.add_exchange(conversation_id, text, reply, set_title=text[:60])
    return {"user_message": user_msg, "assistant_message": assistant_msg}


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Delete a conversation and its messages."""
    if not await ChatbotModel(conn).delete_conversation(conversation_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return None


@router.post("/messages/{message_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    message_id: UUID,
    request: FeedbackRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Thumbs up (1) or down (-1) on an assistant reply. Sending again replaces the earlier rating."""
    saved = await ChatbotModel(conn).save_feedback(message_id, current_user["id"], request.rating, request.comment)
    if not saved:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Feedback saved"}
