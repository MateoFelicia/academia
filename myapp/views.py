from django.db import IntegrityError, connection
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password, make_password
from .forms import *
from functools import wraps
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from .permisos import requiere_permiso, requiere_login, permiso, normalizar_rol, ROLES_EDITABLES

from . import datos_candidatos as datos
from . import datos_comite as comites
from .datos_candidatos import SinComiteError

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            dni = form.cleaned_data["dni"]
            password = form.cleaned_data["password"]

            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT u.username, u.password_hash, u.nivel,
                              COALESCE(a.dni, p.dni, u.username),
                              COALESCE(a.nombre, p.nombre, u.username)
                       FROM usuarios u
                       LEFT JOIN alumno a ON a.id = u.id_alumno
                       LEFT JOIN profesor p ON p.id = u.id_profesor
                       WHERE u.username = %s AND u.activo = 1""",
                    [dni]
                )
                usuario = cursor.fetchone()

            if usuario and check_password(password, usuario[1]):
                request.session["usuario_dni"] = usuario[3]
                request.session["usuario_nombre"] = usuario[4]
                request.session["nivel"] = normalizar_rol(usuario[2])
                messages.success(request, f"Bienvenido, {usuario[4]}.")
                return redirect("index")
            else:
                messages.error(request, "DNI o contraseña incorrectos.")
    else:
        form = LoginForm()

    return render(request, "myapp/login.html", {
        "form": form,
    })


@requiere_login
def logout_view(request):
    if "usuario_dni" in request.session:
        del request.session["usuario_dni"]
        del request.session["usuario_nombre"]
        request.session.pop("nivel", None)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect("login")


@requiere_permiso('usuario', 'crear')
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
                            """INSERT INTO usuarios (username, password_hash, nivel)
                            VALUES (%s, %s, %s)""",
                            [dni, make_password(password), "ALUMNO"]
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


@requiere_login
def index(request):
    resumen = {}
    rol = normalizar_rol(request.session.get("nivel"))
    dni = request.session.get("usuario_dni")
    if rol == "ALUMNO":
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM alumno WHERE dni = %s", [dni])
            alumno = cursor.fetchone()
            if alumno:
                cursor.execute("SELECT COUNT(*) FROM ficha_individual WHERE id_alumno = %s", [alumno[0]])
                resumen["fichas"] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM registro_asistencia ra JOIN ficha_individual fi ON fi.id = ra.id_ficha WHERE fi.id_alumno = %s", [alumno[0]])
                resumen["registros_asistencia"] = cursor.fetchone()[0]
    elif rol == "PROFESOR":
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM hoja_actividad ha JOIN profesor p ON p.id = ha.id_profesor WHERE p.dni = %s", [dni])
            resumen["actividades"] = cursor.fetchone()[0]
    return render(request, "myapp/index.html", {"active_tab": "index", "resumen": resumen, "rol": rol})

@requiere_permiso('candidato', 'ver')
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
        "puede_crear": permiso(request.session.get("nivel"), "candidato", "crear") is not None,
        "puede_editar": permiso(request.session.get("nivel"), "candidato", "editar") is not None,
    })

@requiere_permiso('candidato', 'crear')
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

@requiere_permiso('candidato', 'editar')
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

@requiere_permiso('candidato', 'ver')
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

@requiere_permiso('comite', 'ver')
def comite(request):
    """
    Lista los comités existentes y permite agregar uno nuevo
    desde la misma página.
    """
    guardado = False

    if request.method == "POST" and permiso(request.session.get("nivel"), "comite", "crear") is None:
        messages.warning(request, "No tenés permisos para esta página")
        return redirect("index")
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

@requiere_permiso('comite', 'crear')
def nuevo_comite(request):
    """
    Esta vista ya no es necesaria para el funcionamiento del alta,
    porque el formulario está integrado en comite.html.

    Se mantiene para evitar romper la URL /comite/nuevo/
    si todavía existe en urls.py.
    """
    return comite(request)

@requiere_permiso('alumno', 'ver')
def alumnos(request):
    try:
        with connection.cursor() as cursor:
            if request.alcance == "propio":
                cursor.execute("SELECT dni, nombre, apellidos, id_grupo FROM alumno WHERE dni = %s", [request.session.get("usuario_dni")])
            else:
                cursor.execute("SELECT dni, nombre, apellidos, id_grupo FROM alumno")
            columnas = [col[0] for col in cursor.description]
            alumnos = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

        return render(request, "myapp/alumnos.html", {
            "alumnos": alumnos,
            "active_tab": "alumnos",
            "puede_crear": permiso(request.session.get("nivel"), "alumno", "crear") is not None,
            "puede_editar": permiso(request.session.get("nivel"), "alumno", "editar") is not None,
            "puede_eliminar": permiso(request.session.get("nivel"), "alumno", "eliminar") is not None,
        })
    except Exception as e:
        messages.error(request, f"Error al cargar alumnos: {str(e)}")

    return render(request, "myapp/alumnos.html", {
        "alumnos": [],
        "active_tab": "alumnos",
        "puede_crear": permiso(request.session.get("nivel"), "alumno", "crear") is not None,
        "puede_editar": permiso(request.session.get("nivel"), "alumno", "editar") is not None,
        "puede_eliminar": permiso(request.session.get("nivel"), "alumno", "eliminar") is not None,
    })

@requiere_permiso('alumno', 'crear')
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

@requiere_permiso('alumno', 'editar')
def modificar_alumno(request):
    alumno = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "guardar" in request.POST:
            nuevo_DNI = request.POST.get("dni")
            nuevo_nombre = request.POST.get("nombre")
            DNI_original = request.POST.get("dni_original")
            if request.alcance == "propio" and DNI_original != request.session.get("usuario_dni"):
                raise Http404("Alumno no encontrado")

            if nuevo_DNI and nuevo_nombre and DNI_original:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE alumno
                           SET dni = %s, nombre = %s
                           WHERE dni = %s AND (%s = 'todos' OR dni = %s)""",
                        [nuevo_DNI, nuevo_nombre, DNI_original, request.alcance, request.session.get("usuario_dni")]
                    )
                messages.success(request, "Alumno actualizado correctamente.")
                return redirect('alumnos')
            else:
                messages.error(request, "Faltan campos obligatorios.")

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                if request.alcance == "propio" and dni != request.session.get("usuario_dni"):
                    raise Http404("Alumno no encontrado")
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

