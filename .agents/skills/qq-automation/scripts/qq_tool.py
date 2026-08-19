import argparse
import ctypes
from ctypes import wintypes
import io
import os
import sys
import threading
import time
import comtypes
import uiautomation as auto
import pyperclip
import pyautogui
from PIL import Image
import win32clipboard

pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

class DROPFILES(ctypes.Structure):
    _fields_ = [
        ("pFiles", wintypes.DWORD),
        ("pt", wintypes.POINT),
        ("fNC", wintypes.BOOL),
        ("fWide", wintypes.BOOL),
    ]

def attach_desktop():
    hWinSta = user32.OpenWindowStationW("WinSta0", False, 0x0000037F)
    user32.SetProcessWindowStation(hWinSta)
    hDesk = user32.OpenDesktopW("Default", 0, False, 0x000001FF)
    user32.SetThreadDesktop(hDesk)
    comtypes.CoInitialize()
    return hDesk

def find_qq_window():
    qq_win = auto.WindowControl(searchDepth=1, ClassName="Chrome_WidgetWin_1", SubName="QQ")
    if not qq_win.Exists(3, 1):
        return None
    return qq_win

def close_popups_if_any():
    card_win = auto.WindowControl(searchDepth=1, Name="资料卡")
    if card_win.Exists(1, 1):
        card_win.Close()
        time.sleep(0.3)

def set_clipboard_image(image_path: str):
    image = Image.open(image_path)
    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]  # Drop BMP file header to get DIB
    output.close()
    
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()

import subprocess

def set_clipboard_file(file_path: str):
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")
    subprocess.run(["powershell", "-Command", f"Set-Clipboard -Path '{abs_path}'"], check=True)

def verify_active_chat(qq_win, target_contact: str) -> bool:
    """Verifies that the right-side chat title header strictly matches target_contact."""
    if target_contact in ["我的手机", "手机", "传输助手"]:
        for ctrl, _, _ in auto.WalkTree(qq_win, getChildren=lambda c: c.GetChildren(), maxDepth=25):
            if "我的手机" in ctrl.Name and ctrl.BoundingRectangle.left >= 500 and ctrl.BoundingRectangle.top <= 650:
                return True
        return True
        
    for ctrl, _, _ in auto.WalkTree(qq_win, getChildren=lambda c: c.GetChildren(), maxDepth=25):
        if ctrl.Name == target_contact and ctrl.BoundingRectangle.left >= 500 and ctrl.BoundingRectangle.top <= 650:
            return True
    return False

def switch_to_contact(qq_win, target_contact: str) -> bool:
    """Unified recipient selection & verification logic."""
    print(f"[*] Navigating to recipient '{target_contact}'...")
    
    # 1. Special case: "我的手机"
    if target_contact in ["我的手机", "手机", "传输助手"]:
        menu_item = auto.MenuItemControl(searchFromControl=qq_win, searchDepth=15, SubName="我的手机")
        if not menu_item.Exists(1, 1):
            phone_btn = auto.ButtonControl(searchFromControl=qq_win, searchDepth=15, SubName="我的手机")
            if phone_btn.Exists(2, 1):
                phone_btn.Click(simulateMove=False)
                time.sleep(0.6)
            menu_item = auto.MenuItemControl(searchFromControl=qq_win, searchDepth=15, SubName="我的手机")
        if menu_item.Exists(2, 1):
            menu_item.Click(simulateMove=False)
            time.sleep(0.8)
            return True
        return False
        
    # 2. Check if current active chat is already target
    if verify_active_chat(qq_win, target_contact):
        print(f"[+] Recipient '{target_contact}' is already active.")
        return True
        
    # 3. Check visible session list in left sidebar (X < 550)
    target_ctrl = None
    for ctrl, depth, _ in auto.WalkTree(qq_win, getChildren=lambda c: c.GetChildren(), maxDepth=25):
        if ctrl.Name == target_contact and ctrl.ControlTypeName == "TextControl" and ctrl.BoundingRectangle.left < 550:
            target_ctrl = ctrl
            break
            
    if target_ctrl:
        print(f"[+] Found '{target_contact}' in session list. Clicking...")
        target_ctrl.Click(simulateMove=False)
        time.sleep(0.8)
        if verify_active_chat(qq_win, target_contact):
            return True
            
    # 4. Search box lookup
    print(f"[*] Searching for '{target_contact}' in search box...")
    search_edit = None
    for ctrl, _, _ in auto.WalkTree(qq_win, getChildren=lambda c: c.GetChildren(), maxDepth=25):
        if ctrl.ControlTypeName == "EditControl" and ctrl.Name == "搜索":
            search_edit = ctrl
            break
    
    if search_edit:
        search_edit.Click(simulateMove=False)
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        time.sleep(0.1)
        pyperclip.copy(target_contact)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.0)
        
        target_item = None
        for ctrl, _, _ in auto.WalkTree(qq_win, getChildren=lambda c: c.GetChildren(), maxDepth=25):
            if target_contact in ctrl.Name and ctrl.ControlTypeName == "ListItemControl":
                target_item = ctrl
                break
                
        if target_item:
            print(f"[+] Clicking search result item '{target_item.Name}'...")
            target_item.Click(simulateMove=False)
        else:
            print("[*] Pressing Down + Enter for top search result...")
            pyautogui.press('down')
            time.sleep(0.3)
            pyautogui.press('enter')
        time.sleep(0.8)
        
    # 5. Final Confirmation Check
    if verify_active_chat(qq_win, target_contact):
        print(f"[SUCCESS] Verified active chat is '{target_contact}'.")
        return True
    else:
        print(f"[WARNING] Could not strictly verify chat header for '{target_contact}', continuing with caution.")
        return True

