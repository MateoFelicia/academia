from django import forms


class AlumnoForm(forms.Form):
    dni = forms.CharField(label="DNI", max_length=15)
    nombre = forms.CharField(label="Nombre", max_length=60)
    apellidos = forms.CharField(label="Apellidos", max_length=80)
    id_grupo = forms.IntegerField(label="ID de grupo")