@requiere_permiso('alumno', 'eliminar')
def eliminar_alumno(request):
    alumno = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "eliminar" in request.POST:
            dni = request.POST.get("dni")
            if request.alcance == "propio" and dni != request.session.get("usuario_dni"):
                raise Http404("Alumno no encontrado")
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
                if request.alcance == "propio" and dni != request.session.get("usuario_dni"):
                    raise Http404("Alumno no encontrado")
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

@requiere_permiso('profesor', 'ver')
def profesores(request):
    try:
        lista = comites.listar_profesores()
        if request.alcance == "propio":
            lista = [p for p in lista if p.dni == request.session.get("usuario_dni")]
    except Exception as e:
        messages.error(request, f"Error al cargar profesores: {str(e)}")
        lista = []

    return render(request, "myapp/profesores.html", {
        "profesores": lista,
        "active_tab": "profesores",
        "puede_crear": permiso(request.session.get("nivel"), "profesor", "crear") is not None,
        "puede_editar": permiso(request.session.get("nivel"), "profesor", "editar") is not None,
        "puede_eliminar": permiso(request.session.get("nivel"), "profesor", "eliminar") is not None,
    })

@requiere_permiso('profesor', 'crear')
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

@requiere_permiso('profesor', 'editar')
def modificar_profesor(request):
    profesor = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "guardar" in request.POST:
            nuevo_DNI = request.POST.get("dni")
            nuevo_nombre = request.POST.get("nombre")
            DNI_original = request.POST.get("dni_original")
            if request.alcance == "propio" and DNI_original != request.session.get("usuario_dni"):
                raise Http404("Profesor no encontrado")

            if nuevo_DNI and nuevo_nombre and DNI_original:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """UPDATE profesor
                           SET dni = %s, nombre = %s
                           WHERE dni = %s AND (%s = 'todos' OR dni = %s)""",
                        [nuevo_DNI, nuevo_nombre, DNI_original, request.alcance, request.session.get("usuario_dni")]
                    )
                messages.success(request, "Profesor actualizado correctamente.")
                return redirect('profesores')
            else:
                messages.error(request, "Faltan campos obligatorios.")

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                if request.alcance == "propio" and dni != request.session.get("usuario_dni"):
                    raise Http404("Profesor no encontrado")
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

