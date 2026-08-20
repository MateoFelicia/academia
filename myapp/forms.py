from django import forms


class AlumnoForm(forms.Form):
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
