'use client'

import { useState } from 'react'
import { UserIcon, WrenchScrewdriverIcon, HomeIcon } from '@heroicons/react/24/outline'
import { useRouter } from 'next/navigation'
import { useCurrentUser } from '@/hooks/useCurrentUser'

interface RoleDropdownProps {
  currentRole: 'buyer' | 'seller' | 'builder'
  onRoleChange: (role: 'buyer' | 'seller' | 'builder') => void
}

const roles = [
  { name: 'Buyer', value: 'buyer' as const, icon: UserIcon, color: 'text-blue-600', bgColor: 'bg-blue-50' },
  { name: 'Seller', value: 'seller' as const, icon: HomeIcon, color: 'text-green-600', bgColor: 'bg-green-50' },
  { name: 'Builder', value: 'builder' as const, icon: WrenchScrewdriverIcon, color: 'text-orange-600', bgColor: 'bg-orange-50' },
]

export default function RoleDropdown({ currentRole, onRoleChange }: RoleDropdownProps) {
  const router = useRouter()
  const { user } = useCurrentUser()
  const [isOpen, setIsOpen] = useState(false)

  const currentRoleConfig = roles.find(r => r.value === currentRole)

  const handleRoleChange = (newRole: 'buyer' | 'seller' | 'builder') => {
    onRoleChange(newRole)
    setIsOpen(false)
    router.push(`/${newRole}`)
  }

  if (!currentRoleConfig) return null

  return (
    <div className="relative inline-block text-left">
      <div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="inline-flex items-center w-full justify-center gap-x-1.5 rounded-md bg-white px-3 py-2 text-sm font-semibold shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
        >
          <span className={`font-semibold ${currentRoleConfig.color}`}>
            {currentRoleConfig.name}
          </span>
          <svg className="-mr-1 h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 z-20 mt-2 w-56 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5">
            <div className="py-1">
              {roles.map((role) => {
                const Icon = role.icon
                return (
                  <button
                    key={role.value}
                    onClick={() => handleRoleChange(role.value)}
                    className={`${
                      currentRole === role.value ? role.bgColor : ''
                    } flex items-center w-full px-4 py-2 text-sm hover:bg-gray-100`}
                  >
                    <Icon
                      className={`mr-3 h-5 w-5 ${
                        currentRole === role.value ? role.color : 'text-gray-400'
                      }`}
                    />
                    <span className={`${
                      currentRole === role.value 
                        ? 'font-medium ' + role.color 
                        : 'text-gray-900'
                    }`}>
                      {role.name}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
