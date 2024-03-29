from http import HTTPStatus

from nthp_api.smugmugger import schema

from .fixtures import albumimages


class TestSmugMugResponse:
    def test_ok(self):
        response = schema.SmugMugResponse(**albumimages.three_images_many_pages)
        assert response.Code == HTTPStatus.OK
        assert response.Message == "Ok"

    def test_pages(self):
        response = schema.SmugMugResponse(**albumimages.three_images_many_pages)
        pages = response.Response.Pages
        assert pages.Total == 379  # noqa: PLR2004
        assert pages.Start == 1
        assert pages.Count == 3  # noqa: PLR2004
        assert pages.RequestedCount == 3  # noqa: PLR2004
        assert pages.FirstPage == "/api/v2/album/dvVPZh!images?count=3&start=1"
        assert pages.LastPage == "/api/v2/album/dvVPZh!images?count=3&start=379"
        assert pages.NextPage == "/api/v2/album/dvVPZh!images?count=3&start=4"
