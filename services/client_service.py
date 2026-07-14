"""
services/cliente_service.py
"""

from typing import Optional, List
from db.database import get_cursor
from models.models import Cliente


def crear_cliente(nombre: str, telefono: str = None, email: str = None,
                   direccion: str = None, notas: str = None) -> Cliente:
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO clientes (nombre, telefono, email, direccion, notas)
            VALUES (?, ?, ?, ?, ?)
            """,
            (nombre, telefono, email, direccion, notas),
        )
        cliente_id = cur.lastrowid

    return obtener_cliente(cliente_id)


def obtener_cliente(cliente_id: int) -> Optional[Cliente]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
        row = cur.fetchone()
        return _row_to_cliente(row) if row else None


def buscar_clientes(texto: str) -> List[Cliente]:
    """Busca por nombre o teléfono (LIKE), para el autocompletado en recepción."""
    like = f"%{texto}%"
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM clientes
            WHERE nombre LIKE ? OR telefono LIKE ?
            ORDER BY nombre
            LIMIT 25
            """,
            (like, like),
        )
        return [_row_to_cliente(row) for row in cur.fetchall()]


def actualizar_cliente(cliente: Cliente) -> None:
    with get_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE clientes
            SET nombre = ?, telefono = ?, email = ?, direccion = ?, notas = ?
            WHERE id = ?
            """,
            (cliente.nombre, cliente.telefono, cliente.email,
             cliente.direccion, cliente.notas, cliente.id),
        )


def _row_to_cliente(row) -> Cliente:
    return Cliente(
        id=row["id"],
        nombre=row["nombre"],
        telefono=row["telefono"],
        email=row["email"],
        direccion=row["direccion"],
        notas=row["notas"],
        fecha_registro=row["fecha_registro"],
    )