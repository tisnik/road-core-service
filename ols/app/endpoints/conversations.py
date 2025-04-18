"""FastAPI endpoint for manipulation with converstation history.

This module defines endpoints and supporting functions for handling
converstation history (read, delete).
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ols import config
from ols.app.endpoints.ols import (
    retrieve_previous_input,
    retrieve_skip_user_id_check,
    retrieve_user_id,
)
from ols.app.models.models import (
    CacheEntry,
    ChatHistoryResponse,
    ConversationDeletionResponse,
    ErrorResponse,
    ForbiddenResponse,
    ListConversationsResponse,
    UnauthorizedResponse,
)
from ols.src.auth.auth import get_auth_dependency

logger = logging.getLogger(__name__)

router = APIRouter(tags=["conversations"])
auth_dependency = get_auth_dependency(config.ols_config, virtual_path="/ols-access")


chat_history_response: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Request is valid and chat history is returned",
        "model": ChatHistoryResponse,
    },
    401: {
        "description": "Missing or invalid credentials provided by client",
        "model": UnauthorizedResponse,
    },
    403: {
        "description": "Client does not have permission to access resource",
        "model": ForbiddenResponse,
    },
    500: {
        "description": "Conversation history is not accessible or other internal error",
        "model": ErrorResponse,
    },
}


@router.get("/conversations/{conversation_id}", responses=chat_history_response)
def get_conversation(
    conversation_id: str,
    history_length: Optional[int] = Query(
        None, description="Number of most recent conversations to return", gt=0
    ),
    auth: Any = Depends(auth_dependency),
) -> ChatHistoryResponse:
    """Get conversation history for a given conversation ID.

    Args:
        auth: The Authentication handler (FastAPI Depends) that will handle authentication Logic.
        conversation_id: The conversation ID to retrieve.
        history_length: (Optional)Number of most recent conversations to return.
        user_id: (Optional)The user ID to retrieve the conversation for.

    Returns:
        List of conversation messages.
    """
    # Initialize variables
    chat_history = []

    user_id = retrieve_user_id(auth)
    logger.info("User ID %s", user_id)
    skip_user_id_check = retrieve_skip_user_id_check(auth)

    # Log incoming request (after redaction)
    logger.info(
        "Getting chat history for user: %s with conversation_id: %s",
        user_id,
        conversation_id,
    )
    try:
        chat_history = CacheEntry.cache_entries_to_history(
            retrieve_previous_input(user_id, conversation_id, skip_user_id_check)
        )
        if len(chat_history) == 0:
            logger.info(
                "No chat history found for user: %s with conversation_id: %s",
                user_id,
                conversation_id,
            )
            raise Exception(f"Conversation {conversation_id} not found")

        if history_length is not None:
            chat_history = chat_history[-history_length:]

        return ChatHistoryResponse(chat_history=chat_history)
    except Exception as e:
        logger.error("Error retrieving previous chat history: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "response": "Error retrieving previous chat history",
                "cause": str(e),
            },
        )


delete_conversation_response: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Request is valid and conversation is deleted",
        "model": ConversationDeletionResponse,
    },
    401: {
        "description": "Missing or invalid credentials provided by client",
        "model": UnauthorizedResponse,
    },
    403: {
        "description": "Client does not have permission to access resource",
        "model": ForbiddenResponse,
    },
    500: {
        "description": "Conversation history is not accessible or other internal error",
        "model": ErrorResponse,
    },
}


@router.delete(
    "/conversations/{conversation_id}", responses=delete_conversation_response
)
def delete_conversation(
    conversation_id: str, auth: Any = Depends(auth_dependency)
) -> ConversationDeletionResponse:
    """Delete conversation history for a given conversation ID.

    Args:
        auth: The Authentication handler (FastAPI Depends) that will handle authentication Logic.
        conversation_id: The conversation ID to delete.
        user_id: (Optional)The user ID to delete the conversation for.

    """
    user_id = retrieve_user_id(auth)
    logger.info("User ID %s", user_id)
    skip_user_id_check = retrieve_skip_user_id_check(auth)

    # Log incoming request (after redaction)
    logger.info(
        "Deleting chat history for user: %s with conversation_id: %s",
        user_id,
        conversation_id,
    )

    if config.conversation_cache.delete(user_id, conversation_id, skip_user_id_check):
        return ConversationDeletionResponse(
            response=f"Conversation {conversation_id} successfully deleted"
        )

    logger.info(
        "No chat history found for user: %s with conversation_id: %s",
        user_id,
        conversation_id,
    )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "response": "Error deleting conversation",
            "cause": f"Conversation {conversation_id} not found",
        },
    )


list_conversations_response: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Request is valid and a list of conversations is returned",
        "model": ListConversationsResponse,
    },
    401: {
        "description": "Missing or invalid credentials provided by client",
        "model": UnauthorizedResponse,
    },
    403: {
        "description": "Client does not have permission to access resource",
        "model": ForbiddenResponse,
    },
    500: {
        "description": "Conversation history is not accessible or other internal error",
        "model": ErrorResponse,
    },
}


@router.get("/conversations", responses=list_conversations_response)
def list_conversations(
    history_length: Optional[int] = Query(
        None, description="Number of most recent conversations to return", gt=0
    ),
    auth: Any = Depends(auth_dependency),
) -> ListConversationsResponse:
    """List all conversations for a given user.

    Args:
        auth: The Authentication handler (FastAPI Depends) that will handle authentication Logic.
        history_length: (Optional)Number of most recent conversations to return.
        user_id: (Optional)The user ID to get all conversations for.

    """
    user_id = retrieve_user_id(auth)
    logger.info("User ID %s", user_id)
    skip_user_id_check = retrieve_skip_user_id_check(auth)

    # Log incoming request (after redaction)
    logger.info("Listing all conversations for user: %s ", user_id)
    conversations = config.conversation_cache.list(user_id, skip_user_id_check)

    if history_length is not None:
        conversations = conversations[:history_length]

    new_conversations = []
    for conv in conversations:
        conversation_id = conv["conversation_id"]
        chat_history = CacheEntry.cache_entries_to_history(
            retrieve_previous_input(user_id, conversation_id, skip_user_id_check)
        )
        conv["last_message_timestamp"] = chat_history[-1].response_metadata[
            "created_at"
        ]
        new_conversations.append(conv)

    return ListConversationsResponse(conversations=new_conversations)
