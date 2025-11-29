"""Book Image model."""

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BookImage(Base):
    """Image metadata for book photos (actual images stored in S3)."""

    __tablename__ = "book_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
    )

    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    cloudfront_url: Mapped[str | None] = mapped_column(String(500))
    image_type: Mapped[str | None] = mapped_column(String(50))  # cover, spine, interior, etc.
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    caption: Mapped[str | None] = mapped_column(Text)

    # Relationships
    book = relationship("Book", back_populates="images")
