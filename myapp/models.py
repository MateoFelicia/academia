from django.db import models

# Sector candidatos: se maneja por SQL crudo (ver views.py), igual que
# alumno/profesor. Las tablas myapp_candidato, myapp_llamada,
# myapp_entrevista y myapp_materia ya existen en la base (las creó
# este mismo app en su momento vía migraciones) pero desde acá no se
# vuelven a tocar con el ORM.
