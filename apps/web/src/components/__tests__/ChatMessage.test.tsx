/**
 * Unit tests for ChatMessage component
 */
import { render, screen } from '@testing-library/react'
import ChatMessage from '@/components/ChatMessage'

describe('ChatMessage', () => {
  it('renders user message correctly', () => {
    render(
      <ChatMessage 
        message="Find apartments in Islamabad"
        isUser={true}
      />
    )
    
    expect(screen.getByText('Find apartments in Islamabad')).toBeInTheDocument()
  })

  it('renders AI message correctly', () => {
    render(
      <ChatMessage 
        message="Found 5 properties matching your search"
        isUser={false}
      />
    )
    
    expect(screen.getByText(/Found 5 properties/i)).toBeInTheDocument()
  })

  it('applies correct styling for user vs AI', () => {
    const { container: userContainer } = render(
      <ChatMessage message="User message" isUser={true} />
    )
    const { container: aiContainer } = render(
      <ChatMessage message="AI message" isUser={false} />
    )
    
    // Check for different styling classes
    expect(userContainer.firstChild).toHaveClass(/user/)
    expect(aiContainer.firstChild).toHaveClass(/ai|assistant/)
  })

  it('handles long messages', () => {
    const longMessage = 'A'.repeat(1000)
    render(<ChatMessage message={longMessage} isUser={true} />)
    
    expect(screen.getByText(longMessage)).toBeInTheDocument()
  })

  it('handles empty messages', () => {
    render(<ChatMessage message="" isUser={true} />)
    
    // Should render without crashing
    expect(screen.queryByText('')).toBeInTheDocument()
  })
})

