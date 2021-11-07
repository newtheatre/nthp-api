from smugmugger import schema

from .fixtures import albumimages


class TestSmugMugResponse:
    def test_ok(self):
        response = schema.SmugMugResponse(**albumimages.three_images_many_pages)
        assert response.Code == 200
        assert response.Message == "Ok"

    def test_pages(self):
        response = schema.SmugMugResponse(**albumimages.three_images_many_pages)
        pages = response.Response.Pages
        assert pages.Total == 379
        assert pages.Start == 1
        assert pages.Count == 3
        assert pages.RequestedCount == 3
        assert pages.FirstPage == "/api/v2/album/dvVPZh!images?count=3&start=1"
        assert pages.LastPage == "/api/v2/album/dvVPZh!images?count=3&start=379"
        assert pages.NextPage == "/api/v2/album/dvVPZh!images?count=3&start=4"
