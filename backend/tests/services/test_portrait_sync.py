"""Tests for portrait sync service."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.author import Author
from app.models.binder import Binder
from app.models.publisher import Publisher


class TestQueryWikidata:
    """Tests for Wikidata SPARQL query function."""

    @patch("app.services.portrait_sync.httpx")
    def test_returns_bindings_on_success(self, mock_httpx):
        from app.services.portrait_sync import query_wikidata

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": {"bindings": [{"item": {"value": "http://wd/Q123"}}]}
        }
        mock_httpx.get.return_value = mock_resp

        result = query_wikidata("SELECT ?item WHERE {}")
        assert len(result) == 1
        assert result[0]["item"]["value"] == "http://wd/Q123"

    @patch("app.services.portrait_sync.httpx")
    def test_returns_empty_on_http_error(self, mock_httpx):
        import httpx

        from app.services.portrait_sync import query_wikidata

        mock_httpx.get.side_effect = httpx.HTTPError("timeout")
        mock_httpx.HTTPError = httpx.HTTPError

        result = query_wikidata("SELECT ?item WHERE {}")
        assert result == []


class TestGroupSparqlResults:
    """Tests for grouping SPARQL bindings by item URI."""

    def test_groups_multiple_rows_per_item(self):
        from app.services.portrait_sync import group_sparql_results

        bindings = [
            {
                "item": {"value": "http://wd/Q123"},
                "itemLabel": {"value": "Charles Dickens"},
                "occupationLabel": {"value": "novelist"},
            },
            {
                "item": {"value": "http://wd/Q123"},
                "itemLabel": {"value": "Charles Dickens"},
                "occupationLabel": {"value": "writer"},
                "workLabel": {"value": "Oliver Twist"},
            },
        ]
        grouped = group_sparql_results(bindings)
        assert len(grouped) == 1
        item = grouped["http://wd/Q123"]
        assert set(item["occupations"]) == {"novelist", "writer"}
        assert item["works"] == ["Oliver Twist"]

    def test_skips_empty_item_uri(self):
        from app.services.portrait_sync import group_sparql_results

        bindings = [{"item": {"value": ""}}]
        assert group_sparql_results(bindings) == {}


class TestProcessPortrait:
    """Tests for image processing."""

    def test_processes_valid_image(self):
        from PIL import Image

        from app.services.portrait_sync import process_portrait

        # Create a 800x600 RGB test image
        img = Image.new("RGB", (800, 600), color="red")
        import io

        buf = io.BytesIO()
        img.save(buf, "PNG")
        raw = buf.getvalue()

        result = process_portrait(raw)
        assert result is not None
        # Should be JPEG bytes
        assert result[:2] == b"\xff\xd8"
        # Verify thumbnail dimensions
        processed = Image.open(io.BytesIO(result))
        assert processed.size[0] <= 400
        assert processed.size[1] <= 400

    def test_converts_rgba_to_rgb(self):
        from PIL import Image

        from app.services.portrait_sync import process_portrait

        img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 128))
        import io

        buf = io.BytesIO()
        img.save(buf, "PNG")

        result = process_portrait(buf.getvalue())
        assert result is not None

    def test_returns_none_on_invalid_bytes(self):
        from app.services.portrait_sync import process_portrait

        assert process_portrait(b"not an image") is None


class TestDownloadPortrait:
    """Tests for portrait download."""

    @patch("app.services.portrait_sync.httpx")
    def test_returns_bytes_on_success(self, mock_httpx):
        from app.services.portrait_sync import download_portrait

        mock_resp = MagicMock()
        mock_resp.content = b"fake-image-bytes"
        mock_httpx.get.return_value = mock_resp

        result = download_portrait("http://commons.wikimedia.org/wiki/Special:FilePath/Test.jpg")
        assert result == b"fake-image-bytes"

    @patch("app.services.portrait_sync.httpx")
    def test_returns_none_on_failure(self, mock_httpx):
        import httpx

        from app.services.portrait_sync import download_portrait

        mock_httpx.get.side_effect = httpx.HTTPError("500")
        mock_httpx.HTTPError = httpx.HTTPError

        result = download_portrait("http://commons.wikimedia.org/wiki/Special:FilePath/Test.jpg")
        assert result is None


class TestUploadToS3:
    """Tests for S3 upload."""

    @patch("app.services.portrait_sync.get_s3_client")
    @patch("app.services.portrait_sync.get_settings")
    def test_uploads_with_correct_key(self, mock_settings, mock_s3):
        from app.services.portrait_sync import upload_to_s3

        mock_settings.return_value.images_bucket = "test-bucket"
        mock_client = MagicMock()
        mock_s3.return_value = mock_client

        key = upload_to_s3(b"jpeg-bytes", "author", 42)

        assert key == "entities/author/42/portrait.jpg"
        mock_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="entities/author/42/portrait.jpg",
            Body=b"jpeg-bytes",
            ContentType="image/jpeg",
            CacheControl="public, max-age=86400, stale-while-revalidate=3600",
        )


class TestRunPortraitSync:
    """Integration tests for the portrait sync orchestrator."""

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_dry_run_no_upload(self, mock_query, mock_sleep, db: Session):
        """Dry run should score but not upload."""
        from app.services.portrait_sync import run_portrait_sync

        # Create test author
        author = Author(name="Charles Dickens", birth_year=1812, death_year=1870)
        db.add(author)
        db.flush()

        mock_query.return_value = [
            {
                "item": {"value": "http://wd/Q5686"},
                "itemLabel": {"value": "Charles Dickens"},
                "birth": {"value": "1812-02-07T00:00:00Z"},
                "death": {"value": "1870-06-09T00:00:00Z"},
                "image": {
                    "value": "http://commons.wikimedia.org/wiki/Special:FilePath/Dickens.jpg"
                },
                "occupationLabel": {"value": "novelist"},
            }
        ]

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
        )

        assert result["summary"]["matched"] == 1
        assert result["summary"]["uploaded"] == 0
        assert result["results"][0]["status"] == "dry_run_match"
        assert result["results"][0]["image_url_source"] is not None

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_skip_existing_portraits(self, mock_query, mock_sleep, db: Session):
        """Entities with existing image_url should be skipped."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(
            name="Charles Dickens",
            image_url="https://cdn.example.com/existing.jpg",
        )
        db.add(author)
        db.flush()

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
            skip_existing=True,
        )

        assert result["summary"]["skipped_existing"] == 1
        assert result["results"][0]["status"] == "skipped"
        mock_query.assert_not_called()

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_no_results_from_wikidata(self, mock_query, mock_sleep, db: Session):
        """Empty Wikidata results should produce no_results status."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Unknown Author Nobody")
        db.add(author)
        db.flush()

        mock_query.return_value = []

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
        )

        assert result["results"][0]["status"] == "no_results"
        assert result["summary"]["no_results"] == 1

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_below_threshold(self, mock_query, mock_sleep, db: Session):
        """Low-scoring candidates should produce below_threshold status."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="John Smith")
        db.add(author)
        db.flush()

        mock_query.return_value = [
            {
                "item": {"value": "http://wd/Q999"},
                "itemLabel": {"value": "Completely Different Person"},
            }
        ]

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
            threshold=0.9,
        )

        assert result["results"][0]["status"] == "below_threshold"

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_no_portrait_image(self, mock_query, mock_sleep, db: Session):
        """Match without image should produce no_portrait status."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Charles Dickens", birth_year=1812, death_year=1870)
        db.add(author)
        db.flush()

        mock_query.return_value = [
            {
                "item": {"value": "http://wd/Q5686"},
                "itemLabel": {"value": "Charles Dickens"},
                "birth": {"value": "1812-02-07T00:00:00Z"},
                "death": {"value": "1870-06-09T00:00:00Z"},
                "occupationLabel": {"value": "novelist"},
                # No "image" field
            }
        ]

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
        )

        assert result["results"][0]["status"] == "no_portrait"

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.build_cdn_url")
    @patch("app.services.portrait_sync.upload_to_s3")
    @patch("app.services.portrait_sync.download_portrait")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_full_upload_flow(
        self, mock_query, mock_download, mock_upload, mock_cdn, mock_sleep, db: Session
    ):
        """Full upload flow: query -> score -> download -> process -> upload -> DB update."""
        from PIL import Image

        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Charles Dickens", birth_year=1812, death_year=1870)
        db.add(author)
        db.flush()

        mock_query.return_value = [
            {
                "item": {"value": "http://wd/Q5686"},
                "itemLabel": {"value": "Charles Dickens"},
                "birth": {"value": "1812-02-07T00:00:00Z"},
                "death": {"value": "1870-06-09T00:00:00Z"},
                "image": {
                    "value": "http://commons.wikimedia.org/wiki/Special:FilePath/Dickens.jpg"
                },
                "occupationLabel": {"value": "novelist"},
            }
        ]

        # Create a real image for download
        import io

        img = Image.new("RGB", (200, 200), color="blue")
        buf = io.BytesIO()
        img.save(buf, "PNG")
        mock_download.return_value = buf.getvalue()

        mock_upload.return_value = "entities/author/1/portrait.jpg"
        mock_cdn.return_value = "https://cdn.example.com/entities/author/1/portrait.jpg"

        result = run_portrait_sync(
            db=db,
            dry_run=False,
            entity_type="author",
            entity_ids=[author.id],
        )

        assert result["summary"]["uploaded"] == 1
        r = result["results"][0]
        assert r["status"] == "uploaded"
        assert r["image_uploaded"] is True
        assert r["s3_key"] == "entities/author/1/portrait.jpg"
        assert r["cdn_url"] == "https://cdn.example.com/entities/author/1/portrait.jpg"

        # DB should be updated
        assert author.image_url == "https://cdn.example.com/entities/author/1/portrait.jpg"

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.download_portrait")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_download_failure(self, mock_query, mock_download, mock_sleep, db: Session):
        """Download failure should produce download_failed status."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Charles Dickens", birth_year=1812, death_year=1870)
        db.add(author)
        db.flush()

        mock_query.return_value = [
            {
                "item": {"value": "http://wd/Q5686"},
                "itemLabel": {"value": "Charles Dickens"},
                "birth": {"value": "1812-02-07T00:00:00Z"},
                "death": {"value": "1870-06-09T00:00:00Z"},
                "image": {
                    "value": "http://commons.wikimedia.org/wiki/Special:FilePath/Dickens.jpg"
                },
                "occupationLabel": {"value": "novelist"},
            }
        ]
        mock_download.return_value = None

        result = run_portrait_sync(
            db=db,
            dry_run=False,
            entity_type="author",
            entity_ids=[author.id],
        )

        assert result["results"][0]["status"] == "download_failed"

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_publisher_org_search(self, mock_query, mock_sleep, db: Session):
        """Publishers should use org SPARQL query."""
        from app.services.portrait_sync import run_portrait_sync

        publisher = Publisher(name="Macmillan Publishers")
        db.add(publisher)
        db.flush()

        mock_query.return_value = [
            {
                "item": {"value": "http://wd/Q2350"},
                "itemLabel": {"value": "Macmillan Publishers"},
                "image": {"value": "http://commons.wikimedia.org/wiki/Special:FilePath/Logo.jpg"},
            }
        ]

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="publisher",
            entity_ids=[publisher.id],
        )

        assert result["results"][0]["status"] == "dry_run_match"
        assert result["results"][0]["entity_type"] == "publisher"


