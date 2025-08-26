import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.append(str(ROOT / "backend"))

from app import app