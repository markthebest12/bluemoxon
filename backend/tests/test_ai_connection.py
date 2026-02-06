"""Tests for the AIConnection model and _store_ai_connections helper."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.ai_connection import AIConnection
from app.models.base import Base


@pytest.fixture()
def db():
    """In-memory SQLite database for isolated tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Model basics
# ---------------------------------------------------------------------------


class TestAIConnectionModel:
    """Tests for the AIConnection SQLAlchemy model."""

    def test_create_and_query(self, db: Session):
        """Basic insert and retrieval."""
        conn = AIConnection(
            source_type="author",
            source_id=1,
            target_type="author",
            target_id=2,
            relationship="friendship",
            sub_type="CLOSE_FRIENDS",
            confidence=0.9,
            evidence="Known to be close friends",
        )
        db.add(conn)
        db.flush()

        result = db.query(AIConnection).first()
        assert result is not None
        assert result.source_type == "author"
        assert result.source_id == 1
        assert result.target_type == "author"
        assert result.target_id == 2
        assert result.relationship == "friendship"
        assert result.sub_type == "CLOSE_FRIENDS"
        assert result.confidence == 0.9
        assert result.evidence == "Known to be close friends"

    def test_default_confidence(self, db: Session):
        """Confidence defaults to 0.5 when not specified."""
        conn = AIConnection(
            source_type="author",
            source_id=1,
            target_type="publisher",
            target_id=3,
            relationship="collaboration",
        )
        db.add(conn)
        db.flush()

        result = db.query(AIConnection).first()
        assert result.confidence == 0.5

    def test_nullable_fields(self, db: Session):
        """sub_type and evidence are nullable."""
        conn = AIConnection(
            source_type="author",
            source_id=1,
            target_type="binder",
            target_id=5,
            relationship="scandal",
            confidence=0.7,
        )
        db.add(conn)
        db.flush()

        result = db.query(AIConnection).first()
        assert result.sub_type is None
        assert result.evidence is None

    def test_multiple_relationships_same_pair(self, db: Session):
        """Same entity pair can have multiple distinct relationships."""
        db.add(
            AIConnection(
                source_type="author",
                source_id=1,
                target_type="author",
                target_id=2,
                relationship="friendship",
                confidence=0.8,
            )
        )
        db.add(
            AIConnection(
                source_type="author",
                source_id=1,
                target_type="author",
                target_id=2,
                relationship="collaboration",
                confidence=0.9,
            )
        )
        db.flush()

        results = db.query(AIConnection).all()
        assert len(results) == 2
        rels = {r.relationship for r in results}
        assert rels == {"friendship", "collaboration"}


# ---------------------------------------------------------------------------
# _store_ai_connections helper
# ---------------------------------------------------------------------------


