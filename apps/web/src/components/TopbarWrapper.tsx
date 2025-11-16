"use client"

import { usePathname } from "next/navigation"
import Topbar from "@/components/Topbar"

export default function TopbarWrapper() {
  const pathname = usePathname()
  if (pathname === "/") return null
  return <Topbar />
}


