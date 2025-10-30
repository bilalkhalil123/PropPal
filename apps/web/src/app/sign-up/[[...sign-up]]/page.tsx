import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12" style={{ background: "radial-gradient(1200px 600px at 10% -10%, rgba(224,164,88,0.06), transparent 60%), radial-gradient(800px 400px at 90% 10%, rgba(13,27,42,0.05), transparent 60%), var(--background)" }}>
      <div className="w-full max-w-md">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-600 text-white font-bold">P</div>
          <h2 className="mt-4 text-3xl font-bold text-slate-900">Create your account</h2>
          <p className="mt-1 text-sm text-slate-600">Join PropPal to start your journey</p>
        </div>
        <div className="flex justify-center">
          <SignUp
            appearance={{
              variables: {
                colorPrimary: 'var(--color-gold)',
                colorText: 'var(--foreground)',
                colorBackground: '#ffffff',
                borderRadius: '12px',
                fontSize: '14px',
              },
              elements: {
                card: 'rounded-2xl border border-slate-200 shadow-sm',
                headerTitle: 'text-slate-900',
                headerSubtitle: 'text-slate-600',
                formButtonPrimary: 'text-white rounded-xl hover:shadow-lg transition-all bg-[linear-gradient(to_right,#f59e0b,var(--color-gold))]',
                formFieldInput: 'rounded-xl border-slate-300 focus:ring-2 focus:ring-[color:var(--color-gold)]',
                footerActionLink: 'text-[color:var(--color-gold)] hover:text-amber-600',
                socialButtonsBlockButton: 'rounded-xl border-slate-300 hover:bg-slate-50',
                formFieldLabel: 'text-slate-700',
              },
            }}
          />
        </div>
      </div>
    </div>
  )
}
