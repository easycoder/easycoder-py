from PySide6.QtWidgets import (
    QApplication, QLineEdit, QLabel, QPushButton, QVBoxLayout, QWidget, QFormLayout
)
import sys

class FormApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Form Example")

        # Create a form layout
        form_layout = QFormLayout()

        # Input fields
        self.name_input = QLineEdit()
        self.address_input = QLineEdit()
        self.telephone_input = QLineEdit()

        # Add input fields to the form layout
        form_layout.addRow("Name:", self.name_input)
        form_layout.addRow("Address:", self.address_input)
        form_layout.addRow("Telephone:", self.telephone_input)

        # OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.print_data)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.ok_button)

        self.setLayout(main_layout)

    def print_data(self):
        # Collect data from input fields
        name = self.name_input.text()
        address = self.address_input.text()
        telephone = self.telephone_input.text()

        # Print the collected data
        print(f"Name: {name}")
        print(f"Address: {address}")
        print(f"Telephone: {telephone}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    form_app = FormApp()
    form_app.show()
    sys.exit(app.exec())