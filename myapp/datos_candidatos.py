"""
Acceso a datos del sector Candidatos, contra MySQL con SQL crudo, igual
que el resto de los sectores (ver datos_comite.py y las vistas de alumno y
profesor en views.py).

Reemplaza a mock_candidatos.py. Antes los candidatos, las llamadas y las
entrevistas vivían en listas de Python y se perdían al reiniciar el
servidor; ahora van a las tablas `candidato`, `candidato_materia`,
`llamada` y `entrevista`.

Dos cosas que la base impone y el mock no contemplaba, y que por eso este
módulo traduce en un solo lugar en vez de repetirlo en cada vista:

- Los ENUM de MySQL están en mayúsculas y con otros nombres que las
  palabras que usan los formularios y los templates (`concertada` ->
  `ENTREVISTA_CONCERTADA`, `tutor` -> `TUTOR`). Ver DISPOSICION_A_BD y
  TIPO_DESEADO_A_BD.

- `entrevista` exige `id_candidato`, `id_asignatura` e `id_comite`, y no
  tiene UNIQUE en `id_llamada`. La regla de "una sola entrevista por
  llamada" la tiene que exigir la aplicación.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db import connection


class SinComiteError(Exception):
    """No hay ningún comité cargado, y una entrevista no puede existir sin uno.

    `entrevista.id_comite` es NOT NULL con FK a `comite`, así que sin un
    comité previo no hay entrevista que registrar. Se maneja aparte de
    IntegrityError porque es un problema de orden de carga de datos, no de
    datos inválidos.
    """


# Vocabulario de los formularios/templates <-> ENUM de la base.
TIPO_DESEADO_A_BD = {
    "tutor": "TUTOR",
    "especialista": "ESPECIALISTA",
    "ambos": "AMBOS",
}

DISPOSICION_A_BD = {
    "no_localizado": "NO_LOCALIZADO",
    "no_interesado": "NO_INTERESADO",
    "concertada": "ENTREVISTA_CONCERTADA",
}

TIPO_DESEADO_DE_BD = {v: k for k, v in TIPO_DESEADO_A_BD.items()}
DISPOSICION_DE_BD = {v: k for k, v in DISPOSICION_A_BD.items()}


@dataclass
class Asignatura:
    id: int
    codigo: str
    nombre: str


@dataclass
class Candidato:
    id: int
    dni: str
    nombre: str
    apellidos: str
    curriculum: str | None
    tipo_deseado: str
    materias: list[int] = field(default_factory=list)  # ids de asignatura

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}"


@dataclass
class Llamada:
    id: int
    candidato_id: int
    fecha_hora: object  # datetime con tzinfo: el proyecto tiene USE_TZ = True
    disposicion: str  # 'no_localizado' | 'no_interesado' | 'concertada'


@dataclass
class Entrevista:
    id: int
    candidato_id: int
    llamada_id: int
    fecha: object  # date
    asignatura_id: int
    asignatura_nombre: str | None
    valoracion: str


# ---------- Materias ----------

_SELECT_ASIGNATURA = """
    SELECT id, codigo, nombre
    FROM asignatura
    ORDER BY nombre
"""


def listar_materias() -> list[Asignatura]:
    return [Asignatura(*f) for f in _consultar(_SELECT_ASIGNATURA)]


# ---------- Candidatos ----------

_SELECT_CANDIDATO = """
    SELECT id, dni, nombre, apellidos, curriculum, tipo_deseado
    FROM candidato
