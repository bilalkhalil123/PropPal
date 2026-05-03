"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api-client"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import {
	ArrowLeftIcon,
	DocumentTextIcon,
	TrashIcon,
	CurrencyDollarIcon,
	ClockIcon,
	EyeIcon,
} from "@heroicons/react/24/outline"

type Bid = {
	_id: string
	project_id: string
	proposal_title: string
	proposal_details: string
	estimated_cost: number
	estimated_duration: string
	status: string
	created_at?: string
	project_title?: string
}

const statusColors: Record<string, string> = {
	pending: "bg-amber-100 text-amber-800 border-amber-200",
	shortlisted: "bg-blue-100 text-blue-800 border-blue-200",
	accepted: "bg-emerald-100 text-emerald-800 border-emerald-200",
	rejected: "bg-red-100 text-red-800 border-red-200",
}

export default function MyBidsPage() {
	const { isAuthenticated, loading: userLoading } = useCurrentUser()
	const searchParams = useSearchParams()
	const [bids, setBids] = useState<Bid[]>([])
	const [loading, setLoading] = useState(true)
	const [deletingId, setDeletingId] = useState<string | null>(null)
	const [errorMsg, setErrorMsg] = useState("")
	const [successMsg, setSuccessMsg] = useState("")

	const roleParam = searchParams.get("role")

	useEffect(() => {
		const load = async () => {
			if (userLoading) return
			if (!isAuthenticated) {
				setLoading(false)
				return
			}
			try {
				const res = await api.projects.myBids()
				setBids(res.bids || [])
			} catch (error) {
				console.error(error)
			} finally {
				setLoading(false)
			}
		}
		load()
	}, [isAuthenticated, userLoading])

	const handleDelete = async (bidId: string) => {
		if (!confirm("Are you sure you want to withdraw this bid? This action cannot be undone.")) return
		setDeletingId(bidId)
		setErrorMsg("")
		setSuccessMsg("")
		try {
			await api.projects.deleteBid(bidId)
			setBids((prev) => prev.filter((b) => b._id !== bidId))
			setSuccessMsg("Bid withdrawn successfully.")
		} catch (error) {
			const message = error instanceof Error ? error.message : "Failed to delete bid"
			setErrorMsg(message)
		} finally {
			setDeletingId(null)
		}
	}

	const formatDate = (dateString?: string) => {
		if (!dateString) return ""
		const date = new Date(dateString)
		return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
	}

	if (!isAuthenticated && !userLoading) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))]">
				<div className="text-center">
					<DocumentTextIcon className="h-16 w-16 text-slate-300 mx-auto mb-4" />
					<h2 className="text-xl font-bold text-slate-700 mb-2">Sign in to view your bids</h2>
					<Link href="/sign-in" className="text-indigo-600 hover:underline">Sign in →</Link>
				</div>
			</div>
		)
	}

	return (
		<div className="min-h-screen bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))] pt-8 pb-20">
			<div className="max-w-5xl mx-auto px-4 md:px-8 space-y-8">
				{/* Back Navigation */}
				<div>
					<Link
						href={roleParam === "builder" ? "/builder" : "/projects"}
						className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors"
					>
						<ArrowLeftIcon className="h-4 w-4 mr-1.5" />
						Back to {roleParam === "builder" ? "Builder Dashboard" : "Projects"}
					</Link>
				</div>

				{/* Page Header */}
				<div className="rounded-3xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-xl overflow-hidden relative">
					<div className="absolute top-0 left-0 right-0 h-2 bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))]" />
					<div className="p-8 md:p-10">
						<div className="flex items-center gap-3 mb-2">
							<DocumentTextIcon className="h-7 w-7 text-[color:var(--color-primary)]" />
							<h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 tracking-tight">My Bids</h1>
						</div>
						<p className="text-slate-500 text-base md:text-lg">Track your submitted proposals and their status.</p>
					</div>
				</div>

				{/* Messages */}
				{errorMsg && (
					<div className="p-4 bg-red-50 text-red-700 rounded-xl text-sm font-medium border border-red-200 flex items-start gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-red-500 shrink-0" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
						{errorMsg}
					</div>
				)}
				{successMsg && (
					<div className="p-4 bg-emerald-50 text-emerald-700 rounded-xl text-sm font-medium border border-emerald-200 flex items-start gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-emerald-500 shrink-0" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>
						{successMsg}
					</div>
				)}

				{/* Loading State */}
				{loading && (
					<div className="flex justify-center py-16">
						<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[color:var(--color-primary)]"></div>
					</div>
				)}

				{/* Empty State */}
				{!loading && bids.length === 0 && (
					<div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg p-12 text-center">
						<DocumentTextIcon className="h-16 w-16 text-slate-300 mx-auto mb-4" />
						<h3 className="text-lg font-semibold text-slate-700 mb-2">No bids yet</h3>
						<p className="text-sm text-slate-500 mb-6">You haven&apos;t submitted any proposals yet. Browse open projects to start bidding.</p>
						<Link href={roleParam === "builder" ? "/builder" : "/projects"}>
							<Button className="rounded-xl bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] text-white px-6">
								Browse Projects
							</Button>
						</Link>
					</div>
				)}

				{/* Bids List */}
				{!loading && bids.length > 0 && (
					<div className="space-y-4">
						{bids.map((bid) => (
							<div
								key={bid._id}
								className="rounded-2xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg overflow-hidden hover:shadow-xl transition-shadow"
							>
								<div className="p-6 md:p-8">
									<div className="flex flex-col md:flex-row md:items-start gap-4 justify-between">
										{/* Bid Info */}
										<div className="flex-1 space-y-3">
											<div className="flex items-center gap-3 flex-wrap">
												<h3 className="text-lg font-bold text-slate-900">{bid.proposal_title}</h3>
												<Badge
													variant="outline"
													className={`rounded-full text-xs font-bold uppercase tracking-wide border ${statusColors[bid.status] || statusColors.pending}`}
												>
													{bid.status}
												</Badge>
											</div>

											<p className="text-slate-600 text-sm leading-relaxed line-clamp-2">{bid.proposal_details}</p>

											<div className="flex flex-wrap items-center gap-4 text-sm text-slate-500">
												<div className="flex items-center gap-1.5">
													<CurrencyDollarIcon className="h-4 w-4 text-[color:var(--color-accent-gold)]" />
													<span className="font-semibold text-slate-700">Rs {bid.estimated_cost.toLocaleString()}</span>
												</div>
												<div className="flex items-center gap-1.5">
													<ClockIcon className="h-4 w-4 text-slate-400" />
													<span>{bid.estimated_duration}</span>
												</div>
												{bid.created_at && (
													<span className="text-xs text-slate-400">Submitted {formatDate(bid.created_at)}</span>
												)}
											</div>
										</div>

										{/* Actions */}
										<div className="flex items-center gap-2 shrink-0">
											<Link href={`/projects/${bid.project_id}?role=builder`}>
												<Button
													variant="outline"
													size="sm"
													className="rounded-xl flex items-center gap-1.5"
												>
													<EyeIcon className="h-4 w-4" />
													View Project
												</Button>
											</Link>
											{bid.status === "pending" && (
												<Button
													variant="destructive"
													size="sm"
													onClick={() => handleDelete(bid._id)}
													disabled={deletingId === bid._id}
													className="rounded-xl flex items-center gap-1.5"
												>
													<TrashIcon className="h-4 w-4" />
													{deletingId === bid._id ? "Withdrawing..." : "Withdraw"}
												</Button>
											)}
										</div>
									</div>
								</div>
							</div>
						))}
					</div>
				)}
			</div>
		</div>
	)
}
