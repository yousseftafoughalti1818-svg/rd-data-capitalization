import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from rdcap import config  # noqa: E402
from generate_sample_data import generate  # noqa: E402


@pytest.fixture(scope="session")
def archive(tmp_path_factory):
    """A freshly generated fictive archive, processed by the full pipeline."""
    base = tmp_path_factory.mktemp("rd")
    raw = generate(base / "raw")
    return {"raw": raw, "db": base / "test.db", "reports": base / "reports"}


@pytest.fixture(scope="session")
def processed(archive):
    from rdcap import pipeline
    mp = pytest.MonkeyPatch()
    mp.setattr(config, "REPORTS_DIR", archive["reports"])
    result = pipeline.run(archive["raw"], archive["db"])
    yield {**archive, "result": result}
    mp.undo()
