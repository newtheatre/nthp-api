import pytest
from pydantic import ValidationError

from nthp_build import models


class TestAsset:
    def test_creation(self):
        assert models.Asset(type="poster", image="abc123")
        assert models.Asset(type="poster", video="abc123")
        assert models.Asset(type="poster", filename="abc123", title="hello")

    def test_require_image_xor_video_xor_filename(self):
        models.Asset(type="poster", image="abc123")
        models.Asset(type="poster", video="abc123")
        models.Asset(type="poster", filename="abc123", title="hello")

        with pytest.raises(ValidationError):
            models.Asset(type="poster")
        with pytest.raises(ValidationError):
            models.Asset(type="poster", image="abc123", video="abc123")
        with pytest.raises(ValidationError):
            models.Asset(
                type="poster",
                image="abc123",
                video="abc123",
                filename="abc123",
                title="def",
            )

    def test_require_title_with_filename(self):
        models.Asset(type="poster", filename="abc123", title="hello")
        with pytest.raises(ValidationError):
            models.Asset(type="poster", filename="abc123")

    def test_display_image_only_for_images(self):
        models.Asset(type="poster", image="abc", display_image=True)
        with pytest.raises(ValidationError):
            models.Asset(type="poster", filename="abc", display_image=True)
