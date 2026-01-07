# Agamotto Gesture Control System

Agamotto Gesture Control System 是一个基于摄像头与手势识别的鼠标控制系统：使用 MediaPipe Hands 追踪手部关键点，将手部位置映射为屏幕光标移动，并用“捏合”等手势触发左键点击/拖拽与右键点击。项目内置一个带交互引导的解锁动画，支持启动时选择摄像头，并提供简单的标定流程以适配不同的摄像头摆放位置与使用姿势。

## 主要特性

- 摄像头输入 + MediaPipe Hands 双手追踪（最多 2 只手）
- 需要“解锁”后才会接管鼠标，减少误触风险
- 自定义多点标定 ROI（手在画面中的活动区域），提高映射稳定性
- **超级防抖 (Super Stabilization)**：
  - 多点质心追踪：融合手腕与四指关节坐标，消除单点抖动
  - 强力 One Euro Filter 平滑：极低截止频率 (0.01Hz) 过滤微小抖动
  - 静止死区 (Static Deadzone)：手部微动时锁定光标，彻底消除“帕金森”现象
- 左键：拇指-食指捏合（点按 / 长按拖拽）
- 右键：拇指-中指捏合（右键点击）
- **中键点击**：剪刀手（食指中指伸直，无名指小指大拇指弯曲/握拳）
- **滚轮滚动**：四指并拢伸直（大拇指不作硬性要求），上下挥动触发滚动
- HUD 叠加显示：FPS、模式、ROI、调试距离阈值等
- Windows 声音提示（winsound.Beep）
- 提供一键启动脚本与 PyInstaller 打包脚本

## 运行环境

- 操作系统：Windows（使用了 `winsound`；`pyautogui` 也更常用于桌面环境）
- Python：建议 3.8–3.10（仓库脚本 `start.bat` 会在 3.7–3.10 中择优运行）
- 摄像头：任意 UVC 摄像头（内置会扫描 0–3 号摄像头）

## 依赖安装

依赖定义在 [hand_control/requirements.txt](hand_control/requirements.txt)：

```bash
py -3.10 -m pip install -r requirements.txt
```

如果你不使用 `py` 启动器，也可以：

```bash
python -m pip install -r requirements.txt
```

## 快速开始

### 方式一：直接运行

```bash
cd "Agamotto Gesture Control System\hand_control"
python main.py
```

### 方式二：使用启动脚本（Windows）

```bash
cd "Agamotto Gesture Control System\hand_control"
start.bat
```

启动后会进入“摄像头选择”界面：

- `TAB`：切换摄像头
- `ENTER`：确认选择
- `ESC`：取消并退出

进入主界面后：

- `ESC`：退出程序

## 手势与交互说明

- 项目整体的状态机在 [hand_control/src/controller.py](hand_control/src/controller.py) 的 `MouseController.update_system_state()` 与 `MouseController.process()` 中实现，分为“未激活（Standby）→ 标定（Calibration）→ 运行（Running）”。

### 1) 解锁/激活（接管鼠标）

在未激活状态下，系统要求同时检测到两只手，且按以下顺序完成解锁：

1. 阶段 1：任意一只手执行“无名指与拇指捏合”（Ring Pinch）
2. 阶段 2：在阶段 1 有效时间内（约 3 秒），将双手做“交叉”姿态并持续保持
3. 持续保持约 1.5 秒后，系统进入激活状态（HUD 会显示 OPENING 进度，最终显示 EYE OPENED）

实现细节参考：

- Ring Pinch 判断：`MouseController.is_ring_pinch()`（见 [controller.py](hand_control/src/controller.py)）
- 交叉判断：在 `update_system_state()` 中用双手腕部关键点（landmark 0）的 x 坐标关系近似判断（见 [controller.py](hand_control/src/controller.py)）

### 2) 关闭/停用（释放鼠标）

在激活状态下，同时张开双手（Open Palm），持续保持约 1.5 秒会停用系统：

