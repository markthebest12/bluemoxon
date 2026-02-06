"""Tests for portrait sync service."""

import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
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
        from app.services.portrait_sync import process_portrait

        img = Image.new("RGB", (800, 600), color="red")
        buf = io.BytesIO()
        img.save(buf, "PNG")

        result = process_portrait(buf.getvalue())
        assert result is not None
        assert result[:2] == b"\xff\xd8"
        processed = Image.open(io.BytesIO(result))
        assert processed.size[0] <= 400
        assert processed.size[1] <= 400

    def test_converts_rgba_to_rgb(self):
        from app.services.portrait_sync import process_portrait

        img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 128))
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


class TestExtractQidFromUri:
    """Tests for QID extraction from Wikidata URIs."""

    def test_extracts_qid_from_full_uri(self):
        from app.services.portrait_sync import _extract_qid_from_uri

        assert _extract_qid_from_uri("http://www.wikidata.org/entity/Q5686") == "Q5686"

    def test_extracts_qid_from_uri_with_trailing_slash(self):
        from app.services.portrait_sync import _extract_qid_from_uri

        assert _extract_qid_from_uri("http://www.wikidata.org/entity/Q5686/") == "Q5686"

    def test_returns_none_for_none_input(self):
        from app.services.portrait_sync import _extract_qid_from_uri

        assert _extract_qid_from_uri(None) is None

    def test_returns_none_for_non_qid(self):
        from app.services.portrait_sync import _extract_qid_from_uri

        assert _extract_qid_from_uri("http://www.wikidata.org/entity/P18") is None

    def test_returns_none_for_empty_string(self):
        from app.services.portrait_sync import _extract_qid_from_uri

        assert _extract_qid_from_uri("") is None


class TestDownloadImageDirect:
    """Tests for generic image download."""

    @patch("app.services.portrait_sync.httpx")
    def test_returns_bytes_on_success(self, mock_httpx):
        from app.services.portrait_sync import _download_image_direct

        mock_resp = MagicMock()
        mock_resp.content = b"image-data"
        mock_httpx.get.return_value = mock_resp

        result = _download_image_direct("https://example.com/image.jpg")
        assert result == b"image-data"

    @patch("app.services.portrait_sync.httpx")
    def test_returns_none_on_failure(self, mock_httpx):
        import httpx

        from app.services.portrait_sync import _download_image_direct

        mock_httpx.get.side_effect = httpx.HTTPError("connection refused")
        mock_httpx.HTTPError = httpx.HTTPError

        result = _download_image_direct("https://example.com/image.jpg")
        assert result is None


class TestSearchCommonsSdc:
    """Tests for Wikimedia Commons SDC search."""

    @patch("app.services.portrait_sync.httpx")
    def test_sdc_search_with_qid(self, mock_httpx):
        from app.services.portrait_sync import _search_commons_sdc

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "query": {
                "pages": {
                    "123": {
                        "imageinfo": [
                            {"thumburl": "https://upload.wikimedia.org/thumb/portrait.jpg"}
                        ]
                    }
                }
            }
        }
        mock_httpx.get.return_value = mock_resp

        result = _search_commons_sdc("Charles Dickens", "Q5686")
        assert result == "https://upload.wikimedia.org/thumb/portrait.jpg"

    @patch("app.services.portrait_sync.httpx")
    def test_text_fallback_when_no_qid(self, mock_httpx):
        from app.services.portrait_sync import _search_commons_sdc

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "query": {
                "pages": {
                    "456": {"imageinfo": [{"url": "https://upload.wikimedia.org/portrait.jpg"}]}
                }
            }
        }
        mock_httpx.get.return_value = mock_resp

        result = _search_commons_sdc("John Murray", None)
        assert result == "https://upload.wikimedia.org/portrait.jpg"

    @patch("app.services.portrait_sync.httpx")
    def test_no_results(self, mock_httpx):
        from app.services.portrait_sync import _search_commons_sdc

        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_httpx.get.return_value = mock_resp

        result = _search_commons_sdc("Unknown Entity", None)
        assert result is None

    @patch("app.services.portrait_sync.httpx")
    def test_http_error(self, mock_httpx):
        import httpx

        from app.services.portrait_sync import _search_commons_sdc

        mock_httpx.get.side_effect = httpx.HTTPError("timeout")
        mock_httpx.HTTPError = httpx.HTTPError

        result = _search_commons_sdc("Test", "Q123")
        assert result is None


