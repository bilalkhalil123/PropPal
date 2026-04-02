# Implementation Plan: Star/Shortlist Property Feature

This plan introduces a "Shortlist" (favorite) feature allowing authenticated users to save properties they are interested in. Guests will be prompted to sign in when attempting to use this feature.

## User Review Required

> [!IMPORTANT]
> **Database Migration**: This change requires adding a new table `user_favorites` to the PostgreSQL database. I will provide the model code; ensuring the database is updated (via Alembic or direct sync) is crucial.
> **Authentication Requirement**: As requested, this feature is restricted to authenticated users. Guests will see a toast notification or a prompt to sign in.

## Proposed Changes

### Backend - Database & API

#### [MODIFY] [models.py](file:///d:/8th%20Semester/FYP/PropPal/apps/backend/db/models.py)
- Add `UserFavorite` model:
    - `user_id` (FK to `users.id`)
    - `property_id` (FK to `properties.id`)
    - `created_at` (Timestamp)
    - Primary Key: `(user_id, property_id)`

#### [MODIFY] [property_repository.py](file:///d:/8th%20Semester/FYP/PropPal/apps/backend/common/repositories/property_repository.py)
- Add `add_favorite(user_id, property_id)` method.
- Add `remove_favorite(user_id, property_id)` method.
- Add `list_favorites(user_id)` method to fetch all properties favorited by a user.
- Add `is_favorited(user_id, property_id)` helper.

#### [MODIFY] [router.py (Properties)](file:///d:/8th%20Semester/FYP/PropPal/apps/backend/api/properties/router.py)
- `POST /api/properties/{property_id}/favorite`: Add/Toggle favorite status.
- `DELETE /api/properties/{property_id}/favorite`: Remove from favorites.
- `GET /api/properties/favorites`: List current user's favorites.

---

### Frontend - UI & API Client

#### [MODIFY] [api-client.ts](file:///d:/8th%20Semester/FYP/PropPal/apps/web/src/lib/api-client.ts)
- Add `properties.favorite(id)`, `properties.unfavorite(id)`, and `properties.getFavorites()` to the `api` object.

#### [MODIFY] [BuyerPage.tsx](file:///d:/8th%20Semester/FYP/PropPal/apps/web/src/app/buyer/page.tsx)
- **State**: Add `favoriteIds` state to track which properties the user has favorited.
- **UI - Tabs**: Add a "Shortlisted" tab/section next to "Recommendations".
- **UI - Property Card**: 
    - Add a floating Heart/Star icon on the property image.
    - Implement the toggle logic (check `isAuthenticated` first).
    - If guest clicks, trigger a "Sign in required" notification.

#### [MODIFY] [Property Detail Page](file:///d:/8th%20Semester/FYP/PropPal/apps/web/src/app/properties/%5Bid%5D/page.tsx)
- Add a "Shortlist" button near the "Contact Seller" or "Ask AI" buttons.

## Open Questions

1. **Shortlist Visibility**: Should the "Shortlisted" properties be a separate tab on the Buyer page, or just mixed in with some "Favorite" icon indicator? (I recommend a separate "My Shortlist" tab for better organization).
2. **Guest Experience**: When a guest clicks the star, should we open the `AuthRequired` screen immediately, or just show a small toast notification?

## Verification Plan

### Automated Tests
- Test API endpoints for adding/removing favorites with valid and invalid (guest) authentication.
- Verify that deleting a property also cleans up its "favorite" entries (CASCADE).

### Manual Verification
1. Log in as a Buyer.
2. Go to the Buyer Dashboard.
3. Click the "Star" icon on several properties.
4. Switch to the "Shortlisted" tab and verify they appear.
5. Click "Unstar" and verify they are removed.
6. Log out, try to star a property as a guest, and verify the "Sign In" prompt appears.
