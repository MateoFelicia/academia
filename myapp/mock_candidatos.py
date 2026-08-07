"""
mock_candidatos.py

Base de datos en memoria para el flujo de candidatos: reemplaza
temporalmente a models.py + services.py (Django ORM) para poder
mostrar el proyecto funcionando sin migraciones ni DB real.
Todos los datos viven en listas de Python y se pierden al reiniciar
el servidor.

Este es el módulo que necesita templates/myapp/candidatos.html:
itera `candidatos` y usa c.dni, c.nombre, c.apellidos, c.tipo_deseado.

Para usarlo en views.py:
    from .mock_candidatos import listar_candidatos, crear_candidato, ...

Los templates no necesitan cambios: Django accede a los atributos de
estos objetos (c.dni, c.nombre, etc.) igual que accedería a un objeto
del ORM.
"""

from dataclasses import dataclass
from datetime import datetime
from itertools import count


# ---------- Contadores de ID (simulan el autoincremental de una BD real) ----------

_id_candidatos = count(1)
_id_asignaturas = count(1)
_id_comites = count(1)
_id_candidato_materia = count(1)
_id_llamadas = count(1)
_id_entrevistas = count(1)


# ---------- "Tablas" (clases) ----------

@dataclass
class Candidato:
    id: int
    dni: str
    nombre: str
    apellidos: str
    curriculum: str | None = None
    tipo_deseado: str | None = None


@dataclass
class Asignatura:
    id: int
    nombre: str


@dataclass
class Comite:
    id: int
    nombre: str


@dataclass
class CandidatoMateria:
    id: int
    id_candidato: int
    id_asignatura: int


@dataclass
class Llamada:
    id: int
    id_candidato: int
    fecha_hora: datetime
    disposicion: str | None = None


@dataclass
class Entrevista:
    id: int
    id_candidato: int
    id_llamada: int
    fecha: datetime
    id_asignatura: int
    valoracion: str | None = None
    id_comite: int | None = None


# ---------- Almacenamiento en memoria ----------

candidatos: list[Candidato] = []
asignaturas: list[Asignatura] = []
comites: list[Comite] = []
candidato_materias: list[CandidatoMateria] = []
llamadas: list[Llamada] = []
entrevistas: list[Entrevista] = []


# ---------- Candidatos ----------

def listar_candidatos():
    return candidatos


def crear_candidato(dni, nombre, apellidos, curriculum=None, tipo_deseado=None):
    c = Candidato(
        id=next(_id_candidatos), dni=dni, nombre=nombre, apellidos=apellidos,
        curriculum=curriculum, tipo_deseado=tipo_deseado,
    )
    candidatos.append(c)
    return c


def actualizar_candidato(id_c, dni=None, nombre=None, apellidos=None,
                          curriculum=None, tipo_deseado=None):
    c = next((x for x in candidatos if x.id == id_c), None)
    if not c:
        return None
    if dni:
        c.dni = dni
    if nombre:
        c.nombre = nombre
    if apellidos:
        c.apellidos = apellidos
    if curriculum:
        c.curriculum = curriculum
    if tipo_deseado:
        c.tipo_deseado = tipo_deseado
    return c


def eliminar_candidato(id_c):
    c = next((x for x in candidatos if x.id == id_c), None)
    if c:
        candidatos.remove(c)
    return c


def agregar_materia_candidato(id_candidato, id_asignatura):
    cm = CandidatoMateria(
        id=next(_id_candidato_materia),
        id_candidato=id_candidato,
        id_asignatura=id_asignatura,
    )
    candidato_materias.append(cm)
    return cm


# ---------- Llamadas ----------

def listar_llamadas():
    return llamadas


def crear_llamada(id_candidato, fecha_hora, disposicion=None):
    ll = Llamada(
        id=next(_id_llamadas), id_candidato=id_candidato,
        fecha_hora=fecha_hora, disposicion=disposicion,
    )
    llamadas.append(ll)
    return ll


# ---------- Entrevistas ----------

def listar_entrevistas():
    return entrevistas


def crear_entrevista(id_candidato, id_llamada, fecha, id_asignatura,
                      valoracion=None, id_comite=None):
    e = Entrevista(
        id=next(_id_entrevistas), id_candidato=id_candidato, id_llamada=id_llamada,
        fecha=fecha, id_asignatura=id_asignatura, valoracion=valoracion,
        id_comite=id_comite,
    )
    entrevistas.append(e)
    return e


# ---------- Asignaturas ----------

def listar_asignaturas():
    return asignaturas


# ---------- Datos de ejemplo para que la demo no arranque vacía ----------

def _cargar_datos_de_ejemplo():
    asignaturas.append(Asignatura(id=next(_id_asignaturas), nombre="Programación"))
    asignaturas.append(Asignatura(id=next(_id_asignaturas), nombre="Redes"))
    comites.append(Comite(id=next(_id_comites), nombre="Comité Técnico"))

    crear_candidato(dni="30111222", nombre="Juan", apellidos="Pérez",
                     curriculum="CV de prueba", tipo_deseado="Full Stack")
    crear_candidato(dni="30333444", nombre="Ana", apellidos="Gómez",
                     curriculum="CV de prueba", tipo_deseado="Backend")


_cargar_datos_de_ejemplo()