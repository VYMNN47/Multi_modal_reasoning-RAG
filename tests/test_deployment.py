from pathlib import Path
import json
import subprocess
import unittest
from unittest.mock import patch
from starlette.testclient import TestClient

from app import load_image


ROOT = Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    def test_asgi_entrypoint_serves_the_web_app_without_streamlit_sessions(self):
        from api.index import app
        import rag
        with TestClient(app) as client:
            self.assertEqual(client.get('/api/health').json(), {"status": "ok"})
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn('GeoScan', response.text)
            self.assertNotIn('Streamlit', response.text)
            for asset in ('site.js', 'site.css', 'topography.svg'):
                self.assertEqual(client.get('/assets/' + asset).status_code, 200)
            self.assertEqual(client.get('/.env').status_code, 404)
            self.assertEqual(client.get('/_stcore/health').status_code, 404)
            self.assertIn("script-src 'self'", response.headers['content-security-policy'])
            self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
        self.assertNotIn('streamlit', (ROOT / 'requirements.txt').read_text())
        self.assertEqual(len(rag.load_index()), 16)

    def test_deployment_ignores_secrets_and_raw_data_but_keeps_runtime_assets(self):
        config = json.loads((ROOT / "vercel.json").read_text())
        self.assertEqual(config["outputDirectory"], "public")
        self.assertTrue((ROOT / "public").is_dir())
        self.assertFalse((ROOT / "public/demo_data").exists())
        function = config["functions"]["api/index.py"]
        self.assertLessEqual(len(function["includeFiles"]), 256)
        self.assertEqual(config["rewrites"], [{"source": "/(.*)", "destination": "/api/index"}])
        allowed = ["api/index.py", "asgi.py", "app.py", "assets/site.css", "assets/site.js", "assets/index.html", "assets/topography.svg",
                   "prompts/agronomy_rag_v8.txt", "demo_data/rag_documents/passages.jsonl",
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
