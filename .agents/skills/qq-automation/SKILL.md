---
name: qq-automation
description: Automate QQ NT on Windows to send messages, manage contacts, search friends, and interact with the UI using semantic UI Automation without coordinates.
---

# QQ NT UI Automation Skill

This skill provides seamless, coordinate-independent UI Automation for Tencent QQ NT on Windows.

## Quick Start (CLI Tool)

A ready-to-use Python automation script is located in `scripts/qq_tool.py`:

```bash
# Send a text message to any contact / group / "我的手机"
python .agents/skills/qq-automation/scripts/qq_tool.py --to "联系人姓名" --msg "你的消息内容" --screenshot "verification.png"

# Send an image to a contact
python .agents/skills/qq-automation/scripts/qq_tool.py --to "联系人姓名" --image "path/to/image.jpg"

# Batch send multiple messages with interval
python .agents/skills/qq-automation/scripts/qq_tool.py --to "联系人姓名" --msg "消息内容" --count 100 --interval 0.05
```

## How It Works

1. **Desktop Station Attachment**:
   QQ NT runs on the active interactive desktop (`WinSta0` / `Default`). Any background automation script attaches to the desktop station and initializes COM:
   ```python
   user32.OpenWindowStationW("WinSta0", False, 0x0000037F)
   user32.SetProcessWindowStation(hWinSta)
   hDesk = user32.OpenDesktopW("Default", 0, False, 0x000001FF)
   user32.SetThreadDesktop(hDesk)
   comtypes.CoInitialize()
   ```

2. **Semantic Control Traversal**:
   Instead of using fragile screen coordinates, the tool uses `uiautomation` to navigate QQ NT's Chromium/Electron UI tree:
   - **Recent Sessions**: `PaneControl(Name='会话列表')` -> `TextControl(Name='...')`
   - **Device Assistant**: `ButtonControl(Name='我的手机')` -> `MenuItemControl(Name='我的手机')`
   - **Search Fallback**: `EditControl(Name='搜索')` -> `ListItemControl(Name='... 来自: 我的好友')`
   - **Send Button**: `ButtonControl(Name='发送')`

## Dependencies

Ensure the following Python packages are installed:
- `uiautomation`
- `pyperclip`
- `pyautogui`
- `comtypes`
- `pywin32`
