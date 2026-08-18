from itertools import count

from django.shortcuts import render

from .mock_candidatos import listar_candidatos
from .mock_academia import alumnos as ALUMNOS_MOCK
from .mock_academia import profesores as PROFESORES_MOCK
from .forms import *

_id_alumnos = count(len(ALUMNOS_MOCK) + 1)
_id_profesor = count(len(PROFESORES_MOCK) + 1)


def index(request):
    return render(request, "myapp/index.html", {"active_tab": "index"})


def candidatos(request):
    return render(request, "myapp/candidatos.html", {
        "candidatos": listar_candidatos(),
        "active_tab": "candidatos",
    })


def comite(request):
    return render(request, "myapp/comite.html", {"active_tab": "comite"})


def profesores(request):
    return render(request, "myapp/profesores.html", {"active_tab": "profesores"})


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
            form = AlumnoForm()  # formulario limpio para cargar otro
    else:
        form = AlumnoForm()

    return render(request, "myapp/nuevo_alumno.html", {
        "form": form,
        "guardado": guardado,
        "active_tab": "alumnos",
    })


def alumnos(request):
    return render(request, "myapp/alumnos.html", {
        "alumnos": ALUMNOS_MOCK,
        "active_tab": "alumnos",
    })

def nuevo_profesor(request):
    guardado = False
    if request.method == "POST":
        form = ProfesorForm(request.POST)
        if form.is_valid():
            ALUMNOS_MOCK.append({
                "id_profesor": next(_id_profesor),
                "dni": form.cleaned_data["dni"],
                "nombre": form.cleaned_data["nombre"],
                "apellidos": form.cleaned_data["apellidos"],
                "domicilio": form.cleaned_data["domicilio"], #actualizar respecto al forms
                "nivel": form.cleaned_data["nivel"],
                "titulacion": form.cleaned_data["titulacion"],
                "tipo": form.cleaned_data["tipo"]
            })
            guardado = True
            form = ProfesorForm()  # formulario limpio para cargar otro
    else:
        form = ProfesorForm()

    return render(request, "myapp/profesores.html", {
        "form": form,
        "guardado": guardado,
        "active_tab": "profesores",
    })