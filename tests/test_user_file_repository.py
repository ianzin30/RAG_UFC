"""Tests for UserFileRepository — isolation and status transitions."""
import pytest


@pytest.fixture
def mock_db():
    try:
        import mongomock
        client = mongomock.MongoClient()
        db = client["test_rag_ufc"]
        # Create partial unique index manually (mongomock ignores partialFilterExpression but that's fine for logic tests)
        db["user_files"].create_index(
            [("user_id", 1), ("collection_name", 1), ("filename", 1)],
            sparse=True,
        )
        return db
    except ImportError:
        pytest.skip("mongomock not installed — skipping MongoDB tests")


def test_record_file_creates_document(mock_db):
    from service.storage.UserFileRepository import record_file, list_active_files

    record_file(
        mock_db,
        user_id="user_a",
        filename="01_doc.md",
        original_filename="doc.pdf",
        storage_path="/data/users/user_a/collections/col/01_doc.md",
        collection_name="uploaded_files",
        status="indexed",
    )
    files = list_active_files(mock_db, "user_a")
    assert len(files) == 1
    assert files[0]["filename"] == "01_doc.md"


def test_user_a_files_invisible_to_user_b(mock_db):
    from service.storage.UserFileRepository import record_file, list_active_files

    record_file(
        mock_db,
        user_id="user_a",
        filename="01_doc.md",
        original_filename="doc.pdf",
        storage_path="/data/users/user_a/...",
        collection_name="uploaded_files",
    )
    files_b = list_active_files(mock_db, "user_b")
    assert files_b == []


def test_mark_collection_deleted_only_affects_owner(mock_db):
    from service.storage.UserFileRepository import record_file, mark_collection_deleted, list_active_files

    record_file(
        mock_db,
        user_id="user_a",
        filename="01_a.md",
        original_filename="a.pdf",
        storage_path="/...",
        collection_name="col",
    )
    record_file(
        mock_db,
        user_id="user_b",
        filename="01_b.md",
        original_filename="b.pdf",
        storage_path="/...",
        collection_name="col",
    )

    mark_collection_deleted(mock_db, "user_a", "col")

    # user_a's file should be deleted
    assert list_active_files(mock_db, "user_a") == []
    # user_b's file should be intact
    assert len(list_active_files(mock_db, "user_b")) == 1


def test_status_transition_uploaded_to_indexed(mock_db):
    from service.storage.UserFileRepository import record_file, mark_file_indexed, list_active_files

    record_file(
        mock_db,
        user_id="user_x",
        filename="01_doc.md",
        original_filename="doc.pdf",
        storage_path="/...",
        collection_name="col",
        status="uploaded",
    )
    mark_file_indexed(mock_db, "user_x", "01_doc.md", "col")

    files = list_active_files(mock_db, "user_x")
    assert files[0]["status"] == "indexed"
