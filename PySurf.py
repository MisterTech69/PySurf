from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5 import QtGui
import sys
from PyQt5 import QtWebEngineWidgets, QtWebEngine
from PyQt5.QtWidgets import QApplication, QMainWindow, QStyleFactory
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence
import os
import keyboard
# FORCE SOFTWARE RENDERING ON RESTRICTED MACHINES
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-gpu --disable-software-rasterizer --single-process"
os.environ["QT_OPENGL"] = "software"

QtWebEngine.QtWebEngine.initialize()


class MyWebBrowser(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MyWebBrowser, self).__init__(*args, **kwargs)
        self.setWindowTitle("PySurf")
        self.resize(1000, 700)
        app.setStyle(QStyleFactory.create("Fusion"))

        # Central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL and press Enter")
        self.url_bar.returnPressed.connect(self.load_url)

        # Buttons
        self.go_btn = QPushButton("Go")
        self.back_btn = QPushButton("<")
        self.forward_btn = QPushButton(">")
        self.refresh_btn = QPushButton("🔄")

        self.go_btn.clicked.connect(self.load_url)
        self.back_btn.clicked.connect(self.go_back)
        self.forward_btn.clicked.connect(self.go_forward)
        self.refresh_btn.clicked.connect(self.refresh_page)

        # Button layout
        button_layout.addWidget(self.url_bar)
        button_layout.addWidget(self.go_btn)
        button_layout.addWidget(self.back_btn)
        button_layout.addWidget(self.forward_btn)

        # Add new tab button
        self.new_tab_btn = QPushButton("+")
        self.new_tab_btn.setFixedWidth(30)
        self.new_tab_btn.clicked.connect(self.add_new_tab)
        button_layout.addWidget(self.new_tab_btn)

        # Tetris button
        self.tetris_btn = QPushButton("")  # Add a button for Tetris
        self.tetris_btn.setFixedWidth(40)
        self.tetris_btn.clicked.connect(lambda: os.system("python Tetris.py"))
        button_layout.addWidget(self.tetris_btn)

        # Toggle theme button
        self.toggle_theme_btn = QPushButton("🌙")
        self.toggle_theme_btn.setFixedWidth(40)
        self.toggle_theme_btn.clicked.connect(self.toggle_theme)
        button_layout.addWidget(self.toggle_theme_btn)

        self.dark_mode = False  # Track current theme
        self.set_light_theme()  # Set default theme

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)

        # Add initial tab
        self.add_new_tab(QUrl("https://www.google.com"), "New Tab")

        # Icon
        self.setWindowIcon(QtGui.QIcon('icon.png'))

        # Assemble layouts
        layout.addLayout(button_layout)
        layout.addWidget(self.tabs)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        # new tab shortcut
        self.new_tab_shortcut1 = QShortcut(QKeySequence("Ctrl+T"), self)
        self.new_tab_shortcut1.activated.connect(self.add_new_tab)
        self.new_tab_shortcut2 = QShortcut(QKeySequence("Ctrl+W"), self)
        self.new_tab_shortcut2.activated.connect(self.close_tab)
        self.new_tab_shortcut3 = QShortcut(QKeySequence("Ctrl+R"), self)
        self.new_tab_shortcut3.activated.connect(self.refresh_page)

    def add_new_tab(self, qurl=None, label="New Tab"):
        if qurl is None or isinstance(qurl, bool):
            qurl = QUrl("https://www.google.com")
        browser = QWebEngineView()
        browser.setUrl(qurl)
        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)
        browser.urlChanged.connect(
            lambda qurl, browser=browser: self.update_urlbar(qurl, browser))
        browser.loadFinished.connect(
            lambda _, i=i, browser=browser: self.tabs.setTabText(i, browser.page().title()))

    def close_tab(self, i):
        if self.tabs.count() < 2:
            return
        self.tabs.removeTab(i)

    def current_tab_changed(self, i):
        qurl = self.current_browser().url()
        self.update_urlbar(qurl, self.current_browser())

    def current_browser(self):
        return self.tabs.currentWidget()

    def load_url(self):
        url = self.url_bar.text()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        self.current_browser().setUrl(QUrl(url))

    def go_back(self):
        self.current_browser().back()

    def go_forward(self):
        self.current_browser().forward()

    def update_urlbar(self, qurl, browser=None):
        if browser != self.current_browser():
            return
        self.url_bar.setText(qurl.toString())
        self.url_bar.setCursorPosition(0)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.set_dark_theme()
            self.toggle_theme_btn.setText("☀️")
        else:
            self.set_light_theme()
            self.toggle_theme_btn.setText("🌙")

    def refresh_page(self):
        self.current_browser().reload()

    def set_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.instance().setPalette(palette)

    def set_light_theme(self):
        QApplication.instance().setPalette(QApplication.style().standardPalette())


app = QApplication([])
window = MyWebBrowser()
window.show()
app.exec_()