class TestScoringImport:
    """Verify scoring functions can be imported from app.utils module."""

    def test_score_candidate_import(self):
        from app.utils.wikidata_scoring import score_candidate

        score = score_candidate(
            entity_name="Charles Dickens",
            entity_birth=1812,
            entity_death=1870,
            entity_book_titles=["Oliver Twist"],
            candidate_label="Charles Dickens",
            candidate_birth=1812,
            candidate_death=1870,
            candidate_works=["Oliver Twist"],
            candidate_occupations=["novelist"],
        )
        assert score > 0.7

    def test_name_similarity_import(self):
        from app.utils.wikidata_scoring import name_similarity

        assert name_similarity("Charles Dickens", "Charles Dickens") == 1.0
        assert name_similarity("Charles Dickens", "Completely Different") == 0.0


class TestHelperFunctions:
    """Tests for pure helper functions."""

    def test_escape_sparql_string(self):
        from app.services.portrait_sync import _escape_sparql_string

        assert _escape_sparql_string('Hello "World"') == 'Hello \\"World\\"'
        assert _escape_sparql_string("Line\nBreak") == "Line\\nBreak"

    def test_parse_year_from_datetime(self):
        from app.services.portrait_sync import parse_year_from_datetime

        assert parse_year_from_datetime("1812-02-07T00:00:00Z") == 1812
        assert parse_year_from_datetime(None) is None
        assert parse_year_from_datetime("invalid") is None

    def test_extract_filename_from_commons_url(self):
        from app.services.portrait_sync import extract_filename_from_commons_url

        url = "http://commons.wikimedia.org/wiki/Special:FilePath/Dickens.jpg"
        assert extract_filename_from_commons_url(url) == "Dickens.jpg"

    def test_build_sparql_query_person(self):
        from app.services.portrait_sync import build_sparql_query_person

        sparql = build_sparql_query_person("Charles Dickens")
        assert '"Charles Dickens"@en' in sparql
        assert "wdt:P31 wd:Q5" in sparql

    def test_build_sparql_query_org(self):
        from app.services.portrait_sync import build_sparql_query_org

        sparql = build_sparql_query_org("Macmillan")
        assert '"Macmillan"@en' in sparql
        assert "Q2085381" in sparql  # publisher class

    def test_make_result_factory(self):
        from app.services.portrait_sync import make_result

        r = make_result("author", 1, "Test", "no_results")
        assert r["entity_type"] == "author"
        assert r["entity_id"] == 1
        assert r["entity_name"] == "Test"
        assert r["status"] == "no_results"
        assert r["score"] == 0.0
        assert r["error"] is None

    def test_make_result_with_kwargs(self):
        from app.services.portrait_sync import make_result

        r = make_result("author", 1, "Test", "uploaded", score=0.95, error="oops")
        assert r["score"] == 0.95
        assert r["error"] == "oops"


