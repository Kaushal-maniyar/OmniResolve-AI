"""Compatibility shim for c360.graph.reset."""
from c360.graph.reset import *  # noqa: F401, F403
from c360.graph.reset import reset_demo_data

if __name__ == "__main__":
    reset_demo_data()
