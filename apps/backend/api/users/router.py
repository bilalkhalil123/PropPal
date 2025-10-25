"""
User management and sync API endpoints
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel, EmailStr

from common.repositories.user_repository import UserRepository, get_user_repository
from common.errors import ResourceNotFoundException
from models.users import UserResponse


router = APIRouter(prefix="/api/users", tags=["users"])


class UserSyncRequest(BaseModel):
    """Request model for user sync"""
    clerk_id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = "buyer"
    profile_image: Optional[str] = None


@router.post("/sync", response_model=UserResponse)
async def sync_user(
    request: Request,
    user_data: UserSyncRequest,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Sync user from Clerk to our database
    Called by frontend after successful Clerk authentication
    """
    try:
        print("\n🔄 [USER SYNC] Received sync request:")
        print(f"   📧 Email: {user_data.email}")
        print(f"   👤 Name: {user_data.name}")
        print(f"   🆔 Clerk ID: {user_data.clerk_id}")

        # Check if user already exists
        existing_user = await user_repo.get_user_by_clerk_id(user_data.clerk_id)
        if existing_user:
            print("✅ [USER SYNC] User already exists, updating...")
            update_data = {
                "name": user_data.name,
                "email": user_data.email,
                "phone": user_data.phone,
                "role": user_data.role,
                "profile_image": user_data.profile_image,
            }

            updated_user = await user_repo.update_user(user_data.clerk_id, update_data)
            if updated_user:
                print("✅ [USER SYNC] User updated successfully!")
                return UserResponse(
                    id=updated_user.id,
                    name=updated_user.name,
                    email=updated_user.email,
                    phone=updated_user.phone,
                    role=updated_user.role,
                    profile_image=updated_user.profile_image,
                    clerk_id=updated_user.clerk_id,
                    created_at=updated_user.created_at,
                    updated_at=updated_user.updated_at
                )

        # Create new user
        print("🆕 [USER SYNC] Creating new user...")
        new_user_data = {
            "clerk_id": user_data.clerk_id,
            "name": user_data.name,
            "email": user_data.email,
            "phone": user_data.phone,
            "role": user_data.role,
            "profile_image": user_data.profile_image,
            "password_hash": None,
        }

        created_user = await user_repo.create_user(new_user_data)
        print("✅ [USER SYNC] User created successfully!")

        return UserResponse(
            id=created_user.id,
            name=created_user.name,
            email=created_user.email,
            phone=created_user.phone,
            role=created_user.role,
            profile_image=created_user.profile_image,
            clerk_id=created_user.clerk_id,
            created_at=created_user.created_at,
            updated_at=created_user.updated_at
        )

    except Exception as e:
        print(f"❌ [USER SYNC] Error syncing user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error syncing user: {str(e)}")


@router.get("/sync-status/{clerk_id}")
async def get_sync_status(
    clerk_id: str,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Check if user is synced in our database"""
    try:
        user = await user_repo.get_user_by_clerk_id(clerk_id)
        if user:
            return {
                "synced": True,
                "user_id": str(user.id),
                "last_updated": user.updated_at
            }
        else:
            return {
                "synced": False,
                "message": "User not found in database"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking sync status: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    clerk_id: str = Query(..., description="Clerk user ID"),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Get current user by Clerk ID"""
    try:
        user = await user_repo.get_user_by_clerk_id(clerk_id)
        if not user:
            raise ResourceNotFoundException(
                message=f"User with Clerk ID {clerk_id} not found",
                details={"clerk_id": clerk_id}
            )

        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role,
            profile_image=user.profile_image,
            clerk_id=user.clerk_id,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")


@router.get("/", response_model=List[UserResponse])
async def get_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Get users with optional filtering and pagination"""
    try:
        if role:
            users = await user_repo.get_users_by_role(role, skip, limit)
        else:
            users = await user_repo.get_all_users(skip, limit)

        return [
            UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                phone=user.phone,
                role=user.role,
                profile_image=user.profile_image,
                clerk_id=user.clerk_id,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            for user in users
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")
