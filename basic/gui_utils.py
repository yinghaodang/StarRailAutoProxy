import os

import pyautogui
from pygetwindow import Win32Window


def get_win_by_name(window_name: str) -> Win32Window:
    """
    根据名称找到具体的窗口 需完全相等
    :param window_name: 窗口名称
    :return: Application
    :raise PyAutoGUIException
    """
    windows = pyautogui.getWindowsWithTitle(window_name)
    if len(windows) > 0:
        for win in windows:
            if win.title == window_name:
                return win
    raise pyautogui.PyAutoGUIException


def active_win(win: Win32Window):
    """
    切换到具体的窗口上
    :param win: 窗口
    :return: None
    :raise PyAutoGUIException 找不到对应窗口
    """
    if win is not None:
        win.activate()
    else:
        raise pyautogui.PyAutoGUIException


def is_active_win(win: Win32Window) -> bool:
    """
    判断窗口是否最前激活
    :param win: 窗口
    :return: 是否最前激活 空窗口返回False
    """
    return win.isActive if win is not None else False


def is_active_win_by_name(window_name: str):
    """
    根据窗口名称判断窗口是否最前激活
    :param window_name: 窗口名称
    :return: 如果窗口不存在 返回False 否则返回是否激活
    """
    try:
        win = get_win_by_name(window_name)
        return is_active_win(win)
    except pyautogui.PyAutoGUIException:
        return False


def close_win_with_f4(win: Win32Window):
    """
    先切换到窗口 再使用 ALT+F4 对窗口进行关闭 可能只会最小化到任务栏
    :param win: 窗口
    :return: None
    :raise PyAutoGUIException 找不到对应窗口
    """
    if win is not None:
        win.activate()
        pyautogui.hotkey('alt', 'f4')
    else:
        raise pyautogui.PyAutoGUIException


def close_win_with_f4_by_name(window_name: str):
    """
    根据窗口名称
    先切换到窗口 再使用 ALT+F4 对窗口进行关闭 可能只会最小化到任务栏
    :param window_name: 窗口名称
    :return: None
    :raise PyAutoGUIException 找不到对应窗口
    """
    win: Win32Window = get_win_by_name(window_name)
    close_win_with_f4(win)


def shutdown_sys(seconds: int):
    """
    ${minutes} 秒后自动关机
    使用 shutdown -s -t ${minutes} 来关闭系统
    :param seconds: 秒
    :return:
    """
    os.system("shutdown -s -t %d" % seconds)


def cancel_shutdown_sys():
    """
    取消计划的自动关机
    使用 shutdown -a 命令
    :return:
    """
    os.system("shutdown -a")
