"""Central configuration for the Zhibing MVP."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BT_EXAMPLES_DIR = PROJECT_ROOT / "bt_examples"
BT_REGISTRY_PATH = PROJECT_ROOT / "zhibing" / "registry" / "bt_registry.json"
SCHEMA_DIR = PROJECT_ROOT / "zhibing" / "schemas"

VBS_ORIGIN_WGS84 = {
    "frame": "WGS84_LATLON_ALT",
    "lat": float(os.getenv("ZHIBING_ORIGIN_LAT", "40.2409585")),
    "lon": float(os.getenv("ZHIBING_ORIGIN_LON", "116.1173974")),
    "alt": float(os.getenv("ZHIBING_ORIGIN_ALT", "120.0")),
}

POLL_INTERVAL_S = float(os.getenv("ZHIBING_POLL_INTERVAL_S", "10"))
DEFAULT_DB_URL = os.getenv("ZHIBING_DB_URL", "postgresql+psycopg://zhibing:zhibing@localhost:5432/zhibing")
LLM_CONFIG_FILE = os.getenv("ZHIBING_LLM_CONFIG", str(PROJECT_ROOT / "llm_migration_config.json"))

# The adapter compiles to this logical BT set; deployment can map it to a real absolute VBS path.
DEFAULT_BTSET_PATH = os.getenv("ZHIBING_BTSET_PATH", str(BT_EXAMPLES_DIR / "CgfControl.btset"))


GRAPHRAG_DEFAULT_CORPUS_DIR = PROJECT_ROOT / "zhibing" / "knowledge" / "default_corpus"
GRAPHRAG_TEST_FILES_DIR = PROJECT_ROOT / "test_files"
GRAPHRAG_CORPUS_PATHS = [GRAPHRAG_DEFAULT_CORPUS_DIR, GRAPHRAG_TEST_FILES_DIR]
GRAPHRAG_BENCHMARK_CASES = PROJECT_ROOT / "zhibing" / "knowledge" / "benchmarks" / "rule_grounding_cases.json"
GRAPHRAG_LLM_PROVIDER = os.getenv("ZHIBING_GRAPHRAG_LLM_PROVIDER", "volcengine_ark")
GRAPHRAG_LLM_MODEL = os.getenv("ZHIBING_GRAPHRAG_LLM_MODEL", "ep-20260615114505-247zc")
GRAPHRAG_LOCAL_BASE_URL = os.getenv("ZHIBING_GRAPHRAG_LOCAL_BASE_URL", "http://127.0.0.1:8000/v1")
LOWER_SIM_TRANSPORT = os.getenv("ZHIBING_LOWER_SIM_TRANSPORT", "http")
LOWER_SIM_HTTP_BASE_URL = os.getenv("ZHIBING_LOWER_SIM_HTTP_BASE_URL", "http://127.0.0.1:9000")
LOWER_SIM_SOCKET_HOST = os.getenv("ZHIBING_LOWER_SIM_SOCKET_HOST", "127.0.0.1")
LOWER_SIM_SOCKET_PORT = int(os.getenv("ZHIBING_LOWER_SIM_SOCKET_PORT", "9001"))