-- ============================================================
-- Esquema de base de datos - Sistema de Tintorería (MVP)
-- Módulo: Recepción, Órdenes y Entrega
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- Catálogos
-- ------------------------------------------------------------

-- Tipos de servicio: permite diferenciar tintorería (seguimiento
-- por pieza) de planchado (seguimiento solo por orden completa)
CREATE TABLE tipos_servicio (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL UNIQUE,      -- 'Tintorería', 'Planchado', 'Lavado', etc.
    seguimiento_por_pieza INTEGER NOT NULL DEFAULT 0  -- 0 = solo por orden, 1 = por pieza
);

INSERT INTO tipos_servicio (nombre, seguimiento_por_pieza) VALUES
    ('Tintorería', 1),
    ('Planchado', 0),
    ('Lavado', 0);

-- Catálogo de prendas (para precios sugeridos y reportes)
CREATE TABLE prendas_catalogo (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,             -- 'Camisa', 'Pantalón', 'Vestido', 'Traje', etc.
    tipo_servicio_id INTEGER NOT NULL,
    precio_base     REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (tipo_servicio_id) REFERENCES tipos_servicio(id)
);

-- ------------------------------------------------------------
-- Clientes
-- ------------------------------------------------------------

CREATE TABLE clientes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    telefono        TEXT,
    email           TEXT,
    direccion       TEXT,
    notas           TEXT,
    fecha_registro  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX idx_clientes_nombre ON clientes(nombre);
CREATE INDEX idx_clientes_telefono ON clientes(telefono);

-- ------------------------------------------------------------
-- Usuarios / Empleados (quién recibe, procesa, entrega)
-- ------------------------------------------------------------

CREATE TABLE usuarios (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL,
    usuario         TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    rol             TEXT NOT NULL DEFAULT 'operador',  -- 'admin', 'operador'
    activo          INTEGER NOT NULL DEFAULT 1
);

-- ------------------------------------------------------------
-- Órdenes
-- ------------------------------------------------------------

-- Estado general de la orden. Se mantiene aquí aunque el detalle
-- viva a nivel pieza, para poder listar/filtrar rápido sin JOIN.
-- Valores: 'recibido', 'en_proceso', 'listo', 'entregado', 'cancelado'

CREATE TABLE ordenes (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    folio                   TEXT NOT NULL UNIQUE,   -- ej. 'ORD-000123'
    cliente_id              INTEGER NOT NULL,
    tipo_servicio_id        INTEGER NOT NULL,
    usuario_recepcion_id    INTEGER,
    usuario_entrega_id      INTEGER,

    fecha_recepcion         TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    fecha_entrega_estimada  TEXT,
    fecha_entrega_real      TEXT,

    estado                  TEXT NOT NULL DEFAULT 'recibido',
    num_piezas              INTEGER NOT NULL DEFAULT 0,  -- se recalcula al agregar items

    subtotal                REAL NOT NULL DEFAULT 0,
    descuento               REAL NOT NULL DEFAULT 0,
    total                   REAL NOT NULL DEFAULT 0,
    anticipo                REAL NOT NULL DEFAULT 0,
    saldo                   REAL GENERATED ALWAYS AS (total - anticipo) VIRTUAL,

    notas                   TEXT,

    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (tipo_servicio_id) REFERENCES tipos_servicio(id),
    FOREIGN KEY (usuario_recepcion_id) REFERENCES usuarios(id),
    FOREIGN KEY (usuario_entrega_id) REFERENCES usuarios(id)
);

CREATE INDEX idx_ordenes_folio ON ordenes(folio);
CREATE INDEX idx_ordenes_cliente ON ordenes(cliente_id);
CREATE INDEX idx_ordenes_estado ON ordenes(estado);
CREATE INDEX idx_ordenes_fecha_recepcion ON ordenes(fecha_recepcion);

-- ------------------------------------------------------------
-- Piezas / items de la orden
-- ------------------------------------------------------------

-- Cada renglón es una pieza (o un grupo de piezas idénticas vía 'cantidad').
-- estado_pieza solo se usa activamente cuando el tipo_servicio de la
-- orden tiene seguimiento_por_pieza = 1 (tintorería). Para planchado
-- simplemente queda igual al estado de la orden (se sincroniza).

CREATE TABLE items_orden (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id        INTEGER NOT NULL,
    prenda_catalogo_id INTEGER,             -- opcional, referencia al catálogo
    descripcion     TEXT NOT NULL,          -- 'Camisa blanca a rayas', copiado o libre
    color           TEXT,
    marca           TEXT,
    cantidad        INTEGER NOT NULL DEFAULT 1,
    precio_unitario REAL NOT NULL DEFAULT 0,
    subtotal        REAL GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,

    estado_pieza    TEXT NOT NULL DEFAULT 'recibido',  -- mismos valores que orden.estado
    notas           TEXT,                              -- ej. 'mancha en manga', 'botón flojo'

    FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE,
    FOREIGN KEY (prenda_catalogo_id) REFERENCES prendas_catalogo(id)
);

CREATE INDEX idx_items_orden ON items_orden(orden_id);
CREATE INDEX idx_items_estado ON items_orden(estado_pieza);

-- ------------------------------------------------------------
-- Historial de cambios de estado (auditoría + útil para reportes
-- de tiempos de proceso)
-- ------------------------------------------------------------

CREATE TABLE historial_estados (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id        INTEGER NOT NULL,
    item_orden_id   INTEGER,                -- NULL si el cambio es a nivel orden completa
    estado_anterior TEXT,
    estado_nuevo    TEXT NOT NULL,
    usuario_id      INTEGER,
    fecha           TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),

    FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE,
    FOREIGN KEY (item_orden_id) REFERENCES items_orden(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- ------------------------------------------------------------
-- Pagos (para soportar anticipo + pago restante en entrega)
-- ------------------------------------------------------------

CREATE TABLE pagos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id        INTEGER NOT NULL,
    monto           REAL NOT NULL,
    metodo_pago     TEXT NOT NULL DEFAULT 'efectivo',  -- 'efectivo', 'tarjeta', 'transferencia'
    fecha           TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    usuario_id      INTEGER,

    FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);