"""


def _consultar(sql: str, params: list | None = None) -> list:
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return cursor.fetchall()


def _escapar_like(texto: str) -> str:
    """Convierte texto de usuario en un patrón LIKE seguro.

    Sin esto, buscar "%" traería todos los candidatos y buscar "_"
    devolvería cualquiera de un caracter. Se escapa con '!' para no
    enredarse con los backslashes de los literales de MySQL.
    """
    for caracter in ("!", "%", "_"):
        texto = texto.replace(caracter, f"!{caracter}")
    return f"%{texto}%"


def _a_candidato(fila) -> Candidato:
    """Construye un Candidato desde la fila de la tabla.

    El tipo se devuelve en el vocabulario del formulario ('ambos', no
    'AMBOS'): sin esto, editar_candidato pasa el valor como initial y el
    <select> del tipo queda sin nada marcado, porque no matchea ninguna
    de las choices.
    """
    candidato = Candidato(*fila)
    candidato.tipo_deseado = TIPO_DESEADO_DE_BD.get(candidato.tipo_deseado, candidato.tipo_deseado)
    return candidato


def listar_candidatos(q: str = "", tipo_deseado: str = "") -> list[Candidato]:
    """Listado con los filtros del buscador, ya ordenado por apellido y nombre.

    El filtro va en SQL y no sobre la lista en memoria como hacía el mock,
    porque la lista ahora crece con lo que haya cargado la base.
    """
    condiciones = ["1 = 1"]
    params: list = []

    if q:
        patron = _escapar_like(q.lower())
        condiciones.append(
            "(LOWER(nombre) LIKE %s ESCAPE '!'"
            " OR LOWER(apellidos) LIKE %s ESCAPE '!'"
            " OR dni LIKE %s ESCAPE '!')"
        )
        params += [patron, patron, patron]

    if tipo_deseado in TIPO_DESEADO_A_BD:
        condiciones.append("tipo_deseado = %s")
        params.append(TIPO_DESEADO_A_BD[tipo_deseado])

    sql = (
        _SELECT_CANDIDATO
        + " WHERE "
        + " AND ".join(condiciones)
        + " ORDER BY apellidos, nombre"
    )
    candidatos = [_a_candidato(f) for f in _consultar(sql, params)]
    return _con_materias(candidatos)


def _con_materias(candidatos: list[Candidato]) -> list[Candidato]:
    """Carga las materias de varios candidatos en una sola consulta.

    Antes el mock traía las materias ya pegadas a cada ficha; ahora hay que
    ir a buscarlas, y hacerlo candidato por candidato sería una consulta
    por fila del listado.
    """
    if not candidatos:
        return candidatos

    ids = [c.id for c in candidatos]
    marcadores = ", ".join(["%s"] * len(ids))
    por_candidato: dict[int, list[int]] = {id_: [] for id_ in ids}
    for id_candidato, id_asignatura in _consultar(
        f"""SELECT id_candidato, id_asignatura
            FROM candidato_materia
            WHERE id_candidato IN ({marcadores})""",
        ids,
    ):
        por_candidato[id_candidato].append(id_asignatura)

    for candidato in candidatos:
        candidato.materias = por_candidato[candidato.id]
    return candidatos


def obtener_candidato(id_candidato: int) -> Candidato | None:
    filas = _consultar(_SELECT_CANDIDATO + " WHERE id = %s", [id_candidato])
    return _con_materias([_a_candidato(filas[0])])[0] if filas else None


def crear_candidato(dni, nombre, apellidos, curriculum, tipo_deseado, materias) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO candidato (dni, nombre, apellidos, curriculum, tipo_deseado)
               VALUES (%s, %s, %s, %s, %s)""",
            [
                dni,
                nombre,
                apellidos,
                curriculum,
                TIPO_DESEADO_A_BD[tipo_deseado],
            ],
        )
        nuevo_id = cursor.lastrowid
        _reemplazar_materias(cursor, nuevo_id, materias)
        return nuevo_id


def actualizar_candidato(id_candidato, dni, nombre, apellidos, curriculum, tipo_deseado, materias) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """UPDATE candidato
               SET dni = %s, nombre = %s, apellidos = %s,
                   curriculum = %s, tipo_deseado = %s
               WHERE id = %s""",
            [
                dni,
                nombre,
                apellidos,
                curriculum,
                TIPO_DESEADO_A_BD[tipo_deseado],
                id_candidato,
            ],
        )
        _reemplazar_materias(cursor, id_candidato, materias)


def _reemplazar_materias(cursor, id_candidato: int, materias) -> None:
    """Deja las materias del candidato exactamente iguales a la lista recibida.

    Borra y reinserta en vez de intentar un diff: son pocas filas y así no
    hay que sostener el caso "el usuario deseleccionó una materia".
    """
    cursor.execute(
        "DELETE FROM candidato_materia WHERE id_candidato = %s", [id_candidato]
    )
    # sorted() porque la tabla tiene UNIQUE(id_candidato, id_asignatura) y el
    # formulario puede devolver ids repetidos.
    for id_asignatura in sorted({int(m) for m in materias}):
        cursor.execute(
            """INSERT INTO candidato_materia (id_candidato, id_asignatura)
               VALUES (%s, %s)""",
            [id_candidato, id_asignatura],
        )


