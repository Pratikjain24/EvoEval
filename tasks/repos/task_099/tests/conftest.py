import pytest

@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield
