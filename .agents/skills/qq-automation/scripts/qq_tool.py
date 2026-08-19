import argparse
import ctypes
import sys
import threading
import time
import comtypes
import uiautomation as auto
import pyperclip
import pyautogui

pyautogui.FAILSAFE = False
user32 = ctypes.windll.user32

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

def send_message(target_contact: str, message: str, screenshot_path: str = None) -> bool:
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
        
        # Special case 1: "我的手机"
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
        else:
            # Check visible session list first
            session_list = auto.PaneControl(searchFromControl=qq_win, searchDepth=10, Name="会话列表")
            found_in_list = False
            if session_list.Exists(2, 1):
                for ctrl, _, _ in auto.WalkTree(session_list, getChildren=lambda c: c.GetChildren(), maxDepth=10):
                    if target_contact in ctrl.Name and ctrl.ControlTypeName in ["TextControl", "ListItemControl", "PaneControl"]:
                        ctrl.Click(simulateMove=False)
                        found_in_list = True
                        time.sleep(0.8)
                        break
                        
            if not found_in_list:
                # Search box lookup
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
                    
                    # Match search item in results
                    target_item = None
                    for ctrl, _, _ in auto.WalkTree(qq_win, getChildren=lambda c: c.GetChildren(), maxDepth=25):
                        if target_contact in ctrl.Name and ctrl.ControlTypeName == "ListItemControl":
                            target_item = ctrl
                            break
                            
                    if target_item:
                        target_item.Click(simulateMove=False)
                    else:
                        pyautogui.press('down')
                        time.sleep(0.3)
                        pyautogui.press('enter')
                    time.sleep(0.8)
                    
        # Paste message
        pyperclip.copy(message)
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.4)
        
        # Click Send button
        send_btn = None
        for ctrl, _, _ in auto.WalkTree(qq_win, getChildren=lambda c: c.GetChildren(), maxDepth=25):
            if ctrl.ControlTypeName == "ButtonControl" and ctrl.Name == "发送":
                send_btn = ctrl
                break
                
        if send_btn:
            send_btn.Click(simulateMove=False)
        else:
            pyautogui.press('enter')
        time.sleep(0.8)
        
        if screenshot_path:
            s = pyautogui.screenshot()
            s.save(screenshot_path)
            print(f"[SUCCESS] Screenshot saved to {screenshot_path}")
            
        qq_win.SetTopmost(False)
        comtypes.CoUninitialize()
        success = True
        print(f"[SUCCESS] Message sent to '{target_contact}': '{message}'")

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    return success

def main():
    parser = argparse.ArgumentParser(description="QQ NT UI Automation Tool")
    parser.add_argument("--to", required=True, help="Contact/Group name")
    parser.add_argument("--msg", required=True, help="Message text to send")
    parser.add_argument("--screenshot", default=None, help="Optional path to save verification screenshot")
    args = parser.parse_args()
    
    ok = send_message(args.to, args.msg, args.screenshot)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
