import { notFound } from 'next/navigation'
import Link from 'next/link'
import PropertyDetailPage from '../../../components/PropertyDetailPage'

async function fetchProperty(id: string) {
  try {
    const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const res = await fetch(`${base}/api/properties/${id}`, {
      cache: 'force-cache',
      // revalidate periodically in production if desired:
      // next: { revalidate: 300 },
    })
    if (!res.ok) {
      console.error(`Failed to fetch property ${id}: ${res.status} ${res.statusText}`)
      notFound()
    }
    return res.json()
  } catch (error) {
    console.error(`Error fetching property ${id}:`, error)
    notFound()
  }
}

export default async function PropertyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const property = await fetchProperty(id)

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white shadow-sm border-b border-slate-200 px-4 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center space-x-2 text-indigo-600 hover:text-indigo-700"
          >
            <span className="text-2xl font-bold">PropPal</span>
          </Link>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <Link href="/chat" className="hover:text-indigo-600">
              Chat
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-4">
        <PropertyDetailPage property={property} />
      </main>
    </div>
  )
}
