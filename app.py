import sys
import os
import uuid
import time
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox,
    QScrollArea, QTextEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QFormLayout,
    QSplitter, QFrame, QStackedWidget, QProgressBar, QSizePolicy, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap

import database
import engine
from engine import ConsortiumEngine

# Ensure database is initialized
database.init_db()

# Custom styles for the app
STYLESHEET = """
QMainWindow {
    background-color: #0a0a0f;
}
QWidget {
    color: #d1d1d1;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
QGroupBox {
    border: 1px solid #2a2a35;
    border-radius: 4px;
    margin-top: 15px;
    font-weight: bold;
    color: #888;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #16161e;
    border: 1px solid #2a2a35;
    padding: 6px;
    border-radius: 3px;
    color: #fff;
}
QPushButton {
    background-color: #252530;
    border: 1px solid #3a3a45;
    padding: 10px;
    border-radius: 4px;
    color: #eee;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #303040;
}
QPushButton#primaryBtn {
    background-color: #3d5afe;
    border: none;
}
QPushButton#primaryBtn:hover {
    background-color: #536dfe;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    border: none;
    background: #0a0a0f;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #2a2a35;
    border-radius: 4px;
    min-height: 20px;
}
QTabWidget::pane {
    border: 1px solid #2a2a35;
}
QTabBar::tab {
    background: #16161e;
    padding: 12px 20px;
    border-right: 1px solid #2a2a35;
}
QTabBar::tab:selected {
    background: #252530;
    color: #fff;
}
QTableWidget {
    background-color: #16161e;
    gridline-color: #2a2a35;
    border: none;
    alternate-background-color: #1a1a24;
}
QHeaderView::section {
    background-color: #1c1c28;
    color: #888;
    padding: 8px;
    border: 1px solid #2a2a35;
}
"""

class MessageWidget(QFrame):
    def __init__(self, sender, model, content, pattern):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        
        header_layout = QHBoxLayout()
        sender_lbl = QLabel(f"<b>{sender}</b>")
        sender_lbl.setStyleSheet("color: #3d5afe; font-size: 13px;")
        header_layout.addWidget(sender_lbl)
        
        model_lbl = QLabel(f"[{model}]")
        model_lbl.setStyleSheet("color: #555; font-size: 11px;")
        header_layout.addWidget(model_lbl)
        
        pattern_lbl = QLabel()
        if pattern == "BRUTAL":
            pattern_lbl.setText("ADVERSARIAL")
            pattern_lbl.setStyleSheet("color: #ff1744; font-weight: bold; font-size: 10px;")
            self.setStyleSheet("border-left: 3px solid #ff1744; background-color: #1a1012;")
        elif pattern == "DISMISSIVE":
            pattern_lbl.setText("DISMISSIVE")
            pattern_lbl.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 10px;")
            self.setStyleSheet("border-left: 3px solid #00e5ff; background-color: #10181a;")
        else:
            pattern_lbl.setText("NEUTRAL")
            pattern_lbl.setStyleSheet("color: #757575; font-weight: bold; font-size: 10px;")
            self.setStyleSheet("border-left: 3px solid #424242; background-color: #121216;")
        
        header_layout.addStretch()
        header_layout.addWidget(pattern_lbl)
        layout.addLayout(header_layout)
        
        self.content_lbl = QLabel(content)
        self.content_lbl.setWordWrap(True)
        self.content_lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.content_lbl.setStyleSheet("line-height: 1.4; color: #e0e0e0; font-size: 13px; margin-top: 5px;")
        layout.addWidget(self.content_lbl)

    def append_text(self, text):
        new_text = self.content_lbl.text() + text
        self.content_lbl.setText(new_text)

