"""Tests for ImageProcessingJob model."""

from datetime import UTC, datetime

from app.models import Book, BookImage, ImageProcessingJob


class TestImageProcessingJobCreation:
    def test_create_job_with_required_fields(self, db):
        """Should create job with book_id and source_image_id."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(
            book_id=book.id,
            s3_key="test_123.jpg",
            display_order=0,
            is_primary=True,
        )
        db.add(image)
        db.commit()

        job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=image.id,
        )
        db.add(job)
        db.commit()

        assert job.id is not None
        assert job.status == "pending"
        assert job.attempt_count == 0
        assert job.model_used is None
        assert job.failure_reason is None
        assert job.created_at is not None


class TestImageProcessingJobStatus:
    def test_status_transitions(self, db):
        """Should allow status transitions."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        job = ImageProcessingJob(book_id=book.id, source_image_id=image.id)
        db.add(job)
        db.commit()

        job.status = "processing"
        job.attempt_count = 1
        job.model_used = "u2net-alpha"
        db.commit()
        assert job.status == "processing"

        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        db.commit()
        assert job.status == "completed"


class TestImageProcessingJobRelationships:
    def test_book_relationship(self, db):
        """Should have relationship to Book."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        job = ImageProcessingJob(book_id=book.id, source_image_id=image.id)
        db.add(job)
        db.commit()

        db.refresh(job)
        assert job.book.title == "Test Book"

    def test_cascade_delete_on_book_delete(self, db):
        """Job should be deleted when book is deleted.

        Note: SQLite doesn't enforce foreign key constraints by default,
        so we test via ORM relationship cascade instead of database-level
        ON DELETE CASCADE. We refresh the book to load relationships which
        then triggers cascade on delete.
        """
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        job = ImageProcessingJob(book_id=book.id, source_image_id=image.id)
        db.add(job)
        db.commit()
        job_id = job.id

        db.refresh(book)
        assert len(book.image_processing_jobs) == 1

        db.delete(book)
        db.commit()

        db.expire_all()
        result = db.query(ImageProcessingJob).filter(ImageProcessingJob.id == job_id).first()
        assert result is None
