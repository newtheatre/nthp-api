"""The schemas published for the content repo, and the page rendering them."""

import json
from pathlib import Path
from typing import Any

import pytest

from nthp_api.nthp_build import (
    content_schema,
    content_schema_docs,
    loader,
    models,
    skeleton,
)

DOCUMENT_TYPES = content_schema.CONTENT_DOCUMENT_TYPES


def get_object_schemas(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Every object shape in a schema, the document itself and its `$defs`."""
    shapes = [schema] if schema.get("type") == "object" else []
    return shapes + list(schema.get("$defs", {}).values())


class TestDocumentTypes:
    def test_every_loaded_model_is_exported(self):
        """A model the build loads is a shape someone has to author."""
        exported = {document_type.model for document_type in DOCUMENT_TYPES}
        assert {entry.schema_type for entry in loader.LOADERS} <= exported

    def test_names_are_unique(self):
        names = [document_type.name for document_type in DOCUMENT_TYPES]
        assert len(set(names)) == len(names)

    def test_document_types_are_addressable_by_name(self):
        assert content_schema.DOCUMENT_TYPES_BY_NAME["show"] is content_schema.SHOW


@pytest.mark.parametrize("document_type", DOCUMENT_TYPES, ids=lambda value: value.name)
class TestDocumentSchema:
    def test_declares_the_2020_12_dialect(self, document_type):
        schema = content_schema.get_document_schema(document_type)
        assert schema["$schema"] == content_schema.JSON_SCHEMA_DIALECT

    def test_is_identified_by_its_filename(self, document_type):
        schema = content_schema.get_document_schema(document_type)
        assert schema["$id"] == f"{document_type.name}.json"

    def test_says_where_the_file_lives(self, document_type):
        schema = content_schema.get_document_schema(document_type)
        assert document_type.location in schema["description"]

    def test_rejects_unknown_keys(self, document_type):
        """`extra="forbid"` on the models has to reach the published schema."""
        schemas = get_object_schemas(content_schema.get_document_schema(document_type))
        assert schemas
        assert all(schema["additionalProperties"] is False for schema in schemas)

    def test_every_field_says_what_it_is(self, document_type):
        for schema in get_object_schemas(
            content_schema.get_document_schema(document_type)
        ):
            for name, field in schema["properties"].items():
                assert field.get("title"), f"{schema.get('title', name)}.{name}"

    def test_is_serialisable(self, document_type):
        json.dumps(content_schema.get_document_schema(document_type))


class TestLoaderSuppliedFields:
    def test_the_identifier_is_not_required(self):
        """The loader takes `id` from the path, so authoring it is optional."""
        schema = content_schema.get_document_schema(content_schema.SHOW)
        assert "id" in schema["properties"]
        assert "id" not in schema["required"]

    def test_authored_fields_stay_required(self):
        schema = content_schema.get_document_schema(content_schema.SHOW)
        assert set(schema["required"]) == {"title", "season"}


class TestRules:
    def test_show_rules_cover_the_loader_checks(self):
        rules = " ".join(
            content_schema.get_document_schema(content_schema.SHOW)["x-nthp-rules"]
        )
        assert "date_end" in rules
        assert "playwright_alias" in rules
        assert "venue_sort" in rules

    def test_a_type_without_rules_omits_the_keyword(self):
        schema = content_schema.get_document_schema(content_schema.ROLES)
        assert content_schema.RULES_KEYWORD not in schema


class TestWriteDocumentSchemas:
    def test_writes_a_file_per_type(self, tmp_path: Path):
        content_schema.write_document_schemas(tmp_path)
        assert {path.name for path in tmp_path.iterdir()} == {
            f"{document_type.name}.json" for document_type in DOCUMENT_TYPES
        }

    def test_written_schemas_parse(self, tmp_path: Path):
        content_schema.write_document_schemas(tmp_path)
        written = json.loads((tmp_path / "show.json").read_text())
        assert written["title"] == "Show"


class TestFieldRows:
    def test_a_list_of_a_shape_names_the_shape(self):
        rows = {
            row.name: row
            for row in content_schema_docs.get_root_shape(content_schema.SHOW).rows
        }
        assert rows["cast"].type == "list of PersonRef"
        assert rows["date_start"].type == "date"
        assert rows["season"].required

    def test_the_description_leads_with_the_title(self):
        rows = {
            row.name: row
            for row in content_schema_docs.get_root_shape(content_schema.VENUE).rows
        }
        assert rows["built"].description.startswith("Year the venue was built")


class TestRenderMarkdown:
    def test_a_document_type_carries_its_rules_and_its_fields(self):
        rendered = content_schema_docs.render_document_type_markdown(
            content_schema.PERSON
        )
        assert "# Person" in rendered
        assert "## Rules beyond the schema" in rendered
        assert "| `graduated` | integer |" in rendered

    def test_every_type_is_rendered(self):
        rendered = content_schema_docs.render_markdown()
        for document_type in DOCUMENT_TYPES:
            assert f"# {document_type.title}" in rendered


class TestRenderHtml:
    def test_every_type_gets_a_section(self):
        rendered = content_schema_docs.render_html()
        for document_type in DOCUMENT_TYPES:
            assert f"id='{document_type.name}'" in rendered

    def test_shared_shapes_are_shown_once(self):
        """`Link` is on four document types; the page carries one table for it."""
        rendered = content_schema_docs.render_html()
        assert rendered.count("id='shape-Link'") == 1
        assert "id='nested-Link'" not in rendered

    def test_each_type_links_to_its_schema(self):
        rendered = content_schema_docs.render_html()
        assert "href='show.json'" in rendered

    def test_markup_is_escaped(self):
        assert "<script" not in content_schema_docs.render_html()


class TestSkeleton:
    @pytest.mark.parametrize("name", skeleton.SKELETON_DOCUMENT_TYPES)
    def test_a_skeleton_has_front_matter_and_a_body(self, name: str):
        rendered = skeleton.render_skeleton(content_schema.DOCUMENT_TYPES_BY_NAME[name])
        assert rendered.startswith("---\n")
        assert rendered.count("\n---\n") == 1

    def test_every_field_appears(self):
        rendered = skeleton.render_skeleton(content_schema.SHOW)
        for name in models.Show.model_fields:
            if name == "id":
                continue
            assert f"{name}:" in rendered

    def test_required_fields_are_not_commented_out(self):
        rendered = skeleton.render_skeleton(content_schema.SHOW)
        assert "\ntitle:\n" in rendered
        assert "\n# playwright:\n" in rendered

    def test_an_identifier_names_the_file_and_fills_the_title(self):
        rendered = skeleton.render_skeleton(content_schema.PERSON, "fred_bloggs")
        assert "_people/fred_bloggs.md" in rendered
        assert "\ntitle: Fred Bloggs\n" in rendered

    def test_a_skeleton_is_rejected_until_it_is_filled_in(self):
        """Saved unedited it fails validation, rather than losing the record."""
        import frontmatter

        rendered = skeleton.render_skeleton(content_schema.VENUE)
        with pytest.raises(ValueError):
            models.Venue(**frontmatter.loads(rendered).metadata)
