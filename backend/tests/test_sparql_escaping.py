"""Tests for SPARQL string escaping in wikidata_portraits module."""

from scripts.wikidata_portraits import (
    _escape_sparql_string,
    build_sparql_query_org,
    build_sparql_query_person,
)


class TestEscapeSparqlString:
    """Test _escape_sparql_string function."""

    def test_plain_name_unchanged(self):
        """A simple name with no special characters passes through unchanged."""
        assert _escape_sparql_string("Charles Dickens") == "Charles Dickens"

    def test_single_quotes_unchanged(self):
        """Single quotes (apostrophes) are legal in double-quoted SPARQL strings."""
        assert _escape_sparql_string("O'Brien") == "O'Brien"

    def test_double_quotes_escaped(self):
        """Double quotes are escaped with a backslash."""
        assert _escape_sparql_string('Smith "The Great"') == 'Smith \\"The Great\\"'

    def test_backslash_escaped(self):
        """Backslashes are escaped (and processed before other escapes)."""
        assert _escape_sparql_string("back\\slash") == "back\\\\slash"

    def test_newline_escaped(self):
        """Newlines are escaped to \\n."""
        assert _escape_sparql_string("line1\nline2") == "line1\\nline2"

    def test_carriage_return_escaped(self):
        """Carriage returns are escaped to \\r."""
        assert _escape_sparql_string("line1\rline2") == "line1\\rline2"

    def test_tab_escaped(self):
        """Tabs are escaped to \\t."""
        assert _escape_sparql_string("col1\tcol2") == "col1\\tcol2"

    def test_multiple_special_characters(self):
        """Multiple special characters in one string are all escaped."""
        result = _escape_sparql_string('Name\nWith\tSpecial "chars"\r\\end')
        assert result == 'Name\\nWith\\tSpecial \\"chars\\"\\r\\\\end'

    def test_backslash_before_quote_order(self):
        """Backslash-then-quote sequence: backslash is escaped first, then quote.

        Input:  \\\"  (backslash followed by double-quote)
        Should become: \\\\\\\"  (escaped backslash, then escaped quote)
        """
        assert _escape_sparql_string('\\"') == '\\\\\\"'

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert _escape_sparql_string("") == ""

    def test_crlf_escaped(self):
        r"""Windows-style \\r\\n is escaped to \\r\\n."""
        assert _escape_sparql_string("line1\r\nline2") == "line1\\r\\nline2"


class TestBuildSparqlQueryPerson:
    """Test that build_sparql_query_person uses proper escaping."""

    def test_plain_name_in_query(self):
        """Plain name appears directly in the query."""
        query = build_sparql_query_person("Charles Dickens")
        assert '"Charles Dickens"@en' in query

    def test_quotes_escaped_in_query(self):
        """Double quotes in names are escaped in the SPARQL query."""
        query = build_sparql_query_person('Smith "The Great"')
        assert '"Smith \\"The Great\\""@en' in query
        # Must NOT contain unescaped quote that breaks the string literal
        assert '"Smith "' not in query

    def test_apostrophe_in_query(self):
        """Apostrophe names work without issue."""
        query = build_sparql_query_person("O'Brien")
        assert '"O\'Brien"@en' in query

    def test_newline_escaped_in_query(self):
        """Newlines in entity names are escaped."""
        query = build_sparql_query_person("Name\nBad")
        assert '"Name\\nBad"@en' in query

    def test_tab_escaped_in_query(self):
        """Tabs in entity names are escaped."""
        query = build_sparql_query_person("Name\tBad")
        assert '"Name\\tBad"@en' in query

    def test_query_structure(self):
        """Query contains expected SPARQL structure."""
        query = build_sparql_query_person("Test Author")
        assert "wdt:P31 wd:Q5" in query  # instance of human
        assert "LIMIT 10" in query


class TestBuildSparqlQueryOrg:
    """Test that build_sparql_query_org uses proper escaping."""

    def test_plain_name_in_query(self):
        """Plain org name appears directly in the query."""
        query = build_sparql_query_org("Penguin Books")
        assert '"Penguin Books"@en' in query

    def test_quotes_escaped_in_query(self):
        """Double quotes in org names are escaped."""
        query = build_sparql_query_org('Press "Elite"')
        assert '"Press \\"Elite\\""@en' in query

    def test_backslash_escaped_in_query(self):
        """Backslash in org names are escaped."""
        query = build_sparql_query_org("Name\\Corp")
        assert '"Name\\\\Corp"@en' in query

    def test_query_structure(self):
        """Query contains expected SPARQL structure for orgs."""
        query = build_sparql_query_org("Test Publisher")
        assert "wdt:P31 wd:Q2085381" in query  # publisher
        assert "LIMIT 10" in query
