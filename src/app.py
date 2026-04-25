import json
import os
import sys
import threading
import time

import requests
from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import database
import engine
from classifier import analyze_sentiment
from engine import ConsortiumEngine

LIGHT_THEME = """
QMainWindow {
    background-color: #ffffff;
}
QWidget {
    color: #1e293b;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
QFrame#Sidebar {
    background-color: #f8fafc;
    border-right: 1px solid #e2e8f0;
}
QLabel#Title {
    font-size: 22px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -1px;
}
QLabel#Subtitle {
    font-size: 10px;
    font-weight: 700;
    color: #2563eb;
    text-transform: uppercase;
    letter-spacing: 2px;
}
QLabel#SectionLabel {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
}
QLineEdit, QTextEdit, QSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px;
    color: #1e293b;
}
QLineEdit:focus, QTextEdit:focus {
    border: 2px solid #3b82f6;
}
QPushButton#PrimaryBtn {
    background-color: #0f172a;
    color: #ffffff;
    border-radius: 10px;
    padding: 12px;
    font-weight: 700;
    font-size: 13px;
}
QPushButton#PrimaryBtn:hover {
    background-color: #1e293b;
}
QPushButton#PrimaryBtn:disabled {
    background-color: #94a3b8;
}
QScrollArea#ModelScroll {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}
QScrollArea#ModelScroll QWidget {
    background-color: #ffffff;
}
"""


