"""
User management endpoints for frontend integration
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from common.db import get_database
from common.repositories.user_repository import UserRepository, get_user_repository
from models.users import User, UserResponse
from common.errors import ResourceNotFoundException

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_current_user(
    clerk_id: str = Query(..., description="Clerk user ID"),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Get current user by Clerk ID
    This endpoint should be called from the frontend with the user's Clerk ID
    """
    try:
        print(f"\n👤 [GET USER] Request for Clerk ID: {clerk_id}")
        user = await user_repo.get_user_by_clerk_id(clerk_id)
        if not user:
            print(f"❌ [GET USER] User not found for Clerk ID: {clerk_id}")
            raise ResourceNotFoundException(
                message=f"User with Clerk ID {clerk_id} not found",
                details={"clerk_id": clerk_id}
            )
        
        print(f"✅ [GET USER] User found!")
        print(f"   🆔 Database ID: {user.id}")
        print(f"   📧 Email: {user.email}")
        print(f"   👤 Name: {user.name}")
        print(f"   🎭 Role: {user.role}")
        
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
        print(f"❌ [GET USER] Error fetching user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    clerk_id: str = Query(..., description="Clerk user ID"),
    name: Optional[str] = Query(None, description="Updated name"),
    phone: Optional[str] = Query(None, description="Updated phone"),
    role: Optional[str] = Query(None, description="Updated role"),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Update current user profile
    """
    try:
        # Check if user exists
        existing_user = await user_repo.get_user_by_clerk_id(clerk_id)
        if not existing_user:
            raise ResourceNotFoundException(
                message=f"User with Clerk ID {clerk_id} not found",
                details={"clerk_id": clerk_id}
            )
        
        # Prepare update data
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if phone is not None:
            update_data["phone"] = phone
        if role is not None:
            # Validate role
            valid_roles = ["buyer", "seller", "builder", "admin"]
            if role not in valid_roles:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                )
            update_data["role"] = role
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update user
        updated_user = await user_repo.update_user(clerk_id, update_data)
        if not updated_user:
            raise HTTPException(status_code=500, detail="Failed to update user")
        
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")

@router.get("/stats")
async def get_user_stats(
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Get user statistics (admin only)
    """
    try:
        print(f"\n📊 [USER STATS] Fetching user statistics...")
        stats = await user_repo.get_user_stats()
        print(f"✅ [USER STATS] Statistics retrieved:")
        print(f"   👥 Total Users: {stats['total_users']}")
        print(f"   🏠 Buyers: {stats['buyers']}")
        print(f"   🏗️  Sellers: {stats['sellers']}")
        print(f"   🔨 Builders: {stats['builders']}")
        print(f"   👑 Admins: {stats['admins']}")
        return {
            "message": "User statistics retrieved successfully",
            "stats": stats
        }
    except Exception as e:
        print(f"❌ [USER STATS] Error fetching user stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching user stats: {str(e)}")

@router.get("/", response_model=List[UserResponse])
async def get_users(
    role: Optional[str] = Query(None, description="Filter by role"),
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of users to return"),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Get users with optional filtering and pagination
    """
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

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Get user by MongoDB ObjectId
    """
    try:
        user = await user_repo.get_user_by_id(user_id)
        if not user:
            raise ResourceNotFoundException(
                message=f"User with ID {user_id} not found",
                details={"user_id": user_id}
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

@router.post("/sync/{clerk_id}")
async def sync_user_from_clerk(
    clerk_id: str,
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Manually sync user from Clerk (useful for existing users)
    This endpoint can be called to create a user record for existing Clerk users
    """
    try:
        # Check if user already exists
        existing_user = await user_repo.get_user_by_clerk_id(clerk_id)
        if existing_user:
            return {
                "message": "User already exists in database",
                "user_id": str(existing_user.id),
                "clerk_id": clerk_id
            }
        
        # Note: This endpoint would need Clerk SDK integration to fetch user data
        # For now, it returns a message indicating manual sync is needed
        return {
            "message": "Manual sync not implemented. Use Clerk webhooks for automatic sync.",
            "clerk_id": clerk_id,
            "suggestion": "Ensure Clerk webhooks are properly configured"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing user: {str(e)}")
