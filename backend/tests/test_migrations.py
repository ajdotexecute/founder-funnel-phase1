from sqlalchemy import inspect

EXPECTED_TABLES = {"founders", "submissions", "documents", "extractions", "scores"}


async def test_expected_tables_exist(db_engine):
    async with db_engine.connect() as conn:
        tables = await conn.run_sync(lambda sync_conn: set(inspect(sync_conn).get_table_names()))
    assert EXPECTED_TABLES <= tables


async def test_submissions_founder_version_unique_constraint(db_engine):
    async with db_engine.connect() as conn:
        constraints = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_unique_constraints("submissions")
        )
    names = {c["name"] for c in constraints}
    assert "uq_submissions_founder_version" in names


async def test_documents_submission_slot_unique_constraint(db_engine):
    async with db_engine.connect() as conn:
        constraints = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_unique_constraints("documents")
        )
    names = {c["name"] for c in constraints}
    assert "uq_documents_submission_slot" in names


async def test_submissions_has_declared_sector_not_sector(db_engine):
    async with db_engine.connect() as conn:
        columns = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_columns("submissions"))
    names = {c["name"] for c in columns}
    assert "declared_sector" in names
    assert "sector" not in names
