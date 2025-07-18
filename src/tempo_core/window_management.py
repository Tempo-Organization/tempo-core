import platform

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:

    import ctypes
    from ctypes import wintypes

    import psutil
    import screeninfo

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    SW_MINIMIZE = 6
    SW_MAXIMIZE = 3
    SW_RESTORE = 9
    WM_CLOSE = 0x0010

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.MoveWindow.argtypes = [
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.BOOL,
    ]
    user32.MoveWindow.restype = wintypes.BOOL
    user32.SetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
    user32.SetWindowTextW.restype = wintypes.BOOL
    user32.PostMessageW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL


    def enum_windows():
        windows = []

        @EnumWindowsProc
        def foreach_window(hwnd, lParam):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value
                    windows.append((hwnd, title))
            return True

        user32.EnumWindows(foreach_window, 0)
        return windows


    def does_window_exist(process_name: str, *, use_substring_check: bool = False) -> bool:
        for proc in psutil.process_iter(["name"]):
            if proc.info["name"] and proc.info["name"].lower() == process_name.lower():  # type: ignore
                return True
        return False


    def get_windows_by_title(
        window_title: str, *, use_substring_check: bool = False
    ) -> list:
        matched_windows = []
        try:
            windows = enum_windows()
            # for hwnd, title in enum_windows():
            #     print(f"HWND: {hwnd}, Title: {title}")
            if use_substring_check:
                matched_windows = [
                    (hwnd, title) for hwnd, title in windows if window_title in title
                ]
            else:
                matched_windows = [
                    (hwnd, title)
                    for hwnd, title in windows
                    if title.strip() == window_title.strip()
                ]
        except Exception as e:
            print(f"Error in get_windows_by_title: {e}")
        return matched_windows


    def get_window_by_title(window_title: str, *, use_substring_check: bool = False):
        windows = get_windows_by_title(
            window_title=window_title, use_substring_check=use_substring_check
        )
        if not windows:
            print(f'Warning: No windows found with title "{window_title}"')
            return None
        return windows[0]


    def minimize_window(hwnd):
        user32.ShowWindow(hwnd, SW_MINIMIZE)


    def maximize_window(hwnd):
        user32.ShowWindow(hwnd, SW_MAXIMIZE)


    def restore_window(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)


    def close_window(hwnd):
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


    def move_window_to_monitor(hwnd, monitor_index=0):
        monitors = screeninfo.get_monitors()
        if monitor_index >= len(monitors):
            print("Invalid monitor index")
            return
        monitor = monitors[monitor_index]
        move_window(hwnd, monitor.x, monitor.y, None, None)


    def set_window_size(hwnd, width, height):
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            print("Failed to get window rect")
            return
        x, y = rect.left, rect.top
        user32.MoveWindow(hwnd, x, y, width, height, True)


    def move_window(hwnd, x, y, width=None, height=None):
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            print("Failed to get window rect")
            return
        cur_width = rect.right - rect.left
        cur_height = rect.bottom - rect.top
        w = width if width is not None else cur_width
        h = height if height is not None else cur_height
        success = user32.MoveWindow(hwnd, x, y, w, h, True)
        if not success:
            print("Failed to move window")


    def change_window_name(hwnd, new_title: str):
        if not user32.SetWindowTextW(hwnd, new_title):
            print(f"Failed to set window title to {new_title}")


    def move_window_with_settings(hwnd, window_settings: dict):
        monitor_index = window_settings.get("monitor")
        if monitor_index is not None:
            move_window_to_monitor(hwnd, monitor_index)
        resolution = window_settings.get("resolution", {})
        width = resolution.get("x")
        height = resolution.get("y")
        if width is not None and height is not None:
            set_window_size(hwnd, width, height)


    def get_window_title(hwnd) -> str:
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            return buffer.value
        return ""


    def find_hwnd_by_process_name(process_name):
        # Enumerate all windows and try to find one owned by the process name
        windows = enum_windows()
        for hwnd, title in windows:
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                # Optionally: Get process ID for hwnd and check process name
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                try:
                    proc = psutil.Process(pid.value)
                    if proc.name().lower() == process_name.lower():
                        return hwnd
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        return None
else:
    def not_supported(*args, **kwargs):
        print("Warning: Window control functions are only supported on Windows.")

    # Define dummy versions of functions
    enum_windows = does_window_exist = get_windows_by_title = get_window_by_title = \
    minimize_window = maximize_window = restore_window = close_window = \
    move_window_to_monitor = set_window_size = move_window = change_window_name = \
    move_window_with_settings = get_window_title = find_hwnd_by_process_name = not_supported # type: ignore
