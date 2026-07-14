"""
services/orden_service.py

Contiene la lógica de negocio central:
- Generación de folios
- Creación de órdenes con sus piezas
- Sincronización de estado orden <-> piezas, respetando si el tipo
  de servicio tiene seguimiento_por_pieza o no.
"""

from typing import Optional, List
from datetime import datetime

from db.database import get_cursor
from models.models import (
    Orden, ItemOrden, TipoServicio,
    ESTADO_RECIBIDO, ESTADO_LISTO, ESTADO_ENTREGADO,
    ORDEN_ESTADOS, ESTADOS_VALIDOS,
)


# ------------------------------------------------------------
# Folios
# ------------------------------------------------------------

def generar_folio() -> str:
    """
    Genera el siguiente folio consecutivo con formato ORD-000123.
    Se basa en el máximo id existente + 1 (simple y suficiente para
    un solo punto de venta / instancia local de SQLite).
    """
    with get_cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS siguiente FROM ordenes")
        siguiente = cur.fetchone()["siguiente"]
    return f"ORD-{siguiente:06d}"


# ------------------------------------------------------------
# Tipos de servicio
# ------------------------------------------------------------

def obtener_tipo_servicio(tipo_servicio_id: int) -> Optional[TipoServicio]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM tipos_servicio WHERE id = ?", (tipo_servicio_id,))
        row = cur.fetchone()
        if not row:
            return None
        return TipoServicio(
            id=row["id"],
            nombre=row["nombre"],
            seguimiento_por_pieza=bool(row["seguimiento_por_pieza"]),
        )


def listar_tipos_servicio() -> List[TipoServicio]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM tipos_servicio ORDER BY id")
        return [
            TipoServicio(id=r["id"], nombre=r["nombre"],
                         seguimiento_por_pieza=bool(r["seguimiento_por_pieza"]))
            for r in cur.fetchall()
        ]


# ------------------------------------------------------------
# Creación de orden (recepción)
# ------------------------------------------------------------

