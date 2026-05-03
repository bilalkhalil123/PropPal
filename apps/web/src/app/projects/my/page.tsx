"use client"

import { useEffect, useState } from "react"
import Link from "next/link"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api-client"
import { useCurrentUser } from "@/hooks/useCurrentUser"

type Project = {
	_id: string
	title: string
	project_type: string
	location: string
	status: string
	budget_min: number
	budget_max: number
}

export default function MyProjectsPage() {
	const { isAuthenticated, userRole } = useCurrentUser()
	const [projects, setProjects] = useState<Project[]>([])
	const [loading, setLoading] = useState(true)
	const isBuilder = userRole === "builder"

	useEffect(() => {
		const load = async () => {
			if (isBuilder) {
				setLoading(false)
				return
			}
			try {
				const res = await api.projects.mine()
				setProjects(res.projects || [])
			} catch (error) {
				console.error(error)
			} finally {
				setLoading(false)
			}
		}
		if (isAuthenticated) {
			load()
		} else {
			setLoading(false)
		}
	}, [isAuthenticated, isBuilder])

	if (isBuilder) {
		return (
			<div className="max-w-3xl mx-auto px-6 md:px-10 py-10">
				<Card>
					<CardHeader>
						<CardTitle className="text-lg">Builder Dashboard</CardTitle>
					</CardHeader>
					<CardContent className="text-slate-600">
						Builders can browse open projects and manage their bids from the bids dashboard.
						<Link href="/projects/bids" className="text-indigo-600 hover:underline ml-2">
							Go to My Bids
						</Link>
					</CardContent>
				</Card>
			</div>
		)
	}

	return (
		<div className="max-w-5xl mx-auto px-6 md:px-10 py-10 space-y-6">
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-semibold text-slate-900">My Projects</h1>
					<p className="text-slate-600">Track your posted projects and review bids.</p>
				</div>
				<Link href="/projects/create">
					<Button>Create Project</Button>
				</Link>
			</div>

			{loading && <p className="text-slate-600">Loading projects...</p>}
			{!loading && projects.length === 0 && (
				<Card>
					<CardContent className="py-6 text-slate-600">No projects yet.</CardContent>
				</Card>
			)}

			<div className="grid gap-4">
				{projects.map((project) => (
					<Card key={project._id}>
						<CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
							<CardTitle className="text-lg">{project.title}</CardTitle>
							<Button 
								variant="destructive" 
								size="sm" 
								onClick={async () => {
									if (confirm("Are you sure you want to delete this project?")) {
										try {
											await api.projects.delete(project._id)
											setProjects(projects.filter(p => p._id !== project._id))
										} catch (e: any) {
											alert(e.message || "Failed to delete project")
										}
									}
								}}
							>
								Delete
							</Button>
						</CardHeader>
						<CardContent className="flex flex-col gap-2 text-sm text-slate-600">
							<div>Type: {project.project_type}</div>
							<div>Location: {project.location}</div>
							<div>Budget: Rs {project.budget_min.toLocaleString()} - {project.budget_max.toLocaleString()}</div>
							<div>Status: {project.status}</div>
							<Link href={`/projects/${project._id}`} className="text-indigo-600 hover:underline mt-2">
								View details
							</Link>
						</CardContent>
					</Card>
				))}
			</div>
		</div>
	)
}
