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
        ejercicios = sum(texto.count(t) for t in ('ejercicio resuelto', 'accuracy obtenido', 'train test split', 'import pandas'))
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
    """Descarta preguntas vagas sin una condición que haga única la respuesta."""
    enunciado = _normalizar(p.get('pregunta', ''))
    return any(frase in enunciado for frase in (
        'cual es el mejor', 'cual es la mejor',
        'que metodo es mejor', 'que tecnica se recomienda',
        'cual es la ventaja principal',
    ))


def _tipo_valido(pregunta, tipo):
    """No bloquea materias, nombres de datasets ni disciplinas específicas."""
    return tipo in ('conceptual', 'aplicacion')


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
    if not pagina_verificada:
        return None
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


def generar_examen(contexto, cantidad=5):
    if not isinstance(contexto, str) or not contexto.strip():
        raise ValueError('No hay texto disponible para generar el examen.')
    if type(cantidad) is not int or not 1 <= cantidad <= 30:
        raise ValueError('La cantidad debe estar entre 1 y 30.')

    material, paginas = _preparar_material(contexto, limite=6500)
    if len(material.strip()) < 150:
        raise ValueError('El PDF contiene muy poco texto seleccionable para generar preguntas.')
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
        mensaje = f'''Crea preguntas universitarias de opción múltiple sobre el MATERIAL.
Detecta la materia por el texto: puede ser historia, biología, matemáticas,
literatura, programación o cualquier otra. No presupongas una disciplina.
Solicito {faltan['conceptual']} preguntas conceptuales y
{faltan['aplicacion']} preguntas de aplicación hipotética.
Si no hay suficiente información, devuelve menos preguntas; nunca inventes.
Cada pregunta debe tener cuatro opciones distintas y exactamente una correcta.
La respuesta debe estar apoyada por una frase LITERAL del material.
Copia al menos cinco palabras consecutivas de esa frase en "evidencia" y
copia exactamente la etiqueta FUENTE de su página en "fuente".
No inventes fuentes, datos, citas, definiciones ni resultados.
Evita preguntas ambiguas y distractores que también sean correctos.
En "por_que_no" explica brevemente por qué las otras opciones son incorrectas.
No repitas estas preguntas:
{ya_usadas}

Devuelve exclusivamente JSON válido:
{{"preguntas":[{{"tipo":"conceptual","pregunta":"...",
"opciones":["...","...","...","..."],"correcta":0,
"correctas":[0],"ambigua":false,"explicacion":"...",
"fuente":"etiqueta FUENTE","evidencia":"cita literal de 5 palabras o más",
"por_que_no":["","razón","razón","razón"]}}]}}

MATERIAL:
{material}
'''
        try:
            respuesta = consultar_ollama(
                mensaje,
                sistema=('Eres docente universitario de cualquier materia. '
                         'Solo formula preguntas respaldadas por el material. '
                         'No inventes citas. Devuelve JSON válido.'),
                formato='json', timeout=90, num_predict=1450, num_ctx=4096,
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
    if len(preguntas) != cantidad:
        raise ValueError(
            f'Se generaron {len(preguntas)} de {cantidad} preguntas válidas. '
            'No se mostró un examen incompleto. Puedes intentar de nuevo '
            'o agregar apuntes con más teoría.'
        )
    import random

    for pregunta in preguntas:
        opciones_originales = [re.sub(r'^\\s*[A-Da-d][.)]\\s+', '', o).strip()
                              for o in pregunta['opciones']]
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
