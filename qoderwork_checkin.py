#!/usr/bin/env python3
"""
QoderWork 每日签到自动化脚本
==============================
功能: 自动激活 QoderWork 窗口并完成每日签到领取积分
原理: 通过 Win32 API 查找并激活窗口，通过 pyautogui 模拟鼠标点击

用法:
  python qoderwork_checkin.py           # 正常执行签到
  python qoderwork_checkin.py --dry-run # 仅测试，不执行点击
  python qoderwork_checkin.py --max     # 最大化窗口后签到

日志保存在脚本同目录下的 checkin.log
"""

import sys
import time
import ctypes
import ctypes.wintypes
import logging
import argparse
from pathlib import Path
from datetime import datetime

import pyautogui

# ================================================================
#  配置区域 —— 根据实际环境修改以下参数
# ================================================================

# 按钮的屏幕绝对坐标（根据显示器分辨率设定）
# 如果更换显示器或修改了分辨率/缩放，需要重新获取坐标
CHECKIN_ENTRY_BUTTON = (2218, 19)    # "签到/邀请，赚积分" 按钮
CHECKIN_CONFIRM_BUTTON = (2236, 271)  # "签到" 确认按钮

# 各步骤之间的等待时间（秒），可根据网络/响应速度调整
WAIT_AFTER_ACTIVATE = 1.5     # 激活窗口后等待
WAIT_AFTER_ENTRY = 1.5        # 点击入口按钮后等待
WAIT_AFTER_CONFIRM = 0.5      # 点击签到按钮后等待

# 查找窗口时的重试设置
MAX_RETRIES = 5               # 最大重试次数
RETRY_INTERVAL = 3            # 每次重试间隔（秒）

# 用于匹配 QoderWork 窗口标题的关键词（不区分大小写，任一匹配即可）
WINDOW_KEYWORDS = ["QoderWork", "Qoder", "qoderwork"]

# ================================================================
#  日志配置
# ================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "checkin.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-4s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("checkin")

# ================================================================
#  pyautogui 安全设置
# ================================================================

pyautogui.FAILSAFE = True     # 鼠标移到屏幕左上角可中断
pyautogui.PAUSE = 0.3         # 每次操作后短暂停顿

# ================================================================
#  Win32 API 声明
# ================================================================

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_bool,
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPARAM,
)


def _get_window_text(hwnd: int) -> str:
    """获取窗口标题文本"""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value.strip()


def _is_window_match(hwnd: int) -> bool:
    """判断窗口是否匹配 QoderWork"""
    title = _get_window_text(hwnd).lower()
    return any(kw.lower() in title for kw in WINDOW_KEYWORDS)


# ================================================================
#  窗口操作函数
# ================================================================

def find_qoderwork_hwnd() -> int | None:
    """
    枚举所有可见窗口，查找匹配的 QoderWork 窗口句柄。
    优先匹配标题中精确包含 "QoderWork" 的窗口。
    """
    found: list[int] = []

    def _callback(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            if _is_window_match(hwnd):
                found.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(_callback), 0)

    if not found:
        return None

    # 优先返回标题中精确包含 "QoderWork" 的窗口
    for hwnd in found:
        if "qoderwork" in _get_window_text(hwnd).lower():
            return hwnd
    return found[0]


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    """获取窗口矩形 (left, top, right, bottom)"""
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def activate_window(hwnd: int, maximize: bool = False) -> None:
    """
    激活窗口，使其处于前台可见状态。
    如果窗口被最小化，先恢复；如果指定 maximize=True，则最大化。
    """
    SW_RESTORE = 9
    SW_SHOWMAXIMIZED = 3

    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.5)

    if maximize:
        user32.ShowWindow(hwnd, SW_SHOWMAXIMIZED)
        time.sleep(0.3)

    user32.SetForegroundWindow(hwnd)


def do_click(x: int, y: int, desc: str = "", move_duration: float = 0.3) -> None:
    """平滑移动鼠标到目标位置并单击，避免瞬间跳变"""
    pyautogui.moveTo(x, y, duration=move_duration)
    time.sleep(0.15)
    pyautogui.click()
    log.info("  点击 (%d, %d) %s", x, y, f"— {desc}" if desc else "")


# ================================================================
#  签到主流程
# ================================================================

def run_checkin(maximize: bool = False, dry_run: bool = False) -> bool:
    """
    执行完整的签到流程。
    返回 True 表示成功，False 表示失败。
    """
    # 步骤 1: 查找并激活 QoderWork 窗口
    log.info("正在查找 QoderWork 窗口...")
    hwnd = None
    for attempt in range(1, MAX_RETRIES + 1):
        hwnd = find_qoderwork_hwnd()
        if hwnd:
            break
        if attempt < MAX_RETRIES:
            log.warning("未找到窗口 (%d/%d)，%d 秒后重试...",
                        attempt, MAX_RETRIES, RETRY_INTERVAL)
            time.sleep(RETRY_INTERVAL)

    if not hwnd:
        log.error("在 %d 次尝试后仍未找到 QoderWork 窗口，请确认程序已启动", MAX_RETRIES)
        return False

    title = _get_window_text(hwnd)
    left, top, right, bottom = get_window_rect(hwnd)
    log.info("找到窗口: \"%s\"  位置: (%d,%d) - (%d,%d)", title, left, top, right, bottom)

    # 步骤 2: 激活窗口
    log.info("激活窗口%s...", "（最大化）" if maximize else "")
    activate_window(hwnd, maximize=maximize)
    time.sleep(WAIT_AFTER_ACTIVATE)

    if dry_run:
        log.info("[DRY-RUN] 窗口已激活，跳过点击操作")
        log.info("  将点击入口按钮: (%d, %d)", *CHECKIN_ENTRY_BUTTON)
        log.info("  将点击签到按钮: (%d, %d)", *CHECKIN_CONFIRM_BUTTON)
        return True

    # 步骤 3: 点击 "签到/邀请，赚积分" 按钮
    x1, y1 = CHECKIN_ENTRY_BUTTON
    log.info("点击「签到/邀请，赚积分」按钮...")
    do_click(x1, y1, desc="签到/邀请入口")
    time.sleep(WAIT_AFTER_ENTRY)

    # 步骤 4: 点击 "签到" 确认按钮
    x2, y2 = CHECKIN_CONFIRM_BUTTON
    log.info("点击「签到」确认按钮...")
    do_click(x2, y2, desc="签到确认")
    time.sleep(WAIT_AFTER_CONFIRM)

    return True


# ================================================================
#  入口
# ================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="QoderWork 每日签到自动化")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="测试模式：仅查找并激活窗口，不执行点击",
    )
    parser.add_argument(
        "--max", action="store_true",
        help="激活窗口时将其最大化",
    )
    args = parser.parse_args()

    log.info("=" * 55)
    log.info("QoderWork 签到  |  %s  |  %s",
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             "DRY-RUN" if args.dry_run else "正式执行")

    success = run_checkin(maximize=args.max, dry_run=args.dry_run)

    if success:
        log.info("完成!\n")
    else:
        log.error("签到失败，请检查上方日志\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
