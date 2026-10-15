"""
Acceso a datos del sector Comité y Profesores, contra MySQL con SQL crudo,
igual que ya se hacía con alumno y profesor en views.py.

Reemplaza a mock_comite.py, donde los profesores y los comités vivían en
listas de Python: todo se perdía al reiniciar el servidor y las altas no
llegaban a la base. Ahora salen de las tablas `profesor` y `comite`.

Se usan dataclasses y no diccionarios sueltos porque comite.html necesita
`nombre_completo` en dos lugares distintos: en el JS del wizard y en las
firmas del acta. Con un dict hay que acordarse de repetir "nombre +
apellidos" en cada template; con la propiedad sale solo.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import connection


@dataclass
class Profesor:
    id: int
    dni: str
    nombre: str
    apellidos: str
    domicilio: str | None
    nivel_estudios: str | None
    titulacion: str | None
    tipo: str  # 'TUTOR' | 'ESPECIALISTA' | 'AMBOS'

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}"


@dataclass
class Comite:
    id: int
    anio: int
    presidente: Profesor | None
    secretario: Profesor | None
    vocal: Profesor | None


# El orden por apellidos es el mismo que usan alumnos.html y candidatos.html
# para los listados de personas.
_COLUMNAS_PROFESOR = (
    "id, dni, nombre, apellidos, domicilio, nivel_estudios, titulacion, tipo"
)

_SELECT_PROFESOR = f"""
    SELECT {_COLUMNAS_PROFESOR}
    FROM profesor
    ORDER BY apellidos, nombre
"""


def _columnas_como(alias: str) -> str:
    """Las mismas columnas de profesor, prefijadas con un alias de tabla.

    Necesario para los JOIN de listar_comites: sin esto habría que repetir
    las ocho columnas a mano por cada uno de los tres roles.
    """
    return ", ".join(f"{alias}.{c.strip()}" for c in _COLUMNAS_PROFESOR.split(","))


def _a_profesor(fila) -> Profesor | None:
    return Profesor(*fila) if fila and fila[0] is not None else None


def listar_profesores() -> list[Profesor]:
    with connection.cursor() as cursor:
        cursor.execute(_SELECT_PROFESOR)
        return [_a_profesor(f) for f in cursor.fetchall()]


def obtener_profesor(id_profesor: int) -> Profesor | None:
    with connection.cursor() as cursor:
        cursor.execute(_SELECT_PROFESOR + " WHERE id = %s", [id_profesor])
        return _a_profesor(cursor.fetchone())


def listar_comites() -> list[Comite]:
    """Comités con los tres roles ya resueltos a su Profesor.

    Tres LEFT JOIN en vez de una consulta por comité: la página siempre
    muestra las tres firmas juntas, así que siempre hay que traerlas.
    Se usa LEFT para que un comité cuyo presidente fue borrado siga
    apareciendo en el libro de actas, con la firma vacía, en lugar de
    desaparecer de la lista sin aviso.
    """
    sql = f"""
        SELECT c.id, c.anio,
               {_columnas_como('p1')},
               {_columnas_como('p2')},
               {_columnas_como('p3')}
        FROM comite c
        LEFT JOIN profesor p1 ON p1.id = c.id_presidente
        LEFT JOIN profesor p2 ON p2.id = c.id_secretario
        LEFT JOIN profesor p3 ON p3.id = c.id_vocal
        ORDER BY c.anio DESC, c.id DESC
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        filas = cursor.fetchall()

    return [
        Comite(
            id=f[0],
            anio=f[1],
            presidente=_a_profesor(f[2:10]),
            secretario=_a_profesor(f[10:18]),
            vocal=_a_profesor(f[18:26]),
        )
        for f in filas
    ]


def crear_comite(anio: int, id_presidente: int, id_secretario: int, id_vocal: int) -> int:
    """Da de alta un comité y devuelve el id generado.

    `comite.anio` es UNIQUE en la base, así que dar de alta dos actas del
    mismo año revienta con IntegrityError. Se deja propagar: la vista la
    traduce a un mensaje de error para el usuario en vez de tragársela.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """INSERT INTO comite (anio, id_presidente, id_secretario, id_vocal)
               VALUES (%s, %s, %s, %s)""",
            [anio, id_presidente, id_secretario, id_vocal],
        )
        return cursor.lastrowid
