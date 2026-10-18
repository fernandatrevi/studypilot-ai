"""Generador 80/20 para StudyPilot AI: PDF primero, IA complementaria etiquetada.

Compatible con app.py: generar_examen(contexto, cantidad=5) y
 evaluar_examen(preguntas, respuestas).
"""
import json
import re
import unicodedata

from src.tutor import consultar_ollama


def _normalizar(texto):
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', texto.casefold())).strip()


def _indices_correctos(pregunta):
    indices = pregunta.get('correctas', [pregunta.get('correcta')])
    if (not isinstance(indices, list) or len(indices) != 1
            or type(indices[0]) is not int or indices[0] not in range(4)
            or indices[0] != pregunta.get('correcta')):
        raise ValueError('Índices de respuestas correctas inválidos.')
    return indices


def _parsear_json(respuesta):
    if isinstance(respuesta, dict):
        objeto = respuesta
    else:
        if not isinstance(respuesta, str):
            raise ValueError('Respuesta de IA inválida.')
        limpio = respuesta.strip()
        if limpio.startswith('```'):
            limpio = re.sub(r'^```(?:json)?\s*|\s*```$', '', limpio, flags=re.I)
        try:
            objeto = json.loads(limpio)
        except json.JSONDecodeError as exc:
            raise ValueError('La IA no devolvió JSON válido.') from exc
    preguntas = objeto.get('preguntas') if isinstance(objeto, dict) else None
    if not isinstance(preguntas, list):
        raise ValueError('La IA no devolvió una lista de preguntas.')
    return preguntas


def _separar_paginas(contexto):
    patron = re.compile(r'DOCUMENTO:\s*([^\n]+)\n--- Página (\d+) ---\n')
    marcas = list(patron.finditer(contexto))
    if not marcas:
        return [('Material proporcionado', contexto.strip())]
    paginas = []
    for i, marca in enumerate(marcas):
        fin = marcas[i + 1].start() if i + 1 < len(marcas) else len(contexto)
        contenido = contexto[marca.end():fin].strip()
        if contenido:
            paginas.append((f'{marca.group(1).strip()}, página {marca.group(2)}', contenido))
    return paginas


def _preparar_material(contexto, limite=6500):
    paginas = _separar_paginas(contexto)
    # Combinar páginas para diversificar temas; cada bloque conserva su procedencia.
    def puntaje(pagina):
        texto = _normalizar(pagina[1])
        terminos = ('significa', 'consiste', 'permite', 'diferencia', 'interpret',
                    'importancia', 'concepto', 'porque', 'definicion', 'explica',
                    'means', 'because', 'explains', 'difference', 'definition')
        teoria = sum(texto.count(t) for t in terminos)
        ejercicios = sum(texto.count(t) for t in ('ejercicio', 'dataset', 'accuracy obtenido',
                                                   'train test split', 'import pandas'))
        return teoria * 3 - ejercicios
    paginas = sorted(paginas, key=puntaje, reverse=True)
    bloques = []
    usados = 0
    for fuente, contenido in paginas:
        restante = limite - usados
        if restante < 250:
            break
        trozo = contenido[:min(1900, restante - 100)]
        bloque = f'FUENTE: {fuente}\n{trozo}\n'
        bloques.append(bloque)
        usados += len(bloque)
    return '\n'.join(bloques), paginas


def _riesgo_ambiguedad(p):
    """Detecta patrones de preguntas sin respuesta única evidente.

    Es un filtro preventivo, no una prueba matemática de corrección.
    """
    enunciado = _normalizar(p.get('pregunta', ''))
    opciones = [_normalizar(o) for o in p.get('opciones', [])]
    if any(frase in enunciado for frase in (
        'que modelo se recomienda', 'cual es el mejor modelo',
        'que tecnica se recomienda', 'cual es la mejor tecnica',
        'que tipo de balanceo se recomienda', 'cual es la ventaja principal',
        'que algoritmo es mejor', 'que metodo es mejor',
    )):
        return True
    if any('smote' in o for o in opciones) and any(
        o == 'rus' or 'random undersampling' in o for o in opciones
    ) and any(x in enunciado for x in ('balance', 'desbalance', 'clases')):
        return True
    return False