class TestSearchGoogleKg:
    """Tests for Google Knowledge Graph search."""

    @patch("app.services.portrait_sync.get_settings")
    @patch("app.services.portrait_sync.httpx")
    def test_happy_path(self, mock_httpx, mock_settings):
        from app.services.portrait_sync import _search_google_kg

        mock_settings.return_value.google_api_key = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "itemListElement": [
                {
                    "result": {
                        "name": "Charles Dickens",
                        "image": {"contentUrl": "https://example.com/dickens.jpg"},
                    }
                }
            ]
        }
        mock_httpx.get.return_value = mock_resp

        result = _search_google_kg("Charles Dickens", "author")
        assert result == "https://example.com/dickens.jpg"

    @patch("app.services.portrait_sync.get_settings")
    def test_no_api_key_skips(self, mock_settings):
        from app.services.portrait_sync import _search_google_kg

        mock_settings.return_value.google_api_key = None

        result = _search_google_kg("Charles Dickens", "author")
        assert result is None

    @patch("app.services.portrait_sync.get_settings")
    @patch("app.services.portrait_sync.httpx")
    def test_no_results(self, mock_httpx, mock_settings):
        from app.services.portrait_sync import _search_google_kg

        mock_settings.return_value.google_api_key = "test-key"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"itemListElement": []}
        mock_httpx.get.return_value = mock_resp

        result = _search_google_kg("Nobody Special", "author")
        assert result is None

    @patch("app.services.portrait_sync.get_settings")
    @patch("app.services.portrait_sync.httpx")
    def test_http_error(self, mock_httpx, mock_settings):
        import httpx

        from app.services.portrait_sync import _search_google_kg

        mock_settings.return_value.google_api_key = "test-key"
        mock_httpx.get.side_effect = httpx.HTTPError("connection error")
        mock_httpx.HTTPError = httpx.HTTPError

        result = _search_google_kg("Test", "author")
        assert result is None


class TestProcessAndUpload:
    """Tests for the extracted _process_and_upload pipeline."""

    @patch("app.services.portrait_sync._build_cdn_url")
    @patch("app.services.portrait_sync.upload_to_s3")
    def test_successful_upload(self, mock_upload, mock_cdn, db: Session):
        from app.services.portrait_sync import _make_result, _process_and_upload

        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        # Create a real image
        img = Image.new("RGB", (200, 200), color="blue")
        buf = io.BytesIO()
        img.save(buf, "PNG")

        mock_upload.return_value = "entities/author/1/portrait.jpg"
        mock_cdn.return_value = "https://cdn.example.com/entities/author/1/portrait.jpg"

        result = _make_result("author", author.id, "Test Author", "pending")
        result = _process_and_upload(db, author, "author", buf.getvalue(), result)

        assert result["status"] == "uploaded"
        assert result["image_uploaded"] is True
        assert result["s3_key"] == "entities/author/1/portrait.jpg"

    def test_invalid_image_bytes(self, db: Session):
        from app.services.portrait_sync import _make_result, _process_and_upload

        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        result = _make_result("author", author.id, "Test Author", "pending")
        result = _process_and_upload(db, author, "author", b"not-an-image", result)

        assert result["status"] == "processing_failed"