# ---------- Llamadas ----------

_SELECT_LLAMADA = """
    SELECT id, id_candidato, fecha_hora, disposicion
    FROM llamada
"""


def registrar_llamada(id_candidato: int, fecha_hora, disposicion: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO llamada (id_candidato, fecha_hora, disposicion)
               VALUES (%s, %s, %s)""",
            [id_candidato, fecha_hora, DISPOSICION_A_BD[disposicion]],
        )
        return cursor.lastrowid


def obtener_llamada(id_llamada, id_candidato: int) -> Llamada | None:
    """Busca una llamada validando que sea del candidato indicado.

    Equivalente al WHERE id = %s AND id_candidato = %s: sin ese segundo
    filtro, un POST con el llamada_id de otro candidato podría colgarle
    una entrevista ajena.
    """
    try:
        id_llamada = int(id_llamada)
    except (TypeError, ValueError):
        return None

    filas = _consultar(
        _SELECT_LLAMADA + " WHERE id = %s AND id_candidato = %s",
        [id_llamada, id_candidato],
    )
    if not filas:
        return None
    return Llamada(filas[0][0], filas[0][1], filas[0][2], DISPOSICION_DE_BD[filas[0][3]])


def listar_llamadas(id_candidato: int) -> list[Llamada]:
    filas = _consultar(
        _SELECT_LLAMADA + " WHERE id_candidato = %s ORDER BY fecha_hora DESC",
        [id_candidato],
    )
    return [Llamada(f[0], f[1], f[2], DISPOSICION_DE_BD[f[3]]) for f in filas]


# ---------- Entrevistas ----------

_SELECT_ENTREVISTA = """
    SELECT e.id, e.id_candidato, e.id_llamada, e.fecha,
           e.id_asignatura, a.nombre, e.valoracion
    FROM entrevista e
    LEFT JOIN asignatura a ON a.id = e.id_asignatura
"""


def _a_entrevista(fila) -> Entrevista:
    return Entrevista(*fila)


def entrevista_de_llamada(id_llamada: int) -> Entrevista | None:
    filas = _consultar(
        _SELECT_ENTREVISTA + " WHERE e.id_llamada = %s LIMIT 1", [id_llamada]
    )
    return _a_entrevista(filas[0]) if filas else None


def listar_entrevistas(id_candidato: int) -> list[Entrevista]:
    return [
        _a_entrevista(f)
        for f in _consultar(
            _SELECT_ENTREVISTA + " WHERE e.id_candidato = %s ORDER BY e.fecha DESC",
            [id_candidato],
        )
    ]


def _comite_por_defecto(cursor) -> int | None:
    """El comité más reciente, que es el que evalúa por defecto.

    La columna id_comite de entrevista es NOT NULL y antes no se pedía nada
    en el formulario, así que se resuelve acá con el comité del último año
    cargado, que es el que corresponde a una entrevista de esta temporada.
    """
    cursor.execute("SELECT id FROM comite ORDER BY anio DESC, id DESC LIMIT 1")
    fila = cursor.fetchone()
    return fila[0] if fila else None


def registrar_entrevista(
    id_candidato: int,
    id_llamada: int,
    fecha,
    id_asignatura: int,
    valoracion: int,
) -> int:
    """Carga la entrevista de una llamada. Lanza SinComiteError si no hay comité.

    `valoracion` va como texto porque la columna es varchar en la base,
    aunque el formulario la valide como entero de 1 a 5.
    """
    with connection.cursor() as cursor:
        id_comite = _comite_por_defecto(cursor)
        if id_comite is None:
            raise SinComiteError(
                "No se puede registrar una entrevista sin un comité cargado."
            )

        cursor.execute(
            """INSERT INTO entrevista
                   (id_candidato, id_llamada, fecha, id_asignatura, valoracion, id_comite)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            [
                id_candidato,
                id_llamada,
                fecha,
                id_asignatura,
                str(valoracion),
                id_comite,
            ],
        )
        return cursor.lastrowid
