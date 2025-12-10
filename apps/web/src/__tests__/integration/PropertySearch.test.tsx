/**
 * Integration tests for property search flow
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { rest } from 'msw'
import { setupServer } from 'msw/node'
import ChatPage from '@/app/chat/page'

const server = setupServer(
  rest.post('http://localhost:8000/api/chat/message', (req, res, ctx) => {
    return res(ctx.json({
      success: true,
      response: 'Found 5 properties matching your search',
      classification: 'listing_agent',
      properties: [
        {
          _id: '1',
          title: 'Modern Apartment',
          price: 5000000,
          city: 'Islamabad',
          area: 'F-10',
          bedrooms: 3,
          bathrooms: 2,
          area_sqft: 1200,
          images: ['image1.jpg']
        }
      ]
    }))
  })
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('Property Search Flow', () => {
  it('searches for properties and displays results', async () => {
    const user = userEvent.setup()
    render(<ChatPage />)
    
    // Type search query
    const input = screen.getByPlaceholderText(/Type a message/i)
    await user.type(input, 'Find apartments in Islamabad')
    
    // Submit search
    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)
    
    // Wait for results
    await waitFor(() => {
      expect(screen.getByText(/Found 5 properties/i)).toBeInTheDocument()
    })
    
    // Check property cards displayed
    expect(screen.getByText('Modern Apartment')).toBeInTheDocument()
  })

  it('handles search with no results', async () => {
    server.use(
      rest.post('http://localhost:8000/api/chat/message', (req, res, ctx) => {
        return res(ctx.json({
          success: true,
          response: 'No properties found',
          classification: 'listing_agent',
          properties: []
        }))
      })
    )

    const user = userEvent.setup()
    render(<ChatPage />)
    
    const input = screen.getByPlaceholderText(/Type a message/i)
    await user.type(input, 'Find properties in NonExistentCity')
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)
    
    await waitFor(() => {
      expect(screen.getByText(/No properties found/i)).toBeInTheDocument()
    })
  })

  it('handles API error gracefully', async () => {
    server.use(
      rest.post('http://localhost:8000/api/chat/message', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ error: 'Internal server error' }))
      })
    )

    const user = userEvent.setup()
    render(<ChatPage />)
    
    const input = screen.getByPlaceholderText(/Type a message/i)
    await user.type(input, 'Find apartments')
    
    const sendButton = screen.getByRole('button', { name: /send/i })
    await user.click(sendButton)
    
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument()
    })
  })
})

