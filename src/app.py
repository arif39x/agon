import json
import os
import sys
import threading
import time

import requests
from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette, QTextCursor
from PyQt6 import QtSvg, QtSvgWidgets
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
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
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import database
import engine
from classifier import analyze_sentiment
from engine import AgonEngine

# --- SVG ASSETS ---
QWEN_PATH = '<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path d="M16 16L19 19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
LLAMA_PATH = '<path d="M7 20V11C7 9.89543 7.89543 9 9 9H15C16.1046 9 17 9.89543 17 11V20" stroke="currentColor" stroke-width="2"/><path d="M9 9V5C9 3.89543 9.89543 3 11 3H13C14.1046 3 15 3.89543 15 5V9" stroke="currentColor" stroke-width="2"/>'
GEMMA_PATH = '<path d="M12 3L20 9L12 21L4 9L12 3Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M4 9H20" stroke="currentColor" stroke-width="2"/>'
GPT_PATH = '<path d="M12 2L14.85 8.15L21 11L14.85 13.85L12 20L9.15 13.85L3 11L9.15 8.15L12 2Z" fill="currentColor"/><circle cx="12" cy="11" r="3" stroke="white" stroke-width="1.5"/>'
CLAUDE_PATH = '<path d="M4 19L12 5L20 19M8 15H16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
MISTRAL_PATH = '<path d="M4 6H20L12 18L4 6Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M8 10H16" stroke="currentColor" stroke-width="1.5"/>'
GEMINI_PATH = '<path d="M12 3L14.5 9.5L21 12L14.5 14.5L12 21L9.5 14.5L3 12L9.5 9.5L12 3Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>'
DEEPSEEK_PATH = '<path d="M10 17C13.866 17 17 13.866 17 10C17 6.13401 13.866 3 10 3C6.13401 3 3 6.13401 3 10C3 13.866 6.13401 17 10 17Z" stroke="currentColor" stroke-width="2"/><path d="M21 21L15 15" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>'
GROK_PATH = '<path d="M5 5L19 19M5 19L19 5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>'
BOT_PATH = '<rect x="5" y="8" width="14" height="12" rx="2" stroke="currentColor" stroke-width="2"/><path d="M9 13H9.01" stroke="currentColor" stroke-width="2"/><path d="M15 13H15.01" stroke="currentColor" stroke-width="2"/><path d="M10 4L12 8L14 4" stroke="currentColor" stroke-width="2"/>'
SPARK_PATH = '<path d="M12 3V4M12 20V21M4 12H3M21 12H20M18.36 5.64L19.07 4.93M4.93 19.07L5.64 18.36M18.36 18.36L19.07 19.07M4.93 4.93L5.64 5.64" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'

def get_model_svg(model_name, color="#ffffff"):
    name = model_name.lower()
    if "qwen" in name:
        path = QWEN_PATH
    elif "llama" in name:
        path = LLAMA_PATH
    elif "gemma" in name:
        path = GEMMA_PATH
    elif "gpt" in name or "openai" in name:
        path = GPT_PATH
    elif "claude" in name or "anthropic" in name:
        path = CLAUDE_PATH
    elif "mistral" in name or "mixtral" in name:
        path = MISTRAL_PATH
    elif "gemini" in name:
        path = GEMINI_PATH
    elif "deepseek" in name:
        path = DEEPSEEK_PATH
    elif "grok" in name:
        path = GROK_PATH
    else:
        path = BOT_PATH
    
    return f"""
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        {path.replace('currentColor', color)}
    </svg>
    """.encode('utf-8')

BW_THEME = """
QMainWindow {
    background-color: #ffffff;
}
QWidget {
    font-family: 'Inter', 'Segoe UI', sans-serif;
    color: #000000;
}
QFrame#Sidebar {
    background-color: #000000;
    border-right: 1px solid #1a1a1a;
}
QLabel#Title {
    font-size: 28px;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -1.5px;
}
QLabel#Subtitle {
    font-size: 10px;
    font-weight: 700;
    color: #666666;
    text-transform: uppercase;
    letter-spacing: 2px;
}
QLabel#SectionLabel {
    font-size: 11px;
    font-weight: 800;
    color: #555555;
    text-transform: uppercase;
}
QTextEdit, QSpinBox {
    background-color: #0a0a0a;
    border: 1px solid #222222;
    border-radius: 4px;
    padding: 10px;
    color: #ffffff;
    selection-background-color: #444444;
}
QTextEdit:focus, QSpinBox:focus {
    border: 1px solid #ffffff;
}
QPushButton#PrimaryBtn {
    background-color: #ffffff;
    color: #000000;
    border-radius: 2px;
    padding: 15px;
    font-weight: 800;
    font-size: 14px;
    text-transform: uppercase;
}
QPushButton#PrimaryBtn:hover {
    background-color: #e0e0e0;
}
QPushButton#PrimaryBtn:disabled {
    background-color: #222222;
    color: #444444;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollArea#ModelScroll {
    background-color: #0a0a0a;
    border: 1px solid #222222;
    border-radius: 4px;
}
QScrollArea#ModelScroll QWidget {
    background-color: #0a0a0a;
}
QScrollBar:vertical {
    border: none;
    background: #000000;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #333333;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QCheckBox {
    color: #ffffff;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #444444;
    background: #000000;
}
QCheckBox::indicator:checked {
    background: #ffffff;
    border: 1px solid #ffffff;
}
"""

