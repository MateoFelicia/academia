from itertools import count

from django.shortcuts import render

from .mock_candidatos import listar_candidatos
from .mock_academia import alumnos as ALUMNOS_MOCK
from .mock_comite import (
    ComiteMock,
    COMITES_MOCK,
    comite_detallado_mock,
    listar_comites_mock,
    listar_profesores_mock,
)
from .forms import *


_id_alumnos = count(len(ALUMNOS_MOCK) + 1)
_id_comites = count(len(COMITES_MOCK) + 1)


def index(request):
    return render(request, "myapp/index.html", {
        "active_tab": "index"
    })


def candidatos(request):
    return render(request, "myapp/candidatos.html", {
        "candidatos": listar_candidatos(),
        "active_tab": "candidatos",
    })


def comite(request):
    """
    Lista los comités existentes y permite agregar uno nuevo
    desde la misma página.
    """
    guardado = False

    if request.method == "POST":
        form = ComiteForm(request.POST)

        if form.is_valid():
            nuevo = ComiteMock(
                id=next(_id_comites),
                anio=form.cleaned_data["anio"],
                id_presidente=int(form.cleaned_data["id_presidente"]),
                id_secretario=int(form.cleaned_data["id_secretario"]),
                id_vocal=int(form.cleaned_data["id_vocal"]),
            )

            COMITES_MOCK.append(nuevo)

            guardado = True

            # Limpiamos el formulario después de guardar.
            form = ComiteForm()

    else:
        form = ComiteForm()

    # Ordenamos los comités del más reciente al más antiguo.
    comites_ordenados = sorted(
        listar_comites_mock(),
        key=lambda c: c.anio,
        reverse=True,
    )

    # Convertimos cada comité en su versión detallada,
    # resolviendo presidente, secretario y vocal a sus profesores.
    comites = [
        comite_detallado_mock(c)
        for c in comites_ordenados
    ]

    return render(request, "myapp/comite.html", {
        "form": form,
        "guardado": guardado,
        "comites": comites,
        "profesores": listar_profesores_mock(),
        "active_tab": "comite",
    })


def nuevo_comite(request):
    """
    Esta vista ya no es necesaria para el funcionamiento del alta,
    porque el formulario está integrado en comite.html.

    Se mantiene para evitar romper la URL /comite/nuevo/
    si todavía existe en urls.py.
    """
    return comite(request)


def profesores(request):
    return render(request, "myapp/profesores.html", {
        "active_tab": "profesores"
    })


def nuevo_alumno(request):
    guardado = False

    if request.method == "POST":
        form = AlumnoForm(request.POST)

        if form.is_valid():
            ALUMNOS_MOCK.append({
                "id_alumno": next(_id_alumnos),
                "dni": form.cleaned_data["dni"],
                "nombre": form.cleaned_data["nombre"],
                "apellidos": form.cleaned_data["apellidos"],
                "id_grupo": form.cleaned_data["id_grupo"],
            })

            guardado = True
            form = AlumnoForm()

    else:
        form = AlumnoForm()

    return render(request, "myapp/alumnos.html", {
        "form": form,
        "guardado": guardado,
        "active_tab": "alumnos",
    })


def alumnos(request):
    return render(request, "myapp/listado_alumno.html", {
        "alumnos": ALUMNOS_MOCK,
        "active_tab": "alumnos",
    })


def nuevo_profesor(request):
    guardado = False

    if request.method == "POST":
        form = ProfesorForm(request.POST)

        if form.is_valid():
            ALUMNOS_MOCK.append({
                "id_alumno": next(_id_alumnos),
                "dni": form.cleaned_data["dni"],
                "nombre": form.cleaned_data["nombre"],
                "apellidos": form.cleaned_data["apellidos"],
                "id_grupo": form.cleaned_data["id_grupo"],
            })

            guardado = True
            form = ProfesorForm()

    else:
        form = ProfesorForm()

    return render(request, "myapp/alumnos.html", {
        "form": form,
        "guardado": guardado,
        "active_tab": "alumnos",
    })