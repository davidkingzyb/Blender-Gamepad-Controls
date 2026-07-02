bl_info = {
    "name": "Gamepad Controls",
    "author": "OhMyKing",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Gamepad",
    "description": "Control Blender with a gamepad",
    "category": "3D View",
}

import bpy
import mathutils
import threading
import time
import math
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, PointerProperty, BoolProperty
import ctypes
from ctypes import windll, Structure, c_long, byref


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]

def get_mouse_position():
    pt = POINT()
    windll.user32.GetCursorPos(byref(pt))
    return pt.x, pt.y

def get_pixel_color_win(x, y):
    hdc = ctypes.windll.user32.GetDC(0)
    color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
    ctypes.windll.user32.ReleaseDC(0, hdc)
    
    r = color & 0xFF
    g = (color >> 8) & 0xFF
    b = (color >> 16) & 0xFF
    return (r, g, b)

# 动态检测函数
def check_gamepad_available():
    try:
        from .utils import get_gamepad
        # 尝试获取手柄事件，如果没有手柄会抛出异常
        events = get_gamepad()
        return True
    except:
        return False

def focus_view_to_origin():
    # 遍历当前窗口所有区域，寻找 3D 视图
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            if space.type == 'VIEW_3D':
                # 将视图焦点移动到世界坐标原点 (0, 0, 0)
                space.region_3d.view_location = (0.0, 0.0, 0.0)
                print("视图已聚焦到原点。")
                return
    print("未找到活动的 3D 视图窗口。")

# 手柄状态类
class GamepadState:
    def __init__(self):
        self.left_stick_x = 0.0
        self.left_stick_y = 0.0
        self.right_stick_x = 0.0
        self.right_stick_y = 0.0
        self.buttons = {}
        self.button_states = {}
        self.dpad_up = 0
        self.dpad_down = 0
        self.dpad_left = 0
        self.dpad_right = 0
        self.lb=0
        self.rb=0

gamepad_state = GamepadState()

# 手柄输入监听线程
class GamepadThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = True
        self.error_message = None
        self._consecutive_errors = 0  # 添加连续错误计数器
        self._max_consecutive_errors = 10  # 最大连续错误次数

    def run(self):
        while self.running:
            try:
                from .utils import get_gamepad
                events = get_gamepad()
                # 成功获取事件，重置错误计数
                self._consecutive_errors = 0
                self.error_message = None

                for event in events:
                    if self.running:  # 检查是否仍在运行
                        self.process_event(event)

            except ImportError:
                self.error_message = "未安装 'inputs' 包。请安装后重试。"
                self._consecutive_errors += 1
                time.sleep(1)

            except Exception as e:
                self._consecutive_errors += 1
                if "No gamepad found" in str(e):
                    self.error_message = "未检测到手柄。请确保手柄已连接。"
                else:
                    self.error_message = f"手柄错误: {e}"
                time.sleep(0.5)  # 减少等待时间，提高响应速度

            # 如果连续错误次数过多，可能需要关闭控制
            if self._consecutive_errors >= self._max_consecutive_errors:
                self.error_message = "多次无法检测到手柄，已自动关闭控制。"
                break

    def process_event(self, event):
        """处理手柄事件"""
        # print(event.ev_type, event.code, event.state)
        if event.code == 'ABS_X':
            gamepad_state.left_stick_x = event.state / 32768.0
        elif event.code == 'ABS_Y':
            gamepad_state.left_stick_y = event.state / 32768.0
        elif event.code == 'ABS_RX':
            gamepad_state.right_stick_x = event.state / 32768.0
        elif event.code == 'ABS_RY':
            gamepad_state.right_stick_y = event.state / 32768.0
        elif event.code == 'ABS_HAT0Y':
            if event.state == -1:
                gamepad_state.dpad_up = 1
                gamepad_state.dpad_down = 0
            elif event.state == 1:
                gamepad_state.dpad_down = 1
                gamepad_state.dpad_up = 0
            else:
                gamepad_state.dpad_up = 0
                gamepad_state.dpad_down = 0
        elif event.code == 'ABS_HAT0X':
            if event.state == -1:
                gamepad_state.dpad_left = 1
                gamepad_state.dpad_right = 0
            elif event.state == 1:
                gamepad_state.dpad_right = 1
                gamepad_state.dpad_left = 0
            else:
                gamepad_state.dpad_left = 0
                gamepad_state.dpad_right = 0
        elif event.code=='ABS_RZ':
            if(event.state==255):
                gamepad_state.rb=1
            else:
                gamepad_state.rb=0
        elif event.code=='ABS_Z':
            if(event.state==255):
                gamepad_state.lb=1
            else:
                gamepad_state.lb=0
        elif event.code.startswith('BTN_'):# WEST EAST NORTH SOUTH START SELECT TL TR THUMBL
            # print('btn event code',event.code)
            gamepad_state.buttons[event.code] = event.state
            gamepad_state.button_states[event.code] = event.state

