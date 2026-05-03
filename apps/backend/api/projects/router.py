"""
Projects and bidding API.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.repositories.builder_bid_repository import (
	BuilderBidRepository,
	get_builder_bid_repository,
)
from common.repositories.builder_profile_repository import (
	BuilderProfileRepository,
	get_builder_profile_repository,
)
from common.repositories.user_project_repository import (
	UserProjectRepository,
	get_user_project_repository,
)
from models.builder_bids import BuilderBidCreate
from models.user_projects import UserProjectCreate
from services.auth.utils import get_current_user, get_optional_current_user
from models.users import User

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=dict)
async def create_project(
	payload: UserProjectCreate,
	current_user: User = Depends(get_current_user),
	repo: UserProjectRepository = Depends(get_user_project_repository),
):
	row = await repo.create(
		{
			"user_id": current_user.id,
			"property_id": payload.property_id,
			"title": payload.title,
			"description": payload.description,
			"project_type": payload.project_type,
			"budget_min": payload.budget_min,
			"budget_max": payload.budget_max,
			"location": payload.location,
			"status": payload.status,
		}
	)
	return repo._row_to_dict(row)


@router.get("/open", response_model=dict)
async def list_open_projects(
	limit: int = Query(50, ge=1, le=200),
	exclude_user_id: str = Query(None, description="Exclude projects by this user (for builders viewing their own buyer projects)"),
	repo: UserProjectRepository = Depends(get_user_project_repository),
):
	print(f"DEBUG /open called with exclude_user_id={exclude_user_id}")
	rows = await repo.list_open(limit=limit, exclude_user_id=exclude_user_id)
	print(f"DEBUG /open returned {len(rows)} projects")
	return {"projects": rows}


@router.get("/me", response_model=dict)
async def list_my_projects(
	current_user: User = Depends(get_current_user),
	repo: UserProjectRepository = Depends(get_user_project_repository),
):
	rows = await repo.list_by_user_id(current_user.id)
	return {"projects": rows}


@router.get("/{project_id}", response_model=dict)
async def get_project(
	project_id: str,
	current_user: Optional[User] = Depends(get_optional_current_user),
	repo: UserProjectRepository = Depends(get_user_project_repository),
	bid_repo: BuilderBidRepository = Depends(get_builder_bid_repository),
	builder_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
	row = await repo.get_by_id(project_id)
	if not row:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
		
	# Enforce visibility rules for assigned/closed projects
	if row.get("status") != "open":
		if not current_user:
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project is no longer open")
			
		# Allow the project owner
		if row.get("user_id") == current_user.id:
			return row
			
		# Check if the user is the accepted builder
		builder_profile = await builder_repo.get_by_user_id(current_user.id)
		if builder_profile:
			bids = await bid_repo.list_by_project_id(project_id)
			accepted_bids = [b for b in bids if b["status"] == "accepted" and b["builder_id"] == builder_profile["id"]]
			if accepted_bids:
				return row
				
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project is no longer open")
		
	return row


@router.patch("/{project_id}", response_model=dict)
async def update_project(
	project_id: str,
	payload: dict,
	current_user: User = Depends(get_current_user),
	repo: UserProjectRepository = Depends(get_user_project_repository),
):
	row = await repo.get_by_id(project_id)
	if not row:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
	if row.get("user_id") != current_user.id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
	updated = await repo.update(project_id, payload)
	return updated or row


@router.delete("/{project_id}", response_model=dict)
async def delete_project(
	project_id: str,
	current_user: User = Depends(get_current_user),
	repo: UserProjectRepository = Depends(get_user_project_repository),
):
	row = await repo.get_by_id(project_id)
	if not row:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
	if row.get("user_id") != current_user.id:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
	deleted = await repo.delete(project_id)
	return {"deleted": deleted}


@router.get("/{project_id}/bids", response_model=dict)
async def list_project_bids(
	project_id: str,
	bid_repo: BuilderBidRepository = Depends(get_builder_bid_repository),
	builder_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
	rows = await bid_repo.list_by_project_id(project_id)
	builder_ids = [row["builder_id"] for row in rows]
	profiles = await builder_repo.list_by_ids(builder_ids)
	profile_map = {profile["id"]: profile for profile in profiles}
	enriched = []
	for row in rows:
		profile = profile_map.get(row["builder_id"]) or {}
		row = {**row}
		row["builder_user_id"] = profile.get("user_id")
		row["builder_company_name"] = profile.get("company_name")
		enriched.append(row)
	return {"bids": enriched}


@router.post("/{project_id}/bids", response_model=dict)
async def create_bid(
	project_id: str,
	payload: BuilderBidCreate,
	current_user: User = Depends(get_current_user),
	bid_repo: BuilderBidRepository = Depends(get_builder_bid_repository),
	builder_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
	builder_profile = await builder_repo.get_by_user_id(current_user.id)
	if not builder_profile:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Builder profile not found")
	existing = await bid_repo.get_by_project_and_builder(project_id, builder_profile["id"])
	if existing:
		raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bid already exists for this project")
	row = await bid_repo.create(
		{
			"project_id": project_id,
			"builder_id": builder_profile["id"],
			"proposal_title": payload.proposal_title,
			"proposal_details": payload.proposal_details,
			"estimated_cost": payload.estimated_cost,
			"estimated_duration": payload.estimated_duration,
			"attachments": payload.attachments,
			"status": payload.status,
		}
	)
	payload = bid_repo._row_to_dict(row)
	payload["builder_user_id"] = builder_profile.get("user_id")
	payload["builder_company_name"] = builder_profile.get("company_name")
	return payload


@router.get("/bids/me", response_model=dict)
async def list_my_bids(
	current_user: User = Depends(get_current_user),
	bid_repo: BuilderBidRepository = Depends(get_builder_bid_repository),
	builder_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
	builder_profile = await builder_repo.get_by_user_id(current_user.id)
	if not builder_profile:
		return {"bids": []}
	rows = await bid_repo.list_by_builder_id(builder_profile["id"])
	return {"bids": rows}


@router.patch("/bids/{bid_id}", response_model=dict)
async def update_bid(
	bid_id: str,
	payload: dict,
	current_user: User = Depends(get_current_user),
	bid_repo: BuilderBidRepository = Depends(get_builder_bid_repository),
	project_repo: UserProjectRepository = Depends(get_user_project_repository),
	builder_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
	row = await bid_repo.get_by_id(bid_id)
	if not row:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found")
	builder_profile = await builder_repo.get_by_user_id(current_user.id)
	project = await project_repo.get_by_id(row["project_id"])
	if not project:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
	if project.get("user_id") != current_user.id and (not builder_profile or builder_profile["id"] != row["builder_id"]):
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
	updated = await bid_repo.update(bid_id, payload)
	
	# If the bid was accepted, mark the project as assigned
	if payload.get("status") == "accepted":
		await project_repo.update(project["id"], {"status": "assigned"})
		
	return updated or row


@router.delete("/bids/{bid_id}", response_model=dict)
async def delete_bid(
	bid_id: str,
	current_user: User = Depends(get_current_user),
	bid_repo: BuilderBidRepository = Depends(get_builder_bid_repository),
	builder_repo: BuilderProfileRepository = Depends(get_builder_profile_repository),
):
	row = await bid_repo.get_by_id(bid_id)
	if not row:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found")
	builder_profile = await builder_repo.get_by_user_id(current_user.id)
	if not builder_profile or builder_profile["id"] != row["builder_id"]:
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the bid owner can delete this bid")
	deleted = await bid_repo.delete(bid_id)
	return {"deleted": deleted}
