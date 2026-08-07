"""
mock_academia.py

Datos de muestra para el panel académico: especialidades, cursos,
profesores, grupos, alumnos, fichas individuales, asistencia y
hojas de actividad. Listas de diccionarios en memoria, sin base de datos.

Separado de datos_mock.py, donde vivía mezclado con el mock de
Comité/Profesores y el de Candidatos (tres dominios sin relación).
"""

especialidades = [
    {"id_especialidad": 1, "nombre": "Programación", "descripcion": "Desarrollo de software y aplicaciones"},
    {"id_especialidad": 2, "nombre": "Redes", "descripcion": "Infraestructura y administración de redes"},
    {"id_especialidad": 3, "nombre": "Bases de Datos", "descripcion": "Diseño y gestión de bases de datos"},
]

cursos = [
    {"id_curso": 1, "nombre": "2° Año", "id_especialidad": 1},
    {"id_curso": 2, "nombre": "2° Año", "id_especialidad": 2},
    {"id_curso": 3, "nombre": "3° Año", "id_especialidad": 3},
]

profesores = [
    {"id_profesor": 1, "nombre": "Herrera"},
    {"id_profesor": 2, "nombre": "Aguirre"},
    {"id_profesor": 3, "nombre": "Núñez"},
]

grupos = [
    {"id_grupo": 1, "codigo": "2ºA", "id_curso": 1, "num_alumnos": 24, "id_tutor": 1},
    {"id_grupo": 2, "codigo": "2ºB", "id_curso": 2, "num_alumnos": 21, "id_tutor": 2},
    {"id_grupo": 3, "codigo": "3ºA", "id_curso": 1, "num_alumnos": 19, "id_tutor": 1},
    {"id_grupo": 4, "codigo": "3ºB", "id_curso": 3, "num_alumnos": 22, "id_tutor": 3},
]

alumnos = [
    {"id_alumno": 1, "dni": "30112445", "nombre": "Martina", "apellidos": "Gómez Ferreyra", "id_grupo": 1},
    {"id_alumno": 2, "dni": "29887201", "nombre": "Lucas", "apellidos": "Ibarra Correa", "id_grupo": 1},
    {"id_alumno": 3, "dni": "31004556", "nombre": "Sofía", "apellidos": "Paredes Luna", "id_grupo": 2},
    {"id_alumno": 4, "dni": "30556890", "nombre": "Bruno", "apellidos": "Ríos Aguilar", "id_grupo": 3},
    {"id_alumno": 5, "dni": "31223014", "nombre": "Camila", "apellidos": "Sosa Benítez", "id_grupo": 2},
    {"id_alumno": 6, "dni": "30998673", "nombre": "Nicolás", "apellidos": "Vega Molina", "id_grupo": 3},
]

fichas_individuales = [
    {"id_ficha": 14, "id_alumno": 1, "mes": 7, "anio": 2026},
    {"id_ficha": 21, "id_alumno": 3, "mes": 7, "anio": 2026},
    {"id_ficha": 33, "id_alumno": 4, "mes": 7, "anio": 2026},
]

registros_asistencia = [
    {"id_registro": 1, "id_ficha": 14, "dia": "03/07", "asignatura": "Programación I", "id_profesor": 1, "estado": "presente"},
    {"id_registro": 2, "id_ficha": 14, "dia": "04/07", "asignatura": "Programación I", "id_profesor": 1, "estado": "tarde"},
    {"id_registro": 3, "id_ficha": 21, "dia": "03/07", "asignatura": "Redes I", "id_profesor": 2, "estado": "presente"},
    {"id_registro": 4, "id_ficha": 21, "dia": "05/07", "asignatura": "Redes I", "id_profesor": 2, "estado": "ausente"},
    {"id_registro": 5, "id_ficha": 33, "dia": "04/07", "asignatura": "Base de Datos", "id_profesor": 3, "estado": "presente"},
    {"id_registro": 6, "id_ficha": 33, "dia": "05/07", "asignatura": "Base de Datos", "id_profesor": 3, "estado": "presente"},
]

hojas_actividad = [
    {"id_hoja": 1, "id_grupo": 1, "fecha": "03/07/2026", "id_profesor": 1, "hora_inicio": "08:00", "hora_fin": "10:00"},
    {"id_hoja": 2, "id_grupo": 2, "fecha": "03/07/2026", "id_profesor": 2, "hora_inicio": "10:15", "hora_fin": "12:00"},
    {"id_hoja": 3, "id_grupo": 3, "fecha": "04/07/2026", "id_profesor": 1, "hora_inicio": "08:00", "hora_fin": "09:45"},
    {"id_hoja": 4, "id_grupo": 4, "fecha": "04/07/2026", "id_profesor": 3, "hora_inicio": "13:00", "hora_fin": "15:00"},
]