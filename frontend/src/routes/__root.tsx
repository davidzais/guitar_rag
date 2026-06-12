import { createRootRoute, Outlet } from '@tanstack/react-router'
import { SignedIn, SignedOut, SignIn } from '@clerk/clerk-react'

export const Route = createRootRoute({
  component: () => (
    <div className="min-h-screen bg-background">
      <SignedOut>
        <div className="flex min-h-screen items-center justify-center">
          <SignIn />
        </div>
      </SignedOut>
      <SignedIn>
        <Outlet />
      </SignedIn>
    </div>
  ),
})