class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text

    def setText(self, text):
        self._full_text = text
        self.update_elided_text()

    def resizeEvent(self, event):
        self.update_elided_text()
        super().resizeEvent(event)

    def update_elided_text(self):
        metrics = self.fontMetrics()
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
        super().setText(elided)

class ModelSelectionRow(QFrame):
    def __init__(self, model_name):
        super().__init__()
        self.model_name = model_name
        self.setObjectName("ModelRow")
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        
        self.checkbox = QCheckBox()
        self.checkbox.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.logo = QtSvgWidgets.QSvgWidget()
        self.logo.setFixedSize(18, 18)
        self.logo.load(get_model_svg(model_name))
        
        self.name_label = ElidedLabel(model_name)
        self.name_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500;")
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.logo)
        layout.addWidget(self.name_label, 1)
        
        self.setStyleSheet("""
            QFrame#ModelRow {
                background-color: transparent;
                border-radius: 4px;
            }
            QFrame#ModelRow:hover {
                background-color: #1a1a1a;
            }
        """)

    def mousePressEvent(self, event):
        self.checkbox.setChecked(not self.checkbox.isChecked())
        super().mousePressEvent(event)

class EmptyStateWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        self.icon = QtSvgWidgets.QSvgWidget()
        self.icon.setFixedSize(80, 80)
        spark_svg = f'<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">{SPARK_PATH.replace("currentColor", "#000000")}</svg>'.encode('utf-8')
        self.icon.load(spark_svg)
        
        self.text = QLabel("Knowledge Demands Debate.\nConfigure your parameters to begin.")
        self.text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text.setStyleSheet("color: #333333; font-size: 16px; font-weight: 400; line-height: 1.5;")
        
        layout.addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.text, alignment=Qt.AlignmentFlag.AlignCenter)

