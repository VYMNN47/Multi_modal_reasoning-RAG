from pathlib import Path
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from app import load_image


ROOT = Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    def test_asgi_entrypoint_starts_and_serves_http_and_websocket(self):
        # A child process keeps Streamlit's singleton runtime separate from AppTest.
        script = """
from starlette.testclient import TestClient
from api.index import app
import rag
with TestClient(app) as client:
    assert client.get('/_stcore/health').status_code == 200
    response = client.get('/')
    assert response.status_code == 200 and 'Streamlit' in response.text
    assert 'GEMINI_API_KEY=' not in client.get('/.env').text
    with client.websocket_connect('/_stcore/stream', headers={'Origin': 'http://testserver'}):
        pass
assert len(rag.load_index()) == 16
"""
        result = subprocess.run([sys.executable, "-c", script], cwd=ROOT, capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stderr[-2500:])

    def test_deployment_ignores_secrets_and_raw_data_but_keeps_runtime_assets(self):
        config = json.loads((ROOT / "vercel.json").read_text())
        function = config["functions"]["api/index.py"]
        self.assertLessEqual(len(function["includeFiles"]), 256)
        self.assertEqual(config["rewrites"], [{"source": "/(.*)", "destination": "/api/index"}])
        allowed = ["api/index.py", "asgi.py", "app.py", "assets/app.css", "assets/topography.svg",
                   "prompts/agronomy_rag_v7.txt", "demo_data/rag_documents/passages.jsonl",
                   "demo_data/rag_documents/embedding_index.json",
                   "demo_data/comparison/case.json",
                   "demo_data/comparison/moroccodrought_amo_20230212_lrg.jpg",
                   "demo_data/comparison/moroccodrought_tmo_20240219_lrg.jpg",
                   "demo_data/sentinel2/gharb_2025-02-14_rgb_10m.png"]
        excluded = [".env", ".env.local", ".env.production", ".streamlit/secrets.toml", ".venv/bin/python",
                    ".vercel/cli/auth.json", ".aws/credentials",
                    "demo_data/rag_documents/sources/original.pdf", "demo_data/rag_documents/text/page.txt",
                    "demo_data/rag_documents/pages.jsonl", "demo_data/sentinel2/original.tif"]
        result = subprocess.run(
            ["git", "-c", "core.excludesFile=.vercelignore", "check-ignore", "--no-index", "--stdin"],
            cwd=ROOT, input="\n".join(allowed + excluded) + "\n", capture_output=True, text=True, check=True,
        )
        self.assertEqual(set(result.stdout.splitlines()), set(excluded))
        self.assertTrue(all((ROOT / name).is_file() for name in allowed))

    def test_hosted_upload_boundary_rejects_files_over_four_mib(self):
        with patch("app.MAX_UPLOAD_BYTES", 4 * 1024 * 1024), patch("app.MAX_UPLOAD_MB", 4):
            with self.assertRaisesRegex(ValueError, "4 MB"):
                load_image(b"x" * (4 * 1024 * 1024 + 1))


if __name__ == "__main__":
    unittest.main()
