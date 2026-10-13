import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from c360.core.data import validate_datasets

def test_csv_datasets_integrity():
    """Verify CSV dataset files without requiring a running Neo4j database."""
    validate_datasets()
