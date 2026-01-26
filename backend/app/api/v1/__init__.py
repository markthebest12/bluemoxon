"""API v1 router."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    authors,
    binders,
    books,
    eval_runbook,
    export,
    health,
    images,
    listings,
    notifications,
    orders,
    placeholder,
    publishers,
    search,
    social_circles,
    stats,
    users,
)

router = APIRouter()

router.include_router(health.router, prefix="/health", tags=["health"])
router.include_router(books.router, prefix="/books", tags=["books"])
router.include_router(images.router, prefix="/books/{book_id}/images", tags=["images"])
router.include_router(
    eval_runbook.router, prefix="/books/{book_id}/eval-runbook", tags=["eval-runbook"]
)
router.include_router(placeholder.router, prefix="/images", tags=["images"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(stats.router, prefix="/stats", tags=["statistics"])
router.include_router(publishers.router, prefix="/publishers", tags=["publishers"])
router.include_router(authors.router, prefix="/authors", tags=["authors"])
router.include_router(binders.router, prefix="/binders", tags=["binders"])
router.include_router(export.router, prefix="/export", tags=["export"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(notifications.router, prefix="/users/me", tags=["notifications"])
router.include_router(listings.router, prefix="/listings", tags=["listings"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(orders.router, prefix="/orders", tags=["orders"])
router.include_router(social_circles.router, tags=["social-circles"])
