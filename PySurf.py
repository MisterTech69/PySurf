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
import json
import csv
import hashlib
import base64
from urllib.parse import urlparse
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# FORCE SOFTWARE RENDERING ON RESTRICTED MACHINES
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-gpu --disable-software-rasterizer --single-process"
os.environ["QT_OPENGL"] = "software"

QtWebEngine.QtWebEngine.initialize()


class PasswordManager:
    def __init__(self):
        self.passwords_file = "passwords.enc"
        self.master_key_file = "master.key"
        self.master_password = None
        self.cipher_suite = None
        self.passwords = {}
        
    def create_key_from_password(self, password):
        password = password.encode()
        salt = b'salt_1234567890'  # In production, use a random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def set_master_password(self, password):
        self.master_password = password
        key = self.create_key_from_password(password)
        self.cipher_suite = Fernet(key)
        
        # Save master password hash
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with open(self.master_key_file, 'w') as f:
            f.write(password_hash)
    
    def verify_master_password(self, password):
        if not os.path.exists(self.master_key_file):
            return False
        
        with open(self.master_key_file, 'r') as f:
            stored_hash = f.read().strip()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == stored_hash
    
    def load_passwords(self):
        if not os.path.exists(self.passwords_file) or not self.cipher_suite:
            return
        
        try:
            with open(self.passwords_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            self.passwords = json.loads(decrypted_data.decode())
        except:
            self.passwords = {}
    
    def save_passwords(self):
        if not self.cipher_suite:
            return
        
        data = json.dumps(self.passwords).encode()
        encrypted_data = self.cipher_suite.encrypt(data)
        
        with open(self.passwords_file, 'wb') as f:
            f.write(encrypted_data)
    
    def add_password(self, name, url, username, password, note=""):
        domain = self.extract_domain(url)
        if domain not in self.passwords:
            self.passwords[domain] = []
        
        self.passwords[domain].append({
            'name': name,
            'url': url,
            'username': username,
            'password': password,
            'note': note
        })
        self.save_passwords()
    
    def get_passwords_for_domain(self, url):
        domain = self.extract_domain(url)
        return self.passwords.get(domain, [])
    
    def extract_domain(self, url):
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return url
    
    def import_from_csv(self, file_path):
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if len(row) >= 4:
                        name = row[0].strip()
                        url = row[1].strip()
                        username = row[2].strip()
                        password = row[3].strip()
                        note = row[4].strip() if len(row) > 4 else ""
                        
                        if name and url and username and password:
                            self.add_password(name, url, username, password, note)
            return True
        except Exception as e:
            print(f"Error importing CSV: {e}")
            return False


class PasswordDialog(QDialog):
    def __init__(self, parent=None, is_setup=False):
        super().__init__(parent)
        self.is_setup = is_setup
        self.password = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Master Password" if not self.is_setup else "Setup Master Password")
        self.setFixedSize(300, 150)
        
        layout = QVBoxLayout()
        
        if self.is_setup:
            label = QLabel("Create a master password:")
        else:
            label = QLabel("Enter master password:")
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.accept)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        
        layout.addWidget(label)
        layout.addWidget(self.password_input)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
    
    def accept(self):
        self.password = self.password_input.text()
        if self.password:
            super().accept()


