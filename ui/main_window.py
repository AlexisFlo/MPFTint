"""
ui/main_window.py

Ventana principal de la aplicación. Usa una barra lateral fija para
navegar entre las secciones: Recepción, Seguimiento y Entrega.

Estructura: un QStackedWidget cambia de vista según el botón activo
en la barra lateral. Cada vista es un QWidget independiente que se
irá reemplazando por la implementación real (por ahora, placeholders
excepto por el título y una etiqueta descriptiva).
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QFrame
)
from PyQt5.QtCore import Qt


SIDEBAR_WIDTH = 200

# Paleta simple y consistente para toda la app
COLOR_SIDEBAR_BG = "#2b2d42"
COLOR_SIDEBAR_TEXT = "#edf2f4"
COLOR_SIDEBAR_ACTIVE = "#8d99ae"
COLOR_CONTENT_BG = "#f8f9fa"


class SidebarButton(QPushButton):
    """Botón de navegación con estilo consistente y estado activo/inactivo."""

    def __init__(self, texto: str):
        super().__init__(texto)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(48)
        self._actualizar_estilo()
        self.toggled.connect(self._actualizar_estilo)

    def _actualizar_estilo(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_SIDEBAR_ACTIVE};
                    color: white;
                    text-align: left;
                    padding-left: 20px;
                    border: none;
                    font-weight: bold;
                    font-size: 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLOR_SIDEBAR_BG};
                    color: {COLOR_SIDEBAR_TEXT};
                    text-align: left;
                    padding-left: 20px;
                    border: none;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: #40435f;
                }}
            """)


class PlaceholderView(QWidget):
    """Vista temporal mientras se construye la implementación real de cada sección."""

    def __init__(self, titulo: str, descripcion: str):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        titulo_label = QLabel(titulo)
        titulo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2b2d42;")

        desc_label = QLabel(descripcion)
        desc_label.setStyleSheet("font-size: 14px; color: #6c757d; margin-top: 8px;")
        desc_label.setWordWrap(True)

        layout.addWidget(titulo_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Tintorería")
        self.resize(1000, 650)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLOR_CONTENT_BG}; }}")

        self._construir_ui()

    def _construir_ui(self):
        contenedor = QWidget()
        layout_principal = QHBoxLayout(contenedor)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # --- Barra lateral ---
        sidebar = QFrame()
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        sidebar.setStyleSheet(f"background-color: {COLOR_SIDEBAR_BG};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 0)
        sidebar_layout.setSpacing(4)

        titulo_app = QLabel("🧺  Tintorería")
        titulo_app.setStyleSheet(
            f"color: {COLOR_SIDEBAR_TEXT}; font-size: 16px; font-weight: bold; "
            "padding: 10px 20px 24px 20px;"
        )
        sidebar_layout.addWidget(titulo_app)

        self.btn_recepcion = SidebarButton("📥  Recepción")
        self.btn_seguimiento = SidebarButton("🔄  Seguimiento")
        self.btn_entrega = SidebarButton("📤  Entrega")

        for btn in (self.btn_recepcion, self.btn_seguimiento, self.btn_entrega):
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # --- Contenido (stacked) ---
        self.stack = QStackedWidget()

        self.vista_recepcion = PlaceholderView(
            "Recepción",
            "Aquí irá el formulario de recepción: selección/alta de cliente, "
            "tipo de servicio, captura de piezas y generación del folio."
        )
        self.vista_seguimiento = PlaceholderView(
            "Seguimiento",
            "Aquí irá el listado de órdenes activas con su estado, "
            "y el detalle por pieza para las órdenes de tintorería."
        )
        self.vista_entrega = PlaceholderView(
            "Entrega",
            "Aquí irá la búsqueda de órdenes por folio o cliente, "
            "y el flujo de cobro y entrega."
        )

        self.stack.addWidget(self.vista_recepcion)   # índice 0
        self.stack.addWidget(self.vista_seguimiento) # índice 1
        self.stack.addWidget(self.vista_entrega)      # índice 2

        layout_principal.addWidget(sidebar)
        layout_principal.addWidget(self.stack)

        self.setCentralWidget(contenedor)

        # --- Navegación ---
        botones_a_indice = [
            (self.btn_recepcion, 0),
            (self.btn_seguimiento, 1),
            (self.btn_entrega, 2),
        ]

        def hacer_navegador(indice, boton_actual):
            def navegar():
                self.stack.setCurrentIndex(indice)
                for boton, _ in botones_a_indice:
                    boton.setChecked(boton is boton_actual)
            return navegar

        for boton, indice in botones_a_indice:
            boton.clicked.connect(hacer_navegador(indice, boton))

        # Vista inicial: Recepción
        self.btn_recepcion.setChecked(True)
        self.stack.setCurrentIndex(0)