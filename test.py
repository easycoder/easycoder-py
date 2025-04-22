import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                              QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QFormLayout)

class InputWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Two Column Input Form")
        self.setGeometry(100, 100, 600, 300)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Create left column (wider)
        left_column = QWidget()
        left_layout = QFormLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)  # Right margin larger for more width
        left_layout.setSpacing(5)
        
        # Add 4 label-input pairs to left column
        left_labels = ["Name:", "Email:", "Address:", "Phone:"]
        for label_text in left_labels:
            line_edit = QLineEdit()
            left_layout.addRow(QLabel(label_text), line_edit)
        
        # Create right column (narrower)
        right_column = QWidget()
        right_layout = QFormLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)
        
        # Add 4 label-input pairs to right column
        right_labels = ["ID:", "Department:", "Position:", "Date:"]
        for label_text in right_labels:
            line_edit = QLineEdit()
            right_layout.addRow(QLabel(label_text), line_edit)
        
        # Add columns to main layout with stretch factors to control width
        main_layout.addWidget(left_column, stretch=2)  # Left column gets 2/3 of space
        main_layout.addWidget(right_column, stretch=1)  # Right column gets 1/3 of space
        
        # Add some spacing between columns
        main_layout.setSpacing(20)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InputWindow()
    window.show()
    sys.exit(app.exec())