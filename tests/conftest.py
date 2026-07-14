import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Point the SQLite job store at a throwaway DB so tests never touch the real
# %LOCALAPPDATA%\opencode-cli-mcp\jobs.db. Must be set before job_store first
# connects (connection is lazy, so setting it at conftest import is early enough).
os.environ.setdefault(
    "OPENCODE_CLI_MCP_JOBS_DB",
    str(Path(tempfile.mkdtemp(prefix="opencode-cli-mcp-tests-")) / "jobs.db"),
)
