"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/lib/api-client"
import { useCurrentUser } from "@/hooks/useCurrentUser"

type Project = {
	_id: string
	title: string
	project_type: string
	location: string
	budget_min: number
	budget_max: number
	status?: string
}

export default function ProjectsHubPage() {
	const { userId, userRole, isAuthenticated, loading: userLoading } = useCurrentUser()
	const searchParams = useSearchParams()
	const [projects, setProjects] = useState<Project[]>([])
	const [loading, setLoading] = useState(true)
	const roleOverride = searchParams.get("role")
	const isBuilder = roleOverride === "builder" ? true : roleOverride === "buyer" ? false : userRole === "builder"

	const dashboardLinks = useMemo(() => {
		if (isBuilder) {
			return [
				{
					title: "My Bids",
					description: "Track your submitted bids and updates.",
					href: "/projects/bids?role=builder",
				},
				{
					title: "Messages",
					description: "Chat with homeowners about projects.",
					href: "/messages?role=builder",
				},
			]
		}
		return [
			{
				title: "Create a Project",
				description: "Post a custom project for builders to bid on.",
				href: "/projects/create",
			},
			{
				title: "My Projects",
				description: "Track your projects and manage bids.",
				href: "/projects/my",
			},
			{
				title: "Messages",
				description: "Chat with builders and manage conversations.",
				href: "/messages",
			},
		]
	}, [isBuilder])

	useEffect(() => {
		if (userLoading) return
		const load = async () => {
			console.log(`[DEBUG ProjectsHub] load called. isBuilder=${isBuilder}, isAuthenticated=${isAuthenticated}, userLoading=${userLoading}, userId=${userId}`)
			try {
				if (isBuilder) {
					console.log(`[DEBUG ProjectsHub] Fetching open projects with userId=${userId}`)
					const res = await api.projects.open(userId || undefined)
					// Foolproof frontend filter to ensure builder NEVER sees their own buyer projects
					const allProjects = res.projects || []
					const filtered = userId ? allProjects.filter((p: any) => p.user_id !== userId) : allProjects
					setProjects(filtered)
					return
				}
				if (isAuthenticated) {
					console.log(`[DEBUG ProjectsHub] Fetching my projects`)
					const res = await api.projects.mine()
					setProjects(res.projects || [])
					return
				}
				setProjects([])
			} catch (error) {
				console.error(error)
			} finally {
				setLoading(false)
			}
		}
		load()
	}, [isBuilder, isAuthenticated, userLoading, userId])

	if (userLoading) {
		return (
			<div className="max-w-6xl mx-auto px-6 md:px-10 py-10">
				<p className="text-slate-600">Loading dashboard…</p>
			</div>
		)
	}

	return (
		<div className="max-w-6xl mx-auto px-6 md:px-10 py-10 space-y-6">
			<div>
				<h1 className="text-3xl font-semibold text-slate-900">
					{isBuilder ? "Builder Project Dashboard" : "Buyer Project Dashboard"}
				</h1>
				<p className="text-slate-600 mt-2">
					{isBuilder
						? "Browse open projects and submit bids to win new work."
						: "Create projects, review bids, and manage your ongoing work."}
				</p>
			</div>

			<div className="grid gap-4 sm:grid-cols-2">
				{dashboardLinks.map((link) => (
					<Link key={link.href} href={link.href} className="group">
						<Card className="h-full border-slate-200 shadow-sm hover:shadow-md transition">
							<CardHeader>
								<CardTitle className="text-lg text-slate-900 group-hover:text-indigo-600 transition">
									{link.title}
								</CardTitle>
							</CardHeader>
							<CardContent className="text-sm text-slate-600">{link.description}</CardContent>
						</Card>
					</Link>
				))}
			</div>

			<Card>
				<CardHeader>
					<CardTitle className="text-lg">
						{isBuilder ? "Open Projects" : "My Projects"}
					</CardTitle>
				</CardHeader>
				<CardContent className="space-y-4">
					{loading && <p className="text-slate-600">Loading projects...</p>}
					{!loading && projects.length === 0 && (
						<p className="text-slate-600">
							{isBuilder ? "No open projects available." : "No projects yet."}
						</p>
					)}
					{!loading && projects.map((project) => (
						<div key={project._id} className="border rounded-lg p-4">
							<div className="font-semibold text-slate-900">{project.title}</div>
							<div className="text-sm text-slate-600">{project.project_type} • {project.location}</div>
							<div className="text-sm text-slate-600">
								Budget: Rs {project.budget_min.toLocaleString()} - {project.budget_max.toLocaleString()}
							</div>
							{!isBuilder && project.status && (
								<div className="text-sm text-slate-600">Status: {project.status}</div>
							)}
							<Link
								href={
									isBuilder
										? `/projects/${project._id}?role=builder`
										: `/projects/${project._id}`
								}
								className="text-indigo-600 hover:underline text-sm mt-2 inline-block"
							>
								View details
							</Link>
						</div>
					))}
				</CardContent>
			</Card>
		</div>
	)
}
