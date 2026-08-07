"""
mock_comite.py

Datos de muestra para las vistas de Comité y Profesores.
Antes vivía mezclado en datos_mock.py junto con otros dos módulos
que no tienen nada que ver entre sí (alumnos/grupos y candidatos).
Lo separo para que cada import sea inequívoco.

Uso dataclasses en vez de dicts sueltos: da __repr__, comparación por
valor y autocompletado gratis, documentando la forma de cada entidad
igual que lo haría un modelo real.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ProfesorMock:
    id: int
    dni: str
    nombre: str
    apellidos: str
    domicilio: str
    nivel_estudios: str
    titulacion: str
    tipo: str  # 'TUTOR' | 'ESPECIALISTA' | 'AMBOS'

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}"


@dataclass
class ComiteMock:
    id: int
    anio: int
    id_presidente: int
    id_secretario: int
    id_vocal: int


PROFESORES_MOCK: list[ProfesorMock] = [
    ProfesorMock(1, "30.111.222", "Lucía", "Fernández Suárez",
                 "Av. Colón 1234, Córdoba", "Universitario",
                 "Profesorado en Educación Primaria", "TUTOR"),
    ProfesorMock(2, "28.456.789", "Martín", "Gómez Ibarra",
                 "Bv. Illia 456, Córdoba", "Universitario",
                 "Licenciatura en Educación Física", "ESPECIALISTA"),
    ProfesorMock(3, "32.987.654", "Valentina", "Rossi",
                 "Calle Rivadavia 789, Córdoba", "Terciario",
                 "Profesorado en Inglés", "ESPECIALISTA"),
    ProfesorMock(4, "27.321.098", "Diego", "Herrera",
                 "Av. Vélez Sarsfield 2100, Córdoba", "Universitario",
                 "Profesorado en Matemática", "AMBOS"),
    ProfesorMock(5, "31.654.321", "Camila", "Ortiz",
                 "Calle Belgrano 345, Córdoba", "Universitario",
                 "Licenciatura en Psicopedagogía", "TUTOR"),
    ProfesorMock(6, "29.876.543", "Facundo", "Molina",
                 "Bv. Chacabuco 987, Córdoba", "Terciario",
                 "Profesorado en Música", "ESPECIALISTA"),
    ProfesorMock(7, "33.222.111", "Sofía", "Acosta",
                 "Av. Rafael Núñez 1500, Córdoba", "Universitario",
                 "Profesorado en Educación Primaria", "TUTOR"),
    ProfesorMock(8, "26.789.456", "Emiliano", "Castro",
                 "Calle 27 de Abril 678, Córdoba", "Universitario",
                 "Licenciatura en Ciencias de la Educación", "AMBOS"),
]

COMITES_MOCK: list[ComiteMock] = [
    ComiteMock(1, 2024, id_presidente=4, id_secretario=1, id_vocal=2),
    ComiteMock(2, 2025, id_presidente=8, id_secretario=5, id_vocal=3),
    ComiteMock(3, 2026, id_presidente=4, id_secretario=7, id_vocal=6),
]


def listar_profesores_mock() -> list[ProfesorMock]:
    return PROFESORES_MOCK


def listar_comites_mock() -> list[ComiteMock]:
    return COMITES_MOCK


def obtener_profesor_mock(id_profesor: int) -> ProfesorMock | None:
    """Resuelve id_presidente / id_secretario / id_vocal a su Profesor."""
    return next((p for p in PROFESORES_MOCK if p.id == id_profesor), None)


def comite_detallado_mock(comite: ComiteMock) -> dict:
    """Devuelve un comité con los tres roles ya resueltos a Profesor,
    listo para pasarle a un template Django."""
    return {
        "id": comite.id,
        "anio": comite.anio,
        "presidente": obtener_profesor_mock(comite.id_presidente),
        "secretario": obtener_profesor_mock(comite.id_secretario),
        "vocal": obtener_profesor_mock(comite.id_vocal),
    }