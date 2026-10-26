from django.db import IntegrityError, connection
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password, make_password
from .forms import *
from functools import wraps

from . import datos_candidatos as datos
from . import datos_comite as comites
from .datos_candidatos import SinComiteError

def requerir_rol(*roles_permitidos):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            nivel = request.session.get('nivel')
            if nivel is None:
                messages.warning(request, "Iniciá sesión.")
                return redirect("login")
            if nivel not in roles_permitidos:
                messages.warning(request, "No tenés permisos para esta página.")
                return redirect("inicio")
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            dni = form.cleaned_data["dni"]
            password = form.cleaned_data["password"]

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT dni, nombre, password FROM usuario WHERE dni = %s",
                    [dni]
                )
                usuario = cursor.fetchone()

            if usuario and check_password(password, usuario[2]):
                request.session["usuario_dni"] = usuario[0]
                request.session["usuario_nombre"] = usuario[1]
                messages.success(request, f"Bienvenido, {usuario[1]}.")
                return redirect("index")
            else:
                messages.error(request, "DNI o contraseña incorrectos.")
    else:
        form = LoginForm()

    return render(request, "myapp/login.html", {
        "form": form,
    })


def logout_view(request):
    if "usuario_dni" in request.session:
        del request.session["usuario_dni"]
        del request.session["usuario_nombre"]
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("login")


def nuevo_usuario(request):
    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            dni = form.cleaned_data["dni"]
            nombre = request.POST.get("nombre", "").strip()
            password = form.cleaned_data["password"]

            if not nombre:
                messages.error(request, "Falta el nombre del usuario.")
            else:
                with connection.cursor() as cursor:
                    try:
                        cursor.execute(
                            """INSERT INTO usuario (dni, nombre, password)
                            VALUES (%s, %s, %s)""",
                            [dni, nombre, make_password(password)]
                        )
                        messages.success(request, f"Usuario {dni} creado correctamente.")
                        return redirect("index")
                    except Exception as e:
                        messages.error(request, f"No se pudo crear el usuario: {str(e)}")
    else:
        form = LoginForm()

    return render(request, "myapp/nuevo_usuario.html", {
        "form": form,
    })


def index(request):
    return render(request, "myapp/index.html", {
        "active_tab": "index"
    })


def candidatos(request):
    form = BuscarCandidatoForm(request.GET or None)
    q = tipo_deseado = ""

    if form.is_valid():
        q = form.cleaned_data.get("q") or ""
        tipo_deseado = form.cleaned_data.get("tipo_deseado") or ""

    return render(request, "myapp/candidatos.html", {
        "candidatos": datos.listar_candidatos(q, tipo_deseado),
        "form_buscar": form,
        "active_tab": "candidatos",
    })

@requerir_rol('ADMIN')
def nuevo_candidato(request):
    guardado = False

    if request.method == "POST":
        form = CandidatoForm(request.POST)

        if form.is_valid():
            datos.crear_candidato(**form.cleaned_data)
            guardado = True
            form = CandidatoForm()

    else:
        form = CandidatoForm()

    return render(request, "myapp/nuevo_candidato.html", {
        "form": form,
        "guardado": guardado,
        "active_tab": "candidatos",
    })

