"""Pruebas sin Ollama: formato, citas y calificación del examen."""
import unittest
from unittest.mock import patch

from src.quiz import _separar_paginas, _validar_pregunta, evaluar_examen, generar_examen


CONTEXTO = (
    "DOCUMENTO: Biologia.pdf\n--- Página 2 ---\n"
    "La fotosíntesis transforma la energía luminosa en energía química "
    "y produce oxígeno como subproducto. "
    "Las plantas utilizan la luz solar para realizar este proceso.\n"
)


def ejemplo():
    return {
        "tipo": "conceptual",
        "pregunta": "¿Qué transforma la fotosíntesis en energía química?",
        "opciones": ["La energía luminosa", "La energía sonora",
                     "La energía mecánica", "La energía nuclear"],
        "correcta": 0,
        "correctas": [0],
        "explicacion": "La fotosíntesis convierte la luz en energía química.",
        "fuente": "Biologia.pdf, página 2",
        "evidencia": "La fotosíntesis transforma la energía luminosa en energía química",
        "por_que_no": ["", "No es sonido", "No es movimiento", "No es nuclear"],
    }


class TestQuiz(unittest.TestCase):
    def test_fuente_literal(self):
        paginas = _separar_paginas(CONTEXTO)
        self.assertEqual(_validar_pregunta(ejemplo(), "conceptual", paginas)["origen"], "pdf")

    def test_rechaza_cita_inventada(self):
        pregunta = ejemplo()
        pregunta["evidencia"] = "Las plantas obtienen energía exclusivamente de la luna"
        self.assertIsNone(_validar_pregunta(pregunta, "conceptual", _separar_paginas(CONTEXTO)))

    def test_rechaza_dos_correctas(self):
        pregunta = ejemplo()
        pregunta["correctas"] = [0, 1]
        self.assertIsNone(_validar_pregunta(pregunta, "conceptual", _separar_paginas(CONTEXTO)))

    def test_evaluacion_muestra_texto(self):
        resultado = evaluar_examen([ejemplo()], {0: 0})
        self.assertEqual(resultado["aciertos"], 1)
        self.assertEqual(resultado["resultados"][0]["respuesta_correcta"], "La energía luminosa")

    def test_generacion_con_modelo_simulado(self):
        import json
        with patch("src.quiz.consultar_ollama", return_value=json.dumps({"preguntas": [ejemplo()]})):
            preguntas = generar_examen(CONTEXTO, cantidad=1)
        self.assertEqual(len(preguntas), 1)
        self.assertEqual(preguntas[0]["opciones"][preguntas[0]["correcta"]], "La energía luminosa")


if __name__ == "__main__":
    unittest.main()
