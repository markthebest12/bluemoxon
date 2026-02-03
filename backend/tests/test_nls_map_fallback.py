"""Tests for NLS map fallback portrait pipeline."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# --- TestExtractLocation ---


class TestExtractLocation:
    """Test extract_location function."""

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("scripts.nls_map_fallback.anthropic")
    def test_returns_location_from_anthropic_response(self, mock_anthropic):
        """Anthropic returns a valid location JSON -> returns location string."""
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"location": "Albemarle Street, London"}')]
        mock_client.messages.create.return_value = mock_response

        from scripts.nls_map_fallback import extract_location

        result = extract_location("John Murray", "Victorian publisher based in London")
        assert result == "Albemarle Street, London"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("scripts.nls_map_fallback.anthropic")
    def test_returns_none_when_anthropic_says_null(self, mock_anthropic):
        """Anthropic returns null location -> returns None."""
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"location": null}')]
        mock_client.messages.create.return_value = mock_response

        from scripts.nls_map_fallback import extract_location

        result = extract_location("Unknown Entity", "No location info")
        assert result is None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("scripts.nls_map_fallback.anthropic")
    def test_returns_none_on_api_error(self, mock_anthropic):
        """Anthropic API raises exception -> returns None gracefully."""
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API error")

        from scripts.nls_map_fallback import extract_location

        result = extract_location("John Murray", "Some description")
        assert result is None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("scripts.nls_map_fallback.anthropic")
    def test_works_with_none_description(self, mock_anthropic):
        """None description still calls Anthropic with just entity name."""
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"location": "Paternoster Row, London"}')]
        mock_client.messages.create.return_value = mock_response

        from scripts.nls_map_fallback import extract_location

        result = extract_location("Longmans, Green & Co.", None)
        assert result == "Paternoster Row, London"
        # Verify Anthropic was still called
        mock_client.messages.create.assert_called_once()


# --- TestGeocodeLocation ---


class TestGeocodeLocation:
    """Test geocode_location function."""

    @patch("scripts.nls_map_fallback.Nominatim")
    def test_returns_coords_for_known_location(self, mock_nominatim_cls):
        """Known location 'Albemarle Street, London' -> returns lat/lon tuple."""
        mock_geocoder = MagicMock()
        mock_nominatim_cls.return_value = mock_geocoder
        mock_location = MagicMock()
        mock_location.latitude = 51.5074
        mock_location.longitude = -0.1420
        mock_geocoder.geocode.return_value = mock_location

        from scripts.nls_map_fallback import geocode_location

        result = geocode_location("Albemarle Street, London")
        assert result == (51.5074, -0.1420)

    @patch("scripts.nls_map_fallback.Nominatim")
    def test_returns_none_for_unknown_location(self, mock_nominatim_cls):
        """Unknown location -> geopy returns None -> returns None."""
        mock_geocoder = MagicMock()
        mock_nominatim_cls.return_value = mock_geocoder
        mock_geocoder.geocode.return_value = None

        from scripts.nls_map_fallback import geocode_location

        result = geocode_location("Nonexistent Place XYZ123")
        assert result is None

    @patch("scripts.nls_map_fallback.Nominatim")
    def test_returns_none_on_timeout(self, mock_nominatim_cls):
        """Geocoder timeout -> returns None gracefully."""
        from geopy.exc import GeocoderTimedOut

        mock_geocoder = MagicMock()
        mock_nominatim_cls.return_value = mock_geocoder
        mock_geocoder.geocode.side_effect = GeocoderTimedOut("Timeout")

        from scripts.nls_map_fallback import geocode_location

        result = geocode_location("Albemarle Street, London")
        assert result is None


# --- TestLatLonToTile ---


class TestLatLonToTile:
    """Test latlon_to_tile function."""

    def test_london_coordinates_at_zoom_15(self):
        """London (51.5074, -0.1278) at zoom 15 -> specific tile coords."""
        from scripts.nls_map_fallback import latlon_to_tile

        z, x, y = latlon_to_tile(51.5074, -0.1278, zoom=15)
        assert z == 15
        # At zoom 15, London should be around x=16372, y=10896
        # n = 2^15 = 32768
        # x = int(((-0.1278) + 180) / 360 * 32768) = int(179.8722/360 * 32768) = int(16372.37) = 16372
        assert x == 16372
        # y should be around 10896 for London
        assert 10890 <= y <= 10900

    def test_equator_prime_meridian(self):
        """Equator/prime meridian (0, 0) at zoom 15."""
        from scripts.nls_map_fallback import latlon_to_tile

        z, x, y = latlon_to_tile(0.0, 0.0, zoom=15)
        assert z == 15
        # At equator, prime meridian: x = 32768/2 = 16384, y = 32768/2 = 16384
        assert x == 16384
        assert y == 16384


# --- TestDownloadNlsTile ---


class TestDownloadNlsTile:
    """Test download_nls_tile function."""

    @patch("scripts.nls_map_fallback.requests")
    def test_successful_download(self, mock_requests):
        """Successful tile download -> returns bytes."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"\x89PNG\r\n\x1a\nfake_png_data"
        mock_response.raise_for_status.return_value = None
        mock_requests.get.return_value = mock_response

        from scripts.nls_map_fallback import download_nls_tile

        result = download_nls_tile(15, 16371, 10896)
        assert result == b"\x89PNG\r\n\x1a\nfake_png_data"
        mock_requests.get.assert_called_once()
        call_args = mock_requests.get.call_args
        assert "6inch_2nd_ed/15/16371/10896.png" in call_args[0][0]

    @patch("scripts.nls_map_fallback.requests")
    def test_404_returns_none(self, mock_requests):
        """404 response -> returns None."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_requests.get.return_value = mock_response

        from scripts.nls_map_fallback import download_nls_tile

        result = download_nls_tile(15, 99999, 99999)
        assert result is None

    @patch("scripts.nls_map_fallback.requests")
    def test_network_error_returns_none(self, mock_requests):
        """Network error -> returns None."""
        mock_requests.get.side_effect = Exception("Connection refused")

        from scripts.nls_map_fallback import download_nls_tile

        result = download_nls_tile(15, 16371, 10896)
        assert result is None


# --- TestProcessNlsFallback ---


class TestProcessNlsFallback:
    """Test process_nls_fallback orchestration function."""

    def _make_entity(self, entity_id=1, name="John Murray", image_url=None):
        """Create a mock entity object."""
        entity = SimpleNamespace(id=entity_id, name=name, image_url=image_url)
        return entity

    def _make_settings(self):
        """Create mock settings."""
        settings = SimpleNamespace(
            images_bucket="test-bucket",
            images_cdn_url="https://cdn.test.com",
            images_cdn_domain=None,
        )
        return settings

    @patch("scripts.nls_map_fallback.upload_to_s3")
    @patch("scripts.nls_map_fallback.process_portrait")
    @patch("scripts.nls_map_fallback.download_nls_tile")
    @patch("scripts.nls_map_fallback.latlon_to_tile")
    @patch("scripts.nls_map_fallback.geocode_location")
    @patch("scripts.nls_map_fallback.extract_location")
    def test_happy_path(
        self,
        mock_extract,
        mock_geocode,
        mock_tile_coords,
        mock_download,
        mock_process,
        mock_upload,
    ):
        """Full happy path: location extracted, geocoded, tile downloaded, uploaded."""
        mock_extract.return_value = "Albemarle Street, London"
        mock_geocode.return_value = (51.5074, -0.1420)
        mock_tile_coords.return_value = (15, 16371, 10896)
        mock_download.return_value = b"fake_png_data"
        mock_process.return_value = b"processed_jpg_data"
        mock_upload.return_value = "entities/publisher/1/portrait.jpg"

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(
            bio_summary="Victorian publisher on Albemarle Street"
        )
        entity = self._make_entity()
        settings = self._make_settings()

        from scripts.nls_map_fallback import process_nls_fallback

        result = process_nls_fallback(db, entity, "publisher", dry_run=False, settings=settings)

        assert result["status"] == "uploaded"
        assert result["image_source"] == "nls_map"
        assert result["location"] == "Albemarle Street, London"
        assert result["image_uploaded"] is True
        assert result["entity_id"] == 1
        assert result["entity_name"] == "John Murray"

    @patch("scripts.nls_map_fallback.extract_location")
    def test_no_location_extracted(self, mock_extract):
        """No location extracted -> status 'no_location'."""
        mock_extract.return_value = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        entity = self._make_entity(name="Unknown Publisher")
        settings = self._make_settings()

        from scripts.nls_map_fallback import process_nls_fallback

        result = process_nls_fallback(db, entity, "publisher", dry_run=False, settings=settings)

        assert result["status"] == "no_location"
        assert result["image_source"] == "nls_map"

    @patch("scripts.nls_map_fallback.download_nls_tile")
    @patch("scripts.nls_map_fallback.latlon_to_tile")
    @patch("scripts.nls_map_fallback.geocode_location")
    @patch("scripts.nls_map_fallback.extract_location")
    def test_dry_run_mode(self, mock_extract, mock_geocode, mock_tile_coords, mock_download):
        """Dry run mode -> doesn't upload, returns dry_run status."""
        mock_extract.return_value = "Albemarle Street, London"
        mock_geocode.return_value = (51.5074, -0.1420)
        mock_tile_coords.return_value = (15, 16371, 10896)
        mock_download.return_value = b"fake_png_data"

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        entity = self._make_entity()
        settings = self._make_settings()

        from scripts.nls_map_fallback import process_nls_fallback

        result = process_nls_fallback(db, entity, "publisher", dry_run=True, settings=settings)

        assert result["status"] == "dry_run"
        assert result["image_source"] == "nls_map"
        assert result["location"] == "Albemarle Street, London"
        assert result["image_uploaded"] is False

    @patch("scripts.nls_map_fallback.geocode_location")
    @patch("scripts.nls_map_fallback.extract_location")
    def test_geocode_failed(self, mock_extract, mock_geocode):
        """Geocoding fails -> status 'geocode_failed'."""
        mock_extract.return_value = "Nonexistent Street, Nowhere"
        mock_geocode.return_value = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        entity = self._make_entity()
        settings = self._make_settings()

        from scripts.nls_map_fallback import process_nls_fallback

        result = process_nls_fallback(db, entity, "publisher", dry_run=False, settings=settings)

        assert result["status"] == "geocode_failed"
        assert result["image_source"] == "nls_map"
