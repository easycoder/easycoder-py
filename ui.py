from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QWidget, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QPixmap, QFont, QPalette, QBrush
from PySide6.QtCore import Qt
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Custom UI")
        self.setFixedSize(600, 1024)  # Set the window size to 600x1024

        # Set the background image
        palette = QPalette()
        background_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/backdrop.jpg")
        palette.setBrush(QPalette.Window, QBrush(background_pixmap))
        self.setPalette(palette)

        # Main layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(10)  # Set spacing between rows to 10

        # Create 5 rows
        for _ in range(5):
            row = self.create_row()
            main_layout.addWidget(row)

        # Add a stretch below the last row
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.setCentralWidget(main_widget)

    def create_row(self):
        """Create a single row with the specified elements."""
        row_widget = QWidget()
        row_widget.setFixedHeight(1024 // 12)  # Each row is 1/12 the height of the window
        row_widget.setStyleSheet("background-color: #ffffcc; border: 2px solid gray;")  # Set background and border

        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(10, 0, 10, 0)  # Add margins for spacing
        row_layout.setSpacing(10)  # Add spacing between elements

        # Icon 1: Clock
        clock_icon = QLabel()
        clock_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/clock.png").scaled(1024 // 12 * 3 // 4, 1024 // 12 * 3 // 4, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        clock_icon.setPixmap(clock_pixmap)
        clock_icon.setStyleSheet("border-left: none; border-right: none;")

        # Name label
        name_label = QLabel("Room Name")
        name_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        name_label.setStyleSheet("background-color: transparent; border: none;")  # Transparent background
        font = QFont()
        font.setPointSize(16)  # Adjust font size to fit at least 20 characters
        font.setBold(True)  # Make the font bold
        name_label.setFont(font)

        # Button with white text and blue background
        button = QPushButton("20.0°C")
        button.setStyleSheet("color: white; background-color: blue; border: none;")
        button.setFixedSize(80, 40)  # Adjust button size
        button.setFont(font)  # Use the same font as the label

        # Icon 2: Edit
        edit_icon = QLabel()
        edit_pixmap = QPixmap("/home/graham/dev/rbr/ui/main/edit.png").scaled(1024 // 12 * 3 // 4, 1024 // 12 * 3 // 4, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        edit_icon.setPixmap(edit_pixmap)
        edit_icon.setStyleSheet("border-left: none; border-right: none;")

        # Add elements to the row layout
        row_layout.addWidget(clock_icon)
        row_layout.addWidget(name_label, 1)  # Expand the name label to use all spare space
        row_layout.addWidget(button)
        row_layout.addWidget(edit_icon)

        return row_widget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
