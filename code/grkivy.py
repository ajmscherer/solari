# solari - a simple dashboard app with a Solari board style interface
# Copyright (C) 2024-2026 Alex Scherer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# 

import os
os.environ.setdefault('KIVY_NO_ARGS', '1')

import grabst
import kivy
import kivy.app
import kivy.graphics
import kivy.graphics.texture
import kivy.clock

import datetime
import threading

class KiviGraphicInterface(grabst.GraphicInterface):

    def __init__(self):
        super().__init__()
        self.kivi_app= kivy.app.App()
        self.overscan = 0
        self.display_size = None

    def start(self, drawFunction, sizeRequirement, framePerSecond, fullscreen=False):
        
        def update(timeInterval):

            # get a timeStamp for the drawing request
            timeStamp = datetime.datetime.now()

            # retrieve the Kivy canvas
            root = self.kivi_app.root
            if root:
                kivyCanvas = root.canvas 

                if kivyCanvas:
                    # clear the Kivy object canvas
                    kivyCanvas.clear()

                    with kivyCanvas:

                        kivy.graphics.PushMatrix()

                        if sizeRequirement:
                            raw = self.overscan
                            if isinstance(raw, (tuple, list)) and len(raw) == 4:
                                left, bottom, right, top = [max(0, int(v)) for v in raw]
                            else:
                                inset = max(0, int(raw or 0))
                                left = bottom = right = top = inset
                            width, height = root.size
                            width = max(1.0, width - left - right)
                            height = max(1.0, height - top - bottom)
                            w,h = sizeRequirement
                            f1 = width / w
                            f2 = height / h
                            f = min(f1,f2)
                            pad_x = (width - w * f) / 2.0
                            pad_y = (height - h * f) / 2.0
                            kivy.graphics.Translate(left + pad_x, bottom + pad_y, 0)

                            kivy.graphics.Scale(f, f, 1.0)

                        # build a canvas on the fly based on kivy
                        canvas = CanvasWrapperKivy(kivyCanvas=kivyCanvas)
                        
                        # call the drawing function of the graphic app
                        drawFunction(canvas, timeStamp)
                  
                        kivy.graphics.PopMatrix()

        # schedule the update function to be called at the specified frame rate
        kivy.clock.Clock.schedule_interval(update, 1.0 / framePerSecond)
        
        from kivy.core.window import Window
        window = Window
        if fullscreen:
            if self.display_size:
                window.size = self.display_size
            window.borderless = True
            window.fullscreen = True
        elif sizeRequirement:
            window.size = sizeRequirement
        logger_size = getattr(self, '_logged_size', False)
        if not logger_size:
            self._logged_size = True
            print('Kivy window size', tuple(window.size), 'root will follow')

        # bind keyboard events
        Window.bind(on_key_down=self._on_keyboard)

        threading.current_thread().name = "KivyMain"
        self.kivi_app.run()

    def toggleFullScreen(self):
        from kivy.core.window import Window
        Window.fullscreen = not Window.fullscreen

    def _on_keyboard(self, window, key, scancode, codepoint, modifier):
        self.onKeyEvent.call(key, scancode, codepoint, modifier)

    def setTitle(self, title):
        self.kivi_app.title = title

    
class CanvasWrapperKivy(grabst.Canvas):

    _texture_cache = {}

    def __init__(self, kivyCanvas):
        super().__init__()
        self.kiwyCanvas = kivyCanvas
        self.currentColor = grabst.Palette.WHITE

    def _texture_for(self, image):
        cache = CanvasWrapperKivy._texture_cache
        key = id(image)
        texture = cache.get(key)
        if texture is None:
            texture = kivy.graphics.texture.Texture.create(size=image.size)
            texture.mag_filter = 'nearest'
            texture.min_filter = 'nearest'
            texture.blit_buffer(image.tobytes(), colorfmt='rgba')
            cache[key] = texture
        return texture

    def _drawImage(self, image, x0, y0, rotation, verStretch, horStretch):

        texture = self._texture_for(image)

        # Draw the image onto the canvas
        canvas = self.kiwyCanvas
        with canvas:

            # get image size
            width,height = image.size

            # create texture size based on image size and stretch ratios
            rectSize = (width * horStretch , height*verStretch)

            # create rectangle
            self.rect = kivy.graphics.Rectangle(texture=texture, pos=(x0,y0), size=rectSize, allow_stretch=True, keep_ratio=False)

    
    def _drawLine(self, x0, y0, x1, y1, width, color, opacity):

        canvas = self.kiwyCanvas

        previous_color = self.currentColor

        self.setColor(color, opacity)

        with canvas:
            kivy.graphics.Line(points=[x0, y0, x1, y1], width=width)    
        
        self.setColor(previous_color, 1.0)
    
    def _getSize(self):
        from kivy.core.window import Window
        return Window.width, Window.height
        
    # helper function

    def setColor(self, color, opacity):
        '''Convert from Color to RGBA kivy color'''
        with self.kiwyCanvas:
            r, g, b = [ int(v.hex(),16) / 255.0 for v in color.getRGB()]
            kivy.graphics.Color(r, g, b, opacity)  # Set the color to (RGBA)
            
