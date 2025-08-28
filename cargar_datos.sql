-- 1. Tabla principal con todos los folios y su linaje principal (ltree)
CREATE EXTENSION IF NOT EXISTS ltree;

DROP TABLE IF EXISTS folios_registrales CASCADE;
CREATE TABLE folios_registrales (
    matricula VARCHAR(100) PRIMARY KEY,
    estado_folio VARCHAR(50),
    matriz_original TEXT,
    ruta_jerarquica LTREE
);

-- Insertar todos los folios
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('103474', 'ANTECEDENTE', '', '103474');
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('1037472', 'ACTIVO', '103474, 795879, 795880, 795881, 795882, 795883', '103474.1037472');
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('1037473', 'DERIVADO', '', '103474.1037472.1037473');
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('1037474', 'DERIVADO', '', '103474.1037472.1037474');
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('1037475', 'DERIVADO', '', '103474.1037472.1037475');
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('795879', 'ANTECEDENTE', '', '795879');
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('795880', 'ANTECEDENTE', '', '795880');
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('795881', 'ANTECEDENTE', '', '795881');
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('795882', 'ANTECEDENTE', '', '795882');
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('795883', 'ANTECEDENTE', '', '795883');
INSERT INTO folios_registrales (matricula, estado_folio, matriz_original, ruta_jerarquica) VALUES ('95882', 'ANTECEDENTE', '', '95882');

CREATE INDEX idx_folios_ruta ON folios_registrales USING GIST (ruta_jerarquica);

-- 2. Tabla de vínculos para registrar TODAS las relaciones padre-hijo
DROP TABLE IF EXISTS folio_vinculos;
CREATE TABLE folio_vinculos (
    folio_hijo VARCHAR(100) REFERENCES folios_registrales(matricula),
    folio_padre VARCHAR(100) REFERENCES folios_registrales(matricula),
    PRIMARY KEY (folio_hijo, folio_padre)
);

-- Insertar todos los vínculos
INSERT INTO folio_vinculos (folio_hijo, folio_padre) VALUES ('1037472', '103474');
INSERT INTO folio_vinculos (folio_hijo, folio_padre) VALUES ('1037472', '795879');
INSERT INTO folio_vinculos (folio_hijo, folio_padre) VALUES ('1037472', '795880');
INSERT INTO folio_vinculos (folio_hijo, folio_padre) VALUES ('1037472', '795881');
INSERT INTO folio_vinculos (folio_hijo, folio_padre) VALUES ('1037472', '795882');
INSERT INTO folio_vinculos (folio_hijo, folio_padre) VALUES ('1037472', '795883');
INSERT INTO folio_vinculos (folio_hijo, folio_padre) VALUES ('1037472', '95882');
INSERT INTO folio_vinculos (folio_hijo, folio_padre) VALUES ('1037473', '1037472');
INSERT INTO folio_vinculos (folio_hijo, folio_padre) VALUES ('1037474', '1037472');
INSERT INTO folio_vinculos (folio_hijo, folio_padre) VALUES ('1037475', '1037472');
