from django.db import connection
from django.contrib import messages
from django.http import Http404
from itertools import count
from django.shortcuts import render, redirect

from .mock_comite import (
    ComiteMock,
    COMITES_MOCK,
    comite_detallado_mock,
    listar_comites_mock,
    listar_profesores_mock,
)
from .mock_candidatos import (
    CandidatoMock,
    LlamadaMock,
    EntrevistaMock,
    CANDIDATOS_MOCK,
    LLAMADAS_MOCK,
    ENTREVISTAS_MOCK,
    listar_candidatos_mock,
    obtener_candidato_mock,
    obtener_materia_mock,
    obtener_llamada_mock,
    entrevista_de_llamada_mock,
)
from .forms import *


_id_comites = count(len(COMITES_MOCK) + 1)
_id_candidatos = count(len(CANDIDATOS_MOCK) + 1)
_id_llamadas = count(len(LLAMADAS_MOCK) + 1)
_id_entrevistas = count(len(ENTREVISTAS_MOCK) + 1)


def index(request):
    return render(request, "myapp/index.html", {
        "active_tab": "index"
    })


def candidatos(request):
    form = BuscarCandidatoForm(request.GET or None)
    lista = listar_candidatos_mock()

    if form.is_valid():
        q = form.cleaned_data.get("q")
        tipo_deseado = form.cleaned_data.get("tipo_deseado")

        if q:
            q = q.lower()
            lista = [
                c for c in lista
                if q in c.nombre.lower() or q in c.apellidos.lower() or q in c.dni.lower()
            ]
        if tipo_deseado:
            lista = [c for c in lista if c.tipo_deseado == tipo_deseado]

    lista = sorted(lista, key=lambda c: (c.apellidos, c.nombre))

    return render(request, "myapp/candidatos.html", {
        "candidatos": lista,
        "form_buscar": form,
        "active_tab": "candidatos",
    })


def nuevo_candidato(request):
    guardado = False

    if request.method == "POST":
        form = CandidatoForm(request.POST)

        if form.is_valid():
            nuevo = CandidatoMock(
                id=next(_id_candidatos),
                dni=form.cleaned_data["dni"],
                nombre=form.cleaned_data["nombre"],
                apellidos=form.cleaned_data["apellidos"],
                curriculum=form.cleaned_data["curriculum"],
                tipo_deseado=form.cleaned_data["tipo_deseado"],
                materias=[int(m) for m in form.cleaned_data["materias"]],
            )
            CANDIDATOS_MOCK.append(nuevo)
            guardado = True
            form = CandidatoForm()

    else:
        form = CandidatoForm()

    return render(request, "myapp/nuevo_candidato.html", {
        "form": form,
        "guardado": guardado,
        "active_tab": "candidatos",
    })


def editar_candidato(request, pk):
    candidato = obtener_candidato_mock(pk)
    if not candidato:
        raise Http404("Candidato no encontrado")

    if request.method == "POST":
        form = CandidatoForm(request.POST)
        if form.is_valid():
            candidato.dni = form.cleaned_data["dni"]
            candidato.nombre = form.cleaned_data["nombre"]
            candidato.apellidos = form.cleaned_data["apellidos"]
            candidato.curriculum = form.cleaned_data["curriculum"]
            candidato.tipo_deseado = form.cleaned_data["tipo_deseado"]
            candidato.materias = [int(m) for m in form.cleaned_data["materias"]]
            messages.success(request, "Candidato actualizado correctamente.")
            return redirect('candidatos')
    else:
        form = CandidatoForm(initial={
            "dni": candidato.dni,
            "nombre": candidato.nombre,
            "apellidos": candidato.apellidos,
            "curriculum": candidato.curriculum,
            "tipo_deseado": candidato.tipo_deseado,
            "materias": [str(m) for m in candidato.materias],
        })

    return render(request, "myapp/editar_candidato.html", {
        "form": form,
        "candidato": candidato,
        "active_tab": "candidatos",
    })


