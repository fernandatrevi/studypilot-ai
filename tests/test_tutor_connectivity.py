"""Regression tests for Ollama connection errors (no network required)."""
import unittest
from unittest.mock import patch
from urllib.error import URLError

from src import tutor


class TutorConnectivityTests(unittest.TestCase):
    def test_unreachable_ollama_explains_cloud_localhost(self):
        with patch.object(tutor.request, "urlopen", side_effect=URLError("connection refused")):
            with self.assertRaises(RuntimeError) as captured:
                tutor.consultar_ollama("Hola", timeout=1)
        message = str(captured.exception)
        self.assertIn("Streamlit Cloud", message)
        self.assertIn("localhost", message)
        self.assertIn("STUDYPILOT_OLLAMA_URL", message)

    def test_timeout_keeps_its_specific_message(self):
        import socket
        with patch.object(tutor.request, "urlopen", side_effect=socket.timeout("timed out")):
            with self.assertRaises(RuntimeError) as captured:
                tutor.consultar_ollama("Hola", timeout=2)
        self.assertIn("2 segundos", str(captured.exception))


if __name__ == "__main__":
    unittest.main()