def _tipo_valido(pregunta, tipo):
    texto = _normalizar(pregunta['pregunta'])
    vetadas = ('cual fue el accuracy', 'valor del accuracy', 'accuracy obtenido',
               'accuracy de train', 'accuracy de test', 'cuantos registros',
               'cuantas observaciones', 'en el ejercicio', 'en la pagina',
               'segun la pagina', 'que tipo de overfitting se observa',
               'en el dataset', 'en la actividad', 'en el conjunto de entrenamiento')
    if any(frase in texto for frase in vetadas):
        return False
    if tipo == 'conceptual' and any(t in texto for t in
                                    ('celular', 'pima', 'paciente', 'dataset', 'diabetes')):
        return False
    return True


def _validar_pregunta(p, tipo, paginas):
    if not isinstance(p, dict) or p.get('tipo') != tipo:
        return None
    enunciado = p.get('pregunta')
    opciones = p.get('opciones')
    explicacion = p.get('explicacion')
    if not isinstance(enunciado, str) or len(enunciado.strip()) < 15:
        return None
    if not isinstance(opciones, list) or len(opciones) != 4:
        return None
    if not all(isinstance(o, str) and o.strip() for o in opciones):
        return None
    if len({_normalizar(o) for o in opciones}) != 4:
        return None
    if type(p.get('correcta')) is not int or p['correcta'] not in range(4):
        return None
    if not isinstance(explicacion, str) or len(explicacion.strip()) < 15:
        return None
    if p.get('ambigua') is True or _riesgo_ambiguedad(p) or not _tipo_valido(p, tipo):
        return None
    if tipo == 'aplicacion' and not any(
        palabra in _normalizar(enunciado)
        for palabra in ('si un ', 'si una ', 'supong', 'hipotetic', 'escenario', 'situacion', 'caso ')
    ):
        return None
    try:
        _indices_correctos(p)
    except ValueError:
        return None

    # Una cita solo se considera respaldo del PDF si está literalmente en
    # una de sus páginas. La coincidencia textual NO demuestra verdad semántica.
    evidencia = p.get('evidencia', '')
    fuente = p.get('fuente', '')
    pagina_verificada = None
    if isinstance(evidencia, str) and len(evidencia.split()) >= 5:
        cita = _normalizar(evidencia)
        if cita and 'http' not in cita:
            for etiqueta, material in paginas:
                if cita in _normalizar(material):
                    # Si se proporcionó una fuente, debe coincidir con la página.
                    if not fuente or _normalizar(fuente) == _normalizar(etiqueta):
                        pagina_verificada = etiqueta
                        break
    nueva = dict(p)
    nueva['correctas'] = [p['correcta']]
    nueva['ambigua'] = False
    nueva['tipo'] = tipo
    # Las justificaciones de distractores son opcionales para compatibilidad.
    justificaciones = p.get('por_que_no', [])
    if (isinstance(justificaciones, list) and len(justificaciones) == 4
            and all(isinstance(x, str) for x in justificaciones)):
        nueva['por_que_no'] = justificaciones
    if pagina_verificada:
        nueva['fuente'] = f'PDF: {pagina_verificada}'
        nueva['origen'] = 'pdf'
        nueva['evidencia'] = evidencia.strip()
    else:
        # No presentar como cita PDF lo que no se pudo verificar.
        nueva['fuente'] = 'Conocimiento complementario de IA (no verificado en el PDF)'
        nueva['origen'] = 'ia'
        nueva['evidencia'] = ''
    return nueva