def crear_orden(cliente_id: int, tipo_servicio_id: int,
                 items: List[ItemOrden],
                 fecha_entrega_estimada: str = None,
                 anticipo: float = 0.0,
                 notas: str = None,
                 usuario_recepcion_id: int = None) -> Orden:
    """
    Crea una orden junto con sus piezas en una sola operación.
    El subtotal/total de la orden se calcula a partir de las piezas.
    """
    if not items:
        raise ValueError("Una orden debe tener al menos una pieza.")

    folio = generar_folio()
    subtotal = sum(item.cantidad * item.precio_unitario for item in items)
    total = subtotal  # aquí se restaría descuento si aplica
    num_piezas = sum(item.cantidad for item in items)

    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO ordenes (
                folio, cliente_id, tipo_servicio_id, estado, num_piezas,
                fecha_entrega_estimada, subtotal, total, anticipo, notas,
                usuario_recepcion_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (folio, cliente_id, tipo_servicio_id, ESTADO_RECIBIDO, num_piezas,
             fecha_entrega_estimada, subtotal, total, anticipo, notas,
             usuario_recepcion_id),
        )
        orden_id = cur.lastrowid

        for item in items:
            cur.execute(
                """
                INSERT INTO items_orden (
                    orden_id, prenda_catalogo_id, descripcion, color, marca,
                    cantidad, precio_unitario, estado_pieza, notas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (orden_id, item.prenda_catalogo_id, item.descripcion,
                 item.color, item.marca, item.cantidad, item.precio_unitario,
                 ESTADO_RECIBIDO, item.notas),
            )

        _registrar_historial(cur, orden_id, None, None, ESTADO_RECIBIDO,
                              usuario_recepcion_id)

    return obtener_orden(orden_id)


# ------------------------------------------------------------
# Consulta
# ------------------------------------------------------------

def obtener_orden(orden_id: int) -> Optional[Orden]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,))
        row = cur.fetchone()
        if not row:
            return None
        orden = _row_to_orden(row)

        cur.execute(
            "SELECT * FROM items_orden WHERE orden_id = ? ORDER BY id",
            (orden_id,),
        )
        orden.items = [_row_to_item(r) for r in cur.fetchall()]
        return orden


def buscar_orden_por_folio(folio: str) -> Optional[Orden]:
    with get_cursor() as cur:
        cur.execute("SELECT id FROM ordenes WHERE folio = ?", (folio,))
        row = cur.fetchone()
        return obtener_orden(row["id"]) if row else None


def listar_ordenes_activas() -> List[Orden]:
    """Órdenes que aún no se han entregado ni cancelado (para la vista de seguimiento)."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM ordenes
            WHERE estado NOT IN (?, ?)
            ORDER BY fecha_recepcion
            """,
            (ESTADO_ENTREGADO, "cancelado"),
        )
        return [_row_to_orden(r) for r in cur.fetchall()]


# ------------------------------------------------------------
# Cambios de estado
# ------------------------------------------------------------

def actualizar_estado_pieza(item_orden_id: int, nuevo_estado: str,
                             usuario_id: int = None) -> Orden:
    """
    Actualiza el estado de una pieza individual y recalcula el estado
    de la orden en consecuencia:

    - Si el tipo de servicio NO tiene seguimiento_por_pieza (ej. planchado),
      esta función no debería usarse pieza por pieza; se usa
      actualizar_estado_orden en su lugar. Aun así, por seguridad, si se
      llama aquí, se propaga el mismo estado a todas las piezas.

    - Si SÍ tiene seguimiento_por_pieza (tintorería): el estado de la
      orden se recalcula como el "mínimo" estado entre todas sus piezas
      (si una sola pieza sigue en_proceso, la orden completa no puede
      marcarse como lista).
    """
    _validar_estado(nuevo_estado)

    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT orden_id, estado_pieza FROM items_orden WHERE id = ?",
            (item_orden_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"No existe la pieza {item_orden_id}")

        orden_id = row["orden_id"]
        estado_anterior = row["estado_pieza"]

        cur.execute("SELECT tipo_servicio_id FROM ordenes WHERE id = ?", (orden_id,))
        tipo_servicio_id = cur.fetchone()["tipo_servicio_id"]

    tipo_servicio = obtener_tipo_servicio(tipo_servicio_id)

    if tipo_servicio.seguimiento_por_pieza:
        with get_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE items_orden SET estado_pieza = ? WHERE id = ?",
                (nuevo_estado, item_orden_id),
            )
            _registrar_historial(cur, orden_id, item_orden_id,
                                  estado_anterior, nuevo_estado, usuario_id)

        _recalcular_estado_orden_desde_piezas(orden_id, usuario_id)
    else:
        # Servicio sin seguimiento por pieza: el cambio se hace a nivel orden,
        # y se propaga a todas las piezas para mantener consistencia.
        actualizar_estado_orden(orden_id, nuevo_estado, usuario_id)

    return obtener_orden(orden_id)


def actualizar_estado_orden(orden_id: int, nuevo_estado: str,
                             usuario_id: int = None) -> Orden:
    """
    Cambia el estado de la orden completa y propaga el mismo estado
    a todas sus piezas (uso principal: planchado, o forzar un estado
    manualmente en tintorería, ej. 'cancelado').
    """
    _validar_estado(nuevo_estado)

    with get_cursor(commit=True) as cur:
        cur.execute("SELECT estado FROM ordenes WHERE id = ?", (orden_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"No existe la orden {orden_id}")
        estado_anterior = row["estado"]

        extra_fecha = ""
        params = [nuevo_estado]
        if nuevo_estado == ESTADO_ENTREGADO:
            extra_fecha = ", fecha_entrega_real = ?"
            params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        params.append(orden_id)

        cur.execute(
            f"UPDATE ordenes SET estado = ?{extra_fecha} WHERE id = ?",
            params,
        )
        cur.execute(
            "UPDATE items_orden SET estado_pieza = ? WHERE orden_id = ?",
            (nuevo_estado, orden_id),
        )
        _registrar_historial(cur, orden_id, None, estado_anterior,
                              nuevo_estado, usuario_id)

    return obtener_orden(orden_id)


def _recalcular_estado_orden_desde_piezas(orden_id: int, usuario_id: int = None) -> None:
    """
    Regla: la orden toma el estado MÍNIMO (menos avanzado) entre todas
    sus piezas activas. Ej: si hay piezas en 'recibido' y 'en_proceso',
    la orden queda en 'recibido'. Solo llega a 'listo' cuando TODAS
    las piezas están en 'listo' o más avanzado.

    Excepción: 'cancelado' no participa en este cálculo pieza a pieza
    en este MVP (se maneja manualmente vía actualizar_estado_orden).
    """
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT estado_pieza FROM items_orden WHERE orden_id = ?",
            (orden_id,),
        )
        estados_piezas = [r["estado_pieza"] for r in cur.fetchall()]

        if not estados_piezas:
            return

        estado_calculado = min(estados_piezas, key=lambda e: ORDEN_ESTADOS.get(e, 0))

        cur.execute("SELECT estado FROM ordenes WHERE id = ?", (orden_id,))
        estado_actual = cur.fetchone()["estado"]

        if estado_calculado != estado_actual:
            extra_fecha = ""
            params = [estado_calculado]
            if estado_calculado == ESTADO_ENTREGADO:
                extra_fecha = ", fecha_entrega_real = ?"
                params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            params.append(orden_id)

            cur.execute(
                f"UPDATE ordenes SET estado = ?{extra_fecha} WHERE id = ?",
                params,
            )
            _registrar_historial(cur, orden_id, None, estado_actual,
                                  estado_calculado, usuario_id)


# ------------------------------------------------------------
# Entrega
# ------------------------------------------------------------

def entregar_orden(orden_id: int, pago_final: float = 0.0,
                    usuario_entrega_id: int = None) -> Orden:
    """
    Marca la orden (y todas sus piezas) como entregada, y registra
    el pago final si se cubre saldo pendiente en ese momento.
    """
    with get_cursor(commit=True) as cur:
        if pago_final > 0:
            cur.execute(
                """
                INSERT INTO pagos (orden_id, monto, metodo_pago, usuario_id)
                VALUES (?, ?, 'efectivo', ?)
                """,
                (orden_id, pago_final, usuario_entrega_id),
            )
            cur.execute(
                "UPDATE ordenes SET anticipo = anticipo + ? WHERE id = ?",
                (pago_final, orden_id),
            )
        cur.execute(
            "UPDATE ordenes SET usuario_entrega_id = ? WHERE id = ?",
            (usuario_entrega_id, orden_id),
        )

    return actualizar_estado_orden(orden_id, ESTADO_ENTREGADO, usuario_entrega_id)


# ------------------------------------------------------------
# Helpers internos
# ------------------------------------------------------------

def _validar_estado(estado: str) -> None:
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(f"Estado inválido: {estado}. Válidos: {ESTADOS_VALIDOS}")


def _registrar_historial(cur, orden_id, item_orden_id, estado_anterior,
                          estado_nuevo, usuario_id) -> None:
    cur.execute(
        """
        INSERT INTO historial_estados (
            orden_id, item_orden_id, estado_anterior, estado_nuevo, usuario_id
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (orden_id, item_orden_id, estado_anterior, estado_nuevo, usuario_id),
    )


def _row_to_orden(row) -> Orden:
    return Orden(
        id=row["id"],
        folio=row["folio"],
        cliente_id=row["cliente_id"],
        tipo_servicio_id=row["tipo_servicio_id"],
        estado=row["estado"],
        fecha_recepcion=row["fecha_recepcion"],
        fecha_entrega_estimada=row["fecha_entrega_estimada"],
        fecha_entrega_real=row["fecha_entrega_real"],
        num_piezas=row["num_piezas"],
        subtotal=row["subtotal"],
        descuento=row["descuento"],
        total=row["total"],
        anticipo=row["anticipo"],
        saldo=row["saldo"],
        notas=row["notas"],
        usuario_recepcion_id=row["usuario_recepcion_id"],
        usuario_entrega_id=row["usuario_entrega_id"],
    )


def _row_to_item(row) -> ItemOrden:
    return ItemOrden(
        id=row["id"],
        orden_id=row["orden_id"],
        descripcion=row["descripcion"],
        cantidad=row["cantidad"],
        precio_unitario=row["precio_unitario"],
        color=row["color"],
        marca=row["marca"],
        prenda_catalogo_id=row["prenda_catalogo_id"],
        estado_pieza=row["estado_pieza"],
        notas=row["notas"],
        subtotal=row["subtotal"],
    )