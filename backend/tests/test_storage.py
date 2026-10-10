import pytest

from services.storage import LocalStorageBackend


@pytest.fixture
def backend(tmp_path):
    return LocalStorageBackend(tmp_path)


async def test_save_and_open_roundtrip(backend):
    await backend.save("abc/deck/file.pdf", b"hello")
    assert await backend.open("abc/deck/file.pdf") == b"hello"


async def test_open_missing_raises(backend):
    with pytest.raises(FileNotFoundError):
        await backend.open("nope.pdf")


async def test_delete_is_idempotent(backend):
    await backend.save("abc/deck/file.pdf", b"hello")
    await backend.delete("abc/deck/file.pdf")
    await backend.delete("abc/deck/file.pdf")  # second delete shouldn't raise
    with pytest.raises(FileNotFoundError):
        await backend.open("abc/deck/file.pdf")


async def test_list_filters_by_prefix(backend):
    await backend.save("sub1/deck/a.pdf", b"a")
    await backend.save("sub1/forecast/b.xlsx", b"b")
    await backend.save("sub2/deck/c.pdf", b"c")

    sub1_files = await backend.list("sub1/")
    assert set(sub1_files) == {"sub1/deck/a.pdf", "sub1/forecast/b.xlsx"}


async def test_save_rejects_path_escaping_root(backend):
    with pytest.raises(ValueError):
        await backend.save("../../etc/passwd", b"nope")