def _preguntas_respaldo_xai(contexto):
    """Banco editorial complementario: no atribuir al PDF sin cita literal."""
    temas = _normalizar(contexto)
    if not any(t in temas for t in ('shap', 'lime', 'explainable', 'explicabilidad', 'interpretabilidad')):
        return []
    datos = [
        ('conceptual', '¿Qué diferencia una explicación local de una global?',
         ['La local explica una predicción; la global resume el modelo.', 'La local solo funciona en regresión.', 'La global explica exclusivamente un registro.', 'Ambas muestran siempre los mismos resultados.'], 0,
         'La explicación local analiza una observación; la global describe patrones generales del modelo.'),
        ('conceptual', '¿Qué representa un valor SHAP positivo para una clase concreta?',
         ['Una contribución que aumenta la salida de esa clase.', 'La certeza de que la predicción es correcta.', 'El porcentaje de datos de entrenamiento.', 'Una reducción obligatoria de la salida de esa clase.'], 0,
         'Un valor SHAP positivo empuja hacia arriba la salida explicada, respecto al valor de referencia.'),
        ('conceptual', '¿Por qué una variable importante globalmente puede ser poco relevante para un caso?',
         ['Su contribución cambia entre observaciones.', 'Todas las variables influyen igual en cada caso.', 'La importancia global es siempre un error.', 'Las explicaciones locales ignoran los datos.'], 0,
         'La importancia global resume muchas observaciones, pero la contribución de cada variable puede variar en un caso particular.'),
        ('conceptual', '¿Qué precaución requiere interpretar una explicación de un modelo predictivo?',
         ['Una contribución predictiva no demuestra causalidad.', 'Toda correlación prueba una relación causal.', 'Las explicaciones eliminan cualquier sesgo.', 'Un valor alto garantiza que el modelo es correcto.'], 0,
         'Las explicaciones describen cómo el modelo usa variables; por sí solas no establecen relaciones de causa y efecto.'),
        ('aplicacion', 'Si un equipo necesita explicar por qué cambió una predicción individual, ¿qué análisis corresponde?',
         ['Una explicación local de esa observación.', 'Solo la exactitud promedio del conjunto.', 'El número total de filas disponibles.', 'Únicamente la distribución de clases.'], 0,
         'Una explicación local permite examinar qué variables contribuyeron a una predicción concreta.'),
        ('aplicacion', 'En un escenario hipotético, dos pacientes reciben predicciones diferentes. ¿Qué comparación ayuda a interpretarlas?',
         ['Comparar contribuciones locales de las variables.', 'Comparar solamente el tamaño del archivo.', 'Revisar únicamente el promedio de edades.', 'Eliminar todas las variables del modelo.'], 0,
         'Comparar contribuciones locales muestra qué características influyeron en cada predicción, sin asumir causalidad.'),
        ('aplicacion', 'Si un equipo quiere resumir qué variables influyen en muchas predicciones, ¿qué necesita?',
         ['Un análisis de importancia global.', 'Una sola predicción sin contexto.', 'Eliminar el conjunto de prueba.', 'La etiqueta de un único registro.'], 0,
         'La importancia global resume patrones de contribución de variables a través de múltiples observaciones.'),
    ]
    preguntas = []
    for tipo, enunciado, opciones, correcta, explicacion in datos:
        candidata = {'tipo': tipo, 'pregunta': enunciado, 'opciones': opciones,
                     'correcta': correcta, 'correctas': [correcta], 'ambigua': False,
                     'explicacion': explicacion, 'fuente': 'IA', 'evidencia': '',
                     'por_que_no': ['', '', '', '']}
        validada = _validar_pregunta(candidata, tipo, [])
        if validada:
            validada['fuente'] = 'Banco de estudio complementario (no cita del PDF)'
            validada['origen'] = 'complementario'
            preguntas.append(validada)
    return preguntas


