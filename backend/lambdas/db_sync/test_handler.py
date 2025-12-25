"""Tests for db_sync handler functions."""

from handler import adapt_row_for_insert
from psycopg2.extras import Json


class TestAdaptRowForInsert:
    """Tests for adapt_row_for_insert() JSONB handling."""

    def test_empty_list_in_jsonb_column_is_wrapped(self):
        """Empty list [] in JSONB column should be wrapped with Json()."""
        row = (1, "test", [])
        columns = ["id", "name", "issues"]
        jsonb_cols = {"issues"}

        result = adapt_row_for_insert(row, columns, jsonb_cols)

        assert result[0] == 1
        assert result[1] == "test"
        assert isinstance(result[2], Json)
        assert result[2].adapted == []

    def test_string_list_in_jsonb_column_is_wrapped(self):
        """String list ["a", "b"] in JSONB column should be wrapped with Json()."""
        row = (1, "test", ["issue1", "issue2"])
        columns = ["id", "name", "issues"]
        jsonb_cols = {"issues"}

        result = adapt_row_for_insert(row, columns, jsonb_cols)

        assert result[0] == 1
        assert result[1] == "test"
        assert isinstance(result[2], Json)
        assert result[2].adapted == ["issue1", "issue2"]

    def test_dict_in_jsonb_column_is_wrapped(self):
        """Dict in JSONB column should be wrapped with Json() (original working case)."""
        row = (1, "test", {"key": "value"})
        columns = ["id", "name", "metadata"]
        jsonb_cols = {"metadata"}

        result = adapt_row_for_insert(row, columns, jsonb_cols)

        assert result[0] == 1
        assert result[1] == "test"
        assert isinstance(result[2], Json)
        assert result[2].adapted == {"key": "value"}

    def test_list_of_dicts_in_jsonb_column_is_wrapped(self):
        """List of dicts in JSONB column should be wrapped with Json()."""
        row = (1, "test", [{"id": 1}, {"id": 2}])
        columns = ["id", "name", "items"]
        jsonb_cols = {"items"}

        result = adapt_row_for_insert(row, columns, jsonb_cols)

        assert result[0] == 1
        assert result[1] == "test"
        assert isinstance(result[2], Json)
        assert result[2].adapted == [{"id": 1}, {"id": 2}]

    def test_non_jsonb_column_unchanged(self):
        """Non-JSONB columns should pass through unchanged."""
        row = (1, "test", ["not", "jsonb"])
        columns = ["id", "name", "tags"]
        jsonb_cols = set()  # No JSONB columns

        result = adapt_row_for_insert(row, columns, jsonb_cols)

        assert result[0] == 1
        assert result[1] == "test"
        assert result[2] == ["not", "jsonb"]  # Unchanged, not wrapped
        assert not isinstance(result[2], Json)

    def test_null_value_in_jsonb_column_unchanged(self):
        """NULL values in JSONB columns should pass through as None."""
        row = (1, "test", None)
        columns = ["id", "name", "issues"]
        jsonb_cols = {"issues"}

        result = adapt_row_for_insert(row, columns, jsonb_cols)

        assert result[0] == 1
        assert result[1] == "test"
        assert result[2] is None
        assert not isinstance(result[2], Json)

    def test_multiple_jsonb_columns(self):
        """Multiple JSONB columns should all be wrapped."""
        row = (1, [], {"key": "value"}, "normal")
        columns = ["id", "issues", "metadata", "name"]
        jsonb_cols = {"issues", "metadata"}

        result = adapt_row_for_insert(row, columns, jsonb_cols)

        assert result[0] == 1
        assert isinstance(result[1], Json)
        assert result[1].adapted == []
        assert isinstance(result[2], Json)
        assert result[2].adapted == {"key": "value"}
        assert result[3] == "normal"
        assert not isinstance(result[3], Json)

    def test_empty_row(self):
        """Empty row should return empty tuple."""
        row = ()
        columns = []
        jsonb_cols = set()

        result = adapt_row_for_insert(row, columns, jsonb_cols)

        assert result == ()

    def test_jsonb_with_nested_structure(self):
        """Complex nested JSONB should be wrapped correctly."""
        nested_data = {
            "users": [{"id": 1, "roles": ["admin", "user"]}],
            "settings": {"enabled": True, "limit": 100},
        }
        row = (1, nested_data)
        columns = ["id", "config"]
        jsonb_cols = {"config"}

        result = adapt_row_for_insert(row, columns, jsonb_cols)

        assert result[0] == 1
        assert isinstance(result[1], Json)
        assert result[1].adapted == nested_data
