-- Nuevos registros académicos. No modifica las tablas existentes.
-- Ejecutar manualmente después de confirmar copia de seguridad.

CREATE TABLE calificacion (
    id INT NOT NULL AUTO_INCREMENT,
    id_alumno INT NOT NULL,
    id_asignatura INT NOT NULL,
    nota DECIMAL(4,2) NOT NULL,
    fecha DATE NOT NULL,
    PRIMARY KEY (id),
    KEY idx_calificacion_alumno_asignatura (id_alumno, id_asignatura),
    CONSTRAINT ck_calificacion_nota CHECK (nota >= 0 AND nota <= 10),
    CONSTRAINT fk_calificacion_alumno
        FOREIGN KEY (id_alumno) REFERENCES alumno (id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_calificacion_asignatura
        FOREIGN KEY (id_asignatura) REFERENCES asignatura (id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE faltas_semanales (
    id_alumno INT NOT NULL,
    anio SMALLINT NOT NULL,
    semana TINYINT UNSIGNED NOT NULL,
    cuartos_falta TINYINT UNSIGNED NOT NULL,
    PRIMARY KEY (id_alumno, anio, semana),
    CONSTRAINT ck_faltas_semanales_semana CHECK (semana BETWEEN 1 AND 53),
    CONSTRAINT ck_faltas_semanales_cuartos CHECK (cuartos_falta <= 20),
    CONSTRAINT fk_faltas_semanales_alumno
        FOREIGN KEY (id_alumno) REFERENCES alumno (id)
        ON UPDATE CASCADE ON DELETE CASCADE
);
