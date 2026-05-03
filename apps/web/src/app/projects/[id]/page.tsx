"use client"

import { useEffect, useState } from "react"
import { useParams, useSearchParams, useRouter } from "next/navigation"
import Link from "next/link"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api-client"
import { useCurrentUser } from "@/hooks/useCurrentUser"
import { startAndNavigateToConversation } from "@/lib/conversation-utils"
import {
	MapPinIcon,
	CurrencyDollarIcon,
	ClockIcon,
	TrashIcon,
	ChatBubbleLeftRightIcon,
	PaperAirplaneIcon,
	ArrowLeftIcon,
	WrenchScrewdriverIcon,
	CheckCircleIcon,
	XCircleIcon,
	BuildingOffice2Icon,
	BanknotesIcon,
} from "@heroicons/react/24/outline"
import { Badge } from "lucide-react"

type Project = {
	_id: string
	user_id: string
	title: string
	description: string
	project_type: string
	budget_min: number
	budget_max: number
	location: string
	status: string
}

type Bid = {
	_id: string
	project_id: string
	builder_id: string
	builder_user_id?: string
	builder_company_name?: string
	proposal_title: string
	proposal_details: string
	estimated_cost: number
	estimated_duration: string
	status: string
}

const statusColors: Record<string, string> = {
	open: "bg-emerald-100 text-emerald-800 border-emerald-200",
	pending: "bg-amber-100 text-amber-800 border-amber-200",
	accepted: "bg-blue-100 text-blue-800 border-blue-200",
	rejected: "bg-red-100 text-red-800 border-red-200",
	awarded: "bg-purple-100 text-purple-800 border-purple-200",
}

