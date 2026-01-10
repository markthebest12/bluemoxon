"""Test condition grade normalization migration."""

from sqlalchemy import text

from app.models.book import Book


def test_condition_normalization_sql_is_idempotent(db):
    """Verify the normalization SQL handles all case variants."""
    # Insert test data with mixed casing using ORM
    books = [
        Book(title="Test Good", condition_grade="Good"),
        Book(title="Test GOOD", condition_grade="GOOD"),
        Book(title="Test Fair", condition_grade="Fair"),
        Book(title="Test Poor", condition_grade="Poor"),
        Book(title="Test fine", condition_grade="fine"),
    ]
    for book in books:
        db.add(book)
    db.commit()

    # Run normalization SQL
    db.execute(
        text("""
            UPDATE books
            SET condition_grade = UPPER(condition_grade)
            WHERE condition_grade IS NOT NULL
              AND condition_grade != UPPER(condition_grade)
        """)
    )
    db.commit()

    # Refresh to get updated values
    for book in books:
        db.refresh(book)

    # Verify all are now uppercase
    grades = [b.condition_grade for b in books]
    assert grades == ["GOOD", "GOOD", "FAIR", "POOR", "FINE"]

    # Run again - should be idempotent (no changes)
    db.execute(
        text("""
            UPDATE books
            SET condition_grade = UPPER(condition_grade)
            WHERE condition_grade IS NOT NULL
              AND condition_grade != UPPER(condition_grade)
        """)
    )
    db.commit()

    # Refresh and verify still uppercase
    db.refresh(books[0])
    assert books[0].condition_grade == "GOOD"
