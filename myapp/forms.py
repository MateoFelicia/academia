from django import forms
from django.db import connection


class ProfesorForm(forms.Form): 
    dni = forms.CharField(max_length=10)
    nombre = forms.CharField(max_length=100)
    apellidos = forms.CharField(max_length=100)
    domicilio = forms.CharField(max_length=150)
    nivel_estudios = forms.ChoiceField(choices=[
        ("inicial", "Inicial"),
        ("primario", "Primario"),
        ("secundario", "Secundario"),
        ("Universitarios", "Universitario"),
    ])
    titulacion = forms.CharField(max_length=150)
    tipo = forms.ChoiceField(choices=[
        ("titular", "Titular"),
        ("suplente", "Suplente"),
        ("interino", "Interino"),
    ])

class BuscarDNIForm(forms.Form):
    dni = forms.CharField(label="DNI", max_length=15)

from django import forms
from django.db import connection

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


def _choices_materias():
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, nombre FROM myapp_materia ORDER BY nombre")
        return [(str(id_), nombre) for id_, nombre in cursor.fetchall()]


class AlumnoForm(forms.Form):
    dni = forms.CharField(label="DNI", max_length=15)
    nombre = forms.CharField(label="Nombre", max_length=60)
    apellidos = forms.CharField(label="Apellidos", max_length=80)
    id_grupo = forms.IntegerField(label="ID de grupo")


class ComiteForm(forms.Form):
    """
    Alta de un comité evaluador (acta anual).

    Los tres roles se resuelven contra PROFESORES_MOCK, así que en vez de
    pedir el id "a ciegas" (como AlumnoForm con id_grupo) usamos un
    ChoiceField dinámico: el usuario elige por nombre, el form guarda el id.
    """
    anio = forms.IntegerField(label="Año", min_value=2000, max_value=2100)
    id_presidente = forms.ChoiceField(label="Presidente")
    id_secretario = forms.ChoiceField(label="Secretario")
    id_vocal = forms.ChoiceField(label="Vocal")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .mock_comite import listar_profesores_mock

        opciones = [
            (str(p.id), f"{p.nombre_completo} — {p.titulacion}")
            for p in listar_profesores_mock()
        ]
        self.fields["id_presidente"] = forms.ChoiceField(label="Presidente", choices=opciones)
        self.fields["id_secretario"] = forms.ChoiceField(label="Secretario", choices=opciones)
        self.fields["id_vocal"] = forms.ChoiceField(label="Vocal", choices=opciones)

    def clean(self):
        cleaned = super().clean()
        roles = ("id_presidente", "id_secretario", "id_vocal")
        elegidos = [cleaned.get(r) for r in roles if cleaned.get(r)]
        if len(elegidos) == 3 and len(set(elegidos)) < 3:
            raise forms.ValidationError(
                "Un mismo profesor no puede ocupar dos roles en el mismo comité."
            )
        return cleaned

class CandidatoForm(forms.Form):
    dni = forms.CharField(label="DNI", max_length=9)
    nombre = forms.CharField(label="Nombre", max_length=80)
    apellidos = forms.CharField(label="Apellidos", max_length=80)
    curriculum = forms.CharField(label="Currículum", max_length=255, required=False)
    tipo_deseado = forms.ChoiceField(
        label="Tipo deseado",
        required=False,
        choices=[('', '—')] + TIPO_DESEADO_CHOICES,
    )
    materias = forms.MultipleChoiceField(
        label="Materias",
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        super().__init__(*args, **kwargs)
        self.fields["materia_a_cubrir"].choices = _choices_materias()

class ProfesorForm(forms.Form): 
    dni = forms.CharField(max_length=10)
    nombre = forms.CharField(max_length=100)
    apellidos = forms.CharField(max_length=100)
    domicilio = forms.CharField(max_length=150)
    nivel_estudios = forms.ChoiceField(choices=[
        ("inicial", "Inicial"),
        ("primario", "Primario"),
        ("secundario", "Secundario"),
        ("Universitarios", "Universitario"),
    ])
    titulacion = forms.CharField(max_length=150)
    tipo = forms.ChoiceField(choices=[
        ("titular", "Titular"),
        ("suplente", "Suplente"),
        ("interino", "Interino"),
    ])

class BuscarDNIForm(forms.Form):
    dni = forms.CharField(label="DNI", max_length=15)