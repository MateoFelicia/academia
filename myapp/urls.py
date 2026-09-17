from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("index/", views.index, name="index_path"),
    path('candidatos/', views.candidatos, name='candidatos'),
    path("candidatos/nuevo/", views.nuevo_candidato, name="nuevo_candidato"),
    path("candidatos/<int:pk>/editar/", views.editar_candidato, name="editar_candidato"),
    path("candidatos/<int:pk>/", views.detalle_candidato, name="detalle_candidato"),
    path("comite/", views.comite, name="comite"),
    path("comite/nuevo/", views.nuevo_comite, name="nuevo_comite"),
    path("profesores/", views.profesores, name="profesores"),
    path("alumno/", views.alumnos, name="alumnos"),
    path("alumno/nuevo/", views.nuevo_alumno, name="nuevo_alumno"),
    path("alumno/modificar/", views.modificar_alumno, name="modificar_alumno"),
    path("alumno/eliminar/", views.eliminar_alumno, name="eliminar_alumno"),
    path("profesores/nuevo/", views.nuevo_profesor, name="nuevo_profesor"),
    path("profesores/modificar/", views.modificar_profesor, name="modificar_profesor"),
    path("profesores/eliminar/", views.eliminar_profesor, name="eliminar_profesor"),
]