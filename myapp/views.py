from django.db import DatabaseError, IntegrityError, connection
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password, make_password
from .forms import *
from functools import wraps
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from datetime import date
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


def index(request):
    resumen = {}
    rol = normalizar_rol(request.session.get("nivel"))
    dni = request.session.get("usuario_dni")
    publico = not bool(dni)
    if rol == "ALUMNO" and not publico:
        resumen.update({"registro_alumno": False, "materias": [], "aprobadas": 0, "desaprobadas": 0, "faltas": 0, "semanas_informadas": 0, "datos_academicos_disponibles": False})
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM alumno WHERE dni = %s", [dni])
            alumno = cursor.fetchone()
            if alumno:
                resumen["registro_alumno"] = True
                resumen.update({"materias": [], "aprobadas": 0, "desaprobadas": 0, "faltas": 0, "semanas_informadas": 0, "datos_academicos_disponibles": False})
                try:
                    cursor.execute(
                        """SELECT asi.nombre, AVG(cal.nota)
                           FROM calificacion cal
                           JOIN asignatura asi ON asi.id = cal.id_asignatura
                           WHERE cal.id_alumno = %s
                           GROUP BY asi.id, asi.nombre
                           ORDER BY asi.nombre""",
                        [alumno[0]],
                    )
                    materias = [{"nombre": nombre, "promedio": promedio} for nombre, promedio in cursor.fetchall()]
                    cursor.execute(
                        """SELECT COALESCE(SUM(cuartos_falta), 0), COUNT(*)
                           FROM faltas_semanales WHERE id_alumno = %s""",
                        [alumno[0]],
                    )
                    cuartos_falta, semanas_informadas = cursor.fetchone()
                    resumen.update({
                        "materias": materias,
                        "aprobadas": sum(1 for materia in materias if materia["promedio"] >= 7),
                        "desaprobadas": sum(1 for materia in materias if materia["promedio"] < 7),
                        "faltas": cuartos_falta / 4,
                        "semanas_informadas": semanas_informadas,
                        "datos_academicos_disponibles": True,
                    })
                except DatabaseError:
                    messages.info(request, "El resumen de notas y faltas estará disponible después de ejecutar migracion_academico.sql.")
                cursor.execute("SELECT COUNT(*) FROM ficha_individual WHERE id_alumno = %s", [alumno[0]])
                resumen["fichas"] = cursor.fetchone()[0]
    elif rol == "PROFESOR" and not publico:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM hoja_actividad ha JOIN profesor p ON p.id = ha.id_profesor WHERE p.dni = %s", [dni])
            resumen["actividades"] = cursor.fetchone()[0]
    return render(request, "myapp/index.html", {
        "active_tab": "index",
        "resumen": resumen,
        "rol": rol,
        "publico": publico,
        "rol_asumido": request.session.get("rol_asumido", False),
        "roles_disponibles": ["ADMIN", "COMITE", "PROFESOR", "ALUMNO"],
    })

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
        "puede_eliminar": permiso(request.session.get("nivel"), "candidato", "eliminar") is not None,
    })

@requiere_permiso('candidato', 'crear')
def nuevo_candidato(request):
    guardado = False

    if request.method == "POST":
        form = CandidatoForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    datos.crear_candidato(**form.cleaned_data)
            except IntegrityError:
                form.add_error("dni", "Ya existe un candidato con ese DNI o alguna materia dejó de estar disponible.")
            else:
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
            try:
                with transaction.atomic():
                    datos.actualizar_candidato(pk, **form.cleaned_data)
            except IntegrityError:
                form.add_error("dni", "Ese DNI ya pertenece a otro candidato o alguna materia dejó de estar disponible.")
            else:
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


