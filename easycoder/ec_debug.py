import sys, os, json, html
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QToolBar
)
from PySide6.QtGui import QAction, QKeySequence, QTextCursor
from PySide6.QtCore import Qt, QTimer, QProcess
from typing import Any

class Object():
    """Dynamic object that allows arbitrary attribute assignment"""
    def __setattr__(self, name: str, value: Any) -> None:
        self.__dict__[name] = value
    
    def __getattr__(self, name: str) -> Any:
        return self.__dict__.get(name)

class Debugger(QMainWindow):

    ###########################################################################
    # The left-hand column of the main window
    class MainLeftColumn(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("Left column"))
            layout.addStretch()
    
    ###########################################################################
    # The right-hand column of the main window
    class MainRightColumn(QWidget):
        scroll: QScrollArea
        layout: QHBoxLayout  # type: ignore[assignment]
        blob: QLabel
        
        def __init__(self, parent=None):
            super().__init__(parent)

            # Create a scroll area - its content widget holds the lines
            self.scroll = QScrollArea(self)
            self.scroll.setWidgetResizable(True)

            # Ensure this widget and the scroll area expand to fill available space
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            self.content = QWidget()
            # let the content expand horizontally but have flexible height
            self.content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

            self.inner_layout = QVBoxLayout(self.content)
            # spacing and small top/bottom margins to separate lines
            self.inner_layout.setSpacing(0)
            self.inner_layout.setContentsMargins(0, 0, 0, 0)

            self.scroll.setWidget(self.content)

            # outer layout for this widget contains only the scroll area
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.addWidget(self.scroll)
            # ensure the scroll area gets the stretch so it fills the parent
            main_layout.setStretch(0, 1)

        #######################################################################
        # Add a line to the right-hand column
        def addLine(self, spec):
            class Label(QLabel):
                def __init__(self, text, fixed_width=None, align=Qt.AlignmentFlag.AlignLeft, on_click=spec.onClick):
                    super().__init__()
                    self.setText(text)
                    # remove QLabel's internal margins/padding to reduce top/bottom space
                    self.setMargin(0)
                    self.setContentsMargins(0, 0, 0, 0)
                    self.setStyleSheet("padding:0px; margin:0px; font-family: mono")
                    fm = self.fontMetrics()
                    # set a compact fixed height based on font metrics
                    self.setFixedHeight(fm.height())
                    # optional fixed width (used for the lino column)
                    if fixed_width is not None:
                        self.setFixedWidth(fixed_width)
                    # align horizontally (keep vertically centered)
                    self.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                    # optional click callback
                    self._on_click = on_click

                def mousePressEvent(self, event):
                    if self._on_click:
                        try:
                            self._on_click()
                        except Exception:
                            pass
                    super().mousePressEvent(event)

            spec.label = self
            panel = QWidget()
            # ensure the panel itself has no margins
            try:
                panel.setContentsMargins(0, 0, 0, 0)
            except Exception:
                pass
            # tidy layout: remove spacing/margins so lines sit flush
            layout = QHBoxLayout(panel)
            layout.setSpacing(0)
            layout.setContentsMargins(0, 0, 0, 0)
            self.layout: QHBoxLayout = layout  # type: ignore
            # make panel take minimal vertical space
            panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            # compute width to fit a 4-digit line number using this widget's font
            fm_main = self.fontMetrics()
            width_4 = fm_main.horizontalAdvance('0000') + 8

            # create the red blob (always present). We'll toggle its opacity
            # by changing the stylesheet (rgba alpha 255/0). Do NOT store it
            # on the MainRightColumn instance — keep it per-line.
            blob = QLabel()
            blob_size = 10
            blob.setFixedSize(blob_size, blob_size)

            def set_blob_visible(widget, visible):
                alpha = 255 if visible else 0
                widget.setStyleSheet(f"background-color: rgba(255,0,0,{alpha}); border-radius: {blob_size//2}px; margin:0px; padding:0px;")
                widget._blob_visible = visible
                # force repaint
                widget.update()

            # attach methods to this blob so callers can toggle it via spec.label
            blob.showBlob = lambda: set_blob_visible(blob, True)  # type: ignore[attr-defined]
            blob.hideBlob = lambda: set_blob_visible(blob, False)  # type: ignore[attr-defined]

            # initialize according to spec flag
            if spec.bp:
                blob.showBlob()  # type: ignore[attr-defined]
            else:
                blob.hideBlob()  # type: ignore[attr-defined]

            # expose the blob to the outside via spec['label'] so onClick can call showBlob/hideBlob
            spec.label = blob

            # create the line-number label; clicking it reports back to the caller
            lino_label = Label(str(spec.lino+1), fixed_width=width_4, align=Qt.AlignmentFlag.AlignRight,
                               on_click=lambda: spec.onClick(spec.lino))
            lino_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            # create the text label for the line itself
            text_label = Label(spec.line, fixed_width=None, align=Qt.AlignmentFlag.AlignLeft)
            text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            layout.addWidget(lino_label)
            layout.addSpacing(10)
            layout.addWidget(blob, 0, Qt.AlignmentFlag.AlignVCenter)
            layout.addSpacing(3)
            layout.addWidget(text_label)
            self.inner_layout.addWidget(panel)
            return panel
        
        def showBlob(self):
            self.blob.setStyleSheet("background-color: red; border-radius: 5px; margin:0px; padding:0px;")
        
        def hideBlob(self):
            self.blob.setStyleSheet("background-color: none; border-radius: 5px; margin:0px; padding:0px;")
        
        def addStretch(self):
            self.layout.addStretch()

    ###########################################################################
    # Main debugger class initializer
    def __init__(self, program, width=800, height=600, ratio=0.2):
        super().__init__()
        self.program = program
        self.setWindowTitle("EasyCoder Debugger")
        self.setMinimumSize(width, height)
        self.stopped = True

        # try to load saved geometry from ~/.ecdebug.conf
        cfg_path = os.path.join(os.path.expanduser("~"), ".ecdebug.conf")
        initial_width = width
        # default console height (pixels) if not stored in cfg
        console_height = 150
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                x = int(cfg.get("x", 0))
                y = int(cfg.get("y", 0))
                w = int(cfg.get("width", width))
                h = int(cfg.get("height", height))
                ratio =float(cfg.get("ratio", ratio))
                # load console height if present
                console_height = int(cfg.get("console_height", console_height))
                # Apply loaded geometry
                self.setGeometry(x, y, w, h)
                initial_width = w
        except Exception:
            # ignore errors and continue with defaults
            initial_width = width

        # process handle for running scripts
        self._proc = None
        # in-process Program instance and writer
        self._program = None
        self._writer = None
        self._orig_stdout = None
        self._orig_stderr = None
        self._flush_timer = None

        # Keep a ratio so proportions are preserved when window is resized
        self.ratio = ratio

        # Central horizontal splitter (left/right)
        self.hsplitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.hsplitter.setHandleWidth(8)
        self.hsplitter.splitterMoved.connect(self.on_splitter_moved)

        # Left pane
        left = QFrame()
        left.setFrameShape(QFrame.Shape.StyledPanel)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        self.leftColumn = self.MainLeftColumn()
        left_layout.addWidget(self.leftColumn)
        left_layout.addStretch()

        # Right pane
        right = QFrame()
        right.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        self.rightColumn = self.MainRightColumn()
        # Give the rightColumn a stretch factor so its scroll area fills the vertical space
        right_layout.addWidget(self.rightColumn, 1)

        # Add panes to horizontal splitter
        self.hsplitter.addWidget(left)
        self.hsplitter.addWidget(right)

        # Initial sizes (proportional) for horizontal splitter
        total = initial_width
        self.hsplitter.setSizes([int(self.ratio * total), int((1 - self.ratio) * total)])

        # Create a vertical splitter so we can add a resizable console panel at the bottom
        self.vsplitter = QSplitter(Qt.Orientation.Vertical, self)
        self.vsplitter.setHandleWidth(6)
        # top: the existing horizontal splitter
        self.vsplitter.addWidget(self.hsplitter)

        # bottom: console panel
        console_frame = QFrame()
        console_frame.setFrameShape(QFrame.Shape.StyledPanel)
        console_layout = QVBoxLayout(console_frame)
        console_layout.setContentsMargins(4, 4, 4, 4)
        # simple read-only text console for script output and messages
        from PySide6.QtWidgets import QTextEdit
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        console_layout.addWidget(self.console)
        self.vsplitter.addWidget(console_frame)

        # Set initial vertical sizes: prefer saved console_height if available
        try:
            total_h = int(h) if 'h' in locals() else max(300, self.height())
            ch = max(50, min(total_h - 50, console_height))
            self.vsplitter.setSizes([int(total_h - ch), int(ch)])
        except Exception:
            pass

        # Use the vertical splitter as the central widget
        self.setCentralWidget(self.vsplitter)
        self.parse(program.script.lines)
        self.show()

    def on_splitter_moved(self, pos, index):
        # Update stored ratio when user drags the splitter
        left_width = self.hsplitter.widget(0).width()
        total = max(1, sum(w.width() for w in (self.hsplitter.widget(0), self.hsplitter.widget(1))))
        self.ratio = left_width / total

    def resizeEvent(self, event):
        # Preserve the proportional widths when the window is resized
        total_width = max(1, self.width())
        left_w = max(0, int(self.ratio * total_width))
        right_w = max(0, total_width - left_w)
        self.hsplitter.setSizes([left_w, right_w])
        super().resizeEvent(event)

    ###########################################################################
    # Parse a script into the right-hand column
    def parse(self, script):
        self.scriptLines = []
        # Clear existing lines from the right column layout
        layout = self.rightColumn.inner_layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Parse and add new lines
        lino = 0
        for line in script:
            if len(line) > 0:
                line = line.replace("\t", "   ")
                line = self.coloriseLine(line, lino)
            else:
                # still need to call coloriseLine to keep token list in sync
                self.coloriseLine(line, lino)
            lineSpec = Object()
            lineSpec.lino = lino
            lineSpec.line = line
            lineSpec.bp = False
            lineSpec.onClick = self.onClickLino
            lino += 1
            self.scriptLines.append(lineSpec)
            lineSpec.panel = self.rightColumn.addLine(lineSpec)
        self.rightColumn.addStretch()
    
    ###########################################################################
    # Colorise a line of script for HTML display
    def coloriseLine(self, line, lino=None):
        output = ''

        # Preserve leading spaces (render as &nbsp; except the first)
        if len(line) > 0 and line[0] == ' ':
            output += '<span>'
            n = 0
            while n < len(line) and line[n] == ' ': n += 1
            output += '&nbsp;' * (n - 1)
            output += '</span>'

        # Find the first unquoted ! (not inside backticks)
        comment_start = None
        in_backtick = False
        for idx, c in enumerate(line):
            if c == '`':
                in_backtick = not in_backtick
            elif c == '!' and not in_backtick:
                comment_start = idx
                break

        if comment_start is not None:
            code_part = line[:comment_start]
            comment_part = line[comment_start:]
        else:
            code_part = line
            comment_part = None

        # Tokenize code_part as before (respecting backticks)
        tokens = []
        i = 0
        L = len(code_part)
        while i < L:
            if code_part[i].isspace():
                i += 1
                continue
            if code_part[i] == '`':
                j = code_part.find('`', i + 1)
                if j == -1:
                    tokens.append(code_part[i:])
                    break
                else:
                    tokens.append(code_part[i:j+1])
                    i = j + 1
            else:
                j = i
                while j < L and not code_part[j].isspace():
                    j += 1
                tokens.append(code_part[i:j])
                i = j

        # Colour code tokens and generate a list of elements
        for token in tokens:
            if token == '':
                continue
            elif token[0].isupper():
                esc = html.escape(token)
                element = f'&nbsp;<span style="color: purple; font-weight: bold;">{esc}</span>'
            elif token[0].isdigit():
                esc = html.escape(token)
                element = f'&nbsp;<span style="color: green;">{esc}</span>'
            elif token[0] == '`':
                esc = html.escape(token)
                element = f'&nbsp;<span style="color: peru;">{esc}</span>'
            else:
                esc = html.escape(token)
                element = f'&nbsp;<span>{esc}</span>'
            output += element
        # Colour comment if present
        if comment_part is not None:
            esc = html.escape(comment_part)
            output += f'<span style="color: green;">&nbsp;{esc}</span>'

        return output
    
    ###########################################################################
    # Here when the user clicks a line number
    def onClickLino(self, lino):
        lineSpec = self.scriptLines[lino]
        lineSpec.bp = not lineSpec.bp
        if lineSpec.bp: lineSpec.label.showBlob()
        else: lineSpec.label.hideBlob()
        # Set a breakpoint on this command
        command = self.program.code[self.program.pc]
        command['bp'] = True
        self.program.code[self.program.pc] = command
    
    ###########################################################################
    # Scroll to a given line number
    def scrollTo(self, lino):
        # Ensure the line number is valid
        if lino < 0 or lino >= len(self.scriptLines):
            return
        
        # Get the panel widget for this line
        lineSpec = self.scriptLines[lino]
        panel = lineSpec.panel
        
        if not panel:
            return
        
        # Get the scroll area from the right column
        scroll_area = self.rightColumn.scroll
        
        # Get the vertical position of the panel relative to the content widget
        panel_y = panel.y()
        panel_height = panel.height()
        
        # Get the viewport height (visible area)
        viewport_height = scroll_area.viewport().height()
        
        # Calculate the target scroll position to center the panel
        # We want the panel's center to align with the viewport's center
        target_scroll = panel_y + (panel_height // 2) - (viewport_height // 2)
        
        # Clamp to valid scroll range
        scrollbar = scroll_area.verticalScrollBar()
        target_scroll = max(scrollbar.minimum(), min(target_scroll, scrollbar.maximum()))
        
        # Smoothly scroll to the target position
        scrollbar.setValue(target_scroll)
        
        # Bring the window to the front
        self.raise_()
        self.activateWindow()
    
    ###########################################################################
    # Here when each instruction is about to run
    def step(self):
        if self.stopped:
            lino=self.program.code[self.program.pc]['lino']
            print(lino)
            self.scrollTo(lino)
            return False
        else:
            if self.program.code[self.program.pc]['bp']:
                pass
        return True