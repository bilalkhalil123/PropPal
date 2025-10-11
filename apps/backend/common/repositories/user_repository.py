"""
User repository for database operations
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from fastapi import Depends
from models.users import User, UserCreate, UserResponse
from common.errors import ResourceNotFoundException
from common.db import get_database


class UserRepository:
    """Repository for user database operations"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.users
    
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user in the database"""
        try:
            # Add timestamps
            user_data.update({
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            result = await self.collection.insert_one(user_data)
            
            # Return the created user
            created_user = await self.collection.find_one({"_id": result.inserted_id})
            return User(**created_user)
            
        except Exception as e:
            raise Exception(f"Failed to create user: {str(e)}")
    
    async def get_user_by_clerk_id(self, clerk_id: str) -> Optional[User]:
        """Get user by Clerk ID"""
        try:
            user_doc = await self.collection.find_one({"clerk_id": clerk_id})
            if user_doc:
                return User(**user_doc)
            return None
        except Exception as e:
            raise Exception(f"Failed to get user by clerk_id: {str(e)}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by MongoDB ObjectId"""
        try:
            user_doc = await self.collection.find_one({"_id": ObjectId(user_id)})
            if user_doc:
                return User(**user_doc)
            return None
        except Exception as e:
            raise Exception(f"Failed to get user by id: {str(e)}")
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            user_doc = await self.collection.find_one({"email": email})
            if user_doc:
                return User(**user_doc)
            return None
        except Exception as e:
            raise Exception(f"Failed to get user by email: {str(e)}")
    
    async def update_user(self, clerk_id: str, update_data: Dict[str, Any]) -> Optional[User]:
        """Update user data"""
        try:
            # Add updated timestamp
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"clerk_id": clerk_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                # Return updated user
                updated_user = await self.collection.find_one({"clerk_id": clerk_id})
                return User(**updated_user)
            return None
            
        except Exception as e:
            raise Exception(f"Failed to update user: {str(e)}")
    
    async def soft_delete_user(self, clerk_id: str) -> bool:
        """Soft delete user (mark as deleted)"""
        try:
            result = await self.collection.update_one(
                {"clerk_id": clerk_id},
                {
                    "$set": {
                        "deleted_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            raise Exception(f"Failed to soft delete user: {str(e)}")
    
    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination"""
        try:
            cursor = self.collection.find({"deleted_at": {"$exists": False}}).skip(skip).limit(limit)
            users = []
            async for user_doc in cursor:
                users.append(User(**user_doc))
            return users
        except Exception as e:
            raise Exception(f"Failed to get users: {str(e)}")
    
    async def get_users_by_role(self, role: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users by role"""
        try:
            cursor = self.collection.find({
                "role": role,
                "deleted_at": {"$exists": False}
            }).skip(skip).limit(limit)
            
            users = []
            async for user_doc in cursor:
                users.append(User(**user_doc))
            return users
        except Exception as e:
            raise Exception(f"Failed to get users by role: {str(e)}")
    
    async def user_exists(self, clerk_id: str) -> bool:
        """Check if user exists by Clerk ID"""
        try:
            count = await self.collection.count_documents({"clerk_id": clerk_id})
            return count > 0
        except Exception as e:
            raise Exception(f"Failed to check user existence: {str(e)}")
    
    async def get_user_stats(self) -> Dict[str, int]:
        """Get user statistics"""
        try:
            total_users = await self.collection.count_documents({"deleted_at": {"$exists": False}})
            buyers = await self.collection.count_documents({"role": "buyer", "deleted_at": {"$exists": False}})
            sellers = await self.collection.count_documents({"role": "seller", "deleted_at": {"$exists": False}})
            builders = await self.collection.count_documents({"role": "builder", "deleted_at": {"$exists": False}})
            admins = await self.collection.count_documents({"role": "admin", "deleted_at": {"$exists": False}})
            
            return {
                "total_users": total_users,
                "buyers": buyers,
                "sellers": sellers,
                "builders": builders,
                "admins": admins
            }
        except Exception as e:
            raise Exception(f"Failed to get user stats: {str(e)}")


# Dependency injection function
async def get_user_repository(db: AsyncIOMotorDatabase = Depends(get_database)) -> UserRepository:
    """Get user repository instance"""
    return UserRepository(db)
