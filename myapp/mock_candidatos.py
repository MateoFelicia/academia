"""
mock_candidatos.py

Datos en memoria para el sector de Candidatos (postulantes a dar clases),
armado con el mismo criterio que mock_comite.py: nada de esto toca la
base de datos real, todo vive en listas de Python y se pierde al
reiniciar el servidor. Reemplaza tanto a los viejos models.py
(Candidato, Llamada, Entrevista, Materia) como al SQL crudo que los
sustituyó después, para que este sector funcione exactamente igual que
Comité: sin conexión a MySQL de por medio.

Uso dataclasses en vez de dicts sueltos por la misma razón que en
mock_comite.py: dan __repr__, comparación por valor y autocompletado
gratis, documentando la forma de cada entidad igual que lo haría un
modelo real.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime, timezone


@dataclass
class MateriaMock:
    id: int
    nombre: str


@dataclass
class CandidatoMock:
    id: int
    dni: str
    nombre: str
    apellidos: str
    curriculum: str = ""
    tipo_deseado: str = ""
    materias: list[int] = field(default_factory=list)  # ids de MateriaMock

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}"


@dataclass
class LlamadaMock:
    id: int
    candidato_id: int
    fecha_hora: datetime
    disposicion: str  # 'no_localizado' | 'no_interesado' | 'concertada'


@dataclass
class EntrevistaMock:
    id: int
    llamada_id: int  # OneToOne real: a lo sumo una entrevista por llamada
    fecha: date
    materia_a_cubrir_id: int
    valoracion: int


MATERIAS_MOCK: list[MateriaMock] = [
    MateriaMock(1, "Matemática"),
    MateriaMock(2, "Lengua y Literatura"),
    MateriaMock(3, "Inglés"),
    MateriaMock(4, "Educación Física"),
    MateriaMock(5, "Historia"),
    MateriaMock(6, "Biología"),
    MateriaMock(7, "Química"),
    MateriaMock(8, "Informática"),
]

CANDIDATOS_MOCK: list[CandidatoMock] = [
    CandidatoMock(
        1, "30111222", "Julieta", "Medina",
        "Profesorado en Matemática, 3 años de experiencia en secundario.",
        "tutor", materias=[1, 8],
    ),
    CandidatoMock(
        2, "28444555", "Ramiro", "Suárez",
        "Licenciado en Letras, dicta talleres de escritura creativa.",
        "especialista", materias=[2],
    ),
    CandidatoMock(
        3, "31666777", "Agostina", "Peralta",
        "Profesora de Inglés, certificación First Certificate.",
        "ambos", materias=[3],
    ),
    CandidatoMock(
        4, "29888999", "Tomás", "Ibáñez",
        "Profesor de Educación Física, entrenador de vóley juvenil.",
        "tutor", materias=[4],
    ),
]

LLAMADAS_MOCK: list[LlamadaMock] = [
    # El proyecto tiene USE_TZ = True, así que LlamadaForm siempre entrega
    # datetimes con tzinfo. Estos datos de ejemplo también lo necesitan;
    # si no, sorted() explota al mezclar naive con aware.
    LlamadaMock(1, candidato_id=1,
                fecha_hora=datetime(2026, 8, 20, 10, 30, tzinfo=timezone.utc),
                disposicion="concertada"),
    LlamadaMock(2, candidato_id=2,
                fecha_hora=datetime(2026, 8, 22, 15, 0, tzinfo=timezone.utc),
                disposicion="no_localizado"),
]

ENTREVISTAS_MOCK: list[EntrevistaMock] = [
    EntrevistaMock(1, llamada_id=1, fecha=date(2026, 8, 27),
                   materia_a_cubrir_id=1, valoracion=4),
]


def listar_candidatos_mock() -> list[CandidatoMock]:
    return CANDIDATOS_MOCK


def listar_materias_mock() -> list[MateriaMock]:
    return MATERIAS_MOCK


def obtener_candidato_mock(id_candidato: int) -> CandidatoMock | None:
    return next((c for c in CANDIDATOS_MOCK if c.id == id_candidato), None)


def obtener_materia_mock(id_materia: int) -> MateriaMock | None:
    return next((m for m in MATERIAS_MOCK if m.id == id_materia), None)


def obtener_llamada_mock(id_llamada, id_candidato: int) -> LlamadaMock | None:
    """Busca una llamada por id validando que sea del candidato indicado,
    igual que el WHERE id = %s AND candidato_id = %s que hacía la
    versión en SQL crudo."""
    try:
        id_llamada = int(id_llamada)
    except (TypeError, ValueError):
        return None
    return next(
        (l for l in LLAMADAS_MOCK if l.id == id_llamada and l.candidato_id == id_candidato),
        None,
    )


def entrevista_de_llamada_mock(id_llamada: int) -> EntrevistaMock | None:
    """Resuelve el OneToOne Llamada -> Entrevista (hay a lo sumo una)."""
    return next((e for e in ENTREVISTAS_MOCK if e.llamada_id == id_llamada), None)
