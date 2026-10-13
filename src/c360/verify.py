"""Compatibility shim for c360.graph.verify."""
import sys
from c360.graph.verify import *  # noqa: F401, F403
from c360.graph.verify import verify_database

if __name__ == "__main__":
    success = verify_database()
    sys.exit(0 if success else 1)
