import unittest
from starlette.testclient import TestClient
from agent.web.server import app
from agent.storage.vault import vault

class TestAPIQA(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        # Create a test report in vault
        self.test_report = vault.save_report(
            topic="Quantum Computing Scalability",
            content="# Quantum Computing Scalability\n\nQubit coherence is limited by thermal noise.\n\n## References & Annotated Sources\n\n[1] [Quantum Error](https://arxiv.org/abs/2301.0001) `[ARXIV]`",
            sources=[{"title": "Quantum Error", "url": "https://arxiv.org/abs/2301.0001", "source": "arxiv"}],
            model="llama3.2:latest",
            report_id="test_qa_rep",
        )

    def tearDown(self):
        # Clean up test report from vault
        rep_file = vault.reports_dir / "quantum_computing_scalability_test_qa_rep.md"
        if rep_file.exists():
            rep_file.unlink()
        conv_file = vault.conversations_dir / "test_qa_rep.json"
        if conv_file.exists():
            conv_file.unlink()
        vault._save_history([i for i in vault._load_history() if i.get("id") != "test_qa_rep"])

    def test_zero_friction_access(self):
        # 1. Accessing report conversation without token succeeds
        res = self.client.get("/api/report/test_qa_rep/conversation")
        self.assertEqual(res.status_code, 200)
        self.assertIn("messages", res.json())

    def test_guest_vs_owner_isolation(self):
        # 1. Local requests get owner role and history
        res_local = self.client.get("/api/history")
        self.assertEqual(res_local.status_code, 200)
        self.assertEqual(res_local.json().get("role"), "owner")
        self.assertGreater(len(res_local.json().get("history", [])), 0)

        # 2. Remote guest requests get guest role and empty history
        res_guest = self.client.get("/api/history", headers={"CF-Connecting-IP": "198.51.100.1"})
        self.assertEqual(res_guest.status_code, 200)
        self.assertEqual(res_guest.json().get("role"), "guest")
        self.assertEqual(len(res_guest.json().get("history", [])), 0)

        # 3. Activity log is forbidden for remote guests
        res_activity = self.client.get("/api/activity/queries", headers={"CF-Connecting-IP": "198.51.100.1"})
        self.assertEqual(res_activity.status_code, 403)

    def test_ask_empty_question(self):
        res = self.client.post(
            "/api/report/test_qa_rep/ask",
            json={"question": "   "},
        )
        self.assertEqual(res.status_code, 400)

    def test_deepen_empty_query(self):
        res = self.client.post(
            "/api/report/test_qa_rep/deepen",
            json={"question": "   "},
        )
        self.assertEqual(res.status_code, 400)

    def test_settings_keys_access_and_update(self):
        # 1. Remote guest request is rejected
        res_guest_get = self.client.get("/api/settings/keys", headers={"CF-Connecting-IP": "198.51.100.1"})
        self.assertEqual(res_guest_get.status_code, 403)

        res_guest_post = self.client.post("/api/settings/keys", json={"gemini_api_key": "fake_key"}, headers={"CF-Connecting-IP": "198.51.100.1"})
        self.assertEqual(res_guest_post.status_code, 403)

        # 2. Local owner request succeeds
        res_owner_get = self.client.get("/api/settings/keys")
        self.assertEqual(res_owner_get.status_code, 200)
        data = res_owner_get.json()
        self.assertIn("gemini", data)
        self.assertIn("openai", data)
        self.assertIn("groq", data)
        self.assertIn("openrouter", data)
        self.assertIn("custom", data)

        # 3. Local owner can update keys
        res_owner_post = self.client.post("/api/settings/keys", json={
            "custom_llm_url": "http://localhost:1234/v1",
            "custom_llm_model": "test-model-42",
        })
        self.assertEqual(res_owner_post.status_code, 200)

        # Verify custom model is reflected in models list
        models_res = self.client.get("/api/models")
        self.assertEqual(models_res.status_code, 200)
        model_ids = [m["id"] for m in models_res.json().get("models", [])]
        self.assertIn("custom:test-model-42", model_ids)

        # Clean up custom model
        self.client.post("/api/settings/keys", json={"custom_llm_url": "", "custom_llm_model": ""})

if __name__ == "__main__":
    unittest.main()