class MessageBubble(QFrame):
    def __init__(self, sender, model_name):
        super().__init__()
        self.setObjectName("MessageBubble")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 15, 20, 15)
        self.layout.setSpacing(8)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame#MessageBubble {
                background-color: #f8fafc;
                border-left: 4px solid #94a3b8;
                border-radius: 12px;
            }
        """)

        header = QHBoxLayout()
        self.sender_label = QLabel(f"<b>{sender}</b>")
        self.sender_label.setStyleSheet("color: #0f172a; font-size: 13px;")

        self.model_label = QLabel(f"[{model_name}]")
        self.model_label.setStyleSheet("color: #64748b; font-size: 11px;")

        self.sentiment_label = QLabel("ANALYZING...")
        self.sentiment_label.setStyleSheet(
            "color: #94a3b8; font-size: 10px; font-weight: 700;"
        )

        header.addWidget(self.sender_label)
        header.addWidget(self.model_label)
        header.addStretch()
        header.addWidget(self.sentiment_label)
        self.layout.addLayout(header)

        self.content_text = QLabel()
        self.content_text.setWordWrap(True)
        self.content_text.setStyleSheet(
            "color: #334155; font-size: 14px; line-height: 1.5;"
        )
        self.content_text.setTextFormat(Qt.TextFormat.PlainText)
        self.layout.addWidget(self.content_text)

    def update_content(self, text):
        self.content_text.setText(self.content_text.text() + text)

    def finalize(self, metrics):
        pattern = metrics.get("pattern_id", "NEUTRAL")
        if pattern == "BRUTAL":
            self.setStyleSheet(
                "QFrame#MessageBubble { background-color: #fef2f2; border-left: 4px solid #ef4444; border-radius: 12px; }"
            )
            self.sentiment_label.setText("ADVERSARIAL")
            self.sentiment_label.setStyleSheet(
                "color: #ef4444; font-size: 10px; font-weight: 700;"
            )
        elif pattern == "DISMISSIVE":
            self.setStyleSheet(
                "QFrame#MessageBubble { background-color: #ecfeff; border-left: 4px solid #06b6d4; border-radius: 12px; }"
            )
            self.sentiment_label.setText("DISMISSIVE")
            self.sentiment_label.setStyleSheet(
                "color: #06b6d4; font-size: 10px; font-weight: 700;"
            )
        else:
            self.sentiment_label.setText("NEUTRAL")
            self.sentiment_label.setStyleSheet(
                "color: #94a3b8; font-size: 10px; font-weight: 700;"
            )


class DebateWorker(QThread):
    token_received = pyqtSignal(str, str)  # model_id, token
    turn_started = pyqtSignal(str, str)  # model_id, model_name
    turn_finished = pyqtSignal(dict)
    debate_finished = pyqtSignal()

    def __init__(self, engine, topic, rounds):
        super().__init__()
        self.engine = engine
        self.topic = topic
        self.rounds = rounds
        self._running = True

    def run(self):
        previous_turns = []
        total_turns = self.rounds * len(self.engine.model_ids)

        while self._running and len(previous_turns) < total_turns:
            next_idx = self.engine.carousel.index
            next_mid = self.engine.model_ids[next_idx % len(self.engine.model_ids)]
            model_name = self.engine.agent_configs[next_mid]["model_name"]

            self.turn_started.emit(next_mid, model_name)

            stream = self.engine.iter_turn_stream(previous_turns, self.topic)
            for token in stream:
                if not self._running:
                    break
                self.token_received.emit(next_mid, token)

            if not self._running:
                break

            metrics = self.engine.last_metrics
            if metrics:
                database.insert_turn(
                    "session_gui",
                    metrics["persona_id"],
                    metrics["model_name"],
                    metrics["raw_content"],
                    metrics["pattern_id"],
                    metrics["ttft"],
                    metrics["total_latency"],
                    metrics["token_count"],
                    metrics["aggressiveness"],
                )
                previous_turns.append(metrics)
                self.turn_finished.emit(metrics)

            time.sleep(0.5)

        self.debate_finished.emit()


class ConsortiumGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Consortium Debate Engine")
        self.resize(1200, 850)
        self.setStyleSheet(LIGHT_THEME)

        database.init_db()
        self.init_ui()
        self.refresh_ollama_models()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(320)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(25, 30, 25, 30)
        sidebar_layout.setSpacing(20)

        header_vbox = QVBoxLayout()
        title = QLabel("CONSORTIUM")
        title.setObjectName("Title")
        subtitle = QLabel("AI DEBATE ENGINE")
        subtitle.setObjectName("Subtitle")
        header_vbox.addWidget(title)
        header_vbox.addWidget(subtitle)
        sidebar_layout.addLayout(header_vbox)

        topic_vbox = QVBoxLayout()
        topic_vbox.addWidget(QLabel("RESEARCH TOPIC", objectName="SectionLabel"))
        self.topic_input = QTextEdit()
        self.topic_input.setPlaceholderText("Enter debate topic...")
        self.topic_input.setText(
            "The ethical limits of recursive self-improvement in LLMs."
        )
        self.topic_input.setMaximumHeight(100)
        topic_vbox.addWidget(self.topic_input)
        sidebar_layout.addLayout(topic_vbox)

        rounds_vbox = QVBoxLayout()
        rounds_vbox.addWidget(QLabel("ROUNDS PER MODEL", objectName="SectionLabel"))
        self.rounds_input = QSpinBox()
        self.rounds_input.setRange(1, 50)
        self.rounds_input.setValue(3)
        rounds_vbox.addWidget(self.rounds_input)
        sidebar_layout.addLayout(rounds_vbox)

        models_vbox = QVBoxLayout()
        models_header = QHBoxLayout()
        models_header.addWidget(QLabel("MODELS", objectName="SectionLabel"))
        refresh_btn = QPushButton("REFRESH")
        refresh_btn.setStyleSheet(
            "font-size: 9px; padding: 2px; color: #2563eb; border: none;"
        )
        refresh_btn.clicked.connect(self.refresh_ollama_models)
        models_header.addStretch()
        models_header.addWidget(refresh_btn)
        models_vbox.addLayout(models_header)

        self.model_scroll = QScrollArea()
        self.model_scroll.setWidgetResizable(True)
        self.model_container = QWidget()
        self.model_list_layout = QVBoxLayout(self.model_container)
        self.model_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.model_scroll.setWidget(self.model_container)
        models_vbox.addWidget(self.model_scroll)
        sidebar_layout.addLayout(models_vbox)

        self.start_btn = QPushButton("INITIALIZE DEBATE")
        self.start_btn.setObjectName("PrimaryBtn")
        self.start_btn.clicked.connect(self.toggle_debate)
        sidebar_layout.addWidget(self.start_btn)

        layout.addWidget(sidebar)

        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)

        self.feed_scroll = QScrollArea()
        self.feed_scroll.setWidgetResizable(True)
        self.feed_widget = QWidget()
        self.feed_layout = QVBoxLayout(self.feed_widget)
        self.feed_layout.setContentsMargins(40, 40, 40, 40)
        self.feed_layout.setSpacing(25)
        self.feed_layout.addStretch()
        self.feed_scroll.setWidget(self.feed_widget)
        chat_layout.addWidget(self.feed_scroll)

        layout.addWidget(chat_container)

        self.active_bubbles = {}
        self.selected_models = []
        self.worker = None

    def refresh_ollama_models(self):
        for i in reversed(range(self.model_list_layout.count())):
            self.model_list_layout.itemAt(i).widget().setParent(None)

        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                for m in models:
                    name = m["name"]
                    cb = QCheckBox(name)
                    cb.setStyleSheet("font-size: 13px; padding: 5px;")
                    self.model_list_layout.addWidget(cb)
            else:
                self.model_list_layout.addWidget(QLabel("Ollama not responding"))
        except:
            self.model_list_layout.addWidget(QLabel("Ollama not found"))

    def toggle_debate(self):
        if self.worker and self.worker.isRunning():
            self.worker._running = False
            self.start_btn.setText("STOPPING...")
            return

        selected = []
        for i in range(self.model_list_layout.count()):
            w = self.model_list_layout.itemAt(i).widget()
            if isinstance(w, QCheckBox) and w.isChecked():
                selected.append(w.text())

        if not selected:
            return

        for i in reversed(range(self.feed_layout.count())):
            item = self.feed_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        self.feed_layout.addStretch()

        configs = {
            m: {
                "api_key": "ollama",
                "model_name": m,
                "base_url": "http://localhost:11434/v1",
            }
            for m in selected
        }
        self.engine = ConsortiumEngine(agent_configs=configs)

        self.worker = DebateWorker(
            self.engine, self.topic_input.toPlainText(), self.rounds_input.value()
        )
        self.worker.turn_started.connect(self.on_turn_started)
        self.worker.token_received.connect(self.on_token_received)
        self.worker.turn_finished.connect(self.on_turn_finished)
        self.worker.debate_finished.connect(self.on_debate_finished)

        self.worker.start()
        self.start_btn.setText("STOP DEBATE")

    def on_turn_started(self, mid, name):
        bubble = MessageBubble(mid, name)
        self.feed_layout.insertWidget(self.feed_layout.count() - 1, bubble)
        self.active_bubbles[mid] = bubble
        self.feed_scroll.verticalScrollBar().setValue(
            self.feed_scroll.verticalScrollBar().maximum()
        )

    def on_token_received(self, mid, token):
        if mid in self.active_bubbles:
            self.active_bubbles[mid].update_content(token)
            # Auto-scroll
            vbar = self.feed_scroll.verticalScrollBar()
            if vbar.value() > vbar.maximum() - 100:
                vbar.setValue(vbar.maximum())

    def on_turn_finished(self, metrics):
        mid = metrics["persona_id"]
        if mid in self.active_bubbles:
            self.active_bubbles[mid].finalize(metrics)
            del self.active_bubbles[mid]

    def on_debate_finished(self):
        self.start_btn.setText("INITIALIZE DEBATE")
        self.start_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = ConsortiumGUI()
    gui.show()
    sys.exit(app.exec())
