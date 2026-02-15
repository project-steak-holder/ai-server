from sqlalchemy import inspect

from src.models.base import Base


def test_base_metadata_contains_expected_tables(engine):
    schema = inspect(engine)
    tables = set(schema.get_table_names())
    assert {"user", "conversation", "message"}.issubset(tables)
    assert set(Base.metadata.tables.keys()) == {"user", "conversation", "message"}
