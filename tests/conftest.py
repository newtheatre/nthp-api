import pytest


@pytest.fixture(scope="module")
def vcr_config():
    return {
        # Remove the Authorization request header
        "filter_headers": [("Authorization", None)],
        # SmugMug is silly and puts API keys in the URL
        "filter_query_parameters": ["APIKey"],
    }
