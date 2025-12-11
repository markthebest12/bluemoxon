"""Seed author priority scores based on acquisition protocol."""

# ruff: noqa: T201

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.author import Author

AUTHOR_PRIORITIES = {
    "Thomas Hardy": 50,
    "Charles Darwin": 50,
    "Charles Lyell": 40,
    "James Clerk Maxwell": 40,
    "Charles Dickens": 30,
    "Thomas Carlyle": 25,
    "John Ruskin": 25,
    "Wilkie Collins": 20,
}


def seed_priorities():
    db = SessionLocal()
    try:
        for name, score in AUTHOR_PRIORITIES.items():
            author = db.query(Author).filter(Author.name.ilike(f"%{name}%")).first()
            if author:
                author.priority_score = score
                print(f"Updated {author.name}: {score}")
            else:
                print(f"Not found: {name}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_priorities()