def generar_examen(contexto, cantidad=5):
    if not isinstance(contexto, str) or not contexto.strip():
        raise ValueError('No hay texto disponible para generar el examen.')
    if type(cantidad) is not int or not 1 <= cantidad <= 30:
        raise ValueError('La cantidad debe estar entre 1 y 30.')

    material, paginas = _preparar_material(contexto, limite=2400)
    aplicaciones = round(cantidad * 0.2)
    metas = {'conceptual': cantidad - aplicaciones, 'aplicacion': aplicaciones}
    resultados = {'conceptual': [], 'aplicacion': []}
    vistas = set()

    # Primero 80/20; después se admiten prácticas adicionales, con tope de intentos.
    for intento in range(5):
        faltan = {tipo: meta - len(resultados[tipo]) for tipo, meta in metas.items()}
        if sum(map(len, resultados.values())) >= cantidad:
            break
        if intento >= 2:
            # Rescate: si falta teoría, se permite completar con casos prácticos.
            faltan = {'conceptual': 0, 'aplicacion': cantidad - sum(map(len, resultados.values()))}
        # En rescate pedimos una pregunta extra: una candidata puede no superar el filtro.
        if intento >= 2:
            faltan['aplicacion'] = min(2, faltan['aplicacion'] + 1)
        ya_usadas = '\n'.join('- ' + p['pregunta'] for grupo in resultados.values() for p in grupo) or 'Ninguna'
        mensaje = f'''Genera preguntas de opción múltiple EXCLUSIVAMENTE sobre los temas identificados en el MATERIAL PDF.
NECESITO EXACTAMENTE {faltan['conceptual']} preguntas con tipo "conceptual" y
{faltan['aplicacion']} con tipo "aplicacion". Genera las preguntas que faltan
EN UNA SOLA RESPUESTA. Nivel universitario, español claro.
En intentos de rescate, genera casos con una condición precisa y una única solución.
Ejemplo de tema: si la prioridad es explicar una predicción individual, pregunta
qué método ofrece explicación local (LIME), con alternativas que no cumplan esa función.
NO REPITAS ESTAS PREGUNTAS YA ACEPTADAS:
{ya_usadas}

PRIORIDAD 1: utiliza la teoría del MATERIAL PDF proporcionado.
PRIORIDAD 2: cuando el material solo muestre ejercicios, títulos o código,
completa únicamente con teoría general de los mismos conceptos presentes
en el material. No introduzcas temas diferentes ni inventes resultados.
No generes preguntas cuya respuesta dependa de información no proporcionada.
Evita afirmaciones absolutas como "garantiza", "siempre" o "el mejor".
No preguntes cómo mejorar accuracy sin especificar el problema concreto.
No inventes definiciones de métricas como SHAP, G-Mean, AUC o F1-score.

CONCEPTUAL: exactamente preguntas de comprensión, comparación,
interpretación, causas, límites y cuándo utilizar un método. Evita
preguntas triviales o memorísticas y NO menciones datasets específicos.
APLICACION: caso HIPOTÉTICO breve que obligue a elegir una acción
justificada; no cifras ni resultados de ejercicios. Empieza el enunciado
con «En un escenario hipotético...» o «Si un equipo...».
No preguntes por accuracy obtenido, variable objetivo de un dataset,
ni qué pasó con un entrenamiento que no aparece resuelto.
Cada pregunta tiene 4 opciones DISTINTAS y UNA sola correcta.
PROHIBIDO preguntar «cuál es el mejor modelo», «qué técnica se recomienda»
o «ventaja principal» sin condiciones que hagan única la respuesta.
PROHIBIDO poner SMOTE y RUS como opciones para «qué balancea clases».
Los distractores deben ser claramente falsos EN EL CONTEXTO del enunciado.
Incluye «por_que_no»: arreglo de 4 explicaciones breves (máximo 12 palabras
cada una). En la posición correcta escribe cadena vacía; en las otras,
explica por qué no corresponden. Revisa internamente que no haya dos válidas.
Explica brevemente (máximo 22 palabras) por qué la opción correcta es correcta.
Cada opción tendrá máximo 12 palabras y cada pregunta máximo 22 palabras.

Si una pregunta está RESPALDADA DIRECTAMENTE por texto del PDF, pon
"fuente" igual a la etiqueta FUENTE de la página y "evidencia" como
una frase LITERAL de esa misma página que respalde la respuesta.
Si necesitas conocimiento complementario, pon "fuente":"IA" y
"evidencia":"". No fabriques citas. No mezcles ejercicios distintos.

Devuelve SOLO un JSON con esta forma:
{{"preguntas":[{{"tipo":"conceptual","pregunta":"...",
"opciones":["...","...","...","..."],"correcta":0,
"correctas":[0],"ambigua":false,"explicacion":"...",
"fuente":"IA","evidencia":"",
"por_que_no":["","razón breve","razón breve","razón breve"]}}]}}

MATERIAL PDF (referencia temática):
{material}
'''
        try:
            respuesta = consultar_ollama(
                mensaje,
                sistema='Eres profesor universitario de analítica predictiva. '
                        'Prioriza el material. No inventes citas. Devuelve JSON válido.',
                formato='json', timeout=65, num_predict=1250, num_ctx=3072,
            )
            candidatas = _parsear_json(respuesta)
        except (ValueError, TypeError, RuntimeError) as exc:
            # Conservar preguntas aceptadas aunque una solicitud falle.
            continue
        for candidata in candidatas:
            if not isinstance(candidata, dict):
                continue
            tipo = candidata.get('tipo')
            if tipo not in metas:
                continue
            if sum(map(len, resultados.values())) >= cantidad:
                break
            if intento < 2 and len(resultados[tipo]) >= metas[tipo]:
                continue
            pregunta = _validar_pregunta(candidata, tipo, paginas)
            if pregunta is None:
                continue
            clave = _normalizar(pregunta['pregunta'])
            if clave in vistas:
                continue
            vistas.add(clave)
            resultados[tipo].append(pregunta)

    preguntas = resultados['conceptual'] + resultados['aplicacion']
    # Si Ollama no completó el examen, utilizar preguntas editoriales verificadas
    # sobre XAI, claramente etiquetadas como material complementario.
    if len(preguntas) < cantidad:
        for adicional in _preguntas_respaldo_xai(contexto):
            if len(preguntas) >= cantidad:
                break
            clave = _normalizar(adicional['pregunta'])
            if clave not in vistas:
                preguntas.append(adicional)
                vistas.add(clave)
    if len(preguntas) != cantidad:
        raise ValueError(
            f'Se generaron {len(preguntas)} de {cantidad} preguntas válidas. '
            'No se mostró un examen incompleto. Puedes intentar de nuevo '
            'o agregar apuntes con más teoría.'
        )
    import random

    for pregunta in preguntas:
        opciones_originales = pregunta['opciones']
        correcta_original = pregunta['correcta']
        justificaciones = pregunta.get('por_que_no', [])

        indices = list(range(4))
        random.shuffle(indices)

        pregunta['opciones'] = [opciones_originales[i] for i in indices]
        pregunta['correcta'] = indices.index(correcta_original)
        pregunta['correctas'] = [pregunta['correcta']]

        if isinstance(justificaciones, list) and len(justificaciones) == 4:
            pregunta['por_que_no'] = [justificaciones[i] for i in indices]

    random.shuffle(preguntas)
    return preguntas


