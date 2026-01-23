"""Tests for database session configuration."""

from sqlalchemy.pool import NullPool


class TestDatabaseConfiguration:
    """Test database engine configuration for Lambda optimization."""

    def test_engine_uses_nullpool(self):
        """Engine should use NullPool for Lambda compatibility.

        NullPool creates a new connection for each use and closes immediately,
        which is optimal for Lambda where execution contexts freeze/thaw
        unpredictably and pooled connections become stale.

        Note: pool_pre_ping is intentionally NOT used with NullPool because
        pre_ping validates connections on checkout from a pool - NullPool
        doesn't maintain a pool to check out from.
        """
        from app.db.session import engine

        assert isinstance(
            engine.pool, NullPool
        ), f"Expected NullPool but got {type(engine.pool).__name__}"
