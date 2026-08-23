from django.contrib import admin
from .models import Candidato, Materia, Llamada, Entrevista


class EntrevistaInline(admin.StackedInline):
    model = Entrevista
    extra = 0


class LlamadaInline(admin.TabularInline):
    model = Llamada
    extra = 1


@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    inlines = [LlamadaInline]


@admin.register(Llamada)
class LlamadaAdmin(admin.ModelAdmin):
    inlines = [EntrevistaInline]


admin.site.register(Materia)