class TestFallbackChain:
    """Integration tests for the fallback provider chain."""

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync._search_commons_sdc")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_wikidata_miss_commons_finds_image(
        self, mock_query, mock_commons, mock_sleep, db: Session
    ):
        """When Wikidata misses, Commons SDC should be tried."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        mock_query.return_value = []  # Wikidata miss
        mock_commons.return_value = "https://upload.wikimedia.org/thumb/test.jpg"

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
            enable_fallbacks=True,
        )

        assert result["results"][0]["status"] == "dry_run_match"
        assert result["results"][0]["image_source"] == "commons_sdc"
        assert result["summary"]["fallback_commons_sdc"] == 1

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync._search_google_kg")
    @patch("app.services.portrait_sync._search_commons_sdc")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_commons_miss_google_finds_image(
        self, mock_query, mock_commons, mock_google, mock_sleep, db: Session
    ):
        """When both Wikidata and Commons miss, Google KG should be tried."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        mock_query.return_value = []
        mock_commons.return_value = None  # Commons miss
        mock_google.return_value = "https://example.com/kg-image.jpg"

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
            enable_fallbacks=True,
        )

        assert result["results"][0]["status"] == "dry_run_match"
        assert result["results"][0]["image_source"] == "google_kg"
        assert result["summary"]["fallback_google_kg"] == 1

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync._try_nls_fallback")
    @patch("app.services.portrait_sync._search_google_kg")
    @patch("app.services.portrait_sync._search_commons_sdc")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_all_fallbacks_miss_preserves_status(
        self, mock_query, mock_commons, mock_google, mock_nls, mock_sleep, db: Session
    ):
        """When all fallbacks miss, original status should be preserved."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Nobody Special")
        db.add(author)
        db.flush()

        mock_query.return_value = []
        mock_commons.return_value = None
        mock_google.return_value = None
        mock_nls.return_value = None

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
            enable_fallbacks=True,
        )

        assert result["results"][0]["status"] == "no_results"

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_fallbacks_disabled_by_default(self, mock_query, mock_sleep, db: Session):
        """Fallbacks should not run by default."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Test Author")
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
        assert result["summary"]["fallback_commons_sdc"] == 0
        assert result["summary"]["fallback_google_kg"] == 0
        assert result["summary"]["fallback_nls_map"] == 0

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync._search_google_kg")
    @patch("app.services.portrait_sync._search_commons_sdc")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_skip_commons_flag(
        self, mock_query, mock_commons, mock_google, mock_sleep, db: Session
    ):
        """skip_commons should prevent Commons SDC from being called."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        mock_query.return_value = []
        mock_google.return_value = "https://example.com/image.jpg"

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
            enable_fallbacks=True,
            skip_commons=True,
        )

        mock_commons.assert_not_called()
        assert result["results"][0]["image_source"] == "google_kg"

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync._search_google_kg")
    @patch("app.services.portrait_sync._search_commons_sdc")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_skip_google_flag(self, mock_query, mock_commons, mock_google, mock_sleep, db: Session):
        """skip_google should prevent Google KG from being called."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        mock_query.return_value = []
        mock_commons.return_value = None

        run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
            enable_fallbacks=True,
            skip_google=True,
        )

        mock_google.assert_not_called()

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync._build_cdn_url")
    @patch("app.services.portrait_sync.upload_to_s3")
    @patch("app.services.portrait_sync._download_image_direct")
    @patch("app.services.portrait_sync._search_commons_sdc")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_full_upload_via_fallback(
        self,
        mock_query,
        mock_commons,
        mock_download,
        mock_upload,
        mock_cdn,
        mock_sleep,
        db: Session,
    ):
        """Full upload flow via Commons SDC fallback."""
        from app.services.portrait_sync import run_portrait_sync

        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        mock_query.return_value = []
        mock_commons.return_value = "https://upload.wikimedia.org/thumb/test.jpg"

        img = Image.new("RGB", (200, 200), color="blue")
        buf = io.BytesIO()
        img.save(buf, "PNG")
        mock_download.return_value = buf.getvalue()

        mock_upload.return_value = f"entities/author/{author.id}/portrait.jpg"
        mock_cdn.return_value = f"https://cdn.example.com/entities/author/{author.id}/portrait.jpg"

        result = run_portrait_sync(
            db=db,
            dry_run=False,
            entity_type="author",
            entity_ids=[author.id],
            enable_fallbacks=True,
        )

        assert result["summary"]["uploaded"] == 1
        r = result["results"][0]
        assert r["status"] == "uploaded"
        assert r["image_source"] == "commons_sdc"
        assert r["image_uploaded"] is True

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_wikidata_match_sets_image_source(self, mock_query, mock_sleep, db: Session):
        """Wikidata matches should set image_source='wikidata'."""
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

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
        )

        assert result["results"][0]["image_source"] == "wikidata"

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_max_entities_reduced_with_fallbacks(self, mock_query, mock_sleep, db: Session):
        """With fallbacks enabled, max entities per request should be 3."""
        from app.services.portrait_sync import run_portrait_sync

        for i in range(4):
            db.add(Author(name=f"Author {i}"))
        db.flush()

        with pytest.raises(ValueError, match="Too many entities"):
            run_portrait_sync(
                db=db,
                entity_type="author",
                enable_fallbacks=True,
            )