class EngineWorker(QThread):
    token_received = pyqtSignal(str, str, str) # sender, token, pattern
    turn_finished = pyqtSignal(dict)
    finished = pyqtSignal()
    
    def __init__(self, engine, previous_turns, seed_topic, total_turns):
        super().__init__()
        self.engine = engine
        self.previous_turns = previous_turns
        self.seed_topic = seed_topic
        self.total_turns = total_turns
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running and len(self.previous_turns) < self.total_turns:
            # Predict next model for streaming
            next_idx = self.engine.carousel.index
            next_mid = self.engine.model_ids[next_idx % len(self.engine.model_ids)]
            
            stream = self.engine.iter_turn_stream(self.previous_turns, self.seed_topic)
            
            for token in stream:
                if not self._running:
                    break
                self.token_received.emit(next_mid, token, "NEUTRAL")
            
            if not self._running:
                break

            metrics = self.engine.last_metrics
            if metrics:
                database.insert_turn(
                    session_id="default",
                    persona_id=metrics["persona_id"],
                    model_name=metrics["model_name"],
                    raw_content=metrics["raw_content"],
                    pattern_id=metrics["pattern_id"],
                    ttft=metrics["ttft"],
                    total_latency=metrics["total_latency"],
                    token_count=metrics["token_count"],
                    aggressiveness=metrics["aggressiveness"],
                    happy=metrics["happy"],
                    angry=metrics["angry"],
                    sad=metrics["sad"],
                    disrespect=metrics["disrespect"]
                )
                self.previous_turns.append(metrics)
                self.turn_finished.emit(metrics)
            
            time.sleep(0.5)
        
        self.finished.emit()

class AnalyticsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.charts_tab = QWidget()
        self.charts_layout = QVBoxLayout(self.charts_tab)
        self.figure, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(6, 8))
        self.canvas = FigureCanvas(self.figure)
        self.charts_layout.addWidget(self.canvas)
        self.tabs.addTab(self.charts_tab, "Research Metrics")
        
        self.data_tab = QWidget()
        data_layout = QVBoxLayout(self.data_tab)
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            "ID", "Model ID", "Model Name", "Content", "Pattern", "TTFT", 
            "Latency", "Tokens", "Aggro", "Happy", "Angry", "Sad", "Disrespect"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        data_layout.addWidget(self.table)
        
        self.export_btn = QPushButton("Export Data (CSV)")
        self.export_btn.clicked.connect(self.export_csv)
        data_layout.addWidget(self.export_btn)
        self.tabs.addTab(self.data_tab, "Raw Records")

    def update_data(self, turns):
        if not turns: return
        df = pd.DataFrame(turns)
        
        self.table.setRowCount(len(turns))
        for i, turn in enumerate(turns):
            cols = ["turn_id", "persona_id", "model_name", "raw_content", "pattern_id", "ttft", "total_latency", "token_count", "aggressiveness", "happy", "angry", "sad", "disrespect"]
            for j, col in enumerate(cols):
                self.table.setItem(i, j, QTableWidgetItem(str(turn.get(col, ""))))
        
        self.ax1.clear()
        self.ax2.clear()
        plt.style.use('dark_background')
        self.figure.patch.set_facecolor('#0a0a0f')
        self.ax1.set_facecolor('#0a0a0f')
        self.ax2.set_facecolor('#0a0a0f')

        if "pattern_id" in df.columns:
            agg_counts = df[df["pattern_id"].isin(["BRUTAL", "DISMISSIVE"])].groupby("persona_id").size()
            if not agg_counts.empty:
                agg_counts.plot(kind='bar', ax=self.ax1, color='#ff1744')
                self.ax1.set_title("Adversarial Events per Model", color='#888', fontsize=10)
        
        if "token_count" in df.columns:
            df["token_count"].plot(kind='line', ax=self.ax2, marker='.', color='#3d5afe')
            self.ax2.set_title("Turn Token Count", color='#888', fontsize=10)

        self.figure.tight_layout()
        self.canvas.draw()

    def export_csv(self):
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        data = []
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(cols)]
        for r in range(rows):
            row_data = [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(cols)]
            data.append(row_data)
        
        df = pd.DataFrame(data, columns=headers)
        path, _ = QFileDialog.getSaveFileName(self, "Save Data", "debate_log.csv", "CSV Files (*.csv)")
        if path: df.to_csv(path, index=False)

class ConsortiumApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Consortium AI Debate UI")
        self.resize(1100, 850)
        self.setStyleSheet(STYLESHEET)
        
        self.engine = None
        self.worker = None
        self.turns = []
        
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # LEFT SIDEBAR
        sidebar = QFrame()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet("background-color: #0d0d14; border-right: 1px solid #1c1c28;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 25, 20, 25)
        
        title = QLabel("CONSORTIUM")
        title.setStyleSheet("font-size: 22px; font-weight: 900; color: #fff; letter-spacing: 2px;")
        sidebar_layout.addWidget(title)
        
        subtitle = QLabel("AI DEBATE ENGINE")
        subtitle.setStyleSheet("font-size: 10px; color: #3d5afe; font-weight: bold; margin-bottom: 20px;")
        sidebar_layout.addWidget(subtitle)
        
        self.nav_list = QComboBox()
        self.nav_list.addItems(["Debate Feed", "Analytics"])
        self.nav_list.currentIndexChanged.connect(self.change_page)
        sidebar_layout.addWidget(QLabel("VIEW"))
        sidebar_layout.addWidget(self.nav_list)
        
        sidebar_layout.addSpacing(30)
        sidebar_layout.addWidget(QLabel("TOPIC"))
        self.seed_topic = QLineEdit("The ethical limits of recursive self-improvement in LLMs.")
        sidebar_layout.addWidget(self.seed_topic)
        
        sidebar_layout.addWidget(QLabel("ROUNDS"))
        self.rounds = QSpinBox()
        self.rounds.setRange(1, 100)
        self.rounds.setValue(5)
        sidebar_layout.addWidget(self.rounds)
        
        self.start_btn = QPushButton("INITIALIZE DEBATE")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.clicked.connect(self.start_engine)
        sidebar_layout.addWidget(self.start_btn)
        
        sidebar_layout.addSpacing(30)
        sidebar_layout.addWidget(QLabel("MODELS"))
        
        model_scroll = QScrollArea()
        model_scroll.setWidgetResizable(True)
        model_content = QWidget()
        self.model_layout = QVBoxLayout(model_content)
        self.model_layout.setContentsMargins(0, 0, 0, 0)
        
        self.model_inputs = []
        for i in range(3): # Default to 3 debating models
            self.add_model_input()
            
        model_scroll.setWidget(model_content)
        sidebar_layout.addWidget(model_scroll)
        
        add_model_btn = QPushButton("+ ADD MODEL")
        add_model_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        add_model_btn.clicked.connect(self.add_model_input)
        sidebar_layout.addWidget(add_model_btn)
        
        main_layout.addWidget(sidebar)
        
        # MAIN STACK
        self.stack = QStackedWidget()
        
        # PAGE 1: FEED
        self.feed_page = QWidget()
        feed_layout = QVBoxLayout(self.feed_page)
        feed_layout.setContentsMargins(0, 0, 0, 0)
        
        self.feed_scroll = QScrollArea()
        self.feed_scroll.setWidgetResizable(True)
        self.feed_container = QWidget()
        self.feed_vbox = QVBoxLayout(self.feed_container)
        self.feed_vbox.setContentsMargins(30, 30, 30, 30)
        self.feed_vbox.setSpacing(20)
        self.feed_vbox.addStretch()
        self.feed_scroll.setWidget(self.feed_container)
        feed_layout.addWidget(self.feed_scroll)
        
        input_bar = QFrame()
        input_bar.setStyleSheet("background-color: #0d0d14; border-top: 1px solid #1c1c28;")
        input_layout = QHBoxLayout(input_bar)
        input_layout.setContentsMargins(20, 15, 20, 15)
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Inject prompt into debate...")
        self.user_input.returnPressed.connect(self.send_user_message)
        input_layout.addWidget(self.user_input)
        
        send_btn = QPushButton("SEND")
        send_btn.setFixedWidth(80)
        send_btn.clicked.connect(self.send_user_message)
        input_layout.addWidget(send_btn)
        feed_layout.addWidget(input_bar)
        
        self.stack.addWidget(self.feed_page)
        
        # PAGE 2: ANALYTICS
        self.analytics_page = AnalyticsTab()
        self.stack.addWidget(self.analytics_page)
        
        main_layout.addWidget(self.stack)

    def add_model_input(self):
        count = len(self.model_inputs) + 1
        group = QGroupBox(f"Model {count}")
        form = QFormLayout(group)
        form.setContentsMargins(10, 15, 10, 10)
        
        mid = QLineEdit(f"Model_{count}")
        prov = QComboBox()
        prov.addItems(["OpenRouter", "Google", "OpenAI", "Mock"])
        key = QLineEdit()
        key.setEchoMode(QLineEdit.EchoMode.Password)
        model = QLineEdit("gpt-4o-mini")
        
        form.addRow("ID:", mid)
        form.addRow("Provider:", prov)
        form.addRow("API Key:", key)
        form.addRow("Model:", model)
        
        self.model_inputs.append((mid, prov, key, model))
        self.model_layout.addWidget(group)

    def change_page(self, idx):
        self.stack.setCurrentIndex(idx)

    def start_engine(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        
        configs = {}
        for mid, prov, key, model in self.model_inputs:
            m_id = mid.text()
            provider = prov.currentText()
            api_key = key.text() or ("sk-test" if provider == "Mock" else "")
            
            base_url = None
            if provider == "OpenRouter": base_url = "https://openrouter.ai/api/v1"
            elif provider == "Google": base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                
            configs[m_id] = {"api_key": api_key, "model_name": model.text(), "base_url": base_url}

        self.engine = ConsortiumEngine(agent_configs=configs)
        self.turns = []
        
        for i in reversed(range(self.feed_vbox.count())):
            w = self.feed_vbox.itemAt(i).widget()
            if w: w.setParent(None)
        self.feed_vbox.addStretch()
        
        self.worker = EngineWorker(self.engine, self.turns, self.seed_topic.text(), self.rounds.value() * len(configs))
        self.worker.token_received.connect(self.on_token_received)
        self.worker.turn_finished.connect(self.on_turn_finished)
        self.worker.start()

    def on_token_received(self, sender, token, pattern):
        if self.feed_vbox.count() > 1:
            last_w = self.feed_vbox.itemAt(self.feed_vbox.count() - 2).widget()
            if isinstance(last_w, MessageWidget) and last_w.sender_lbl.text() == f"<b>{sender}</b>":
                last_w.append_text(token)
                self.feed_scroll.verticalScrollBar().setValue(self.feed_scroll.verticalScrollBar().maximum())
                return
        
        model_name = self.engine.agent_configs.get(sender, {}).get("model_name", "AI")
        msg = MessageWidget(sender, model_name, token, pattern)
        self.feed_vbox.insertWidget(self.feed_vbox.count() - 1, msg)

    def on_turn_finished(self, metrics):
        if self.feed_vbox.count() > 1:
            last_w = self.feed_vbox.itemAt(self.feed_vbox.count() - 2).widget()
            if isinstance(last_w, MessageWidget):
                # Apply the correct color after sentiment analysis
                pattern = metrics["pattern_id"]
                if pattern == "BRUTAL":
                    last_w.setStyleSheet("border-left: 3px solid #ff1744; background-color: #1a1012;")
                elif pattern == "DISMISSIVE":
                    last_w.setStyleSheet("border-left: 3px solid #00e5ff; background-color: #10181a;")
        self.analytics_page.update_data(self.turns)

    def send_user_message(self):
        text = self.user_input.text()
        if not text: return
        m = {"turn_id": len(self.turns)+1, "persona_id": "User", "model_name": "Human", "raw_content": text, "pattern_id": "NEUTRAL", "token_count": len(text.split())}
        self.turns.append(m)
        msg = MessageWidget("User", "Human", text, "NEUTRAL")
        self.feed_vbox.insertWidget(self.feed_vbox.count() - 1, msg)
        self.user_input.clear()
        self.analytics_page.update_data(self.turns)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ConsortiumApp()
    window.show()
    sys.exit(app.exec())
