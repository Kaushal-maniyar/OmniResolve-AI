"""Compatibility shim for c360.graph.seed."""
from c360.graph.seed import *  # noqa: F401, F403
from c360.graph.seed import seed_database

if __name__ == "__main__":
    seed_database()