@requerir_rol('ADMIN')
def editar_candidato(request, pk):
    candidato = datos.obtener_candidato(pk)
    if not candidato:
        raise Http404("Candidato no encontrado")

    if request.method == "POST":
        form = CandidatoForm(request.POST)
        if form.is_valid():
            datos.actualizar_candidato(pk, **form.cleaned_data)
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
    candidato = datos.obtener_candidato(pk)
    if not candidato:
        raise Http404("Candidato no encontrado")

    form_llamada = LlamadaForm()

    if request.method == "POST" and request.POST.get("accion") == "llamada":
        form_llamada = LlamadaForm(request.POST)
        if form_llamada.is_valid():
            datos.registrar_llamada(
                candidato.id,
                form_llamada.cleaned_data["fecha_hora"],
                form_llamada.cleaned_data["disposicion"],
            )
            messages.success(request, "Llamada registrada correctamente.")
            return redirect('detalle_candidato', pk=pk)

    elif request.method == "POST" and request.POST.get("accion") == "entrevista":
        llamada = datos.obtener_llamada(request.POST.get("llamada_id"), candidato.id)
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
        elif datos.entrevista_de_llamada(llamada.id) is not None:
            # La columna id_llamada de entrevista NO tiene UNIQUE en la base,
            # así que esta regla la tiene que cumplir la aplicación.
            messages.error(request, "Esa llamada ya tiene una entrevista cargada.")
        elif form_entrevista.is_valid():
            try:
                datos.registrar_entrevista(
                    candidato.id,
                    llamada.id,
                    form_entrevista.cleaned_data["fecha"],
                    int(form_entrevista.cleaned_data["materia_a_cubrir"]),
                    form_entrevista.cleaned_data["valoracion"],
                )
            except SinComiteError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Entrevista registrada correctamente.")
        else:
            messages.error(request, "No se pudo guardar la entrevista: revisá los datos.")
        return redirect('detalle_candidato', pk=pk)

    disposicion_labels = dict(DISPOSICION_CHOICES)

    # El template dibuja el color del sello comparando la disposición en
    # minúsculas ('concertada', 'no_interesado'), así que lo que se le pasa
    # es el valor del formulario, no el ENUM de la base.
    llamadas = []
    for llamada in datos.listar_llamadas(candidato.id):
        entrevista = datos.entrevista_de_llamada(llamada.id)
        item = {
            "pk": llamada.id,
            "fecha_hora": llamada.fecha_hora,
            "disposicion": llamada.disposicion,
            "get_disposicion_display": disposicion_labels.get(
                llamada.disposicion, llamada.disposicion
            ),
        }
        if entrevista is not None:
            item["entrevista"] = {
                "fecha": entrevista.fecha,
                "materia_a_cubrir": entrevista.asignatura_nombre,
                "valoracion": entrevista.valoracion,
            }
        elif llamada.disposicion == "concertada":
            # Solo una llamada concertada y sin entrevista habilita el
            # formulario de carga.
            item["form_entrevista"] = EntrevistaForm()
        llamadas.append(item)

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
            try:
                comites.crear_comite(
                    form.cleaned_data["anio"],
                    int(form.cleaned_data["id_presidente"]),
                    int(form.cleaned_data["id_secretario"]),
                    int(form.cleaned_data["id_vocal"]),
                )
            except IntegrityError:
                # comite.anio es UNIQUE: solo puede haber un acta por año.
                # Es el único IntegrityError alcanzable acá: los tres ids de
                # profesor ya los validó el ChoiceField contra la base.
                #
                # Va como error del form y no como messages.error porque
                # comite.html no imprime el bloque de messages (base.html
                # tampoco lo trae): solo pinta non_field_errors.
                form.add_error(None, "Ya existe un comité cargado para ese año.")
            else:
                guardado = True
                # Limpiamos el formulario después de guardar.
                form = ComiteForm()

    else:
        form = ComiteForm()

    return render(request, "myapp/comite.html", {
        "form": form,
        "guardado": guardado,
        # listar_comites() ya viene ordenado del más reciente al más
        # antiguo y con los tres roles resueltos a su profesor.
        "comites": comites.listar_comites(),
        "profesores": comites.listar_profesores(),
        "active_tab": "comite",
    })

@requerir_rol('ADMIN')
def nuevo_comite(request):
    """
    Esta vista ya no es necesaria para el funcionamiento del alta,
    porque el formulario está integrado en comite.html.

    Se mantiene para evitar romper la URL /comite/nuevo/
    si todavía existe en urls.py.
    """
    return comite(request)