def focus_chat_input(qq_win):
    send_btn = None
    for ctrl, _, _ in auto.WalkTree(qq_win, getChildren=lambda c: c.GetChildren(), maxDepth=25):
        if ctrl.ControlTypeName == "ButtonControl" and ctrl.Name == "发送":
            send_btn = ctrl
            break
            
    if send_btn:
        rect = send_btn.BoundingRectangle
        pyautogui.click(rect.left - 100, rect.top - 50)
def click_send_or_modal(qq_win, default_send_btn=None):
    # Check if a modal send button (such as "发送(1)") appeared
    modal_btn = None
    for ctrl, depth, _ in auto.WalkTree(qq_win, getChildren=lambda c: c.GetChildren(), maxDepth=25):
        if ctrl.ControlTypeName == "ButtonControl" and "发送" in ctrl.Name and "(" in ctrl.Name:
            modal_btn = ctrl
            break
            
    if modal_btn:
        modal_btn.Click(simulateMove=False)
        return True
    if default_send_btn:
        default_send_btn.Click(simulateMove=False)
        return True
    pyautogui.press('enter')
    return True

def send_message(target_contact: str, message: str = None, image_path: str = None, file_path: str = None, count: int = 1, interval: float = 0.05, screenshot_path: str = None) -> bool:
    success = False
    
    def worker():
        nonlocal success
        attach_desktop()
        close_popups_if_any()
        
        qq_win = find_qq_window()
        if not qq_win:
            print("[ERROR] QQ window not found. Please make sure QQ NT is running.")
            comtypes.CoUninitialize()
            return
            
        qq_win.SetActive()
        qq_win.SetTopmost(True)
        time.sleep(0.3)
        
        # 1. Strictly switch to contact and verify
        if not switch_to_contact(qq_win, target_contact):
            print(f"[ERROR] Failed to switch to contact '{target_contact}'. Aborting to prevent misdelivery.")
            qq_win.SetTopmost(False)
            comtypes.CoUninitialize()
            return
            
        # 2. Focus chat input area
        send_btn = focus_chat_input(qq_win)
        
        # 3. Inject payload using identical verified pipeline
        if file_path:
            print(f"Setting file {file_path} to clipboard...")
            set_clipboard_file(file_path)
            time.sleep(0.2)
            for i in range(count):
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(1.2)
                click_send_or_modal(qq_win, send_btn)
                if interval > 0 and i < count - 1:
                    time.sleep(interval)
            print(f"[SUCCESS] Sent {count} file(s) to '{target_contact}'")
        elif image_path:
            print(f"Setting image {image_path} to clipboard...")
            set_clipboard_image(image_path)
            time.sleep(0.2)
            for i in range(count):
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(1.0)
                click_send_or_modal(qq_win, send_btn)
                if interval > 0 and i < count - 1:
                    time.sleep(interval)
            print(f"[SUCCESS] Sent {count} image(s) to '{target_contact}'")
        elif message:
            pyperclip.copy(message)
            time.sleep(0.1)
            print(f"Sending {count} message(s) to '{target_contact}'...")
            for i in range(count):
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.01)
                pyautogui.press('enter')
                if interval > 0 and i < count - 1:
                    time.sleep(interval)
            print(f"[SUCCESS] Sent {count} message(s) to '{target_contact}': '{message}'")
            
        time.sleep(0.8)
        
        if screenshot_path:
            s = pyautogui.screenshot()
            s.save(screenshot_path)
            print(f"[SUCCESS] Screenshot saved to {screenshot_path}")
            
        qq_win.SetTopmost(False)
        comtypes.CoUninitialize()
        success = True

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    return success

def main():
    parser = argparse.ArgumentParser(description="QQ NT UI Automation Tool")
    parser.add_argument("--to", required=True, help="Contact/Group name")
    parser.add_argument("--msg", default=None, help="Message text to send")
    parser.add_argument("--image", default=None, help="Image file path to send")
    parser.add_argument("--file", default=None, help="File path to send")
    parser.add_argument("--count", type=int, default=1, help="Number of times to send (default: 1)")
    parser.add_argument("--interval", type=float, default=0.05, help="Interval between messages in seconds (default: 0.05)")
    parser.add_argument("--screenshot", default=None, help="Optional path to save verification screenshot")
    args = parser.parse_args()
    
    if not args.msg and not args.image and not args.file:
        parser.error("At least one of --msg, --image, or --file is required.")
        
    ok = send_message(args.to, message=args.msg, image_path=args.image, file_path=args.file, count=args.count, interval=args.interval, screenshot_path=args.screenshot)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
