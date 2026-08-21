from django import forms


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

class CandidatosForm(forms.Form): #actualizar con como son los candidatos
    dni = forms.CharField(label="DNI", max_length=15)
    nombre = forms.CharField(label="Nombre", max_length=60)
    apellidos = forms.CharField(label="Apellidos", max_length=80)
    id_grupo = forms.IntegerField(label="ID de grupo")
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