@requiere_permiso('profesor', 'eliminar')
def eliminar_profesor(request):
    profesor = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "eliminar" in request.POST:
            dni = request.POST.get("dni")
            if request.alcance == "propio" and dni != request.session.get("usuario_dni"):
                raise Http404("Profesor no encontrado")
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
                if request.alcance == "propio" and dni != request.session.get("usuario_dni"):
                    raise Http404("Profesor no encontrado")
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


def set_role(request):
    return redirect("index")


def _solo_admin(request):
    if not request.session.get("usuario_dni"):
        messages.warning(request, "Iniciá sesión.")
        return redirect("login")
    if normalizar_rol(request.session.get("nivel")) != "ADMIN":
        messages.warning(request, "No tenés permisos para esta página")
        return redirect("index")
    return None


@requiere_permiso("panel_permisos", "ver")
def panel_permisos(request):
    from .forms import PermisosForm
    from .permisos import RECURSOS, ACCIONES
    denegado = _solo_admin(request)
    if denegado:
        return denegado
    with connection.cursor() as cursor:
        cursor.execute("SELECT rol, recurso, accion, alcance FROM permisos WHERE rol IN (%s, %s, %s)", list(ROLES_EDITABLES))
        actual = {(r, rec, acc): alc for r, rec, acc, alc in cursor.fetchall()}
    initial = {f"{r}_{rec}_{acc}": actual.get((r, rec, acc), "") for r in ROLES_EDITABLES for rec in RECURSOS for acc in ACCIONES}
    form = PermisosForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            with connection.cursor() as cursor:
                for rol in ROLES_EDITABLES:
                    for recurso in RECURSOS:
                        for accion in ACCIONES:
                            nuevo = form.cleaned_data[f"{rol}_{recurso}_{accion}"] or None
                            anterior = actual.get((rol, recurso, accion))
                            if nuevo == anterior:
                                continue
                            if nuevo is None:
                                cursor.execute("DELETE FROM permisos WHERE rol = %s AND recurso = %s AND accion = %s", [rol, recurso, accion])
                            elif anterior is None:
                                cursor.execute("INSERT INTO permisos (rol, recurso, accion, alcance) VALUES (%s, %s, %s, %s)", [rol, recurso, accion, nuevo])
                            else:
                                cursor.execute("UPDATE permisos SET alcance = %s WHERE rol = %s AND recurso = %s AND accion = %s", [nuevo, rol, recurso, accion])
                            cursor.execute("INSERT INTO permisos_log (fecha, admin_dni, admin_nombre, rol, recurso, accion, valor_anterior, valor_nuevo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", [timezone.now(), request.session.get("usuario_dni"), request.session.get("usuario_nombre", ""), rol, recurso, accion, anterior, nuevo])
        messages.success(request, "Permisos actualizados.")
        return redirect("panel_permisos")
    filas = [{"recurso": r, "accion": a, "celdas": [form[f"{rol}_{r}_{a}"] for rol in ROLES_EDITABLES]} for r in RECURSOS for a in ACCIONES]
    return render(request, "myapp/panel_permisos.html", {"form": form, "filas": filas, "roles": ROLES_EDITABLES, "active_tab": "panel_permisos"})


@requiere_permiso("panel_permisos", "ver")
def permisos_log(request):
    denegado = _solo_admin(request)
    if denegado:
        return denegado
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, fecha, admin_dni, admin_nombre, rol, recurso, accion, valor_anterior, valor_nuevo FROM permisos_log ORDER BY fecha DESC, id DESC")
        registros = [dict(zip([col[0] for col in cursor.description], fila)) for fila in cursor.fetchall()]
    pagina = Paginator(registros, 25).get_page(request.GET.get("page"))
    return render(request, "myapp/permisos_log.html", {"pagina": pagina, "active_tab": "permisos_log"})
