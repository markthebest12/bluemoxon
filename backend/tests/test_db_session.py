"""Tests for database session configuration."""

from sqlalchemy.pool import NullPool


class TestDatabaseConfiguration:
    """Test database engine configuration for Lambda optimization."""

    def test_engine_uses_nullpool(self):
        """Engine should use NullPool for Lambda compatibility.

        NullPool creates a new connection for each use and closes immediately,
        which is optimal for Lambda where:
        - Execution contexts are frozen/thawed unpredictably
        - Pooled connections can become stale between invocations
        - Each Lambda instance would maintain its own pool anyway
        """
        from app.db.session import engine

        assert isinstance(
            engine.pool, NullPool
        ), f"Expected NullPool but got {type(engine.pool).__name__}"

    def test_engine_has_pool_pre_ping_enabled(self):
        """Engine should have pool_pre_ping enabled for connection validation.

        pool_pre_ping tests connections before use, catching stale connections
        immediately rather than failing mid-request.
        """
        from app.db.session import engine

        assert engine.pool._pre_ping is True, "pool_pre_ping should be enabled"