class PasswordManagerWindow(QDialog):
    def __init__(self, password_manager, parent=None):
        super().__init__(parent)
        self.password_manager = password_manager
        self.setup_ui()
        self.load_passwords()
    
    def setup_ui(self):
        self.setWindowTitle("Password Manager")
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton("Add Password")
        import_btn = QPushButton("Import CSV")
        delete_btn = QPushButton("Delete Selected")
        
        add_btn.clicked.connect(self.add_password)
        import_btn.clicked.connect(self.import_csv)
        delete_btn.clicked.connect(self.delete_selected)
        
        toolbar.addWidget(add_btn)
        toolbar.addWidget(import_btn)
        toolbar.addWidget(delete_btn)
        toolbar.addStretch()
        
        # Password list
        self.password_table = QTableWidget()
        self.password_table.setColumnCount(6)
        self.password_table.setHorizontalHeaderLabels(["Name", "URL", "Username", "Password", "Note", "Show"])
        
        header = self.password_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        layout.addLayout(toolbar)
        layout.addWidget(self.password_table)
        
        self.setLayout(layout)
    
    def load_passwords(self):
        self.password_table.setRowCount(0)
        
        for domain, entries in self.password_manager.passwords.items():
            for entry in entries:
                row = self.password_table.rowCount()
                self.password_table.insertRow(row)
                
                self.password_table.setItem(row, 0, QTableWidgetItem(entry['name']))
                self.password_table.setItem(row, 1, QTableWidgetItem(entry['url']))
                self.password_table.setItem(row, 2, QTableWidgetItem(entry['username']))
                self.password_table.setItem(row, 3, QTableWidgetItem("••••••••"))
                self.password_table.setItem(row, 4, QTableWidgetItem(entry['note']))
                
                show_btn = QPushButton("Show")
                show_btn.clicked.connect(lambda checked, r=row, p=entry['password']: self.show_password(r, p))
                self.password_table.setCellWidget(row, 5, show_btn)
    
    def show_password(self, row, password):
        # Ask for master password again for security
        dialog = PasswordDialog(self, is_setup=False)
        if dialog.exec_() == QDialog.Accepted:
            if self.password_manager.verify_master_password(dialog.password):
                self.password_table.setItem(row, 3, QTableWidgetItem(password))
                # Hide password again after 10 seconds
                QTimer.singleShot(10000, lambda: self.password_table.setItem(row, 3, QTableWidgetItem("••••••••")))
            else:
                QMessageBox.warning(self, "Error", "Incorrect master password!")
    
    def add_password(self):
        dialog = AddPasswordDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.password_manager.add_password(
                dialog.name_input.text(),
                dialog.url_input.text(),
                dialog.username_input.text(),
                dialog.password_input.text(),
                dialog.note_input.toPlainText()
            )
            self.load_passwords()
    
    def import_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv)")
        if file_path:
            if self.password_manager.import_from_csv(file_path):
                QMessageBox.information(self, "Success", "Passwords imported successfully!")
                self.load_passwords()
            else:
                QMessageBox.warning(self, "Error", "Failed to import CSV file!")
    
    def delete_selected(self):
        current_row = self.password_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this password?")
            if reply == QMessageBox.Yes:
                # This is a simplified delete - in a full implementation, you'd need to properly track and delete from the password manager
                self.password_table.removeRow(current_row)


class AddPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Add Password")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.url_input = QLineEdit()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.note_input = QTextEdit()
        self.note_input.setMaximumHeight(60)
        
        form.addRow("Name:", self.name_input)
        form.addRow("URL:", self.url_input)
        form.addRow("Username:", self.username_input)
        form.addRow("Password:", self.password_input)
        form.addRow("Note:", self.note_input)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Add")
        cancel_btn = QPushButton("Cancel")
        
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        
        layout.addLayout(form)
        layout.addLayout(buttons)
        
        self.setLayout(layout)


