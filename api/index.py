import sys, pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parents[1]

sys.path.append(str(ROOT))

from backend.app import app