- Open Palm 判断：`MouseController.is_palm_open()`（见 [controller.py](hand_control/src/controller.py)）
- 停用逻辑：`update_system_state()`（见 [controller.py](hand_control/src/controller.py)）

### 3) 标定流程（首次激活后）

首次激活后默认未标定，会进入“自定义位置四点标定”，用于确定你在画面中“有效操作区域 ROI”：

1. 用户用手在画面中移动到你希望的边界位置
2. 用“小拇指 + 拇指捏合”并保持一小段时间，确认当前点（共 4 个点）
3. 每个点确认成功后会强制等待约 2 秒，并提示 “CALIBRATION SUCCESS | PROCEED TO POINT X”，避免连续在同一位置重复确认
4. 若标定点不满意，保持“单手握拳”可删除上一个标定点并重新标定
5. 当 4 个点都确认完成后自动结束标定并进入运行模式（ROI 取 4 点的 min/max x/y）

相关实现：

- 标定处理：`MouseController.process_calibration()`（见 [controller.py](hand_control/src/controller.py)）
- ROI 更新：`MouseController.update_roi_from_calibration()`（见 [controller.py](hand_control/src/controller.py)）

### 4) 运行模式：光标移动、左键、拖拽、右键

当已标定后进入运行模式：

#### 光标移动

- 取手部关键点 **（手腕与四指关节的质心）** 作为“控制点”，比单一关节更稳定
- 将其在 ROI 中的归一化坐标映射到屏幕坐标
- 使用 **高强度 One Euro Filter** 对 x/y 进行平滑
- **静止死区**：当移动距离小于阈值（默认 4px）时，光标保持静止

对应代码：

- 映射与平滑：`MouseController.map_coordinates()`（见 [controller.py](hand_control/src/controller.py)）
- 光标移动：`MouseController.move_cursor()`（见 [controller.py](hand_control/src/controller.py)）

#### 左键（点击 / 拖拽）

手势：拇指-食指捏合（`left_pinch`）

- 当开始捏合时锁定一个“起点位置”（用于区分点按与拖拽）
- 若捏合后移动距离超过死区半径，则触发 `mouseDown` 并进入拖拽
- 若捏合持续时间较短（默认 ≤ 0.6s）并释放，则在锁定点触发一次左键点击

对应参数与代码：

- 捏合阈值（按下/释放）：`pinch_trigger`、`left_pinch_release`（见 [controller.py](hand_control/src/controller.py)）
- 点按最大时长：`tap_max_duration`（默认 0.6s，见 [controller.py](hand_control/src/controller.py)）
- 拖拽死区：`deadzone_radius`（默认 30px，见 [controller.py](hand_control/src/controller.py)）
- 静止死区：`static_movement_deadzone`（默认 4px，见 [controller.py](hand_control/src/controller.py)）
- 主要逻辑：`MouseController.process_running()`（见 [controller.py](hand_control/src/controller.py)）

#### 右键

手势：拇指-中指捏合（`right_pinch`）

- 进入 `right_pinch` 状态的瞬间触发一次右键点击
- 内置最小触发间隔，避免连点（`right_click_min_interval`）

#### 中键点击

手势：剪刀手 + 拇指握拳（`middle_click`）

- 食指、中指伸直
- 无名指、小指弯曲
- 大拇指弯曲（握在手心）
- 保持该手势触发一次中键点击（有冷却间隔）

#### 滚轮滚动

手势：四指并拢伸直（食指/中指/无名指/小指，`scroll`；大拇指不作硬性要求）

- 保持四指伸直且紧密并拢（大拇指不作硬性要求）
- 手势保持期间光标位置锁定（不移动）
- **向上挥动**手掌 -> 向下滚动
- **向下挥动**手掌 -> 向上滚动

#### 双击（左键）

手势：除大拇指外的四指弯曲（`fist`）

- 无论大拇指是否伸直，只要食指、中指、无名指、小指同时弯曲即可触发
- 仅在运行模式下生效（标定模式下为“删除点”）
- 握拳保持一小段时间触发双击
- 同样内置冷却间隔，避免连续触发

