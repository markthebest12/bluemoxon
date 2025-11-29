"""API v1 router."""

from fastapi import APIRouter

from app.api.v1 import books, search, stats, publishers, authors, binders, export, images, placeholder

router = APIRouter()

router.include_router(books.router, prefix="/books", tags=["books"])
router.include_router(images.router, prefix="/books/{book_id}/images", tags=["images"])
router.include_router(placeholder.router, prefix="/images", tags=["images"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(stats.router, prefix="/stats", tags=["statistics"])
router.include_router(publishers.router, prefix="/publishers", tags=["publishers"])
router.include_router(authors.router, prefix="/authors", tags=["authors"])
router.include_router(binders.router, prefix="/binders", tags=["binders"])
router.include_router(export.router, prefix="/export", tags=["export"])