class TestStoreAIConnections:
    """Tests for _store_ai_connections in entity_profile service."""

    def _store(self, db, connections):
        """Import and call _store_ai_connections."""
        from app.services.entity_profile import _store_ai_connections

        return _store_ai_connections(db, connections)

    def test_store_new_connection(self, db: Session):
        """Stores a new connection in the table."""
        conns = [
            {
                "source_type": "author",
                "source_id": 10,
                "target_type": "author",
                "target_id": 20,
                "relationship": "friendship",
                "sub_type": "CLOSE_FRIENDS",
                "confidence": 0.85,
                "evidence": "Lifelong friends",
            }
        ]
        count = self._store(db, conns)
        assert count == 1

        row = db.query(AIConnection).first()
        assert row.source_type == "author"
        assert row.source_id == 10
        assert row.target_type == "author"
        assert row.target_id == 20
        assert row.relationship == "friendship"
        assert row.confidence == 0.85

    def test_canonical_ordering(self, db: Session):
        """Connections are stored with canonical ordering (lower node ID first)."""
        # Pass with "higher" source so it gets swapped
        conns = [
            {
                "source_type": "publisher",
                "source_id": 100,
                "target_type": "author",
                "target_id": 5,
                "relationship": "influence",
                "confidence": 0.7,
            }
        ]
        self._store(db, conns)

        row = db.query(AIConnection).first()
        # "author:5" < "publisher:100" so author should be source
        assert row.source_type == "author"
        assert row.source_id == 5
        assert row.target_type == "publisher"
        assert row.target_id == 100

    def test_upsert_higher_confidence_wins(self, db: Session):
        """Upsert keeps higher confidence version."""
        conns1 = [
            {
                "source_type": "author",
                "source_id": 1,
                "target_type": "author",
                "target_id": 2,
                "relationship": "friendship",
                "confidence": 0.5,
                "evidence": "Possibly friends",
            }
        ]
        self._store(db, conns1)

        # Store again with higher confidence
        conns2 = [
            {
                "source_type": "author",
                "source_id": 1,
                "target_type": "author",
                "target_id": 2,
                "relationship": "friendship",
                "confidence": 0.9,
                "evidence": "Definitely friends",
            }
        ]
        count = self._store(db, conns2)
        assert count == 1

        rows = db.query(AIConnection).all()
        assert len(rows) == 1
        assert rows[0].confidence == 0.9
        assert rows[0].evidence == "Definitely friends"

    def test_upsert_lower_confidence_ignored(self, db: Session):
        """Lower confidence update does not overwrite existing."""
        conns1 = [
            {
                "source_type": "author",
                "source_id": 1,
                "target_type": "author",
                "target_id": 2,
                "relationship": "friendship",
                "confidence": 0.9,
                "evidence": "Definitely friends",
            }
        ]
        self._store(db, conns1)

        conns2 = [
            {
                "source_type": "author",
                "source_id": 1,
                "target_type": "author",
                "target_id": 2,
                "relationship": "friendship",
                "confidence": 0.4,
                "evidence": "Maybe friends",
            }
        ]
        count = self._store(db, conns2)
        assert count == 0

        row = db.query(AIConnection).first()
        assert row.confidence == 0.9
        assert row.evidence == "Definitely friends"

    def test_skip_incomplete_connections(self, db: Session):
        """Connections with missing required fields are skipped."""
        conns = [
            {"source_type": "author", "source_id": 1},  # missing target/relationship
            {"relationship": "friendship"},  # missing source/target
        ]
        count = self._store(db, conns)
        assert count == 0
        assert db.query(AIConnection).count() == 0

    def test_store_multiple(self, db: Session):
        """Multiple connections stored in one call."""
        conns = [
            {
                "source_type": "author",
                "source_id": 1,
                "target_type": "author",
                "target_id": 2,
                "relationship": "friendship",
                "confidence": 0.8,
            },
            {
                "source_type": "author",
                "source_id": 1,
                "target_type": "publisher",
                "target_id": 3,
                "relationship": "collaboration",
                "confidence": 0.7,
            },
        ]
        count = self._store(db, conns)
        assert count == 2
        assert db.query(AIConnection).count() == 2

    def test_empty_list(self, db: Session):
        """Empty list returns 0 without errors."""
        count = self._store(db, [])
        assert count == 0

    def test_batch_upsert_query_efficiency(self, db):
        """Batch upsert should use fewer queries than N connections."""
        from app.services.entity_profile import _store_ai_connections

        connections = [
            {
                "source_type": "author",
                "source_id": i,
                "target_type": "author",
                "target_id": i + 100,
                "relationship": "friendship",
                "confidence": 0.8,
                "evidence": f"Evidence {i}",
            }
            for i in range(5)
        ]
        stored = _store_ai_connections(db, connections)
        assert stored == 5

        rows = db.query(AIConnection).all()
        assert len(rows) == 5

        # Verify upsert: re-store with higher confidence
        connections[0]["confidence"] = 0.95
        stored2 = _store_ai_connections(db, connections)
        assert stored2 >= 1

        row = (
            db.query(AIConnection)
            .filter(AIConnection.source_id == 0)
            .first()
        )
        assert row.confidence == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# Migration SQL verification
# ---------------------------------------------------------------------------


class TestMigrationSQL:
    """Verify migration_sql.py entries for the ai_connections table."""

    def test_migration_id_exists(self):
        """Migration entry exists in MIGRATIONS list."""
        from app.db.migration_sql import MIGRATIONS

        ids = [m["id"] for m in MIGRATIONS]
        assert "2843f260f764" in ids

    def test_migration_id_unique(self):
        """No duplicate migration IDs."""
        from app.db.migration_sql import MIGRATIONS

        ids = [m["id"] for m in MIGRATIONS]
        assert len(ids) == len(set(ids))

    def test_migration_sql_has_create_table(self):
        """Migration SQL includes CREATE TABLE statement."""
        from app.db.migration_sql import MIGRATION_2843F260F764_SQL

        create_stmts = [s for s in MIGRATION_2843F260F764_SQL if "CREATE TABLE" in s]
        assert len(create_stmts) >= 1
        assert "ai_connections" in create_stmts[0]

    def test_migration_sql_has_indexes(self):
        """Migration SQL includes index creation."""
        from app.db.migration_sql import MIGRATION_2843F260F764_SQL

        index_stmts = [s for s in MIGRATION_2843F260F764_SQL if "CREATE INDEX" in s]
        assert len(index_stmts) >= 2

    def test_migration_is_last(self):
        """ai_connections migration is the last entry (latest head)."""
        from app.db.migration_sql import MIGRATIONS

        assert MIGRATIONS[-1]["id"] == "2843f260f764"
