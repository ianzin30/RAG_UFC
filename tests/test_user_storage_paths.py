"""Tests for UserStoragePaths — path construction and containment safety."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def _make_config(base_dir="data/users"):
    cfg = MagicMock()
    cfg.user_storage.base_dir = base_dir
    return cfg


@pytest.fixture(autouse=True)
def patch_runtime_config(tmp_path):
    mock_cfg = _make_config(str(tmp_path / "data" / "users"))
    with patch("service.storage.UserStoragePaths.get_runtime_config", return_value=mock_cfg):
        with patch("service.storage.UserStoragePaths.PROJECT_ROOT", tmp_path):
            yield tmp_path


def test_collections_root_for_valid_uid(patch_runtime_config):
    from service.storage.UserStoragePaths import collections_root_for
    uid = "abc123"
    path = collections_root_for(uid)
    assert path.parts[-1] == "collections"
    assert uid in str(path)


def test_vector_cache_root_for_valid_uid(patch_runtime_config):
    from service.storage.UserStoragePaths import vector_cache_root_for
    path = vector_cache_root_for("uid_xyz")
    assert path.parts[-1] == "vector"


def test_uid_with_path_traversal_rejected():
    from service.storage.UserStoragePaths import _validate_uid
    with pytest.raises(ValueError):
        _validate_uid("../etc/passwd")


def test_uid_with_slash_rejected():
    from service.storage.UserStoragePaths import _validate_uid
    with pytest.raises(ValueError):
        _validate_uid("user/name")


def test_empty_uid_rejected():
    from service.storage.UserStoragePaths import _validate_uid
    with pytest.raises(ValueError):
        _validate_uid("")


def test_assert_safe_path_rejects_escape(patch_runtime_config):
    from service.storage.UserStoragePaths import assert_safe_path, user_root
    uid = "user1"
    safe = user_root(uid) / "collections" / "docs"
    safe.mkdir(parents=True, exist_ok=True)
    # A path that is outside the user root should be rejected
    from service.storage.UserStoragePaths import _users_base
    outside = _users_base() / "user2" / "evil.md"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.touch()
    with pytest.raises(ValueError, match="escapes user root"):
        assert_safe_path(outside, uid)


def test_assert_safe_path_accepts_valid(patch_runtime_config):
    from service.storage.UserStoragePaths import assert_safe_path, collections_root_for
    uid = "user1"
    root = collections_root_for(uid)
    root.mkdir(parents=True, exist_ok=True)
    target = root / "file.md"
    target.touch()
    result = assert_safe_path(target, uid)
    assert result.exists()