def detalle_candidato(request, pk):
    candidato = obtener_candidato_mock(pk)
    if not candidato:
        raise Http404("Candidato no encontrado")

    form_llamada = LlamadaForm()

    if request.method == "POST" and request.POST.get("accion") == "llamada":
        form_llamada = LlamadaForm(request.POST)
        if form_llamada.is_valid():
            nueva_llamada = LlamadaMock(
                id=next(_id_llamadas),
                candidato_id=candidato.id,
                fecha_hora=form_llamada.cleaned_data["fecha_hora"],
                disposicion=form_llamada.cleaned_data["disposicion"],
            )
            LLAMADAS_MOCK.append(nueva_llamada)
            messages.success(request, "Llamada registrada correctamente.")
            return redirect('detalle_candidato', pk=pk)

    elif request.method == "POST" and request.POST.get("accion") == "entrevista":
        llamada = obtener_llamada_mock(request.POST.get("llamada_id"), candidato.id)
        if not llamada:
            raise Http404("Llamada no encontrada")

        form_entrevista = EntrevistaForm(request.POST)

        # Regla que antes vivía en Entrevista.clean(): solo se puede
        # cargar una entrevista si la llamada quedó "concertada".
        if llamada.disposicion != "concertada":
            messages.error(
                request,
                "Solo se puede cargar una entrevista si la llamada fue 'Entrevista concertada'."
            )
        elif entrevista_de_llamada_mock(llamada.id) is not None:
            # Equivalente al UNIQUE que tenía la columna llamada_id en la base.
            messages.error(request, "Esa llamada ya tiene una entrevista cargada.")
        elif form_entrevista.is_valid():
            nueva_entrevista = EntrevistaMock(
                id=next(_id_entrevistas),
                llamada_id=llamada.id,
                fecha=form_entrevista.cleaned_data["fecha"],
                materia_a_cubrir_id=int(form_entrevista.cleaned_data["materia_a_cubrir"]),
                valoracion=form_entrevista.cleaned_data["valoracion"],
            )
            ENTREVISTAS_MOCK.append(nueva_entrevista)
            messages.success(request, "Entrevista registrada correctamente.")
        else:
            messages.error(request, "No se pudo guardar la entrevista: revisá los datos.")
        return redirect('detalle_candidato', pk=pk)

    disposicion_labels = dict(DISPOSICION_CHOICES)
    llamadas_candidato = sorted(
        (l for l in LLAMADAS_MOCK if l.candidato_id == candidato.id),
        key=lambda l: l.fecha_hora,
        reverse=True,
    )

    llamadas = []
    for l in llamadas_candidato:
        entrevista = entrevista_de_llamada_mock(l.id)
        llamada = {
            "id": l.id,
            "pk": l.id,
            "fecha_hora": l.fecha_hora,
            "disposicion": l.disposicion,
            "disposicion_display": disposicion_labels.get(l.disposicion, l.disposicion),
            "get_disposicion_display": disposicion_labels.get(l.disposicion, l.disposicion),
        }
        if entrevista is not None:
            materia = obtener_materia_mock(entrevista.materia_a_cubrir_id)
            llamada["entrevista"] = {
                "fecha": entrevista.fecha,
                "materia_a_cubrir": materia.nombre if materia else entrevista.materia_a_cubrir_id,
                "valoracion": entrevista.valoracion,
            }
        elif l.disposicion == "concertada":
            # Equivalente a la property puede_cargar_entrevista de antes.
            llamada["form_entrevista"] = EntrevistaForm()
        llamadas.append(llamada)

    return render(request, "myapp/detalle_candidato.html", {
        "candidato": candidato,
        "llamadas": llamadas,
        "form_llamada": form_llamada,
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

def eliminar_alumno(request):
    alumno = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "eliminar" in request.POST:
            dni = request.POST.get("dni")
            if dni:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM datos_personales WHERE dni = %s", [dni])
                messages.success(request, "Alumno eliminado correctamente.")
                return redirect('alumnos')
            else:
                messages.error(request, "Falta el DNI.")

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                with connection.cursor() as cursor:
                    cursor.execute("SELECT dni, nombre FROM datos_personales WHERE dni = %s", [dni])
                    alumno = cursor.fetchone()
                if not alumno:
                    messages.warning(request, "No se encontró ningún alumno con ese DNI.")

    except Exception as e:
        messages.error(request, f"Error en la base de datos: {str(e)}")

    return render(request, "myapp/eliminar_alumno.html", {
        "form_buscar": form_buscar,
        "alumno": {"dni": alumno[0], "nombre": alumno[1]} if alumno else None,
        "active_tab": "alumnos",
    })

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

def eliminar_profesor(request):
    profesor = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "eliminar" in request.POST:
            dni = request.POST.get("dni")
            if dni:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM datos_personales WHERE dni = %s", [dni])
                messages.success(request, "Profesor eliminado correctamente.")
                return redirect('profesores')
            else:
                messages.error(request, "Falta el DNI.")

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                with connection.cursor() as cursor:
                    cursor.execute("SELECT dni, nombre FROM datos_personales WHERE dni = %s", [dni])
                    profesor = cursor.fetchone()
                if not profesor:
                    messages.warning(request, "No se encontró ningún profesor con ese DNI.")

    except Exception as e:
        messages.error(request, f"Error en la base de datos: {str(e)}")

    return render(request, "myapp/eliminar_profesor.html", {
        "form_buscar": form_buscar,
        "profesor": {"dni": profesor[0], "nombre": profesor[1]} if profesor else None,
        "active_tab": "profesores",
    })
