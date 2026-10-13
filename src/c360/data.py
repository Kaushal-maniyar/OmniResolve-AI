"""Compatibility shim for c360.core.data."""
from c360.core.data import *  # noqa: F401, F403
from c360.core.data import validate_datasets, read_csv, DATA_DIR

if __name__ == "__main__":
    validate_datasets()
