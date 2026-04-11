from pathlib import Path
import sys


CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[2]
API_SRC_DIR = REPO_ROOT / "apps" / "api" / "src"

if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from rfq_api.main import app  # noqa: E402

