import sys
import os
import json
import subprocess
import requests
import socks
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QComboBox, QMessageBox
)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt

CONFIG_PATH = os.path.expanduser("~/.fluxip/settings.json")

class FluxIP(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FluxIP (Proxy Switcher)")
        self.setFixedSize(420, 380)
        self.setStyleSheet("background-color: #121212; color: white;")
        self.setWindowIcon(QIcon("icon.icns"))  # <- pastikan icon.icns ada

        font = QFont("Segoe UI", 10)

        # Inputs
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("e.g. 123.45.67.89")

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("e.g. 8080")

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("(optional)")

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("(optional)")

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["http", "socks4", "socks5"])

        layout = QVBoxLayout()
        layout.addLayout(self._form_row("Proxy IP", self.ip_input, font))
        layout.addLayout(self._form_row("Port", self.port_input, font))
        layout.addLayout(self._form_row("Username", self.user_input, font))
        layout.addLayout(self._form_row("Password", self.pass_input, font))
        layout.addLayout(self._form_row("Protocol", self.protocol_combo, font))

        self.status_label = QLabel("Current IP: Not Checked")
        self.status_label.setFont(font)
        self.status_label.setStyleSheet("color: #999;")

        self.proxy_status = QLabel("Proxy: Disconnected")
        self.proxy_status.setFont(font)
        self.proxy_status.setStyleSheet("color: red;")

        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("✓ Connect Proxy")
        self.disconnect_btn = QPushButton("× Disconnect")
        self.save_btn = QPushButton("💾 Save Config")

        for btn in [self.connect_btn, self.disconnect_btn, self.save_btn]:
            btn.setFont(font)
            btn.setStyleSheet("background-color: #1e1e1e; padding: 6px; border-radius: 6px;")

        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.disconnect_btn)

        layout.addWidget(self.status_label)
        layout.addWidget(self.proxy_status)
        layout.addLayout(btn_layout)
        layout.addWidget(self.save_btn)

        self.footer_label = QLabel('<a href="https://github.com/yogaxdd">Made With 💖 By @yogakokxd</a>')
        self.footer_label.setTextFormat(Qt.TextFormat.RichText)
        self.footer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.footer_label.setOpenExternalLinks(True)
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_label.setFont(QFont("Segoe UI", 9))
        self.footer_label.setStyleSheet("margin-top: 10px; color: #888;")
        layout.addWidget(self.footer_label)

        self.setLayout(layout)

        # Signals
        self.connect_btn.clicked.connect(self.connect_proxy)
        self.disconnect_btn.clicked.connect(self.disconnect_proxy)
        self.save_btn.clicked.connect(self.save_config)

        self.load_config()
        self.check_ip()

    def _form_row(self, label_text, widget, font):
        layout = QHBoxLayout()
        label = QLabel(label_text + ":")
        label.setFont(font)
        label.setFixedWidth(90)
        widget.setFont(font)
        widget.setStyleSheet("background-color: #1e1e1e; color: white; border: none; padding: 4px;")
        layout.addWidget(label)
        layout.addWidget(widget)
        return layout

    def get_active_services(self):
        result = subprocess.run(["networksetup", "-listallnetworkservices"], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        services = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("*") or "denotes that" in line.lower():
                continue
            services.append(line)
        return services

    def connect_proxy(self):
        ip = self.ip_input.text()
        port = self.port_input.text()
        username = self.user_input.text()
        password = self.pass_input.text()
        protocol = self.protocol_combo.currentText()

        try:
            session = requests.Session()
            proxy_url = f"{protocol}://{ip}:{port}"
            if protocol.startswith("socks"):
                session.proxies = {
                    "http": f"socks5://{ip}:{port}",
                    "https": f"socks5://{ip}:{port}"
                }
            else:
                session.proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
            r = session.get("https://ipinfo.io/ip", timeout=5)
            if r.status_code != 200:
                raise Exception("Proxy unreachable")
        except Exception as e:
            self.proxy_status.setText("Proxy: Error Connect")
            self.proxy_status.setStyleSheet("color: orange;")
            QMessageBox.critical(self, "Error", f"Failed to connect to proxy:\n{e}")
            return

        services = self.get_active_services()

        try:
            for service in services:
                if protocol == "http":
                    subprocess.run(["networksetup", "-setwebproxy", service, ip, port], check=True)
                    subprocess.run(["networksetup", "-setsecurewebproxy", service, ip, port], check=True)
                    if username:
                        subprocess.run(["networksetup", "-setwebproxyusername", service, username], check=True)
                    if password:
                        subprocess.run(["networksetup", "-setwebproxypassword", service, password], check=True)
                    subprocess.run(["networksetup", "-setwebproxystate", service, "on"], check=True)
                    subprocess.run(["networksetup", "-setsecurewebproxystate", service, "on"], check=True)
                else:
                    subprocess.run(["networksetup", "-setsocksfirewallproxy", service, ip, port], check=True)
                    subprocess.run(["networksetup", "-setsocksfirewallproxystate", service, "on"], check=True)

            self.proxy_status.setText("Proxy: Connected")
            self.proxy_status.setStyleSheet("color: green;")
            self.check_ip()
            QMessageBox.information(self, "Connected", "Proxy connected globally!")
        except subprocess.CalledProcessError as e:
            self.proxy_status.setText("Proxy: Error Connect")
            self.proxy_status.setStyleSheet("color: orange;")
            QMessageBox.critical(self, "Error", f"System failed to apply proxy:\n{e}")

    def disconnect_proxy(self):
        services = self.get_active_services()
        for service in services:
            subprocess.run(["networksetup", "-setwebproxystate", service, "off"])
            subprocess.run(["networksetup", "-setsecurewebproxystate", service, "off"])
            subprocess.run(["networksetup", "-setsocksfirewallproxystate", service, "off"])
        self.status_label.setText("Current IP: Not Checked")
        self.proxy_status.setText("Proxy: Disconnected")
        self.proxy_status.setStyleSheet("color: red;")
        QMessageBox.information(self, "Disconnected", "Proxy disconnected.")

    def save_config(self):
        config = {
            "ip": self.ip_input.text(),
            "port": self.port_input.text(),
            "username": self.user_input.text(),
            "password": self.pass_input.text(),
            "protocol": self.protocol_combo.currentText()
        }
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f)
        QMessageBox.information(self, "Saved", "Configuration saved.")

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                config = json.load(f)
                self.ip_input.setText(config.get("ip", ""))
                self.port_input.setText(config.get("port", ""))
                self.user_input.setText(config.get("username", ""))
                self.pass_input.setText(config.get("password", ""))
                self.protocol_combo.setCurrentText(config.get("protocol", "http"))

    def check_ip(self):
        try:
            ip = requests.get("https://ipinfo.io/ip", timeout=5).text.strip()
            self.status_label.setText(f"Current IP: {ip}")
        except:
            self.status_label.setText("Current IP: (failed to check)")

    def closeEvent(self, event):
        if "Connected" in self.proxy_status.text():
            reply = QMessageBox()
            reply.setWindowTitle("Proxy is Still Active")
            reply.setText("If you want to disconnect proxy, please click 'Disconnect' first.")
            reply.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
            reply.setDefaultButton(QMessageBox.StandardButton.Cancel)
            reply.button(QMessageBox.StandardButton.Yes).setText("Exit Anyway")
            reply.button(QMessageBox.StandardButton.Cancel).setText("Back to Proxy Switcher")
            result = reply.exec()
            if result == QMessageBox.StandardButton.Cancel:
                event.ignore()
            else:
                event.accept()
        else:
            event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FluxIP()
    window.show()
    sys.exit(app.exec())
