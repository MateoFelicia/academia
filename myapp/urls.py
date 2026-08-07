from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("index/", views.index, name="index"),
    path("candidatos/", views.candidatos, name="candidatos"),
    path("comite/", views.comite, name="comite"),
    path("profesores/", views.profesores, name="profesores"),
    path("alumno/nuevo/", views.nuevo_alumno, name="nuevo_alumno"),
    path("alumno/", views.listado_alumno, name="listado_alumno"),
]