# 设置属性
class GamepadSettings(PropertyGroup):
    pan_speed: FloatProperty(
        name="平移速度",
        description="视角平移的速度",
        default=0.1,
        min=0.01,
        max=1.0
    )
    rotation_speed: FloatProperty(
        name="旋转速度",
        description="视角旋转的速度",
        default=0.05,
        min=0.01,
        max=1.0
    )
    zoom_speed: FloatProperty(
        name="缩放速度",
        description="视角缩放的速度",
        default=0.1,
        min=0.1,
        max=2.0
    )
    invert_x_axis: BoolProperty(
        name="反转X轴",
        description="反转X轴的控制方向",
        default=False
    )
    invert_y_axis: BoolProperty(
        name="反转Y轴",
        description="反转Y轴的控制方向",
        default=False
    )
    invert_z_axis: BoolProperty(
        name="反转Z轴",
        description="反转Z轴的控制方向",
        default=False
    )

    def update_enable_gamepad_control(self, context):
        if self.enable_gamepad_control:
            bpy.ops.gamepad.control('INVOKE_DEFAULT')
        else:
            # 操作器会检测到这个变化并自行取消
            pass

    enable_gamepad_control: BoolProperty(
        name="启用手柄控制",
        description="启用或禁用手柄控制",
        default=False,
        update=update_enable_gamepad_control
    )


