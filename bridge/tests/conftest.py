"""pytest configuration and fixtures."""
import os
import sys
from pathlib import Path

# Set required env vars before any imports
os.environ.setdefault("SECRET_KEY", "test-secret-key")

# Add only bridge/src to Python path
SRC_DIR = str(Path(__file__).parent.parent / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