class MessageBubble(QFrame):
    def __init__(self, sender, model_name):
        super().__init__()
        self.setObjectName("MessageBubble")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.container = QFrame()
        self.container.setObjectName("BubbleContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(25, 20, 25, 20)
        self.container_layout.setSpacing(12)

        self.setStyleSheet("""
            QFrame#BubbleContainer {
                background-color: #ffffff;
                border: 1px solid #e5e5e5;
                border-left: 4px solid #000000;
            }
        """)

        header = QHBoxLayout()
        self.sender_label = QLabel(f"<b>{sender}</b>")
        self.sender_label.setStyleSheet("color: #000000; font-size: 13px; text-transform: uppercase; letter-spacing: 1px;")

        self.model_label = QLabel(f"• {model_name}")
        self.model_label.setStyleSheet("color: #888888; font-size: 11px;")

        self.sentiment_label = QLabel("ANALYZING...")
        self.sentiment_label.setStyleSheet(
            "color: #aaaaaa; font-size: 10px; font-weight: 800; text-transform: uppercase;"
        )

        header.addWidget(self.sender_label)
        header.addWidget(self.model_label)
        header.addStretch()
        header.addWidget(self.sentiment_label)
        self.container_layout.addLayout(header)

        self.content_browser = QTextBrowser()
        self.content_browser.setOpenExternalLinks(True)
        self.content_browser.setFrameShape(QFrame.Shape.NoFrame)
        self.content_browser.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_browser.setStyleSheet("background: transparent; border: none;")
        self.container_layout.addWidget(self.content_browser)
        
        self.layout.addWidget(self.container)
        
        self._raw_text = ""
        self._update_timer = time.time()

    def update_content(self, text):
        self._raw_text += text
        # Throttling updates for performance
        if time.time() - self._update_timer > 0.1:
            self.render_markdown()
            self._update_timer = time.time()

    def render_markdown(self):
        import re
        html = self._raw_text
        
        # Simple escape for HTML
        html = html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Bold
        html = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html)
        
        # Code blocks (```lang ... ```)
        def highlight_code(match):
            lang = match.group(1).strip()
            code = match.group(2).strip()
            try:
                lexer = get_lexer_by_name(lang)
            except:
                try:
                    lexer = guess_lexer(code)
                except:
                    lexer = get_lexer_by_name("text")
            
            formatter = HtmlFormatter(style='bw', noclasses=True)
            highlighted = highlight(code, lexer, formatter)
            return f'<div style="background-color: #f5f5f5; border: 1px solid #e0e0e0; padding: 10px; margin: 10px 0; font-family: monospace;">{highlighted}</div>'

        html = re.sub(r"```(.*?)\n(.*?)```", highlight_code, html, flags=re.DOTALL)
        
        # Inline code
        html = re.sub(r"`(.*?)`", r'<code style="background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-family: monospace;">\1</code>', html)
        
        # Simple Math block approximation (Physics/Math)
        html = re.sub(r"\$\$(.*?)\$\$", r'<div style="text-align: center; font-style: italic; margin: 15px 0; font-family: serif; font-size: 18px; color: #000000;">\1</div>', html, flags=re.DOTALL)
        
        html_formatted = html.replace('\n', '<br>')
        final_html = f"""
        <html>
        <head>
        <style>
            body {{ font-family: 'Inter', sans-serif; font-size: 14px; color: #1a1a1a; line-height: 1.6; }}
            pre {{ white-space: pre-wrap; }}
        </style>
        </head>
        <body>{html_formatted}</body>
        </html>
        """
        self.content_browser.setHtml(final_html)
        
        # Adjust height based on content
        doc = self.content_browser.document()
        doc.setTextWidth(self.content_browser.width())
        new_height = doc.size().height() + 15
        self.content_browser.setFixedHeight(int(new_height))

    def finalize(self, metrics):
        self.render_markdown() # Final render
        pattern = metrics.get("pattern_id", "NEUTRAL")
        if pattern == "BRUTAL":
            self.setStyleSheet(
                "QFrame#BubbleContainer { background-color: #fafafa; border: 1px solid #000000; border-left: 8px solid #000000; }"
            )
            self.sentiment_label.setText("ADVERSARIAL")
            self.sentiment_label.setStyleSheet("color: #000000; font-size: 10px; font-weight: 900;")
        elif pattern == "DISMISSIVE":
            self.setStyleSheet(
                "QFrame#BubbleContainer { background-color: #ffffff; border: 1px solid #e5e5e5; border-left: 4px solid #666666; }"
            )
            self.sentiment_label.setText("DISMISSIVE")
            self.sentiment_label.setStyleSheet("color: #666666; font-size: 10px; font-weight: 800;")
        else:
            self.sentiment_label.setText("NEUTRAL")
            self.sentiment_label.setStyleSheet("color: #aaaaaa; font-size: 10px; font-weight: 800;")


class DebateWorker(QThread):
    token_received = pyqtSignal(str, str)
    turn_started = pyqtSignal(str, str)
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


class AgonGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agon")
        self.resize(1200, 850)
        self.setStyleSheet(BW_THEME)

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
        sidebar_layout.setContentsMargins(30, 40, 30, 40)
        sidebar_layout.setSpacing(0)

        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(4)
        title = QLabel("Agon")
        title.setObjectName("Title")
        subtitle = QLabel("Knowledge Demands Debate")
        subtitle.setObjectName("Subtitle")
        header_vbox.addWidget(title)
        header_vbox.addWidget(subtitle)
        sidebar_layout.addLayout(header_vbox)
        sidebar_layout.addSpacing(40)

        # Topic
        topic_label = QLabel("TOPIC")
        topic_label.setObjectName("SectionLabel")
        sidebar_layout.addWidget(topic_label)
        sidebar_layout.addSpacing(8)
        self.topic_input = QTextEdit()
        self.topic_input.setPlaceholderText("Enter debate topic...")
        self.topic_input.setText("The ethical limits of recursive self-improvement in LLMs.")
        self.topic_input.setMaximumHeight(120)
        sidebar_layout.addWidget(self.topic_input)
        sidebar_layout.addSpacing(30)

        # Rounds
        rounds_label = QLabel("ROUNDS PER MODEL")
        rounds_label.setObjectName("SectionLabel")
        sidebar_layout.addWidget(rounds_label)
        sidebar_layout.addSpacing(8)
        self.rounds_input = QSpinBox()
        self.rounds_input.setRange(1, 50)
        self.rounds_input.setValue(3)
        self.rounds_input.setFixedHeight(45)
        sidebar_layout.addWidget(self.rounds_input)
        sidebar_layout.addSpacing(30)

        # Models
        models_header = QHBoxLayout()
        models_label = QLabel("MODELS")
        models_label.setObjectName("SectionLabel")
        models_header.addWidget(models_label)
        refresh_btn = QPushButton("REFRESH")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("font-size: 9px; font-weight: 800; color: #666666; border: none; background: none;")
        refresh_btn.clicked.connect(self.refresh_ollama_models)
        models_header.addStretch()
        models_header.addWidget(refresh_btn)
        sidebar_layout.addLayout(models_header)
        sidebar_layout.addSpacing(8)

        self.model_scroll = QScrollArea()
        self.model_scroll.setObjectName("ModelScroll")
        self.model_scroll.setWidgetResizable(True)
        self.model_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.model_container = QWidget()
        self.model_list_layout = QVBoxLayout(self.model_container)
        self.model_list_layout.setContentsMargins(5, 5, 5, 5)
        self.model_list_layout.setSpacing(2)
        self.model_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.model_scroll.setWidget(self.model_container)
        sidebar_layout.addWidget(self.model_scroll)
        sidebar_layout.addSpacing(30)

        self.start_btn = QPushButton("Start Debate")
        self.start_btn.setObjectName("PrimaryBtn")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.toggle_debate)
        sidebar_layout.addWidget(self.start_btn)

        layout.addWidget(sidebar)

        # Chat Panel
        chat_container = QWidget()
        chat_container.setStyleSheet("background-color: #ffffff;")
        self.chat_layout = QVBoxLayout(chat_container)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)

        self.feed_scroll = QScrollArea()
        self.feed_scroll.setWidgetResizable(True)
        self.feed_widget = QWidget()
        self.feed_layout = QVBoxLayout(self.feed_widget)
        self.feed_layout.setContentsMargins(60, 60, 60, 60)
        self.feed_layout.setSpacing(30)
        
        # Empty State
        self.empty_state = EmptyStateWidget()
        self.feed_layout.addWidget(self.empty_state)
        
        self.feed_layout.addStretch()
        self.feed_scroll.setWidget(self.feed_widget)
        self.chat_layout.addWidget(self.feed_scroll)

        layout.addWidget(chat_container)

        self.active_bubbles = {}
        self.worker = None

    def refresh_ollama_models(self):
        for i in reversed(range(self.model_list_layout.count())):
            self.model_list_layout.itemAt(i).widget().setParent(None)

        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                if not models:
                    self.model_list_layout.addWidget(QLabel("No models found", styleSheet="color: #666; padding: 10px;"))
                for m in models:
                    name = m["name"]
                    row = ModelSelectionRow(name)
                    self.model_list_layout.addWidget(row)
            else:
                self.model_list_layout.addWidget(QLabel("Ollama error", styleSheet="color: #666; padding: 10px;"))
        except:
            self.model_list_layout.addWidget(QLabel("Ollama offline", styleSheet="color: #666; padding: 10px;"))

    def toggle_debate(self):
        if self.worker and self.worker.isRunning():
            self.worker._running = False
            self.start_btn.setText("Stopping...")
            self.start_btn.setEnabled(False)
            return

        selected = []
        for i in range(self.model_list_layout.count()):
            w = self.model_list_layout.itemAt(i).widget()
            if isinstance(w, ModelSelectionRow) and w.checkbox.isChecked():
                selected.append(w.model_name)

        if not selected:
            return

        # Hide empty state and clear feed
        self.empty_state.hide()
        for i in reversed(range(self.feed_layout.count())):
            item = self.feed_layout.itemAt(i)
            if item.widget() and item.widget() != self.empty_state:
                item.widget().setParent(None)
        
        # Re-add stretch if it was removed
        if self.feed_layout.count() == 0 or not isinstance(self.feed_layout.itemAt(self.feed_layout.count()-1), QVBoxLayout):
             self.feed_layout.addStretch()

        configs = {
            m: {
                "api_key": "ollama",
                "model_name": m,
                "base_url": "http://localhost:11434/v1",
            }
            for m in selected
        }
        self.engine = AgonEngine(agent_configs=configs)

        self.worker = DebateWorker(
            self.engine, self.topic_input.toPlainText(), self.rounds_input.value()
        )
        self.worker.turn_started.connect(self.on_turn_started)
        self.worker.token_received.connect(self.on_token_received)
        self.worker.turn_finished.connect(self.on_turn_finished)
        self.worker.debate_finished.connect(self.on_debate_finished)

        self.worker.start()
        self.start_btn.setText("Stop Debate")

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
            vbar = self.feed_scroll.verticalScrollBar()
            if vbar.value() > vbar.maximum() - 150:
                vbar.setValue(vbar.maximum())

    def on_turn_finished(self, metrics):
        mid = metrics["persona_id"]
        if mid in self.active_bubbles:
            self.active_bubbles[mid].finalize(metrics)
            del self.active_bubbles[mid]

    def on_debate_finished(self):
        self.start_btn.setText("Start Debate")
        self.start_btn.setEnabled(True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set global font
    font = QFont("Inter", 10)
    app.setFont(font)
    
    gui = AgonGUI()
    gui.show()
    sys.exit(app.exec())
