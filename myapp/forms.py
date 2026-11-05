from django import forms

class BuscarDNIForm(forms.Form):
    dni = forms.CharField(label="DNI", max_length=15)

# Estas opciones están en minúsculas y son el vocabulario de los
# formularios y los templates. La traducción al ENUM de MySQL (que las
# guarda en mayúsculas) es una responsabilidad de datos_candidatos.py.
TIPO_DESEADO_CHOICES = [
    ('tutor', 'Tutor'),
    ('especialista', 'Especialista'),
    ('ambos', 'Ambos'),
]

DISPOSICION_CHOICES = [
    ('no_localizado', 'No localizado'),
    ('no_interesado', 'No está interesado'),
    ('concertada', 'Entrevista concertada'),
]

class LoginForm(forms.Form):
    dni = forms.CharField(label="DNI o nombre de usuario", max_length=50, widget=forms.TextInput(attrs={
        "placeholder": "DNI o nombre de usuario",
        "autofocus": True,
    }))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={
        "placeholder": "Contraseña",
    }))

def _choices_materias():
    """Materias que se pueden cubrir en una entrevista.

    La tabla se llama `asignatura`, no `materia`: es el mismo concepto con
    el nombre que le daba el diseño de la base.
    """
    from .datos_candidatos import listar_materias

    return [(str(a.id), a.nombre) for a in listar_materias()]


