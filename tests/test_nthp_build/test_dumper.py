from pathlib import Path

import pytest

from nthp_api.nthp_build import dumper


@pytest.fixture()
def output_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(dumper, "OUTPUT_DIR", tmp_path)
    return tmp_path


class TestCopyStaticFiles:
    def test_writes_docs_page(self, output_dir: Path):
        dumper.copy_static_files()
        assert (output_dir / "index.html").is_file()

    def test_docs_page_finds_spec_relatively(self, output_dir: Path):
        dumper.copy_static_files()
        page = (output_dir / "index.html").read_text()
        assert 'apiDescriptionUrl="openapi.json"' in page