export default function ProjectDetailPage() {
	const params = useParams()
	const searchParams = useSearchParams()
	const router = useRouter()
	const projectId = params?.id as string
	const { userId, userRole, clerkId, isAuthenticated } = useCurrentUser()
	const [project, setProject] = useState<Project | null>(null)
	const [bids, setBids] = useState<Bid[]>([])
	const [loading, setLoading] = useState(true)

	const [proposalTitle, setProposalTitle] = useState("")
	const [proposalDetails, setProposalDetails] = useState("")
	const [estimatedCost, setEstimatedCost] = useState("")
	const [estimatedDuration, setEstimatedDuration] = useState("")
	const [submitting, setSubmitting] = useState(false)
	const [errorMsg, setErrorMsg] = useState("")
	const [successMsg, setSuccessMsg] = useState("")

	const loadData = async () => {
		try {
			const projectData = await api.projects.getById(projectId)
			const bidData = await api.projects.listBids(projectId)
			setProject(projectData)
			setBids(bidData.bids || [])
		} catch (error) {
			console.error(error)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		if (projectId) {
			loadData()
		}
	}, [projectId])

	const roleOverride = searchParams.get("role")
	const isBuilderView =
		roleOverride === "builder" ? true : roleOverride === "buyer" ? false : userRole === "builder"
	const isOwner = userId === project?.user_id

	const handleSubmitBid = async () => {
		setErrorMsg("")
		setSuccessMsg("")
		if (!isAuthenticated) {
			window.location.href = `/sign-in?redirect=/projects/${projectId}`
			return
		}
		if (!proposalTitle.trim() || !proposalDetails.trim() || !estimatedCost || !estimatedDuration.trim()) {
			setErrorMsg("Please fill in all bid details (title, details, cost, duration) before submitting.")
			return
		}
		setSubmitting(true)
		try {
			await api.projects.createBid(projectId, {
				proposal_title: proposalTitle,
				proposal_details: proposalDetails,
				estimated_cost: Number(estimatedCost),
				estimated_duration: estimatedDuration,
			})
			setProposalTitle("")
			setProposalDetails("")
			setEstimatedCost("")
			setEstimatedDuration("")
			setSuccessMsg("Proposal submitted successfully!")
			await loadData()
		} catch (error: unknown) {
			let message = "Failed to submit bid"
			if (error instanceof Error) {
				// Parse array stringification if it happened
				try {
					const parsed = JSON.parse(error.message)
					if (Array.isArray(parsed) && parsed[0]?.msg) {
						message = parsed[0].msg
					} else {
						message = error.message
					}
				} catch {
					message = error.message
				}
			}
			// If message is literally [object Object] (unlikely now but just in case)
			if (message === "[object Object]") {
				message = "Failed to submit bid due to an unknown error."
			}
			setErrorMsg(message)
		} finally {
			setSubmitting(false)
		}
	}

	const handleBidStatus = async (bidId: string, status: string) => {
		try {
			await api.projects.updateBid(bidId, { status })
			await loadData()
		} catch (error: unknown) {
			const message = error instanceof Error ? error.message : "Failed to update bid"
			alert(message)
		}
	}

	const handleChat = async (bid: Bid) => {
		if (!clerkId || !bid.builder_user_id) return
		await startAndNavigateToConversation({
			clerkId,
			participantId: bid.builder_user_id,
			conversationType: "direct",
			projectId: bid.project_id,
			role: "buyer",
		})
	}

	const handleChatOwner = async () => {
		if (!clerkId || !project) return
		await startAndNavigateToConversation({
			clerkId,
			participantId: project.user_id,
			conversationType: "direct",
			projectId: project._id,
			role: "builder",
		})
	}

	const handleDeleteProject = async () => {
		if (confirm("Are you sure you want to delete this project? This action cannot be undone.")) {
			try {
				await api.projects.delete(projectId)
				router.push("/projects/my")
			} catch (error: unknown) {
				const message = error instanceof Error ? error.message : "Failed to delete project"
				alert(message)
			}
		}
	}

	if (loading) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))]">
				<div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[color:var(--color-primary)]"></div>
			</div>
		)
	}

	if (!project) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))]">
				<div className="text-center">
					<WrenchScrewdriverIcon className="h-16 w-16 text-slate-300 mx-auto mb-4" />
					<h2 className="text-xl font-bold text-slate-700">Project not found</h2>
					<Link href={isBuilderView ? "/builder" : "/projects/my"} className="text-indigo-600 hover:underline mt-2 inline-block">
						← Go back
					</Link>
				</div>
			</div>
		)
	}
	const hasSubmittedBid = bids.some((b) => b.builder_user_id === userId)

	return (
		<div className="min-h-screen bg-[linear-gradient(to_bottom,rgba(249,249,249,0.85),rgba(237,236,232,0.9))] pt-8 pb-20">
			<div className="max-w-5xl mx-auto px-4 md:px-8 space-y-8">
				
				{/* Back Navigation */}
				<div>
					<Link 
						href={isBuilderView ? "/builder" : "/projects"}
						className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors"
					>
						<ArrowLeftIcon className="h-4 w-4 mr-1.5" />
						Back to {isBuilderView ? "Dashboard" : "Projects"}
					</Link>
				</div>

				{/* Main Project Detail Card */}
				<div className="rounded-3xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-xl overflow-hidden relative">
					{/* Top Accent Gradient */}
					<div className="absolute top-0 left-0 right-0 h-2 bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))]" />
					
					<div className="p-8 md:p-10 flex flex-col md:flex-row gap-8 justify-between">
						{/* Left Content */}
						<div className="space-y-6 flex-1">
							<div>
								<div className="flex items-center gap-3 mb-3">
									<Badge fontVariant="outline" className="rounded-full px-3 border-slate-300 text-slate-600 uppercase tracking-wider font-semibold text-xs">
										{project.project_type}
									</Badge>
									<span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide border ${statusColors[project.status] || statusColors.pending}`}>
										{project.status}
									</span>
								</div>
								<h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
									{project.title}
								</h1>
							</div>

							<div className="prose prose-slate max-w-none">
								<p className="text-slate-600 leading-relaxed text-base md:text-lg">
									{project.description}
								</p>
							</div>
							
							{/* Key Metrics */}
							<div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-slate-200/60">
								<div className="bg-slate-50/50 rounded-xl p-4 border border-slate-100">
									<div className="flex items-center gap-2 text-slate-500 mb-1">
										<MapPinIcon className="h-4 w-4" />
										<span className="text-xs font-semibold uppercase tracking-wider">Location</span>
									</div>
									<p className="font-medium text-slate-900">{project.location}</p>
								</div>
								<div className="bg-slate-50/50 rounded-xl p-4 border border-slate-100">
									<div className="flex items-center gap-2 text-slate-500 mb-1">
										<BanknotesIcon className="h-4 w-4" />
										<span className="text-xs font-semibold uppercase tracking-wider">Budget</span>
									</div>
									<p className="font-medium text-slate-900">
										Rs {project.budget_min.toLocaleString()} - {project.budget_max.toLocaleString()}
									</p>
								</div>
							</div>
						</div>

						{/* Right Actions (Owner Only) */}
						<div className="flex flex-col gap-3 shrink-0">
							{isOwner && (
								<Button 
									variant="destructive" 
									onClick={handleDeleteProject}
									className="flex items-center gap-1.5 shrink-0"
								>
									<TrashIcon className="h-4 w-4" />
									Delete
								</Button>
							)}
						</div>
					</div>
				</div>

				{/* Bid Submission Card (Builder view, non-owner only) */}
				{isBuilderView && !isOwner && (
					<div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg p-6 md:p-8">
						<div className="flex items-center gap-2 mb-5">
							<PaperAirplaneIcon className="h-5 w-5 text-[color:var(--color-primary)]" />
							<h2 className="text-xl font-bold text-slate-900">Submit Your Proposal</h2>
						</div>

						{hasSubmittedBid ? (
							<div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl flex items-center gap-3">
								<svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-emerald-600 shrink-0" viewBox="0 0 20 20" fill="currentColor">
									<path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
								</svg>
								<p className="font-medium text-sm">You have successfully submitted a proposal for this project. The buyer will review your bid shortly.</p>
							</div>
						) : (
						<div className="space-y-4">
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
							<div>
								<label className="block text-sm font-medium text-slate-700 mb-1.5">Proposal Title</label>
								<Input
									value={proposalTitle}
									onChange={(e) => setProposalTitle(e.target.value)}
									placeholder="e.g. Professional Renovation with Premium Materials"
									className="rounded-xl border-slate-300"
								/>
							</div>
							<div>
								<label className="block text-sm font-medium text-slate-700 mb-1.5">Proposal Details</label>
								<Textarea
									value={proposalDetails}
									onChange={(e) => setProposalDetails(e.target.value)}
									placeholder="Describe your approach, experience, and why you're the best fit..."
									className="rounded-xl border-slate-300 min-h-[120px]"
								/>
							</div>
							<div className="grid gap-4 sm:grid-cols-2">
								<div>
									<label className="block text-sm font-medium text-slate-700 mb-1.5">Estimated Cost (PKR)</label>
									<Input
										value={estimatedCost}
										onChange={(e) => setEstimatedCost(e.target.value)}
										placeholder="e.g. 500000"
										type="number"
										className="rounded-xl border-slate-300"
									/>
								</div>
								<div>
									<label className="block text-sm font-medium text-slate-700 mb-1.5">Estimated Duration</label>
									<Input
										value={estimatedDuration}
										onChange={(e) => setEstimatedDuration(e.target.value)}
										placeholder="e.g. 3-4 weeks"
										className="rounded-xl border-slate-300"
									/>
								</div>
							</div>
							<div className="flex flex-wrap gap-3 pt-2">
								<Button
									onClick={handleSubmitBid}
									disabled={submitting}
									className="rounded-xl px-6 bg-[linear-gradient(to_right,var(--color-primary),var(--color-accent-gold))] text-white hover:shadow-lg transition-all"
								>
									{submitting ? "Submitting..." : "Submit Bid"}
								</Button>
							</div>
						</div>
						)}
					</div>
				)}

				{/* Bids Section */}
				{(() => {
					// For builders: only show their own bid + total count
					// For buyers/owners: show all bids
					const myBid = isBuilderView ? bids.find((b) => b.builder_user_id === userId) : null
					const visibleBids = isBuilderView ? (myBid ? [myBid] : []) : bids

					return (
						<div className="rounded-2xl bg-white/70 backdrop-blur-xl border border-slate-200 shadow-lg p-6 md:p-8">
							<div className="flex items-center justify-between mb-5">
								<h2 className="text-xl font-bold text-slate-900">
									{isBuilderView ? (
										<>{bids.length} {bids.length === 1 ? "Bid" : "Bids"} on this project</>
									) : (
										<>Bids ({bids.length})</>
									)}
								</h2>
							</div>

							{visibleBids.length === 0 ? (
								<div className="text-center py-10">
									<WrenchScrewdriverIcon className="h-12 w-12 text-slate-300 mx-auto mb-3" />
									<p className="text-slate-500">
										{isBuilderView
											? "You haven't submitted a bid on this project yet."
											: "No bids have been submitted yet."}
									</p>
								</div>
							) : (
								<div className="space-y-4">
									{isBuilderView && myBid && (
										<p className="text-sm text-slate-500 mb-2">Your submitted proposal:</p>
									)}
									{visibleBids.map((bid) => (
										<div
											key={bid._id}
											className="rounded-xl border border-slate-200 bg-white/60 p-5 hover:shadow-md transition-shadow"
										>
											<div className="flex items-start justify-between gap-3 mb-3">
												<div className="flex-1">
													<h3 className="font-bold text-slate-900 text-lg">{bid.proposal_title}</h3>
													{bid.builder_company_name && (
														<div className="flex items-center gap-1.5 text-sm text-slate-500 mt-0.5">
															<BuildingOffice2Icon className="h-4 w-4" />
															<span>{bid.builder_company_name}</span>
														</div>
													)}
												</div>
												<span
													className={`px-3 py-1 text-xs font-semibold rounded-full border ${statusColors[bid.status] || "bg-slate-100 text-slate-700 border-slate-200"}`}
												>
													{bid.status.charAt(0).toUpperCase() + bid.status.slice(1)}
												</span>
											</div>
											<p className="text-sm text-slate-600 mb-4 leading-relaxed">{bid.proposal_details}</p>
											<div className="flex flex-wrap gap-4 text-sm mb-4">
												<div className="flex items-center gap-1.5 font-semibold text-emerald-700">
													<CurrencyDollarIcon className="h-4 w-4" />
													Rs {bid.estimated_cost?.toLocaleString()}
												</div>
												<div className="flex items-center gap-1.5 text-slate-600">
													<ClockIcon className="h-4 w-4" />
													{bid.estimated_duration}
												</div>
											</div>
											{/* Action buttons — buyer/owner only */}
											{!isBuilderView && isOwner && (
												<div className="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
													{bid.status === "pending" && (
														<>
															<Button
																size="sm"
																onClick={() => handleBidStatus(bid._id, "accepted")}
																className="rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5"
															>
																<CheckCircleIcon className="h-4 w-4" />
																Hire
															</Button>
															<Button
																size="sm"
																variant="outline"
																onClick={() => handleBidStatus(bid._id, "rejected")}
																className="rounded-lg flex items-center gap-1.5 text-red-600 border-red-200 hover:bg-red-50"
															>
																<XCircleIcon className="h-4 w-4" />
																Reject
															</Button>
														</>
													)}
													{bid.builder_user_id && (
														<Button
															size="sm"
															variant="outline"
															onClick={() => handleChat(bid)}
															className="rounded-lg flex items-center gap-1.5"
														>
															<ChatBubbleLeftRightIcon className="h-4 w-4" />
															Chat with Builder
														</Button>
													)}
												</div>
											)}
										</div>
									))}
								</div>
							)}
						</div>
					)
				})()}
			</div>
		</div>
	)
}
