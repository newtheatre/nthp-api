from os import environ

import pytest

environ["CONTENT_ROOT"] = "content"
environ["SMUGMUG_API_KEY"] = environ.get("SMUGMUG_API_KEY", "a123")


@pytest.fixture(scope="module")
def vcr_config():
    return {
        # Remove the Authorization request header
        "filter_headers": [("Authorization", None)],
        # SmugMug is silly and puts API keys in the URL
        "filter_query_parameters": ["APIKey"],
    }
