import sys, os, json, html
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSplitter,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QToolBar,
    QPushButton,
    QInputDialog
)
from PySide6.QtGui import QTextCursor, QIcon
from PySide6.QtCore import Qt, QTimer
from typing import Any
from typing import Any, Optional

class Object():
    def __setattr__(self, name: str, value: Any) -> None:
        self.__dict__[name] = value
    
    def __getattr__(self, name: str) -> Any:
        return self.__dict__.get(name)

class Debugger(QMainWindow):
    # Help type-checkers know these attributes exist
    _flush_timer: Optional[QTimer]

    class ConsoleWriter:
        def __init__(self, debugger: 'Debugger'):
            self.debugger = debugger
            self._buf: list[str] = []

        def write(self, text: str):
            if not text:
                return
            # Buffer text and request a flush on the GUI timer
            self._buf.append(text)
            if self.debugger._flush_timer and not self.debugger._flush_timer.isActive():
                self.debugger._flush_timer.start()

        def flush(self):
            # Explicit flush request
            self.debugger._flush_console_buffer()

    ###########################################################################
    # The left-hand column of the main window
    class MainLeftColumn(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.debugger = parent
            layout = QVBoxLayout(self)
            
            # Create toolbar with icon buttons
            toolbar = QToolBar()
            toolbar.setMovable(False)
            
            # Get the icons directory path
            icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
            
            # Run button
            run_btn = QPushButton()
            run_icon_path = os.path.join(icons_dir, 'run.png')
            run_btn.setIcon(QIcon(run_icon_path))
            run_btn.setToolTip("Run")
            run_btn.clicked.connect(self.on_run_clicked)
            toolbar.addWidget(run_btn)
            
            # Step button
            step_btn = QPushButton()
            step_icon_path = os.path.join(icons_dir, 'step.png')
            step_btn.setIcon(QIcon(step_icon_path))
            step_btn.setToolTip("Step")
            step_btn.clicked.connect(self.on_step_clicked)
            toolbar.addWidget(step_btn)
            
            # Stop button
            stop_btn = QPushButton()
            stop_icon_path = os.path.join(icons_dir, 'stop.png')
            stop_btn.setIcon(QIcon(stop_icon_path))
            stop_btn.setToolTip("Stop")
            stop_btn.clicked.connect(self.on_stop_clicked)
            toolbar.addWidget(stop_btn)
            
            # Exit button
            exit_btn = QPushButton()
            exit_icon_path = os.path.join(icons_dir, 'exit.png')
            exit_btn.setIcon(QIcon(exit_icon_path))
            exit_btn.setToolTip("Exit")
            exit_btn.clicked.connect(self.on_exit_clicked)
            toolbar.addWidget(exit_btn)
            

            layout.addWidget(toolbar)

            # --- Watch panel (like VS Code) ---
            watch_panel = QFrame()
            watch_panel.setFrameShape(QFrame.Shape.StyledPanel)
            # Ensure the VARIABLES bar stretches to full available width
            watch_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            watch_layout = QHBoxLayout(watch_panel)
            watch_layout.setContentsMargins(4, 4, 4, 4)
            watch_layout.setSpacing(4)


            # Title label
            title_label = QLabel("VARIABLES")
            title_label.setStyleSheet("font-weight: bold; letter-spacing: 1px;")
            watch_layout.addWidget(title_label)

            # Stretch to push buttons right
            watch_layout.addStretch()

            # Placeholder add/remove icons (replace with real icons later)
            add_btn = QPushButton()
            add_btn.setToolTip("Add variable to watch")
            # TODO: set add_btn.setIcon(QIcon(path)) when icon is available
            add_btn.setText("+")
            add_btn.setFixedSize(24, 24)
            add_btn.clicked.connect(self.on_add_clicked)
            watch_layout.addWidget(add_btn)

            layout.addWidget(watch_panel)

            # Watch list area (renders selected variables beneath the toolbar)
            self.watch_list_widget = QWidget()
            self.watch_list_layout = QVBoxLayout(self.watch_list_widget)
            self.watch_list_layout.setContentsMargins(6, 2, 6, 2)
            self.watch_list_layout.setSpacing(2)
            layout.addWidget(self.watch_list_widget)

            # Keep a simple set to prevent duplicate labels
            self._watch_set = set()

            layout.addStretch()

        def on_add_clicked(self):
            # Build the variable list from the program. Prefer Program.symbols mapping.
            try:
                program = self.debugger.program  # type: ignore[attr-defined]
                # Fallback to scanning code if symbols is empty
                items = []
                if hasattr(program, 'symbols') and isinstance(program.symbols, dict) and program.symbols:
                    items = sorted([name for name in program.symbols.keys() if name and not name.endswith(':')])
                else:
                    # Fallback heuristic: look for commands whose 'type' == 'symbol' (as per requirement)
                    for cmd in getattr(program, 'code', []):
                        try:
                            if cmd.get('type') == 'symbol' and 'name' in cmd:
                                items.append(cmd['name'])
                        except Exception:
                            pass
                    items = sorted(set(items))
                if not items:
                    QMessageBox.information(self, "Add Watch", "No variables found in this program.")
                    return
                choice, ok = QInputDialog.getItem(self, "Add Watch", "Select a variable:", items, 0, False)
                if ok and choice:
                    # Record the choice for future use (UI for list will be added later)
                    if not hasattr(self.debugger, 'watched'):
                        self.debugger.watched = []  # type: ignore[attr-defined]
                    if choice not in self.debugger.watched:  # type: ignore[attr-defined]
                        self.debugger.watched.append(choice)  # type: ignore[attr-defined]
                    # Render as a plain label beneath the toolbar if not already present
                    if choice not in self._watch_set:
                        self._add_watch_row(choice)
                        self._watch_set.add(choice)
                    # Optionally echo to console for now
                    try:
                        self.debugger.console.append(f"Watching: {choice}")  # type: ignore[attr-defined]
                    except Exception:
                        pass
            except Exception as exc:
                QMessageBox.warning(self, "Add Watch", f"Could not list variables: {exc}")

        def _add_watch_row(self, name: str):
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            lbl = QLabel(name)
            lbl.setStyleSheet("font-family: mono; padding: 1px 2px;")
            h.addWidget(lbl)
            h.addStretch()
            btn = QPushButton()
            btn.setText("–")  # placeholder until icon provided
            btn.setToolTip(f"Remove '{name}' from watch")
            btn.setFixedSize(20, 20)

            def on_remove():
                try:
                    # update internal structures
                    if hasattr(self.debugger, 'watched') and name in self.debugger.watched:  # type: ignore[attr-defined]
                        self.debugger.watched.remove(name)  # type: ignore[attr-defined]
                    if name in self._watch_set:
                        self._watch_set.remove(name)
                    # remove row from layout/UI
                    row.setParent(None)
                    row.deleteLater()
                except Exception:
                    pass

            btn.clicked.connect(on_remove)
            h.addWidget(btn)
            self.watch_list_layout.addWidget(row)
        
        def on_run_clicked(self):
            self.debugger.doRun()  # type: ignore[attr-defined]
        
        def on_step_clicked(self):
            self.debugger.doStep()  # type: ignore[attr-defined]
        
        def on_stop_clicked(self):
            self.debugger.doStop()  # type: ignore[attr-defined]

        def on_exit_clicked(self):
            self.debugger.doClose()  # type: ignore[attr-defined]
    
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

            # Determine if this line is a command (not empty, not a comment), using the original script line
            orig_line = getattr(spec, 'orig_line', spec.line) if hasattr(spec, 'orig_line') or 'orig_line' in spec.__dict__ else spec.line
            line_lstripped = orig_line.lstrip()
            is_command = bool(line_lstripped and not line_lstripped.startswith('!'))

            class Label(QLabel):
                def __init__(self, text, fixed_width=None, align=Qt.AlignmentFlag.AlignLeft, on_click=None):
                    super().__init__()
                    self.setText(text)
                    self.setMargin(0)
                    self.setContentsMargins(0, 0, 0, 0)
                    self.setStyleSheet("padding:0px; margin:0px; font-family: mono")
                    fm = self.fontMetrics()
                    self.setFixedHeight(fm.height())
                    if fixed_width is not None:
                        self.setFixedWidth(fixed_width)
                    self.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
                    self._on_click = on_click if is_command else None

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

            class ClickableBlob(QLabel):
                def __init__(self, on_click=None):
                    super().__init__()
                    self._on_click = on_click if is_command else None
                def mousePressEvent(self, event):
                    if self._on_click:
                        try:
                            self._on_click()
                        except Exception:
                            pass
                    super().mousePressEvent(event)

            blob_size = 10
            blob = ClickableBlob(on_click=(lambda: spec.onClick(spec.lino)) if is_command else None)
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
                               on_click=(lambda: spec.onClick(spec.lino)) if is_command else None)
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
        # Disable the window close button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
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
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(50)
        self._flush_timer.timeout.connect(self._flush_console_buffer)
        self._flush_timer.stop()

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
        self.leftColumn = self.MainLeftColumn(self)
        left_layout.addWidget(self.leftColumn)
        left_layout.addStretch()

        # Right pane
        right = QFrame()
        right.setFrameShape(QFrame.Shape.StyledPanel)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        self.rightColumn = self.MainRightColumn(self)
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

        # Redirect stdout/stderr so all program output is captured in the console
        try:
            self._orig_stdout = sys.stdout
            self._orig_stderr = sys.stderr
            self._writer = self.ConsoleWriter(self)
            sys.stdout = self._writer  # type: ignore[assignment]
            sys.stderr = self._writer  # type: ignore[assignment]
        except Exception:
            # Best effort; if redirection fails, continue without it
            self._writer = None

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

    def _flush_console_buffer(self):
        try:
            writer = self._writer
            if not writer:
                return
            if getattr(writer, '_buf', None):
                text = ''.join(writer._buf)
                writer._buf.clear()
                # Append to the console and scroll to bottom
                self.console.moveCursor(QTextCursor.MoveOperation.End)
                self.console.insertPlainText(text)
                self.console.moveCursor(QTextCursor.MoveOperation.End)
        except Exception:
            pass

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
            orig_line = line
            if len(line) > 0:
                line = line.replace("\t", "   ")
                color_line = self.coloriseLine(line, lino)
            else:
                # still need to call coloriseLine to keep token list in sync
                color_line = self.coloriseLine(line, lino)
            lineSpec = Object()
            lineSpec.lino = lino
            lineSpec.line = color_line
            lineSpec.orig_line = orig_line
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
        # Show or hide the red blob next to this line
        lineSpec = self.scriptLines[lino]
        lineSpec.bp = not lineSpec.bp
        if lineSpec.bp: lineSpec.label.showBlob()
        else: lineSpec.label.hideBlob()
        # Set or clear a breakpoint on this command
        for command in self.program.code:
            if 'lino' in command and command['lino'] == lino:
                command['bp'] = lineSpec.bp
                break
    
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
    # Set the background color of one line of the script
    def setBackground(self, lino, color):
        # Set the background color of the given line
        if lino < 0 or lino >= len(self.scriptLines):
            return
        lineSpec = self.scriptLines[lino]
        panel = lineSpec.panel
        if not panel:
            return
        if color == 'none':
            panel.setStyleSheet("")
        else:
            panel.setStyleSheet(f"background-color: {color};")
    
    ###########################################################################
    # Here when each instruction is about to run
    def continueExecution(self):
        result = True
        self.pc = self.program.pc
        command = self.program.code[self.pc]
        lino = command['lino'] + 1
        if self.stopped: result = False
        elif command['bp']:
            print(f"Hit breakpoint at line {lino}")
            self.stopped = True
            result = False
        if not result:
            self.scrollTo(lino)
            self.setBackground(command['lino'], 'LightYellow')
        return result
    
    def doRun(self):
        self.stopped = False
        print("Continuing execution at line", self.program.pc + 1)
        self.program.run(self.pc)
    
    def doStep(self):
        command = self.program.code[self.pc]
        # print("Stepping at line", command['lino'] + 1)
        self.setBackground(command['lino'], 'none')
        self.program.run(self.pc)
    
    def doStop(self):
        self.stopped = True
    
    def doClose(self):
        self.closeEvent(None)

    ###########################################################################
    # Override closeEvent to save window geometry
    def closeEvent(self, event):
        """Save window position and size to ~/.ecdebug.conf as JSON on exit."""
        cfg = {
            "x": self.x(),
            "y": self.y(),
            "width": self.width(),
            "height": self.height(),
            "ratio": self.ratio
        }
        # try to persist console height (bottom pane) if present
        try:
            ch = None
            if hasattr(self, 'vsplitter'):
                sizes = self.vsplitter.sizes()
                if len(sizes) >= 2:
                    ch = int(sizes[1])
            if ch is not None:
                cfg['console_height'] = ch
        except Exception:
            pass
        try:
            cfg_path = os.path.join(os.path.expanduser("~"), ".ecdebug.conf")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as exc:
            # best-effort only; avoid blocking shutdown
            try:
                self.statusBar().showMessage(f"Could not save config: {exc}", 3000)
            except Exception:
                pass
        # Restore stdout/stderr and stop timers
        try:
            if self._orig_stdout is not None:
                sys.stdout = self._orig_stdout
            if self._orig_stderr is not None:
                sys.stderr = self._orig_stderr
            if self._flush_timer is not None:
                try:
                    self._flush_timer.stop()
                except Exception:
                    pass
        except Exception:
            pass
        super().close()