class TestValidation:
    """Tests for input validation in run_portrait_sync."""

    def test_entity_ids_requires_entity_type(self, db: Session):
        from app.services.portrait_sync import run_portrait_sync

        with pytest.raises(ValueError, match="entity_type is required"):
            run_portrait_sync(db=db, entity_ids=[1, 2])

    def test_too_many_entity_ids_rejected(self, db: Session):
        from app.services.portrait_sync import run_portrait_sync

        with pytest.raises(ValueError, match="Maximum 50"):
            run_portrait_sync(db=db, entity_type="author", entity_ids=list(range(51)))

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_too_many_entities_rejected(self, mock_query, mock_sleep, db: Session):
        """More than MAX_ENTITIES_PER_REQUEST should raise ValueError."""
        from app.services.portrait_sync import run_portrait_sync

        # Create 11 authors (exceeds MAX_ENTITIES_PER_REQUEST=10)
        for i in range(11):
            db.add(Author(name=f"Author {i}"))
        db.flush()

        with pytest.raises(ValueError, match="Too many entities"):
            run_portrait_sync(db=db, entity_type="author")


class TestBinderUsesOrgQuery:
    """Binders should use org SPARQL query, not person query."""

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_binder_uses_org_search(self, mock_query, mock_sleep, db: Session):
        from app.services.portrait_sync import run_portrait_sync

        binder = Binder(name="Zaehnsdorf")
        db.add(binder)
        db.flush()

        mock_query.return_value = [
            {
                "item": {"value": "http://wd/Q999"},
                "itemLabel": {"value": "Zaehnsdorf"},
                "image": {"value": "http://commons.wikimedia.org/wiki/Special:FilePath/Z.jpg"},
            }
        ]

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="binder",
            entity_ids=[binder.id],
        )

        assert result["results"][0]["entity_type"] == "binder"
        # Verify the org query was used (not person query)
        sparql_arg = mock_query.call_args[0][0]
        assert "Q2085381" in sparql_arg or "Q7275" in sparql_arg
