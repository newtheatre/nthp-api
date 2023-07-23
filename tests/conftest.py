from os import environ

import pytest

environ["CONTENT_ROOT"] = "content"


@pytest.fixture(scope="module")
def vcr_config():
    return {
        # Remove the Authorization request header
        "filter_headers": [("Authorization", None)],
        # SmugMug is silly and puts API keys in the URL
        "filter_query_parameters": ["APIKey"],
    }
