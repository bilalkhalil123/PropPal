# Clerk Authentication Setup for Mobile App

This guide explains how to set up Clerk authentication in your mobile app.

## Step 1: Get Your Clerk Publishable Key

1. Go to [Clerk Dashboard](https://dashboard.clerk.com/)
2. Select your application
3. Go to **API Keys** in the sidebar
4. Copy your **Publishable Key** (starts with `pk_test_` or `pk_live_`)

## Step 2: Configure the Key

### Option A: Add to app.json (Recommended for Development)

Edit `apps/mobile/app.json` and add your Clerk publishable key:

```json
{
  "expo": {
    "extra": {
      "apiUrl": "http://192.168.110.89:8000",
      "localIp": "192.168.110.89",
      "clerkPublishableKey": "pk_test_your_key_here"
    }
  }
}
```

### Option B: Use Environment Variable

Create a `.env` file in `apps/mobile/` (make sure it's in `.gitignore`):

```env
EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
```

**Note:** For Expo, environment variables must be prefixed with `EXPO_PUBLIC_` to be accessible in the app.

## Step 3: Restart the App

After adding the key, restart your Expo development server:

```bash
# Stop the current server (Ctrl+C)
# Then restart
npm start
```

## Step 4: Test Authentication

1. Open the app in Expo Go
2. Navigate to the sign-in or sign-up page
3. You should see Clerk's authentication UI
4. Try signing in with:
   - Email/Password
   - Google (if configured in Clerk dashboard)
   - Other social providers (if configured)

## Features Included

✅ **Sign In Page** (`/sign-in`) - Full Clerk sign-in component with Google OAuth
✅ **Sign Up Page** (`/sign-up`) - Full Clerk sign-up component with Google OAuth
✅ **Secure Token Storage** - Uses Expo SecureStore for secure token caching
✅ **Auto-redirect** - Automatically redirects to home after successful authentication
✅ **Styled Components** - Matches your app's design theme

## Google OAuth Setup

To enable Google sign-in:

1. Go to [Clerk Dashboard](https://dashboard.clerk.com/)
2. Navigate to **User & Authentication** → **Social Connections**
3. Enable **Google**
4. Configure your Google OAuth credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create OAuth 2.0 credentials
   - Add authorized redirect URIs from Clerk
   - Copy Client ID and Client Secret to Clerk

## Using Authentication in Your App

### Check if user is signed in:

```typescript
import { useAuth } from '@clerk/clerk-expo';

function MyComponent() {
  const { isSignedIn, userId } = useAuth();
  
  if (isSignedIn) {
    return <Text>Welcome! User ID: {userId}</Text>;
  }
  
  return <Text>Please sign in</Text>;
}
```

### Get user information:

```typescript
import { useUser } from '@clerk/clerk-expo';

function MyComponent() {
  const { user } = useUser();
  
  return (
    <View>
      <Text>Email: {user?.primaryEmailAddress?.emailAddress}</Text>
      <Text>Name: {user?.fullName}</Text>
    </View>
  );
}
```

### Sign out:

```typescript
import { useAuth } from '@clerk/clerk-expo';

function SignOutButton() {
  const { signOut } = useAuth();
  
  return (
    <TouchableOpacity onPress={() => signOut()}>
      <Text>Sign Out</Text>
    </TouchableOpacity>
  );
}
```

## Troubleshooting

### "Clerk publishable key is not set"

- Make sure you've added the key to `app.json` or `.env` file
- Restart the Expo development server
- Check that the key starts with `pk_test_` or `pk_live_`

### Google sign-in not working

- Verify Google OAuth is enabled in Clerk dashboard
- Check that redirect URIs are configured correctly
- Make sure you're using the correct OAuth credentials

### Tokens not persisting

- Ensure `expo-secure-store` is installed (already included)
- Check device permissions for secure storage

## Security Notes

- **Never commit your Clerk secret key** to version control
- Use test keys (`pk_test_`) for development
- Use production keys (`pk_live_`) only in production builds
- The publishable key is safe to include in client-side code
- Secret keys should only be used in backend/server code

## Next Steps

After setting up authentication, you can:

1. Protect routes that require authentication
2. Add user profile pages
3. Integrate with your backend API using Clerk tokens
4. Add role-based access control

For more information, visit the [Clerk React Native documentation](https://clerk.com/docs/quickstarts/expo).