class AlumnoForm(forms.Form):
    dni = forms.CharField(label="DNI", max_length=20)
    nombre = forms.CharField(label="Nombre", max_length=255)
    apellidos = forms.CharField(label="Apellidos", max_length=255)
    id_grupo = forms.ChoiceField(
        label="Grupo",
        error_messages={"required": "Elegí un grupo existente para poder matricular al alumno."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT g.id, g.codigo, c.numero_curso, e.nombre
                   FROM grupo g
                   JOIN curso c ON c.id = g.id_curso
                   JOIN especialidad e ON e.id = c.id_especialidad
                   ORDER BY c.numero_curso, e.nombre, g.codigo"""
            )
            self.fields["id_grupo"].choices = [
                ("", "Elegí un grupo")
            ] + [
                (str(id_grupo), f"{numero_curso}° {especialidad} · Grupo {codigo}")
                for id_grupo, codigo, numero_curso, especialidad in cursor.fetchall()
            ]


class ComiteForm(forms.Form):
    """
    Alta de un comité evaluador (acta anual).

    Los tres roles se resuelven contra la tabla `profesor`, así que en vez de
    pedir el id "a ciegas" (como AlumnoForm con id_grupo) usamos un
    ChoiceField dinámico: el usuario elige por nombre, el form guarda el id.
    """
    anio = forms.IntegerField(label="Año", min_value=2000, max_value=2100)
    id_presidente = forms.ChoiceField(label="Presidente")
    id_secretario = forms.ChoiceField(label="Secretario")
    id_vocal = forms.ChoiceField(label="Vocal")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .datos_comite import listar_profesores

        opciones = [
            (str(p.id), f"{p.nombre_completo} — {p.titulacion}")
            for p in listar_profesores()
        ]
        self.fields["id_presidente"] = forms.ChoiceField(label="Presidente", choices=opciones)
        self.fields["id_secretario"] = forms.ChoiceField(label="Secretario", choices=opciones)
        self.fields["id_vocal"] = forms.ChoiceField(label="Vocal", choices=opciones)
        self.cantidad_profesores = len(opciones)

    def clean(self):
        cleaned = super().clean()
        if self.cantidad_profesores < 3:
            raise forms.ValidationError(
                "Para crear un comité hacen falta al menos tres profesores cargados."
            )
        roles = ("id_presidente", "id_secretario", "id_vocal")
        elegidos = [cleaned.get(r) for r in roles if cleaned.get(r)]
        if len(elegidos) == 3 and len(set(elegidos)) < 3:
            raise forms.ValidationError(
                "Un mismo profesor no puede ocupar dos roles en el mismo comité."
            )
        return cleaned

class CandidatoForm(forms.Form):
    dni = forms.CharField(label="DNI", max_length=20)
    nombre = forms.CharField(label="Nombre", max_length=80)
    apellidos = forms.CharField(label="Apellidos", max_length=80)
    curriculum = forms.CharField(label="Currículum", max_length=255, required=False)
    tipo_deseado = forms.ChoiceField(
        label="Tipo deseado",
        choices=TIPO_DESEADO_CHOICES,
    )
    materias = forms.MultipleChoiceField(
        label="Materias",
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super(CandidatoForm, self).__init__(*args, **kwargs)
        self.fields["materias"].choices = _choices_materias()




class BuscarCandidatoForm(forms.Form):
    """
    Filtro del listado de candidatos (candidatos.html).

    Antes el listado armaba el queryset directamente contra el modelo
    (Candidato.objects.all(), sin validar ni tipar nada de lo que
    llegara por GET). Este form es el que valida y limpia esos
    parámetros de búsqueda antes de tocar la base (por SQL crudo).
    """
    q = forms.CharField(
        label="Buscar",
        required=False,
        max_length=80,
        widget=forms.TextInput(attrs={"placeholder": "Nombre, apellido o DNI"}),
    )
    tipo_deseado = forms.ChoiceField(
        label="Tipo",
        required=False,
        choices=[('', 'Todos')] + TIPO_DESEADO_CHOICES,
    )


class LlamadaForm(forms.Form):
    fecha_hora = forms.DateTimeField(
        label="Fecha y hora",
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        input_formats=['%Y-%m-%dT%H:%M'],
    )
    disposicion = forms.ChoiceField(label="Disposición", choices=DISPOSICION_CHOICES)


class EntrevistaForm(forms.Form):
    fecha = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    materia_a_cubrir = forms.ChoiceField(label="Materia a cubrir")
    valoracion = forms.IntegerField(label="Valoración (1 a 5)", min_value=1, max_value=5)

    def __init__(self, *args, **kwargs):
        super(EntrevistaForm, self).__init__(*args, **kwargs)
        self.fields["materia_a_cubrir"].choices = _choices_materias()


class ProfesorForm(forms.Form): 
    dni = forms.CharField(label="DNI", max_length=20)
    nombre = forms.CharField(max_length=100)
    apellidos = forms.CharField(max_length=100)
    domicilio = forms.CharField(max_length=255, required=False)
    nivel_estudios = forms.ChoiceField(choices=[
        ("inicial", "Inicial"),
        ("primario", "Primario"),
        ("secundario", "Secundario"),
        ("Universitarios", "Universitario"),
    ])
    titulacion = forms.CharField(max_length=150)
    # Estas son las opciones del ENUM `tipo` de la tabla profesor. Antes
    # había acá titular/suplente/interino, que la base no acepta.
    tipo = forms.ChoiceField(choices=[
        ("TUTOR", "Tutor"),
        ("ESPECIALISTA", "Especialista"),
        ("AMBOS", "Ambos"),
    ])


class PermisosForm(forms.Form):
    """Selector de alcance por cada permiso de los roles editables."""
    RECURSOS = ("usuario", "alumno", "profesor", "comite", "candidato")
    ACCIONES = ("ver", "crear", "editar", "eliminar")
    ROLES = ("COMITE", "PROFESOR", "ALUMNO")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for rol in self.ROLES:
            for recurso in self.RECURSOS:
                for accion in self.ACCIONES:
                    choices = [("", "Ninguno"), ("todos", "Todos")]
                    if recurso in ("alumno", "profesor"):
                        choices.insert(1, ("propio", "Propio"))
                    self.fields[f"{rol}_{recurso}_{accion}"] = forms.ChoiceField(
                        choices=choices, required=False,
                        label=f"{rol} · {recurso} · {accion}",
                    )

    def clean(self):
        cleaned = super().clean()
        allowed = {"", "todos", "propio"}
        for rol in self.ROLES:
            for recurso in self.RECURSOS:
                for accion in self.ACCIONES:
                    key = f"{rol}_{recurso}_{accion}"
                    valor = cleaned.get(key)
                    if valor not in allowed:
                        self.add_error(key, "Alcance desconocido.")
                    elif valor == "propio" and recurso not in ("alumno", "profesor"):
                        self.add_error(key, "El alcance propio solo aplica a alumnos y profesores.")
        return cleaned


class CalificacionForm(forms.Form):
    alumno_dni = forms.CharField(label="DNI del alumno", max_length=20)
    id_asignatura = forms.ChoiceField(label="Materia")
    nota = forms.DecimalField(label="Nota (0 a 10)", max_digits=4, decimal_places=2, min_value=0, max_value=10)
    fecha = forms.DateField(label="Fecha", widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["id_asignatura"].choices = [("", "Elegí una materia")] + _choices_materias()


class FaltaSemanalForm(forms.Form):
    alumno_dni = forms.CharField(label="DNI del alumno", max_length=20)
    anio = forms.IntegerField(label="Año", min_value=2000, max_value=2100)
    semana = forms.IntegerField(label="Semana ISO", min_value=1, max_value=53)
    faltas = forms.DecimalField(
        label="Faltas de la semana (0 a 5, en cuartos)",
        max_digits=3, decimal_places=2, min_value=0, max_value=5,
    )

    def clean_faltas(self):
        faltas = self.cleaned_data["faltas"]
        if faltas * 4 != (faltas * 4).to_integral_value():
            raise forms.ValidationError("La cantidad debe avanzar en incrementos de 0,25.")
        return faltas
