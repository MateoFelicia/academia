USE academia

CREATE TABLE permisos (
    rol VARCHAR(20) NOT NULL,
    recurso VARCHAR(20) NOT NULL,
    accion VARCHAR(20) NOT NULL,
    alcance ENUM('todos','propio') NOT NULL,
    PRIMARY KEY (rol, recurso, accion)
);

CREATE TABLE permisos_log (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    fecha DATETIME NOT NULL,
    admin_dni VARCHAR(20) NOT NULL,
    admin_nombre VARCHAR(255) NOT NULL,
    rol VARCHAR(20) NOT NULL,
    recurso VARCHAR(20) NOT NULL,
    accion VARCHAR(20) NOT NULL,
    valor_anterior ENUM('todos','propio') NULL,
    valor_nuevo ENUM('todos','propio') NULL
);

INSERT INTO permisos (rol, recurso, accion, alcance) VALUES
('COMITE','candidato','ver','todos'),('COMITE','candidato','crear','todos'),('COMITE','candidato','editar','todos'),
('COMITE','comite','ver','todos'),('COMITE','comite','crear','todos'),('COMITE','profesor','ver','todos'),
('PROFESOR','alumno','ver','todos'),('PROFESOR','profesor','ver','todos'),('PROFESOR','profesor','editar','propio'),('PROFESOR','comite','ver','todos'),
('ALUMNO','alumno','ver','propio');
