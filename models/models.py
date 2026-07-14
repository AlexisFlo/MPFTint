"""
models/models.py

Dataclasses que representan las filas principales de la base de datos.
No son un ORM: son contenedores tipados para pasar datos entre la capa
de servicios y la UI de forma clara.
"""

from dataclasses import dataclass, field
from typing import Optional


# Valores válidos para estado de orden / pieza.
# Se centralizan aquí para no tener strings sueltos regados en el código.
ESTADO_RECIBIDO = "recibido"
ESTADO_EN_PROCESO = "en_proceso"
ESTADO_LISTO = "listo"
ESTADO_ENTREGADO = "entregado"
ESTADO_CANCELADO = "cancelado"

ESTADOS_VALIDOS = [
    ESTADO_RECIBIDO,
    ESTADO_EN_PROCESO,
    ESTADO_LISTO,
    ESTADO_ENTREGADO,
    ESTADO_CANCELADO,
]

# Orden lógico de avance (útil para validar que no se "retroceda" por error,
# y para calcular el estado mínimo/máximo de un conjunto de piezas)
ORDEN_ESTADOS = {
    ESTADO_RECIBIDO: 0,
    ESTADO_EN_PROCESO: 1,
    ESTADO_LISTO: 2,
    ESTADO_ENTREGADO: 3,
    ESTADO_CANCELADO: 99,
}


@dataclass
class Cliente:
    id: Optional[int]
    nombre: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None
    fecha_registro: Optional[str] = None


@dataclass
class TipoServicio:
    id: int
    nombre: str
    seguimiento_por_pieza: bool


@dataclass
class ItemOrden:
    id: Optional[int]
    orden_id: Optional[int]
    descripcion: str
    cantidad: int = 1
    precio_unitario: float = 0.0
    color: Optional[str] = None
    marca: Optional[str] = None
    prenda_catalogo_id: Optional[int] = None
    estado_pieza: str = ESTADO_RECIBIDO
    notas: Optional[str] = None
    subtotal: float = 0.0  # calculado por la BD (GENERATED), solo lectura


@dataclass
class Orden:
    id: Optional[int]
    folio: str
    cliente_id: int
    tipo_servicio_id: int
    estado: str = ESTADO_RECIBIDO
    fecha_recepcion: Optional[str] = None
    fecha_entrega_estimada: Optional[str] = None
    fecha_entrega_real: Optional[str] = None
    num_piezas: int = 0
    subtotal: float = 0.0
    descuento: float = 0.0
    total: float = 0.0
    anticipo: float = 0.0
    saldo: float = 0.0  # calculado por la BD, solo lectura
    notas: Optional[str] = None
    usuario_recepcion_id: Optional[int] = None
    usuario_entrega_id: Optional[int] = None
    items: list = field(default_factory=list)  # List[ItemOrden], se llena al consultar