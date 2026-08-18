from django import forms


class AlumnoForm(forms.Form):
    dni = forms.CharField(label="DNI", max_length=15)
    nombre = forms.CharField(label="Nombre", max_length=60)
    apellidos = forms.CharField(label="Apellidos", max_length=80)
    id_grupo = forms.IntegerField(label="ID de grupo")

class ProfesorForm(forms.Form): 
    dni = forms.CharField(label="DNI", max_length=15)
    nombre = forms.CharField(label="Nombre", max_length=60)
    apellidos = forms.CharField(label="Apellidos", max_length=80)
    domicilio = forms.CharField(label="Domicilio", max_length=80)
    nivel = forms.CharField(label="Nivel", max_length=15)
    titulacion = forms.CharField(label="Titulacion", max_length=80)
    tipo = forms.CharField(label="Tipo", max_length=15)
