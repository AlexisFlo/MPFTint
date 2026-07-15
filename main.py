"""
main.py

Punto de entrada de la aplicación. Inicializa la base de datos
(si no existe) y lanza la ventana principal.
"""

import sys
from PyQt5.QtWidgets import QApplication

from db.database import init_db
from ui.main_window import MainWindow


def main():
    init_db()  # crea tintoreria.db y las tablas si no existen (no borra datos)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    ventana = MainWindow()
    ventana.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()