class TestRunPortraitSync:
    """Integration tests for the portrait sync orchestrator (base features)."""

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_dry_run_no_upload(self, mock_query, mock_sleep, db: Session):
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

        result = run_portrait_sync(
            db=db,
            dry_run=True,
            entity_type="author",
            entity_ids=[author.id],
        )

        assert result["summary"]["matched"] == 1
        assert result["summary"]["uploaded"] == 0
        assert result["results"][0]["status"] == "dry_run_match"

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_skip_existing_portraits(self, mock_query, mock_sleep, db: Session):
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
    @patch("app.services.portrait_sync._build_cdn_url")
    @patch("app.services.portrait_sync.upload_to_s3")
    @patch("app.services.portrait_sync.download_portrait")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_full_upload_flow(
        self, mock_query, mock_download, mock_upload, mock_cdn, mock_sleep, db: Session
    ):
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

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.download_portrait")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_download_failure(self, mock_query, mock_download, mock_sleep, db: Session):
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

    def test_build_sparql_query_person_string(self):
        from app.services.portrait_sync import build_sparql_query_person

        sparql = build_sparql_query_person("Charles Dickens")
        assert '"Charles Dickens"@en' in sparql
        assert "wdt:P31 wd:Q5" in sparql
        assert "skos:altLabel" in sparql
        assert "VALUES ?searchName" in sparql

    def test_build_sparql_query_person_list(self):
        from app.services.portrait_sync import build_sparql_query_person

        sparql = build_sparql_query_person(["Sir Walter Scott", "Walter Scott"])
        assert '"Sir Walter Scott"@en' in sparql
        assert '"Walter Scott"@en' in sparql
        assert "skos:altLabel" in sparql

    def test_build_sparql_query_org_string(self):
        from app.services.portrait_sync import build_sparql_query_org

        sparql = build_sparql_query_org("Macmillan")
        assert '"Macmillan"@en' in sparql
        assert "Q2085381" in sparql
        assert "skos:altLabel" in sparql
        assert "VALUES ?searchName" in sparql

    def test_build_sparql_query_org_list(self):
        from app.services.portrait_sync import build_sparql_query_org

        sparql = build_sparql_query_org(["Macmillan Publishers", "Macmillan"])
        assert '"Macmillan Publishers"@en' in sparql
        assert '"Macmillan"@en' in sparql

    def test_make_result_factory(self):
        from app.services.portrait_sync import _make_result

        r = _make_result("author", 1, "Test", "no_results")
        assert r["entity_type"] == "author"
        assert r["entity_id"] == 1
        assert r["entity_name"] == "Test"
        assert r["status"] == "no_results"
        assert r["score"] == 0.0
        assert r["error"] is None
        assert r["image_source"] is None

    def test_make_result_with_image_source(self):
        from app.services.portrait_sync import _make_result

        r = _make_result("author", 1, "Test", "uploaded", image_source="commons_sdc")
        assert r["image_source"] == "commons_sdc"


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
        from app.services.portrait_sync import run_portrait_sync

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
        sparql_arg = mock_query.call_args[0][0]
        assert "Q2085381" in sparql_arg or "Q7275" in sparql_arg


class TestExtractParentheticalAlias:
    """Tests for extract_parenthetical_alias()."""

    def test_extracts_person_name(self):
        from app.services.portrait_sync import extract_parenthetical_alias

        assert extract_parenthetical_alias("George Eliot (Mary Ann Evans)") == "Mary Ann Evans"

    def test_skips_descriptive_of(self):
        from app.services.portrait_sync import extract_parenthetical_alias

        assert extract_parenthetical_alias("John Murray (of London)") is None

    def test_skips_descriptive_est(self):
        from app.services.portrait_sync import extract_parenthetical_alias

        assert extract_parenthetical_alias("Macmillan (est. 1843)") is None

    def test_skips_editor(self):
        from app.services.portrait_sync import extract_parenthetical_alias

        assert extract_parenthetical_alias("John Smith (editor)") is None

    def test_skips_single_word(self):
        from app.services.portrait_sync import extract_parenthetical_alias

        assert extract_parenthetical_alias("Voltaire (philosopher)") is None

    def test_no_parentheses(self):
        from app.services.portrait_sync import extract_parenthetical_alias

        assert extract_parenthetical_alias("Charles Dickens") is None

    def test_skips_lowercase_start(self):
        from app.services.portrait_sync import extract_parenthetical_alias

        assert extract_parenthetical_alias("Some Name (née something)") is None