@requiere_permiso('candidato', 'eliminar')
def eliminar_candidato(request, pk):
    candidato = datos.obtener_candidato(pk)
    if not candidato:
        raise Http404("Candidato no encontrado")
    if request.method == "POST":
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM candidato WHERE id = %s", [pk])
        except IntegrityError:
            messages.error(request, "No se puede eliminar el candidato porque tiene registros relacionados.")
        else:
            messages.success(request, "Candidato eliminado correctamente.")
            return redirect("candidatos")
    return render(request, "myapp/eliminar_candidato.html", {"candidato": candidato, "active_tab": "candidatos"})

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

    profesores_disponibles = comites.listar_profesores()
    return render(request, "myapp/comite.html", {
        "form": form,
        "guardado": guardado,
        # listar_comites() ya viene ordenado del más reciente al más
        # antiguo y con los tres roles resueltos a su profesor.
        "comites": comites.listar_comites(),
        "profesores": profesores_disponibles,
        "comite_posible": len(profesores_disponibles) >= 3,
        "puede_crear": permiso(request.session.get("nivel"), "comite", "crear") is not None,
        "puede_editar": permiso(request.session.get("nivel"), "comite", "editar") is not None,
        "puede_eliminar": permiso(request.session.get("nivel"), "comite", "eliminar") is not None,
        "active_tab": "comite",
    })


