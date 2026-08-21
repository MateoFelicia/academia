from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages
from itertools import count

from .mock_candidatos import listar_candidatos

from .mock_comite import (
    ComiteMock,
    COMITES_MOCK,
    comite_detallado_mock,
    listar_comites_mock,
    listar_profesores_mock,
)
from .forms import *


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



def alumnos(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT dni, nombre, apellidos FROM alumno")
        columnas = [col[0] for col in cursor.description]
        alumnos = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

    return render(request, "myapp/alumnos.html", {
        "alumnos": alumnos,
        "active_tab": "alumnos",
    })

def nuevo_alumno(request):
    guardado = False

    if request.method == "POST":
        form = AlumnoForm(request.POST)

        if form.is_valid():
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO alumno (dni, nombre, apellidos,id_grupo)
                    VALUES (%s, %s, %s)""",
                    [form.cleaned_data["dni"], form.cleaned_data["nombre"], form.cleaned_data["apellidos"], form.cleaned_data["id_grupo"]]
                )
            guardado = True
            form = AlumnoForm()

    else:
        form = AlumnoForm()

    return render(request, "myapp/nuevo_alumno.html", {
        "form": form,
        "guardado": guardado,
        "active_tab": "alumnos",
    })

def modificar_alumno(request):
    alumno = None
    form_buscar = AlumnoForm(request.GET or None)

    try:
        if request.method == "POST" and "guardar" in request.POST:
            nuevo_DNI = request.POST.get("dni")
            nuevo_nombre = request.POST.get("nombre")
            DNI_original = request.POST.get("dni")

            if nuevo_DNI and nuevo_nombre and DNI_original:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE datos_personales
                           SET dni = %s, nombre = %s
                           WHERE dni = %s""",
                        [nuevo_DNI, nuevo_nombre, DNI_original]
                    )
                messages.success(request, "Alumno actualizado correctamente.")
                return redirect('alumnos')
            else:
                messages.error(request, "Faltan campos obligatorios.")

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT dni, nombre FROM datos_personales WHERE dni = %s",
                        [dni]
                    )
                    alumno = cursor.fetchone()

                if not alumno:
                    messages.warning(request, "No se encontró ningún alumno con ese DNI.")

    except Exception as e:
        messages.error(request, f"Error en la base de datos: {str(e)}")

    contexto = {
        "form_buscar": form_buscar,
        "alumno": {"dni": alumno[0], "nombre": alumno[1]} if alumno else None
    }

    return render(request, "myapp/modificar_alumno.html", contexto)

def profesores(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT dni, nombre, apellidos,titulacion,tipo FROM profesor")
        columnas = [col[0] for col in cursor.description]
        profesores = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

    return render(request, "myapp/profesores.html", {
        "profesores": profesores,
        "active_tab": "profesores",
    })


def nuevo_profesor(request):
    guardado = False

    if request.method == "POST":
        form = ProfesorForm(request.POST)

        if form.is_valid():
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO profesor (dni, nombre, apellidos, domicilio, nivel_estudios, titulacion, tipo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        [form.cleaned_data["dni"], form.cleaned_data["nombre"], form.cleaned_data["apellidos"],form.cleaned_data["domicilio"],form.cleaned_data["nivel_estudios"],form.cleaned_data["titulacion"],form.cleaned_data["tipo"]]
                )
            guardado = True
            form = ProfesorForm()

    else:
        form = ProfesorForm()

    return render(request, "myapp/nuevo_profesor.html", {
        "form": form,
        "guardado": guardado,
        "active_tab": "profesores",
    })

def modificar_profesor(request):
    profesor = None
    form_buscar = ProfesorForm(request.GET or None)

    try:
        if request.method == "POST" and "guardar" in request.POST:
            nuevo_DNI = request.POST.get("dni")
            nuevo_nombre = request.POST.get("nombre")
            DNI_original = request.POST.get("dni")

            if nuevo_DNI and nuevo_nombre and DNI_original:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE profesor
                           SET dni = %s, nombre = %s
                           WHERE dni = %s""",
                        [nuevo_DNI, nuevo_nombre, DNI_original]
                    )
                messages.success(request, "Profesor actualizado correctamente.")
                redirect('profesores')
            else:
                messages.error(request, "Faltan campos obligatorios.")

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT dni, nombre FROM datos_personales WHERE dni = %s",
                        [dni]
                    )
                    profesor = cursor.fetchone()

                if not profesor:
                    messages.warning(request, "No se encontró ningún profesor con ese DNI.")

    except Exception as e:
        messages.error(request, f"Error en la base de datos: {str(e)}")

    contexto = {
        "form_buscar": form_buscar,
        "profesor": {"dni": profesor[0], "nombre": profesor[1]} if profesor else None
    }

    return render(request, "myapp/modificar_profesor.html", contexto)