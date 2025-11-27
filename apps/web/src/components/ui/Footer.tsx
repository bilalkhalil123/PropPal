import Link from "next/link"

interface Column {
  title: string
  items: { label: string; href: string }[]
}

interface FooterProps {
  columns: Column[]
}

export default function Footer({ columns }: FooterProps) {
  return (
    <footer className="bg-slate-900 text-white py-16">
      <div className="max-w-7xl mx-auto px-6 md:px-12 lg:px-24">
        <div className="grid md:grid-cols-4 gap-12 mb-12">
          <div>
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 bg-teal-600 rounded-lg flex items-center justify-center">P</div>
              <span className="text-2xl font-bold">PropPal</span>
            </div>
            <p className="text-slate-400 text-sm leading-relaxed">
              Your AI-powered real estate platform for the modern world.
            </p>
          </div>
          {columns.map((col) => (
            <div key={col.title}>
              <h3 className="text-lg font-semibold mb-4">{col.title}</h3>
              <ul className="space-y-3 text-slate-400 text-sm">
                {col.items.map((i) => (
                  <li key={i.href}>
                    <Link href={i.href} className="hover:text-white transition-colors">
                      {i.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t border-slate-800 pt-8 text-center text-slate-400 text-sm">
          <p>&copy; {new Date().getFullYear()} PropPal. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}