class MyWebBrowser(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MyWebBrowser, self).__init__(*args, **kwargs)
        self.setWindowTitle("PySurf")
        self.resize(1000, 700)
        app.setStyle(QStyleFactory.create("Fusion"))

        # Initialize password manager
        self.password_manager = PasswordManager()
        self.setup_password_manager()

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

        # Password manager button
        self.password_btn = QPushButton("🔒")
        self.password_btn.setFixedWidth(40)
        self.password_btn.clicked.connect(self.open_password_manager)
        button_layout.addWidget(self.password_btn)

        # Tetris button
        self.tetris_btn = QPushButton("")
        self.tetris_btn.setFixedWidth(40)
        self.tetris_btn.clicked.connect(lambda: os.system("python Tetris.py"))
        button_layout.addWidget(self.tetris_btn)

        # Toggle theme button
        self.toggle_theme_btn = QPushButton("🌙")
        self.toggle_theme_btn.setFixedWidth(40)
        self.toggle_theme_btn.clicked.connect(self.toggle_theme)
        button_layout.addWidget(self.toggle_theme_btn)

        self.dark_mode = False
        self.set_light_theme()

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

        # Shortcuts
        self.new_tab_shortcut1 = QShortcut(QKeySequence("Ctrl+T"), self)
        self.new_tab_shortcut1.activated.connect(self.add_new_tab)
        self.new_tab_shortcut2 = QShortcut(QKeySequence("Ctrl+W"), self)
        self.new_tab_shortcut2.activated.connect(self.close_tab)
        self.new_tab_shortcut3 = QShortcut(QKeySequence("Ctrl+R"), self)
        self.new_tab_shortcut3.activated.connect(self.refresh_page)

    def setup_password_manager(self):
        if not os.path.exists(self.password_manager.master_key_file):
            # First time setup
            dialog = PasswordDialog(self, is_setup=True)
            if dialog.exec_() == QDialog.Accepted:
                self.password_manager.set_master_password(dialog.password)
                self.password_manager.load_passwords()
            else:
                QApplication.quit()
        else:
            # Load existing setup
            dialog = PasswordDialog(self, is_setup=False)
            if dialog.exec_() == QDialog.Accepted:
                if self.password_manager.verify_master_password(dialog.password):
                    self.password_manager.set_master_password(dialog.password)
                    self.password_manager.load_passwords()
                else:
                    QMessageBox.critical(self, "Error", "Incorrect master password!")
                    QApplication.quit()
            else:
                QApplication.quit()

    def open_password_manager(self):
        dialog = PasswordManagerWindow(self.password_manager, self)
        dialog.exec_()

    def add_new_tab(self, qurl=None, label="New Tab"):
        if qurl is None or isinstance(qurl, bool):
            qurl = QUrl("https://www.google.com")
        browser = QWebEngineView()
        browser.setUrl(qurl)
        
        # Set up autofill
        browser.loadFinished.connect(lambda ok, b=browser: self.setup_autofill(b))
        
        i = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(i)
        browser.urlChanged.connect(
            lambda qurl, browser=browser: self.update_urlbar(qurl, browser))
        browser.loadFinished.connect(
            lambda _, i=i, browser=browser: self.tabs.setTabText(i, browser.page().title()))

    def setup_autofill(self, browser):
        current_url = browser.url().toString()
        passwords = self.password_manager.get_passwords_for_domain(current_url)
        
        if passwords:
            # Inject autofill JavaScript
            for password_entry in passwords:
                script = f"""
                (function() {{
                    var inputs = document.querySelectorAll('input[type="email"], input[type="text"], input[name*="user"], input[name*="email"], input[id*="user"], input[id*="email"]');
                    var passwordInputs = document.querySelectorAll('input[type="password"]');
                    
                    if (inputs.length > 0 && passwordInputs.length > 0) {{
                        var loginForm = inputs[0].closest('form');
                        if (loginForm) {{
                            var fillButton = document.createElement('button');
                            fillButton.innerHTML = '🔒 Fill Password';
                            fillButton.style.cssText = 'position: fixed; top: 10px; right: 10px; z-index: 10000; background: #4CAF50; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;';
                            fillButton.onclick = function(e) {{
                                e.preventDefault();
                                inputs[0].value = '{password_entry["username"]}';
                                passwordInputs[0].value = '{password_entry["password"]}';
                                inputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                                passwordInputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                            }};
                            document.body.appendChild(fillButton);
                        }}
                    }}
                }})();
                """
                browser.page().runJavaScript(script)
                break  # Only use the first matching password

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