# 主操作器
class GAMEPAD_OT_control(Operator):
    bl_idname = "gamepad.control"
    bl_label = "手柄控制"
    bl_description = "启动手柄控制"

    _timer = None
    _thread = None
    _last_error_time = 0  # 错误消息时间戳
    _last_error_message = None  # 上一次错误消息

    def modal(self, context, event):
        print('[gamepad] modal')
        settings = context.scene.gamepad_settings

        # 检查线程状态
        if self._thread:
            if not self._thread.is_alive():
                # 线程已结束，说明发生了严重错误
                settings.enable_gamepad_control = False
                self.report({'WARNING'}, "手柄控制已自动关闭")
                self.cancel(context)
                return {'CANCELLED'}

            # 检查错误信息
            if self._thread.error_message:
                current_time = time.time()
                # 如果是新的错误消息或者距离上次显示超过3秒
                if (self._thread.error_message != self._last_error_message or
                        current_time - self._last_error_time > 3):
                    self.report({'WARNING'}, self._thread.error_message)
                    self._last_error_time = current_time
                    self._last_error_message = self._thread.error_message

                # 如果提示自动关闭控制，则关闭
                if "已自动关闭控制" in self._thread.error_message:
                    settings.enable_gamepad_control = False
                    self.cancel(context)
                    return {'CANCELLED'}

                # 如果提示未安装包，则关闭
                if "未安装 'inputs' 包" in self._thread.error_message:
                    settings.enable_gamepad_control = False
                    self.cancel(context)
                    return {'CANCELLED'}

        if not settings.enable_gamepad_control:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            try:
                self.handle_button_brush(context)
                self.handle_button_actions(context)
                self.handle_dpad_view_switch(context)
                self.handle_view3d(context)
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}  # 改为 RUNNING_MODAL 以确保持续运行
            except Exception as err:
                print('[gamepad] OT timer err',err)
                settings.enable_gamepad_control = False
                self.cancel(context)
                return {'CANCELLED'}

        elif event.type == 'ESC':
            self.cancel(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}
    
    def handle_view3d(self,context):
        view3d = context.space_data.region_3d
        settings = context.scene.gamepad_settings
        #视角平移
        if abs(gamepad_state.right_stick_x) > 0.1 or abs(gamepad_state.right_stick_y) > 0.1:
            pan_speed = settings.pan_speed
            dx = gamepad_state.right_stick_x * pan_speed
            dy = -gamepad_state.right_stick_y * pan_speed

            if settings.invert_x_axis:
                dx = -dx
            if not settings.invert_y_axis:
                dy = -dy

            view3d.view_location += view3d.view_rotation @ mathutils.Vector((-dy, dx, 0.0))
        #视角旋转
        if abs(gamepad_state.left_stick_x) > 0.1 or abs(gamepad_state.left_stick_y) > 0.1:
            rot_speed = settings.rotation_speed
            euler = view3d.view_rotation.to_euler()

            delta_euler_z = gamepad_state.left_stick_x * rot_speed
            delta_euler_x = gamepad_state.left_stick_y * rot_speed

            if settings.invert_z_axis:
                delta_euler_z = -delta_euler_z
            if settings.invert_x_axis:
                delta_euler_x = -delta_euler_x
            euler.z += delta_euler_x
            euler.x += delta_euler_z
            view3d.view_rotation = euler.to_quaternion()
        #缩放
        zoom_speed = settings.zoom_speed
        if gamepad_state.buttons.get('BTN_TL'):
            view3d.view_distance += zoom_speed
        if gamepad_state.lb:
            view3d.view_distance -= zoom_speed
    
    # 笔刷
    def handle_button_brush(self, context):
        if context.mode == 'SCULPT':
            brush=context.tool_settings.sculpt.brush
            # if gamepad_state.button_states.get('BTN_TR')==1:
                # gamepad_state.button_states['BTN_TR']=0
            if gamepad_state.rb:
                if brush.direction=='ADD':
                    brush.direction='SUBTRACT'
                else:
                    brush.direction='ADD'
                time.sleep(0.2)
                return
        elif context.mode=='PAINT_TEXTURE':
            brush=context.tool_settings.image_paint.brush
            # if gamepad_state.button_states.get('BTN_TR')==1:
                # gamepad_state.button_states['BTN_TR']=0
            if gamepad_state.rb:
                if brush.blend=="MIX":
                    brush.blend="ERASE_ALPHA"
                else:
                    brush.blend="MIX"
                time.sleep(0.2)
                return
        elif context.mode=='PAINT_WEIGHT':
            brush=context.tool_settings.weight_paint.brush
        elif context.mode=='PAINT_VERTEX':
            brush=context.tool_settings.vertex_paint.brush
        
        if gamepad_state.button_states.get('BTN_TR')==1:
            x,y=get_mouse_position()
            color=get_pixel_color_win(x,y)
            context.tool_settings.unified_paint_settings.color=(color[0]/255,color[1]/255,color[2]/255)
            gamepad_state.button_states['BTN_TR']=0
            
        unified_brush=context.tool_settings.unified_paint_settings
        if gamepad_state.button_states.get('BTN_WEST') == 1:# Y
            # gamepad_state.button_states['BTN_WEST'] = 0
            # if brush:
            #     brush.size = max(1,int(brush.size*0.99))
            # else:
            unified_brush.size = max(1,int(unified_brush.size*0.99))
        if gamepad_state.button_states.get('BTN_EAST') == 1:# A
            # gamepad_state.button_states['BTN_EAST'] = 0
            if brush:
                brush.strength=min(1.0,brush.strength+0.01)
            else:
                unified_brush.strength=min(1.0,unified_brush.strength+0.01)
        if gamepad_state.button_states.get('BTN_NORTH') == 1:# X
            # gamepad_state.button_states['BTN_NORTH'] = 0
            # if brush:
            #     brush.size=min(500,math.ceil(brush.size * 1.01))
            # else:
            unified_brush.size=min(500,math.ceil(unified_brush.size * 1.01))
        if gamepad_state.button_states.get('BTN_SOUTH') == 1:# B
            # gamepad_state.button_states['BTN_SOUTH'] = 
            if brush:
                brush.strength=max(0.0,brush.strength-0.01)
            else:
                unified_brush.strength=max(0.0,unified_brush.strength-0.01)

    # redo undo
    def handle_button_actions(self, context):
        if gamepad_state.buttons.get('BTN_SELECT')==1:
            try:
                bpy.ops.ed.redo()
            except Exception as err:
                self.report({'INFO'}, "redo fail")
            time.sleep(0.2)
            gamepad_state.button_states['BTN_SELECT']=0
        elif gamepad_state.buttons.get('BTN_START')==1:
            try:
                bpy.ops.ed.undo()
            except Exception as err:
                self.report({'INFO'}, "undo fail")
            time.sleep(0.2)
            gamepad_state.button_states['BTN_START']=0

    # 视角回正
    def handle_dpad_view_switch(self, context):
        if gamepad_state.button_states.get('BTN_THUMBL')==1:
            # bpy.ops.view3d.view_selected()
            # focus_view_to_origin()
            bpy.ops.view3d.view_axis(type='FRONT')
            gamepad_state.button_states['BTN_THUMBL']=0
            time.sleep(0.2)

        if gamepad_state.dpad_up == 1:
            bpy.ops.view3d.view_axis(type='RIGHT')
            gamepad_state.dpad_up = 0

        if gamepad_state.dpad_down == 1:
            bpy.ops.view3d.view_axis(type='LEFT')
            gamepad_state.dpad_down = 0

        if gamepad_state.dpad_left == 1:
            bpy.ops.view3d.view_axis(type='TOP')
            gamepad_state.dpad_left = 0

        if gamepad_state.dpad_right == 1:
            bpy.ops.view3d.view_axis(type='FRONT')
            gamepad_state.dpad_right = 0

    def execute(self, context):
        print('[gamepad] OT execute')
        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "激活区域必须是3D视图")
            return {'CANCELLED'}
        # 重置手柄状态
        global gamepad_state
        gamepad_state = GamepadState()
        # 开始新线程
        self._thread = GamepadThread()
        self._thread.start()
        # 设置计时器
        wm = context.window_manager
        self._timer = wm.event_timer_add(1 / 60, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        print('[gamepad] OT cancel')
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
        if self._thread:
            self._thread.running = False
            self._thread.join(timeout=1.0)  # 添加超时
        # 重置手柄状态
        global gamepad_state
        gamepad_state = GamepadState()


# UI 面板
class GAMEPAD_PT_panel(Panel):
    bl_label = "游戏手柄控制"
    bl_idname = "GAMEPAD_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Gamepad'

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.gamepad_settings

        box = layout.box()
        row = box.row()
        row.prop(settings, "enable_gamepad_control")

        # 如果 inputs 包已安装，显示其他设置
        if settings.enable_gamepad_control:
            box = layout.box()
            box.label(text="视角控制设置:", icon='VIEW3D')
            box.prop(settings, "pan_speed")
            box.prop(settings, "rotation_speed")
            box.prop(settings, "zoom_speed")

            # 添加控制说明
            help_box = layout.box()
            help_box.label(text="控制说明:", icon='HELP')
            col = help_box.column(align=True)
            col.label(text="F5: 打开")
            col.label(text="右摇杆: 平移 左摇杆: 旋转")
            col.label(text="L/L2: 缩小/放大 R:取色 R2:橡皮")
            col.label(text="方向键: 切换视图 -:undo +:redo")
            col.label(text="brush XY:size AB:strength")

class GAMEPAD_Start(bpy.types.Operator):
    bl_idname = "gamepad.start"
    bl_label = "GamePad Start"
    bl_description = "开启Gamepad控制"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'INFO'}, "已开启Gamepad控制")
        settings = context.scene.gamepad_settings
        settings.enable_gamepad_control=True
        return {'FINISHED'}

