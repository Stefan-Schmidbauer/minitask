import ctypes
import ctypes.util

_CLIENT_MESSAGE = 33
_PROPERTY_CHANGE_MASK = 1 << 22
_SUBSTRUCTURE_NOTIFY_MASK = 1 << 19
_SUBSTRUCTURE_REDIRECT_MASK = 1 << 20
_PROP_MODE_APPEND = 2
_SOURCE_PAGER = 2


class _XPropertyEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("atom", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("state", ctypes.c_int),
    ]


class _XClientMessageEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("window", ctypes.c_ulong),
        ("message_type", ctypes.c_ulong),
        ("format", ctypes.c_int),
        ("data", ctypes.c_long * 5),
    ]


class _XEvent(ctypes.Union):
    _fields_ = [
        ("type", ctypes.c_int),
        ("xproperty", _XPropertyEvent),
        ("xclient", _XClientMessageEvent),
        ("pad", ctypes.c_long * 24),
    ]


def _load_xlib():
    xlib = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
    xlib.XOpenDisplay.restype = ctypes.c_void_p
    xlib.XOpenDisplay.argtypes = [ctypes.c_char_p]
    xlib.XDefaultRootWindow.restype = ctypes.c_ulong
    xlib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    xlib.XInternAtom.restype = ctypes.c_ulong
    xlib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    xlib.XCreateSimpleWindow.restype = ctypes.c_ulong
    xlib.XCreateSimpleWindow.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
        ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_ulong, ctypes.c_ulong,
    ]
    xlib.XSelectInput.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_long]
    xlib.XChangeProperty.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
    ]
    xlib.XWindowEvent.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_long, ctypes.POINTER(_XEvent),
    ]
    xlib.XSendEvent.argtypes = [
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long,
        ctypes.POINTER(_XEvent),
    ]
    xlib.XDestroyWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    xlib.XFlush.argtypes = [ctypes.c_void_p]
    xlib.XCloseDisplay.argtypes = [ctypes.c_void_p]
    return xlib


def _server_time(xlib, display, root) -> int:
    """Current X server time, read from the PropertyNotify of a dummy change."""
    window = xlib.XCreateSimpleWindow(display, root, 0, 0, 1, 1, 0, 0, 0)
    xlib.XSelectInput(display, window, _PROPERTY_CHANGE_MASK)
    atom = xlib.XInternAtom(display, b"_MINITASK_TIMESTAMP", False)
    xlib.XChangeProperty(display, window, atom, atom, 8, _PROP_MODE_APPEND, b"", 0)
    event = _XEvent()
    xlib.XWindowEvent(display, window, _PROPERTY_CHANGE_MASK, ctypes.byref(event))
    xlib.XDestroyWindow(display, window)
    return event.xproperty.time


def activate_window(win_id: int) -> None:
    """Ask the window manager to activate win_id with a current timestamp.

    Qt's activateWindow() sends the time of the last X event the app received.
    When the request is triggered from outside (a second launch), that time
    predates the user's last interaction elsewhere, so focus stealing
    prevention (e.g. Muffin) only marks the window as demanding attention.
    """
    xlib = _load_xlib()
    display = xlib.XOpenDisplay(None)
    if not display:
        return
    try:
        root = xlib.XDefaultRootWindow(display)
        event = _XEvent()
        event.xclient.type = _CLIENT_MESSAGE
        event.xclient.window = win_id
        event.xclient.message_type = xlib.XInternAtom(
            display, b"_NET_ACTIVE_WINDOW", False
        )
        event.xclient.format = 32
        event.xclient.data[0] = _SOURCE_PAGER
        event.xclient.data[1] = _server_time(xlib, display, root)
        xlib.XSendEvent(
            display, root, False,
            _SUBSTRUCTURE_NOTIFY_MASK | _SUBSTRUCTURE_REDIRECT_MASK,
            ctypes.byref(event),
        )
        xlib.XFlush(display)
    finally:
        xlib.XCloseDisplay(display)
