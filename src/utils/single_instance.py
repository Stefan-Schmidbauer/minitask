import getpass
import os

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    """Ensure only one MiniTask instance runs per user.

    A second instance connects to the running one via a local socket,
    which then emits activation_requested; the second instance exits.

    On Wayland, windows may only take focus with an xdg-activation token.
    The launcher hands it to the second instance (XDG_ACTIVATION_TOKEN),
    so it is forwarded to the running instance, where Qt's Wayland backend
    picks it up on the next activateWindow().
    """

    activation_requested = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._name = f"minitask-{getpass.getuser()}"
        self._server = QLocalServer(self)
        self._server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self._server.newConnection.connect(self._on_new_connection)

    def notify_running_instance(self) -> bool:
        """Return True if another instance is running and was asked to activate."""
        socket = QLocalSocket()
        socket.connectToServer(self._name)
        if not socket.waitForConnected(500):
            return False
        token = os.environ.get("XDG_ACTIVATION_TOKEN", "")
        if token:
            socket.write(token.encode())
            socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return True

    def listen(self) -> None:
        if not self._server.listen(self._name):
            # Stale socket left behind by a crashed instance
            QLocalServer.removeServer(self._name)
            self._server.listen(self._name)

    def _on_new_connection(self):
        socket = self._server.nextPendingConnection()
        if not socket:
            return
        if socket.state() == QLocalSocket.LocalSocketState.UnconnectedState:
            self._on_client_done(socket)
        else:
            socket.disconnected.connect(lambda: self._on_client_done(socket))

    def _on_client_done(self, socket: QLocalSocket):
        token = bytes(socket.readAll().data()).decode(errors="ignore").strip()
        socket.deleteLater()
        if token:
            os.environ["XDG_ACTIVATION_TOKEN"] = token
        self.activation_requested.emit()