def alumnos(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT dni, nombre, apellidos, id_grupo FROM alumno")
            columnas = [col[0] for col in cursor.description]
            alumnos = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

        return render(request, "myapp/alumnos.html", {
            "alumnos": alumnos,
            "active_tab": "alumnos",
        })
    except Exception as e:
        messages.error(request, f"Error al cargar alumnos: {str(e)}")

    return render(request, "myapp/alumnos.html", {
        "alumnos": [],
        "active_tab": "alumnos",
    })

@requerir_rol('ADMIN')
def nuevo_alumno(request):
    guardado = False

    if request.method == "POST":
        form = AlumnoForm(request.POST)

        if form.is_valid():
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO alumno (dni, nombre, apellidos,id_grupo)
                    VALUES (%s, %s, %s,%s)""",
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

@requerir_rol('ADMIN')
def modificar_alumno(request):
    alumno = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "guardar" in request.POST:
            nuevo_DNI = request.POST.get("dni")
            nuevo_nombre = request.POST.get("nombre")
            DNI_original = request.POST.get("dni_original")

            if nuevo_DNI and nuevo_nombre and DNI_original:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE alumno
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
                        "SELECT dni, nombre FROM alumno WHERE dni = %s",
                        [dni]
                    )
                    alumno = cursor.fetchone()

                if not alumno:
                    messages.warning(request, "No se encontró ningún alumno con ese DNI.")

    except Exception as e:
        messages.error(request, f"Error en la base de datos: {str(e)}")

    contexto = {
        "form_buscar": form_buscar,
        "alumno": {"dni": alumno[0], "nombre": alumno[1]} if alumno else None,
        "active_tab": "modificar_alumno",
    }

    return render(request, "myapp/modificar_alumno.html", contexto)

@requerir_rol('ADMIN')
def eliminar_alumno(request):
    alumno = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "eliminar" in request.POST:
            dni = request.POST.get("dni")
            if dni:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM alumno WHERE dni = %s", [dni])
                messages.success(request, "Alumno eliminado correctamente.")
                return redirect('alumnos')
            else:
                messages.error(request, "Falta el DNI.")

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                with connection.cursor() as cursor:
                    cursor.execute("SELECT dni, nombre FROM alumno WHERE dni = %s", [dni])
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
    try:
        lista = comites.listar_profesores()
    except Exception as e:
        messages.error(request, f"Error al cargar profesores: {str(e)}")
        lista = []

    return render(request, "myapp/profesores.html", {
        "profesores": lista,
        "active_tab": "profesores",
    })

@requerir_rol('ADMIN')
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
        "active_tab": "nuevo_profesor",
    })

@requerir_rol('ADMIN')
def modificar_profesor(request):
    profesor = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "guardar" in request.POST:
            nuevo_DNI = request.POST.get("dni")
            nuevo_nombre = request.POST.get("nombre")
            DNI_original = request.POST.get("dni_original")

            if nuevo_DNI and nuevo_nombre and DNI_original:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE profesor
                           SET dni = %s, nombre = %s
                           WHERE dni = %s""",
                        [nuevo_DNI, nuevo_nombre, DNI_original]
                    )
                messages.success(request, "Profesor actualizado correctamente.")
                return redirect('profesores')
            else:
                messages.error(request, "Faltan campos obligatorios.")

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT dni, nombre FROM profesor WHERE dni = %s",
                        [dni]
                    )
                    profesor = cursor.fetchone()

                if not profesor:
                    messages.warning(request, "No se encontró ningún profesor con ese DNI.")

    except Exception as e:
        messages.error(request, f"Error en la base de datos: {str(e)}")

    contexto = {
        "form_buscar": form_buscar,
        "profesor": {"dni": profesor[0], "nombre": profesor[1]} if profesor else None,
        "active_tab": "modificar_profesor",
    }

    return render(request, "myapp/modificar_profesor.html", contexto)

@requerir_rol('ADMIN')
def eliminar_profesor(request):
    profesor = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "eliminar" in request.POST:
            dni = request.POST.get("dni")
            if dni:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM profesor WHERE dni = %s", [dni])
                messages.success(request, "Profesor eliminado correctamente.")
                return redirect('profesores')
            else:
                messages.error(request, "Falta el DNI.")

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                with connection.cursor() as cursor:
                    cursor.execute("SELECT dni, nombre FROM profesor WHERE dni = %s", [dni])
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