@requiere_permiso("comite", "editar")
def editar_comite(request, pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, anio, id_presidente, id_secretario, id_vocal FROM comite WHERE id = %s", [pk])
        fila = cursor.fetchone()
    if not fila:
        raise Http404("Comité no encontrado")
    inicial = {"anio": fila[1], "id_presidente": fila[2], "id_secretario": fila[3], "id_vocal": fila[4]}
    form = ComiteForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE comite SET anio = %s, id_presidente = %s,
                       id_secretario = %s, id_vocal = %s WHERE id = %s""",
                    [form.cleaned_data["anio"], int(form.cleaned_data["id_presidente"]), int(form.cleaned_data["id_secretario"]), int(form.cleaned_data["id_vocal"]), pk],
                )
        except IntegrityError:
            form.add_error(None, "Ya existe un comité para ese año o uno de los profesores ya no está disponible.")
        else:
            messages.success(request, "Comité actualizado correctamente.")
            return redirect("comite")
    return render(request, "myapp/editar_comite.html", {"form": form, "comite_id": pk, "active_tab": "comite"})


@requiere_permiso("comite", "eliminar")
def eliminar_comite(request, pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, anio FROM comite WHERE id = %s", [pk])
        comite_actual = cursor.fetchone()
    if not comite_actual:
        raise Http404("Comité no encontrado")
    if request.method == "POST":
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM comite WHERE id = %s", [pk])
        except IntegrityError:
            messages.error(request, "No se puede eliminar el comité porque tiene entrevistas asociadas.")
        else:
            messages.success(request, "Comité eliminado correctamente.")
            return redirect("comite")
    return render(request, "myapp/eliminar_comite.html", {"comite": {"id": comite_actual[0], "anio": comite_actual[1]}, "active_tab": "comite"})

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
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT id FROM grupo WHERE id = %s FOR UPDATE", [form.cleaned_data["id_grupo"]])
                        grupo = cursor.fetchone()
                        if not grupo:
                            form.add_error("id_grupo", "El grupo ya no existe. Actualizá la página y elegí otro.")
                        else:
                            cursor.execute("SELECT COUNT(*) FROM alumno WHERE id_grupo = %s", [form.cleaned_data["id_grupo"]])
                            cantidad_alumnos = cursor.fetchone()[0]
                            if cantidad_alumnos >= 15:
                                form.add_error("id_grupo", "El grupo ya alcanzó el máximo de 15 alumnos.")
                        if grupo and not form.errors:
                            cursor.execute(
                                """INSERT INTO alumno (dni, nombre, apellidos, id_grupo)
                                   VALUES (%s, %s, %s, %s)""",
                                [form.cleaned_data["dni"], form.cleaned_data["nombre"], form.cleaned_data["apellidos"], form.cleaned_data["id_grupo"]],
                            )
                            cursor.execute("UPDATE grupo SET num_alumnos = %s WHERE id = %s", [cantidad_alumnos + 1, form.cleaned_data["id_grupo"]])
                if not form.errors:
                    guardado = True
                    form = AlumnoForm()
            except IntegrityError:
                form.add_error("dni", "Ese DNI ya está registrado o el grupo dejó de estar disponible.")

    else:
        form = AlumnoForm()

    return render(request, "myapp/nuevo_alumno.html", {
        "form": form,
        "guardado": guardado,
        "grupos_disponibles": len(form.fields["id_grupo"].choices) > 1,
        "active_tab": "alumnos",
    })

@requiere_permiso('alumno', 'editar')
def modificar_alumno(request):
    alumno = None
    form_editar = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "guardar" in request.POST:
            DNI_original = request.POST.get("dni_original", "")
            form_editar = AlumnoForm(request.POST)
            if request.alcance == "propio" and DNI_original != request.session.get("usuario_dni"):
                raise Http404("Alumno no encontrado")
            if request.alcance == "propio" and form_editar.data.get("dni") != DNI_original:
                form_editar.add_error("dni", "No podés cambiar el DNI de tu propio registro.")
            if form_editar.is_valid():
                try:
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "SELECT id, id_grupo FROM alumno WHERE dni = %s AND (%s = 'todos' OR dni = %s) FOR UPDATE",
                                [DNI_original, request.alcance, request.session.get("usuario_dni")],
                            )
                            actual = cursor.fetchone()
                            if not actual:
                                raise Http404("Alumno no encontrado")
                            grupo_anterior = actual[1]
                            grupo_nuevo = int(form_editar.cleaned_data["id_grupo"])
                            for id_grupo in sorted({grupo_anterior, grupo_nuevo}):
                                cursor.execute("SELECT id FROM grupo WHERE id = %s FOR UPDATE", [id_grupo])
                                if not cursor.fetchone():
                                    form_editar.add_error("id_grupo", "El grupo ya no existe.")
                            if grupo_nuevo != grupo_anterior and not form_editar.errors:
                                cursor.execute("SELECT COUNT(*) FROM alumno WHERE id_grupo = %s", [grupo_nuevo])
                                if cursor.fetchone()[0] >= 15:
                                    form_editar.add_error("id_grupo", "El grupo elegido ya alcanzó el máximo de 15 alumnos.")
                            if not form_editar.errors:
                                cursor.execute(
                                    """UPDATE alumno SET dni = %s, nombre = %s, apellidos = %s, id_grupo = %s
                                       WHERE id = %s""",
                                    [form_editar.cleaned_data["dni"], form_editar.cleaned_data["nombre"], form_editar.cleaned_data["apellidos"], grupo_nuevo, actual[0]],
                                )
                                for id_grupo in {grupo_anterior, grupo_nuevo}:
                                    cursor.execute("SELECT COUNT(*) FROM alumno WHERE id_grupo = %s", [id_grupo])
                                    cantidad_alumnos = cursor.fetchone()[0]
                                    cursor.execute("UPDATE grupo SET num_alumnos = %s WHERE id = %s", [cantidad_alumnos, id_grupo])
                    if not form_editar.errors:
                        messages.success(request, "Alumno actualizado correctamente.")
                        return redirect("alumnos")
                except IntegrityError:
                    form_editar.add_error("dni", "Ese DNI ya pertenece a otro alumno.")
                alumno = {"dni": DNI_original}

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                if request.alcance == "propio" and dni != request.session.get("usuario_dni"):
                    raise Http404("Alumno no encontrado")
                with connection.cursor() as cursor:
                    cursor.execute("SELECT dni, nombre, apellidos, id_grupo FROM alumno WHERE dni = %s", [dni])
                    fila = cursor.fetchone()
                alumno = {"dni": fila[0], "nombre": fila[1], "apellidos": fila[2], "id_grupo": fila[3]} if fila else None

                if not alumno:
                    messages.warning(request, "No se encontró ningún alumno con ese DNI.")
                elif form_editar is None:
                    form_editar = AlumnoForm(initial={"dni": alumno["dni"], "nombre": alumno["nombre"], "apellidos": alumno["apellidos"], "id_grupo": str(alumno["id_grupo"])})

    except Http404:
        raise
    except IntegrityError:
        messages.error(request, "No se pudo eliminar el alumno porque tiene registros académicos relacionados.")
    except Exception as e:
        messages.error(request, f"Error en la base de datos: {str(e)}")

    contexto = {
        "form_buscar": form_buscar,
        "form_editar": form_editar,
        "alumno": alumno,
        "grupos_disponibles": bool(form_editar and len(form_editar.fields["id_grupo"].choices) > 1),
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
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT id, id_grupo FROM alumno WHERE dni = %s AND (%s = 'todos' OR dni = %s) FOR UPDATE", [dni, request.alcance, request.session.get("usuario_dni")])
                        fila = cursor.fetchone()
                        if fila:
                            cursor.execute("DELETE FROM alumno WHERE id = %s", [fila[0]])
                            cursor.execute("SELECT COUNT(*) FROM alumno WHERE id_grupo = %s", [fila[1]])
                            cantidad_alumnos = cursor.fetchone()[0]
                            cursor.execute("UPDATE grupo SET num_alumnos = %s WHERE id = %s", [cantidad_alumnos, fila[1]])
                if not fila:
                    messages.warning(request, "No se encontró ningún alumno con ese DNI.")
                else:
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

    except Http404:
        raise
    except IntegrityError:
        messages.error(request, "No se pudo eliminar el alumno porque tiene registros académicos relacionados.")
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
        if request.alcance == "propio":
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT id, dni, nombre, apellidos, domicilio,
                              nivel_estudios, titulacion, tipo
                       FROM profesor WHERE dni = %s""",
                    [request.session.get("usuario_dni")],
                )
                fila = cursor.fetchone()
            lista = [comites.Profesor(*fila)] if fila else []
        else:
            lista = comites.listar_profesores()
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
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO profesor (dni, nombre, apellidos, domicilio, nivel_estudios, titulacion, tipo)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                        [form.cleaned_data["dni"], form.cleaned_data["nombre"], form.cleaned_data["apellidos"], form.cleaned_data["domicilio"], form.cleaned_data["nivel_estudios"], form.cleaned_data["titulacion"], form.cleaned_data["tipo"]],
                    )
            except IntegrityError:
                form.add_error("dni", "Ese DNI ya está registrado como profesor.")
            else:
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
    form_editar = None
    form_buscar = BuscarDNIForm(request.GET or None)

    try:
        if request.method == "POST" and "guardar" in request.POST:
            DNI_original = request.POST.get("dni_original", "")
            form_editar = ProfesorForm(request.POST)
            if request.alcance == "propio" and DNI_original != request.session.get("usuario_dni"):
                raise Http404("Profesor no encontrado")
            if request.alcance == "propio" and form_editar.data.get("dni") != DNI_original:
                form_editar.add_error("dni", "No podés cambiar el DNI de tu propio registro.")
            if form_editar.is_valid():
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """UPDATE profesor SET dni = %s, nombre = %s, apellidos = %s,
                               domicilio = %s, nivel_estudios = %s, titulacion = %s, tipo = %s
                               WHERE dni = %s AND (%s = 'todos' OR dni = %s)""",
                            [form_editar.cleaned_data["dni"], form_editar.cleaned_data["nombre"], form_editar.cleaned_data["apellidos"], form_editar.cleaned_data["domicilio"], form_editar.cleaned_data["nivel_estudios"], form_editar.cleaned_data["titulacion"], form_editar.cleaned_data["tipo"], DNI_original, request.alcance, request.session.get("usuario_dni")],
                        )
                except IntegrityError:
                    form_editar.add_error("dni", "Ese DNI ya pertenece a otro profesor.")
                else:
                    messages.success(request, "Profesor actualizado correctamente.")
                    return redirect("profesores")

        if "buscar" in request.GET:
            if form_buscar.is_valid():
                dni = form_buscar.cleaned_data["dni"]
                if request.alcance == "propio" and dni != request.session.get("usuario_dni"):
                    raise Http404("Profesor no encontrado")
                with connection.cursor() as cursor:
                    cursor.execute("SELECT dni, nombre, apellidos, domicilio, nivel_estudios, titulacion, tipo FROM profesor WHERE dni = %s", [dni])
                    fila = cursor.fetchone()
                profesor = {"dni": fila[0], "nombre": fila[1], "apellidos": fila[2], "domicilio": fila[3], "nivel_estudios": fila[4], "titulacion": fila[5], "tipo": fila[6]} if fila else None

                if not profesor:
                    messages.warning(request, "No se encontró ningún profesor con ese DNI.")
                elif form_editar is None:
                    form_editar = ProfesorForm(initial=profesor)

    except Http404:
        raise
    except IntegrityError:
        messages.error(request, "No se pudo actualizar el profesor porque alguno de los datos está relacionado o dejó de estar disponible.")
    except Exception as e:
        messages.error(request, f"Error en la base de datos: {str(e)}")

    contexto = {
        "form_buscar": form_buscar,
        "form_editar": form_editar,
        "profesor": profesor,
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

    except Http404:
        raise
    except IntegrityError:
        messages.error(request, "No se puede eliminar el profesor porque participa en un comité o tiene registros académicos asociados.")
    except Exception as e:
        messages.error(request, f"Error en la base de datos: {str(e)}")

    return render(request, "myapp/eliminar_profesor.html", {
        "form_buscar": form_buscar,
        "profesor": {"dni": profesor[0], "nombre": profesor[1]} if profesor else None,
        "active_tab": "profesores",
    })


def set_role(request):
    if request.method == "POST":
        rol = normalizar_rol(request.POST.get("rol"))
        if rol in {"ADMIN", "COMITE", "PROFESOR", "ALUMNO"}:
            request.session["nivel"] = rol
            request.session["rol_asumido"] = True
            if not request.session.get("usuario_dni"):
                request.session["usuario_dni"] = "invitado"
                request.session["usuario_nombre"] = "Visitante"
            messages.success(request, f"Ahora estás navegando como {rol}.")
        else:
            messages.error(request, "Rol no válido.")
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


def cargar_calificacion(request):
    denegado = _solo_admin(request)
    if denegado:
        return denegado
    form = CalificacionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        alumno_dni = form.cleaned_data["alumno_dni"]
        id_asignatura = int(form.cleaned_data["id_asignatura"])
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT al.id
                   FROM alumno al
                   JOIN grupo g ON g.id = al.id_grupo
                   JOIN asignatura asi ON asi.id_curso = g.id_curso
                   WHERE al.dni = %s AND asi.id = %s""",
                [alumno_dni, id_asignatura],
            )
            alumno = cursor.fetchone()
            if not alumno:
                form.add_error("alumno_dni", "El alumno no existe o la materia no corresponde a su curso.")
            else:
                cursor.execute(
                    """INSERT INTO calificacion (id_alumno, id_asignatura, nota, fecha)
                       VALUES (%s, %s, %s, %s)""",
                    [alumno[0], id_asignatura, form.cleaned_data["nota"], form.cleaned_data["fecha"]],
                )
                messages.success(request, "Nota cargada. El promedio de la materia se recalcula automáticamente.")
                return redirect("cargar_calificacion")
    return render(request, "myapp/cargar_calificacion.html", {"form": form, "active_tab": "academico"})


def cargar_faltas_semanales(request):
    denegado = _solo_admin(request)
    if denegado:
        return denegado
    fecha = timezone.localdate()
    semana_actual = fecha.isocalendar()
    form = FaltaSemanalForm(request.POST or None, initial={"anio": semana_actual.year, "semana": semana_actual.week})
    if request.method == "POST" and form.is_valid():
        try:
            date.fromisocalendar(form.cleaned_data["anio"], form.cleaned_data["semana"], 1)
        except ValueError:
            form.add_error("semana", "Esa semana no existe para el año indicado.")
        else:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM alumno WHERE dni = %s", [form.cleaned_data["alumno_dni"]])
                alumno = cursor.fetchone()
                if not alumno:
                    form.add_error("alumno_dni", "No existe un alumno con ese DNI.")
                else:
                    unidades = int(form.cleaned_data["faltas"] * 4)
                    cursor.execute(
                        """INSERT INTO faltas_semanales (id_alumno, anio, semana, cuartos_falta)
                           VALUES (%s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE cuartos_falta = %s""",
                        [alumno[0], form.cleaned_data["anio"], form.cleaned_data["semana"], unidades, unidades],
                    )
                    messages.success(request, "Faltas semanales guardadas. Si ya había un registro, se reemplazó.")
                    return redirect("cargar_faltas_semanales")
    return render(request, "myapp/cargar_faltas_semanales.html", {"form": form, "active_tab": "academico"})