相关代码：

- 右键捏合阈值：`right_pinch_trigger`、`right_pinch_release`（见 [controller.py](hand_control/src/controller.py)）
- 触发逻辑：`process_running()`（见 [controller.py](hand_control/src/controller.py)）

## HUD 与可视化

HUD（Heads-Up Display）是一个实时显示系统状态与操作提示的可视化界面。

### 主程序入口在 [hand_control/main.py](hand_control/main.py)：

- 启动摄像头选择器（TAB/ENTER/ESC）
- 持续读取帧 → MediaPipe 识别关键点 → 鼠标控制器计算状态/动作
- 绘制手部骨架与 HUD，并在窗口中显示

HUD 主要包括：

- Standby：解锁引导与“阿戈摩托之眼”动画（根据解锁阶段变化）
- Calibration：目标点、进度圈、提示文本
- Running：FPS、当前模式（ACTIVE/DRAGGING）、ROI 边框、调试信息

## 项目结构

```
Agamotto Gesture Control System/
  README.md
  hand_control/
    main.py             # 程序入口：摄像头选择、循环、HUD 绘制
    start.bat           # Windows 一键启动（优先 3.10→3.7）
    build.bat           # PyInstaller 打包命令
    requirements.txt    # Python 依赖
    icon.png            # 打包图标
    check_proxy.py      # 打印系统代理（调试用）
    hand_tracking.py    # 独立的手部追踪示例/调试脚本
    src/
      vision.py         # MediaPipe Hands 封装：输出左右手关键点
      controller.py     # 手势→鼠标控制：状态机、标定、映射与点击拖拽
      filter.py         # One Euro Filter 实现：平滑
      sound.py          # 声音提示：激活/停用/标定
```

## 打包为可执行文件（PyInstaller）

仓库提供了 [hand_control/build.bat](hand_control/build.bat)：

```bash
cd "Agamotto Gesture Control System\hand_control"
pyinstaller -F -w -i icon.png --collect-all mediapipe --collect-all cv2 --hidden-import=numpy --hidden-import=src.vision --hidden-import=src.controller --add-data="src;src" main.py
```

说明：

- `-F`：打包为单文件
- `-w`：不弹出控制台窗口
- `--collect-all mediapipe/cv2`：收集运行所需资源
- `--add-data="src;src"`：将 `src` 目录一并打包

## 常见问题与排错

### 1) 识别不到手或识别不稳定

- 确保光线充足，手与背景对比明显
- 尽量让手完整出现在画面中，避免过近导致关键点丢失
- 若帧率偏低，尝试降低摄像头分辨率（可在 OpenCV 打开摄像头后设置）

### 2) 鼠标移动太快/太慢、边缘不够到位

可在 [hand_control/src/controller.py](hand_control/src/controller.py) 中调整：

- `roi`：标定后的有效区域，标定时尽量覆盖你习惯的活动范围
- `overdrive_factor`：放大 ROI 内的映射幅度（默认 1.3）
- One Euro Filter 参数：`min_cutoff`、`beta`（影响抖动与延迟权衡）

### 3) 捏合太敏感/不敏感

- 可调整捏合阈值（都在 [controller.py](hand_control/src/controller.py)）：

- 左键：`pinch_trigger`、`left_pinch_release`
- 右键：`right_pinch_trigger`、`right_pinch_release`

### 4) 程序接管鼠标后不好“救场”

程序内置退出键：

- 主窗口按 `ESC` 退出

另外需要注意：项目把 `pyautogui.FAILSAFE` 设置为了 `False`（默认的“移动到屏幕角落自动停止”机制被关闭）。如果你希望保留 PyAutoGUI 的 failsafe，可自行修改 [controller.py](hand_control/src/controller.py) 顶部的设置。

## 致谢

- Hyan
- MediaPipe Hands
- OpenCV
- PyAutoGUI


