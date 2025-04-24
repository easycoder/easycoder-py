import sys

from PySide6.QtWidgets import (QApplication, 
                               QDialog, 
                               QMainWindow, 
                               QPushButton, 
                               QDialogButtonBox,
                               QVBoxLayout,
                               QLabel)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My App")

        button = QPushButton("Press me for a dialog!")
        button.clicked.connect(self.button_clicked)
        self.setCentralWidget(button)

    def button_clicked(self, s):
        print("click", s)

        dlg = QDialog()
        dlg.setWindowTitle("HELLO!")

        QBtn = (
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        dlg.buttonBox = QDialogButtonBox(QBtn)
        dlg.buttonBox.accepted.connect(dlg.accept)
        dlg.buttonBox.rejected.connect(dlg.reject)

        layout = QVBoxLayout()
        message = QLabel("Something happened, is that OK?")
        layout.addWidget(message)
        layout.addWidget(dlg.buttonBox)
        dlg.setLayout(layout)

        result = dlg.exec()
        print(result)
        if result:
            print("Success!")
        else:
            print("Cancel!")

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()