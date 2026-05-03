/**
 * Conversation utilities for starting and managing user-to-user conversations
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface StartConversationParams {
  clerkId: string
  participantId: string
  conversationType?: 'direct' | 'project_inquiry' | 'bid_discussion'
  projectId?: string
  bidId?: string
  initialMessage?: string
  /** Pass the current role so the messages page keeps the correct nav highlight */
  role?: 'buyer' | 'builder'
}

export interface ConversationResult {
  success: boolean
  conversationId?: string
  error?: string
}

/**
 * Start a new conversation or get existing one between two users
 */
export async function startConversation(
  params: StartConversationParams
): Promise<ConversationResult> {
  const { clerkId, participantId, conversationType = 'direct', projectId, bidId, initialMessage } = params
  if (!API_BASE_URL) {
    return { success: false, error: 'API URL not configured' }
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/api/conversations?clerk_id=${encodeURIComponent(clerkId)}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          participant_ids: [participantId],
          conversation_type: conversationType,
          project_id: projectId || undefined,
          bid_id: bidId || undefined,
          initial_message: initialMessage || undefined,
        }),
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to start conversation' }))
      return { success: false, error: errorData.detail || 'Failed to start conversation' }
    }

    const data = await response.json()
    return {
      success: true,
      conversationId: data.conversation?._id || data.conversation_id,
    }
  } catch (error: unknown) {
    console.error('Error starting conversation:', error)
    const message = error instanceof Error ? error.message : 'Network error'
    return { success: false, error: message }
  }
}

/**
 * Navigate to messages page with a specific conversation
 */
export function navigateToConversation(conversationId: string, role?: string): void {
  const params = new URLSearchParams({ conversation: conversationId })
  if (role) params.set('role', role)
  window.location.href = `/messages?${params.toString()}`
}

/**
 * Start a conversation and navigate to it
 */
export async function startAndNavigateToConversation(
  params: StartConversationParams
): Promise<ConversationResult> {
  const result = await startConversation(params)
  if (result.success && result.conversationId) {
    navigateToConversation(result.conversationId, params.role)
  }
  return result
}
