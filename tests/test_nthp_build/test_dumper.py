import json
from pathlib import Path

import pytest

from nthp_api.nthp_build import content_schema, database, dumper, models, schema


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
        assert 'url: "openapi.json"' in page


class TestDumpContentSchema:
    def test_writes_a_schema_per_document_type(self, output_dir: Path):
        dumper.dump_content_schema(state=None)
        written = {path.name for path in (output_dir / "content-schema").iterdir()}
        assert written == {
            "index.html",
            *(
                f"{document_type.name}.json"
                for document_type in content_schema.CONTENT_DOCUMENT_TYPES
            ),
        }

    def test_the_page_links_to_the_schemas_beside_it(self, output_dir: Path):
        dumper.dump_content_schema(state=None)
        page = (output_dir / "content-schema" / "index.html").read_text()
        assert "href='show.json'" in page


class TestWriteFile:
    """One serialisation for every path: lists always, null scalars never."""

    @staticmethod
    def write(output_dir: Path, obj) -> dict:
        path = output_dir / "a_record.json"
        dumper.write_file(path, obj)
        return json.loads(path.read_text())

    def test_empty_lists_are_written(self, output_dir: Path):
        written = self.write(
            output_dir,
            schema.SeasonList(id="in-house", name="In House", show_count=0),
        )
        assert written["aliases"] == []

    def test_null_scalars_are_omitted(self, output_dir: Path):
        written = self.write(output_dir, schema.ImageRef(id="abc12"))
        assert written == {"id": "abc12"}

    def test_fields_left_at_their_default_are_written(self, output_dir: Path):
        """Nothing turns on whether a field was set explicitly."""
        written = self.write(
            output_dir,
            schema.VenueDetail(
                id="new-theatre",
                name="New Theatre",
                show_count=0,
                has_record=True,
                sentinel=False,
            ),
        )
        assert written["shows"] == []
        assert written["assets"] == []
        assert written["links"] == []


class TestDumpRealPerson:
    """Honourifics travel from the loaded document to the person's JSON."""

    @staticmethod
    def dump(output_dir: Path, person: models.Person) -> dict:
        database.Person.create(
            id=person.id,
            source_path=f"_people/{person.id}.md",
            title=person.title,
            data=person.model_dump_json(),
        )
        dumper.dump_real_people(dumper.DumperSharedState(search_documents=[]))
        return json.loads((output_dir / "people" / f"{person.id}.json").read_text())

    def test_honourifics_are_written(self, output_dir: Path, test_db):
        written = self.dump(
            output_dir,
            models.Person(
                id="fred_bloggs",
                title="Fred Bloggs",
                pre_nominal="Sir",
                post_nominals=["OBE", "FRS"],
            ),
        )
        assert written["title"] == "Fred Bloggs"
        assert written["preNominal"] == "Sir"
        assert written["postNominals"] == ["OBE", "FRS"]

    def test_absent_honourifics(self, output_dir: Path, test_db):
        written = self.dump(
            output_dir, models.Person(id="fred_bloggs", title="Fred Bloggs")
        )
        assert "preNominal" not in written
        assert written["postNominals"] == []
