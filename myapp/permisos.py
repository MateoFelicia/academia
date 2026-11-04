from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.db import connection, DatabaseError

ROL_ADMIN = "ADMIN"
RECURSOS = ("usuario", "alumno", "profesor", "comite", "candidato")
ACCIONES = ("ver", "crear", "editar", "eliminar")
ROLES_EDITABLES = ("COMITE", "PROFESOR", "ALUMNO")

PERMISOS_ADMIN = {
    ("usuario", "ver"): "todos", ("usuario", "crear"): "todos",
    ("usuario", "editar"): "todos", ("usuario", "eliminar"): "todos",
    ("alumno", "ver"): "todos", ("alumno", "crear"): "todos",
    ("alumno", "editar"): "todos", ("alumno", "eliminar"): "todos",
    ("profesor", "ver"): "todos", ("profesor", "crear"): "todos",
    ("profesor", "editar"): "todos", ("profesor", "eliminar"): "todos",
    ("comite", "ver"): "todos", ("comite", "crear"): "todos",
    ("candidato", "ver"): "todos", ("candidato", "crear"): "todos",
    ("candidato", "editar"): "todos", ("panel_permisos", "ver"): "todos",
    ("panel_permisos", "editar"): "todos",
}

ITEMS_MENU = {
    "index": None, "candidatos": ("candidato", "ver"),
    "nuevo_candidato": ("candidato", "crear"), "comite": ("comite", "ver"),
    "alumnos": ("alumno", "ver"), "nuevo_alumno": ("alumno", "crear"),
    "modificar_alumno": ("alumno", "editar"), "eliminar_alumno": ("alumno", "eliminar"),
    "profesores": ("profesor", "ver"), "nuevo_profesor": ("profesor", "crear"),
    "modificar_profesor": ("profesor", "editar"), "eliminar_profesor": ("profesor", "eliminar"),
    "nuevo_usuario": ("usuario", "crear"),
}


def normalizar_rol(valor):
    rol = (valor or "").strip().upper()
    return "ADMIN" if rol == "ADMINISTRACION" else rol


def permiso(rol, recurso, accion):
    rol = normalizar_rol(rol)
    if rol == ROL_ADMIN:
        return PERMISOS_ADMIN.get((recurso, accion))
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT alcance FROM permisos WHERE rol = %s AND recurso = %s AND accion = %s", [rol, recurso, accion])
            fila = cursor.fetchone()
    except DatabaseError:
        return None
    return fila[0] if fila else None


def requiere_permiso(recurso, accion):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.session.get("usuario_dni"):
                messages.warning(request, "Iniciá sesión.")
                return redirect("login")
            alcance = permiso(request.session.get("nivel"), recurso, accion)
            if alcance is None:
                messages.warning(request, "No tenés permisos para esta página")
                return redirect("index")
            request.alcance = alcance
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def requiere_login(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.session.get("usuario_dni"):
            messages.warning(request, "Iniciá sesión.")
            return redirect("login")
        return vista(request, *args, **kwargs)
    return envoltura


def permisos_menu(request):
    if not request.session.get("usuario_dni"):
        return {"permisos": set()}
    rol = request.session.get("nivel")
    visibles = {"index"}
    rol = normalizar_rol(rol)
    if rol == ROL_ADMIN:
        visibles.update(("panel_permisos", "permisos_log"))
        visibles.update(item for item, regla in ITEMS_MENU.items() if regla)
    else:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT recurso, accion FROM permisos WHERE rol = %s", [rol])
                habilitados = set(cursor.fetchall())
        except DatabaseError:
            habilitados = set()
        visibles.update(item for item, regla in ITEMS_MENU.items() if regla in habilitados)
    return {"permisos": visibles}
