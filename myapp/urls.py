from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("index/", views.index, name="index"),
    path("candidatos/", views.candidatos, name="candidatos"),
    path("comite/", views.comite, name="comite"),
    path("comite/nuevo/", views.nuevo_comite, name="nuevo_comite"),
    path("profesores/", views.profesores, name="profesores"),
    path("alumno/", views.alumnos, name="listado_alumno"),
    path("alumno/nuevo/", views.nuevo_alumno, name="nuevo_alumno"),
    path("profesores/nuevo/", views.nuevo_profesor, name="nuevo_profesor"),
]