class TestPrepareNameVariants:
    """Tests for prepare_name_variants()."""

    def test_plain_name_returns_single(self):
        from app.services.portrait_sync import prepare_name_variants

        variants = prepare_name_variants("Charles Dickens", "author")
        assert variants[0] == "Charles Dickens"
        assert len(variants) >= 1

    def test_honorific_stripping(self):
        from app.services.portrait_sync import prepare_name_variants

        variants = prepare_name_variants("Sir Walter Scott", "author")
        assert "Sir Walter Scott" in variants
        assert "Walter Scott" in variants

    def test_alias_extraction(self):
        from app.services.portrait_sync import prepare_name_variants

        variants = prepare_name_variants("George Eliot (Mary Ann Evans)", "author")
        assert "George Eliot (Mary Ann Evans)" in variants
        assert "George Eliot" in variants
        assert "Mary Ann Evans" in variants

    def test_initial_spacing(self):
        from app.services.portrait_sync import prepare_name_variants

        variants = prepare_name_variants("W.S. Gilbert", "author")
        assert "W. S. Gilbert" in variants

    def test_dedup(self):
        from app.services.portrait_sync import prepare_name_variants

        variants = prepare_name_variants("Charles Dickens", "author")
        assert len(variants) == len(set(variants))

    def test_max_four_variants(self):
        from app.services.portrait_sync import prepare_name_variants

        variants = prepare_name_variants("Sir W.S. Gilbert (William Schwenck Gilbert)", "author")
        assert len(variants) <= 4

    def test_publisher_strips_parenthetical_only(self):
        from app.services.portrait_sync import prepare_name_variants

        variants = prepare_name_variants("Macmillan (est. 1843)", "publisher")
        assert "Macmillan (est. 1843)" in variants
        assert "Macmillan" in variants
        # Publishers shouldn't get normalize_author_name treatment
        assert len(variants) == 2

    def test_publisher_no_parens(self):
        from app.services.portrait_sync import prepare_name_variants

        variants = prepare_name_variants("Macmillan Publishers", "publisher")
        assert variants == ["Macmillan Publishers"]


class TestEnhancedSparqlBuilders:
    """Tests for enhanced SPARQL builders with altLabel and VALUES."""

    def test_person_altlabel_present(self):
        from app.services.portrait_sync import build_sparql_query_person

        sparql = build_sparql_query_person("Walter Scott")
        assert "skos:altLabel" in sparql
        assert "rdfs:label" in sparql
        assert "UNION" in sparql

    def test_person_multiple_variants(self):
        from app.services.portrait_sync import build_sparql_query_person

        sparql = build_sparql_query_person(["Sir Walter Scott", "Walter Scott"])
        assert '"Sir Walter Scott"@en' in sparql
        assert '"Walter Scott"@en' in sparql
        assert "VALUES ?searchName" in sparql

    def test_person_backward_compat_string(self):
        from app.services.portrait_sync import build_sparql_query_person

        sparql = build_sparql_query_person("Charles Dickens")
        assert '"Charles Dickens"@en' in sparql
        assert "wdt:P31 wd:Q5" in sparql

    def test_org_altlabel_present(self):
        from app.services.portrait_sync import build_sparql_query_org

        sparql = build_sparql_query_org("Macmillan")
        assert "skos:altLabel" in sparql
        assert "rdfs:label" in sparql

    def test_org_multiple_variants(self):
        from app.services.portrait_sync import build_sparql_query_org

        sparql = build_sparql_query_org(["Macmillan Publishers", "Macmillan"])
        assert '"Macmillan Publishers"@en' in sparql
        assert '"Macmillan"@en' in sparql

    def test_sparql_escaping_in_variants(self):
        from app.services.portrait_sync import build_sparql_query_person

        sparql = build_sparql_query_person(['O\'Brien "The Writer"'])
        assert "O'Brien" in sparql
        assert '\\"The Writer\\"' in sparql
