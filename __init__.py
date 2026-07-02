"""Inputs - user input for humans.

Inputs aims to provide easy to use, cross-platform, user input device
support for Python. I.e. keyboards, mice, gamepads, etc.

Currently supported platforms are the Raspberry Pi, Linux, Windows and
Mac OS X.

"""

# Copyright (c) 2016, 2018: Zeth
# All rights reserved.
#
# BSD Licence
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from .devices.gamepad.gamepad import GamePad
from .devices.base import OtherDevice
from .devices.mouse.mouse import Mouse, MightyMouse
from .devices.keyboard.keyboard import Keyboard
from .devices.led.led import LED, GamepadLED, SystemLED
from .manager import DeviceManager
from .utils import devices, get_gamepad, get_key, get_mouse

__version__ = "0.6"

__all__ = [
    "GamePad",
    "Mouse",
    "MightyMouse",
    "Keyboard",
    "LED",
    "GamepadLED",
    "SystemLED",
    "OtherDevice",
    "DeviceManager",
    "devices",
    "get_gamepad",
    "get_key",
    "get_mouse",
]

# blender gamepad controller

bl_info = {
    "name": "Gamepad Controls",
    "author": "DKZ",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Gamepad",
    "description": "Control Blender with a gamepad",
    "category": "3D View",
}

import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, PointerProperty, BoolProperty
from .BlenderGamepad import GamepadSettings, GAMEPAD_OT_control, GAMEPAD_PT_panel, GAMEPAD_Start


classes = (
    GamepadSettings,
    GAMEPAD_OT_control,
    GAMEPAD_PT_panel,
    GAMEPAD_Start,
)

addon_keymaps = []
def safe_register():
    """安全注册所有类"""
    try:
        # 注册属性组
        if not hasattr(bpy.types.Scene, "gamepad_settings"):
            bpy.utils.register_class(GamepadSettings)
            bpy.types.Scene.gamepad_settings = PointerProperty(type=GamepadSettings)

        # 注册操作器和面板
        bpy.utils.register_class(GAMEPAD_OT_control)
        bpy.utils.register_class(GAMEPAD_PT_panel)
        bpy.utils.register_class(GAMEPAD_Start)

        # 获取窗口管理器
        wm = bpy.context.window_manager
        if wm.keyconfigs.addon:
            # name: 映射所属的区域名称 (如 '3D View', 'Mesh')
            # space_type: 空间类型 (如 'VIEW_3D', 'IMAGE_EDITOR')
            km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
            
            # value: 触发方式 ('PRESS', 'RELEASE', 'CLICK', 'DOUBLE_CLICK', 'ANY')
            kmi = km.keymap_items.new(
                idname=GAMEPAD_Start.bl_idname, 
                type='F5', 
                value='PRESS', 
                ctrl=False, 
                shift=False,
                alt=False
            )
            addon_keymaps.append((km, kmi))
        return True
    except Exception as e:
        print(f"游戏手柄插件注册失败: {str(e)}")
        return False


def safe_unregister():
    """安全注销所有类"""
    try:
        # 注销操作器和面板
        bpy.utils.unregister_class(GAMEPAD_PT_panel)
        bpy.utils.unregister_class(GAMEPAD_OT_control)
        bpy.utils.unregister_class(GAMEPAD_Start)

        # 注销属性组
        if hasattr(bpy.types.Scene, "gamepad_settings"):
            bpy.utils.unregister_class(GamepadSettings)
            del bpy.types.Scene.gamepad_settings
        
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
        addon_keymaps.clear()

    except Exception as e:
        print(f"游戏手柄插件注销失败: {str(e)}")


def register():
    """插件注册入口点"""
    if not safe_register():
        # 如果注册失败，确保完全清理
        safe_unregister()
        return {'CANCELLED'}
    return {'FINISHED'}


def unregister():
    """插件注销入口点"""
    safe_unregister()


if __name__ == "__main__":
    register()