def evaluar_examen(preguntas, respuestas):
    resultados = []
    aciertos = 0
    for indice, pregunta in enumerate(preguntas):
        opciones = pregunta['opciones']
        seleccionada = respuestas.get(indice)
        correctas = _indices_correctos(pregunta)
        es_correcta = type(seleccionada) is int and seleccionada in correctas
        if es_correcta:
            aciertos += 1
        origen = pregunta.get('fuente', 'Origen no especificado')
        explicacion = pregunta['explicacion'] + '\nFuente: ' + origen
        por_que_no = pregunta.get('por_que_no', [])
        if isinstance(por_que_no, list) and len(por_que_no) == 4:
            detalles = [f'• {opciones[i]}: {motivo.strip()}'
                        for i, motivo in enumerate(por_que_no)
                        if i not in correctas and isinstance(motivo, str) and motivo.strip()]
            if detalles:
                explicacion += '\nPor qué las otras opciones no corresponden:\n' + '\n'.join(detalles)
        if pregunta.get('evidencia'):
            explicacion += '\nCita textual del material: ' + pregunta['evidencia']
        resultados.append({
            'pregunta': pregunta['pregunta'],
            'opciones': opciones,
            'respuesta_usuario': (opciones[seleccionada] if
                                  type(seleccionada) is int and 0 <= seleccionada < 4
                                  else 'Sin responder'),
            'respuesta_correcta': ' / '.join(opciones[i] for i in correctas),
            'acierto': es_correcta,
            'explicacion': explicacion,
        })
    total = len(preguntas)
    return {
        'aciertos': aciertos,
        'total': total,
        'calificacion': round(aciertos / total * 100, 1) if total else 0,
        'resultados': resultados,
    }
