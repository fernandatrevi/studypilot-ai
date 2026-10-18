"""Pruebas para lectura de documentos y distribución de contexto."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from src import documents


class TestDocuments(unittest.TestCase):
    def test_contexto_varios_pdf(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with patch.object(documents, "CARPETA_DOCUMENTOS", Path(carpeta)):
                for nombre, texto in (
                    ("Biologia.pdf", "La célula es la unidad básica de los seres vivos. " * 15),
                    ("Historia.pdf", "La revolución transformó las instituciones sociales. " * 15),
                ):
                    pdf = pymupdf.open()
                    pagina = pdf.new_page()
                    pagina.insert_textbox(pymupdf.Rect(50, 50, 500, 750), texto)
                    pdf.save(documents.ruta_documento("General", nombre))
                    pdf.close()
                contexto = documents.obtener_contexto("General", limite=2500)
                self.assertIn("DOCUMENTO: Biologia.pdf", contexto)
                self.assertIn("DOCUMENTO: Historia.pdf", contexto)
                self.assertIn("--- Página 1 ---", contexto)

    def test_rechaza_limite_invalido(self):
        with self.assertRaises(ValueError):
            documents.obtener_contexto("General", limite=0)


if __name__ == "__main__":
    unittest.main()
