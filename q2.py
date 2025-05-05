from PySide6.QtWidgets import (
    QApplication, QLineEdit, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QFormLayout
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import sys

class ScatterPlotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scatter Plot Example")

        # Create a form layout for X-Y inputs
        form_layout = QFormLayout()
        self.x_inputs = []
        self.y_inputs = []

        for i in range(5):
            x_input = QLineEdit()
            y_input = QLineEdit()
            self.x_inputs.append(x_input)
            self.y_inputs.append(y_input)
            form_layout.addRow(f"X{i+1}:", x_input)
            form_layout.addRow(f"Y{i+1}:", y_input)

        # Plot button
        self.plot_button = QPushButton("Plot")
        self.plot_button.clicked.connect(self.plot_data)

        # Matplotlib canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.plot_button)
        main_layout.addWidget(self.canvas)

        self.setLayout(main_layout)

    def plot_data(self):
        # Collect data from input fields
        x_data = []
        y_data = []

        try:
            for x_input, y_input in zip(self.x_inputs, self.y_inputs):
                x = float(x_input.text())
                y = float(y_input.text())
                x_data.append(x)
                y_data.append(y)
        except ValueError:
            print("Please enter valid numeric values for all X and Y inputs.")
            return

        # Plot the data
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.scatter(x_data, y_data, color="blue")
        ax.set_title("Scatter Plot")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        self.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    scatter_plot_app = ScatterPlotApp()
    scatter_plot_app.show()
    sys.exit(app.exec())