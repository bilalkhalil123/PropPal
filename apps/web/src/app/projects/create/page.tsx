"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api-client"
import { useCurrentUser } from "@/hooks/useCurrentUser"

export default function CreateProjectPage() {
	const router = useRouter()
	const { isAuthenticated } = useCurrentUser()
	const { getToken } = useAuth()
	const [title, setTitle] = useState("")
	const [description, setDescription] = useState("")
	const [projectType, setProjectType] = useState("")
	const [budgetMin, setBudgetMin] = useState("")
	const [budgetMax, setBudgetMax] = useState("")
	const [location, setLocation] = useState("")
	const [submitting, setSubmitting] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

	const validateForm = () => {
		const nextErrors: Record<string, string> = {}
		if (!title.trim()) nextErrors.title = "Project title is required"
		if (!description.trim()) nextErrors.description = "Description is required"
		if (!projectType.trim()) nextErrors.projectType = "Project type is required"
		if (!location.trim()) nextErrors.location = "Location is required"
		const minValue = Number(budgetMin)
		const maxValue = Number(budgetMax)
		if (!budgetMin.trim() || Number.isNaN(minValue) || minValue <= 0) {
			nextErrors.budgetMin = "Budget minimum must be a positive number"
		}
		if (!budgetMax.trim() || Number.isNaN(maxValue) || maxValue <= 0) {
			nextErrors.budgetMax = "Budget maximum must be a positive number"
		}
		if (!Number.isNaN(minValue) && !Number.isNaN(maxValue) && minValue > maxValue) {
			nextErrors.budgetMax = "Budget maximum must be greater than or equal to minimum"
		}
		setFieldErrors(nextErrors)
		return Object.keys(nextErrors).length === 0
	}

	const handleSubmit = async () => {
		if (!isAuthenticated) {
			router.push("/sign-in?redirect=/projects/create")
			return
		}
		if (!validateForm()) {
			return
		}
		setSubmitting(true)
		setError(null)
		try {
			const token = await getToken()
			const project = await api.projects.create({
				title,
				description,
				project_type: projectType,
				budget_min: Number(budgetMin),
				budget_max: Number(budgetMax),
				location,
			}, token ? { headers: { Authorization: `Bearer ${token}` } } : undefined)
			router.push(`/projects/${project._id || project.id}`)
		} catch (err: unknown) {
			const message = err instanceof Error ? err.message : "Failed to create project"
			setError(message)
		} finally {
			setSubmitting(false)
		}
	}

	return (
		<div className="max-w-3xl mx-auto px-6 md:px-10 py-10">
			<Card>
				<CardHeader>
					<CardTitle>Create a Project</CardTitle>
				</CardHeader>
				<CardContent className="space-y-4">
					<div className="space-y-2">
						<label className="text-sm font-medium text-slate-700">Project title</label>
						<Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Renovate a 3-bed house" />
						{fieldErrors.title && <p className="text-sm text-red-600">{fieldErrors.title}</p>}
					</div>
					<div className="space-y-2">
						<label className="text-sm font-medium text-slate-700">Description</label>
						<Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Share details about your project" />
						{fieldErrors.description && <p className="text-sm text-red-600">{fieldErrors.description}</p>}
					</div>
					<div className="grid gap-4 sm:grid-cols-2">
						<div className="space-y-2">
							<label className="text-sm font-medium text-slate-700">Project type</label>
							<Input value={projectType} onChange={(e) => setProjectType(e.target.value)} placeholder="Construction, renovation..." />
							{fieldErrors.projectType && <p className="text-sm text-red-600">{fieldErrors.projectType}</p>}
						</div>
						<div className="space-y-2">
							<label className="text-sm font-medium text-slate-700">Location</label>
							<Input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="City, area" />
							{fieldErrors.location && <p className="text-sm text-red-600">{fieldErrors.location}</p>}
						</div>
					</div>
					<div className="grid gap-4 sm:grid-cols-2">
						<div className="space-y-2">
							<label className="text-sm font-medium text-slate-700">Budget minimum</label>
							<Input value={budgetMin} onChange={(e) => setBudgetMin(e.target.value)} placeholder="1000000" type="number" />
							{fieldErrors.budgetMin && <p className="text-sm text-red-600">{fieldErrors.budgetMin}</p>}
						</div>
						<div className="space-y-2">
							<label className="text-sm font-medium text-slate-700">Budget maximum</label>
							<Input value={budgetMax} onChange={(e) => setBudgetMax(e.target.value)} placeholder="2000000" type="number" />
							{fieldErrors.budgetMax && <p className="text-sm text-red-600">{fieldErrors.budgetMax}</p>}
						</div>
					</div>
					{error && <p className="text-sm text-red-600">{error}</p>}
					<div className="flex justify-end">
						<Button onClick={handleSubmit} disabled={submitting}>
							{submitting ? "Creating..." : "Create Project"}
						</Button>
					</div>
				</CardContent>
			</Card>
		</div>
	)
}
