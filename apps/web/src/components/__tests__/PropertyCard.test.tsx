/**
 * Unit tests for PropertyCard component
 */
import { render, screen } from '@testing-library/react'
import PropertyCard from '@/components/PropertyCard'

describe('PropertyCard', () => {
  const mockProperty = {
    _id: '123',
    title: 'Modern Apartment',
    price: 5000000,
    city: 'Islamabad',
    area: 'F-10',
    bedrooms: 3,
    bathrooms: 2,
    area_sqft: 1200,
    images: ['image1.jpg'],
  }

  it('renders property details correctly', () => {
    render(<PropertyCard property={mockProperty} />)
    
    expect(screen.getByText('Modern Apartment')).toBeInTheDocument()
    expect(screen.getByText(/Islamabad/i)).toBeInTheDocument()
    expect(screen.getByText(/3 Bed/i)).toBeInTheDocument()
    expect(screen.getByText(/2 Bath/i)).toBeInTheDocument()
  })

  it('formats price correctly', () => {
    render(<PropertyCard property={mockProperty} />)
    
    // Should format as "PKR 50 Lakh" or similar
    expect(screen.getByText(/PKR/i)).toBeInTheDocument()
  })

  it('handles missing images gracefully', () => {
    const propWithoutImages = { ...mockProperty, images: [] }
    render(<PropertyCard property={propWithoutImages} />)
    
    // Should show placeholder or default image
    const img = screen.getByRole('img')
    expect(img).toBeInTheDocument()
  })

  it('displays area information', () => {
    render(<PropertyCard property={mockProperty} />)
    
    expect(screen.getByText(/F-10/i)).toBeInTheDocument()
    expect(screen.getByText(/1200/i)).toBeInTheDocument()
  })
})

