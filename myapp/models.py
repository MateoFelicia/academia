from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError

# Create your models here.
class Materia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class Candidato(models.Model):
    class TipoDeseado(models.TextChoices):
        TUTOR = 'tutor', 'Tutor'
        ESPECIALISTA = 'especialista', 'Especialista'
        AMBOS = 'ambos', 'Ambos'

    dni = models.CharField(max_length=9, unique=True)
    nombre = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    curriculum = models.CharField(max_length=255, blank=True)
    tipo_deseado = models.CharField(
        max_length=20,
        choices=TipoDeseado.choices,
        blank=True,
    )
    materias = models.ManyToManyField(Materia, related_name='candidatos', blank=True)

    def __str__(self):
        return f"{self.nombre} {self.apellidos}"


class Llamada(models.Model):
    class Disposicion(models.TextChoices):
        NO_LOCALIZADO = 'no_localizado', 'No localizado'
        NO_INTERESADO = 'no_interesado', 'No está interesado'
        CONCERTADA = 'concertada', 'Entrevista concertada'

    candidato = models.ForeignKey(
        Candidato,
        on_delete=models.CASCADE,
        related_name='llamadas',
    )
    fecha_hora = models.DateTimeField()
    disposicion = models.CharField(max_length=20, choices=Disposicion.choices)

    def __str__(self):
        return f"Llamada a {self.candidato} — {self.get_disposicion_display()}"
    
    def clean(self):
        if self.pk:
            try:
                entrevista_existente = self.entrevista
            except Entrevista.DoesNotExist:
                entrevista_existente = None

            if entrevista_existente and self.disposicion != self.Disposicion.CONCERTADA:
                raise ValidationError({
                    'disposicion': (
                        f"No se puede cambiar: {self.candidato} ya fue entrevistado el "
                        f"{entrevista_existente.fecha} para la materia "
                        f"{entrevista_existente.materia_a_cubrir}, con valoración "
                        f"{entrevista_existente.valoracion}. Si fue un error, borrá primero "
                        f"esa entrevista antes de modificar la disposición."
                    )
                })
    
    @property
    def puede_cargar_entrevista(self):
        if self.disposicion != self.Disposicion.CONCERTADA:
            return False
        try:
            self.entrevista
            return False
        except Entrevista.DoesNotExist:
            return True


class Entrevista(models.Model):
    llamada = models.OneToOneField(
        Llamada,
        on_delete=models.PROTECT,
        related_name='entrevista',
    )
    fecha = models.DateField()
    materia_a_cubrir = models.ForeignKey(
        Materia,
        on_delete=models.PROTECT,
        related_name='entrevistas',
    )
    valoracion = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    def __str__(self):
        return f"Entrevista a {self.llamada.candidato} — {self.fecha}"
    
    def clean(self):
        if self.llamada_id and self.llamada.disposicion != Llamada.Disposicion.CONCERTADA:
            raise ValidationError(
                f"Solo se puede cargar una entrevista si la llamada fue "
                f"'{Llamada.Disposicion.CONCERTADA.label}'."
            )