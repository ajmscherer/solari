import grabst

import kivy
import kivy.app
import kivy.graphics
import kivy.graphics.texture
import kivy.clock
import kivy.core.window

import datetime

class KiviGraphicInterface(grabst.GraphicInterface):

    def __init__(self):
        self.kivi_app= kivy.app.App()

    def start(self, drawFunction, sizeRequirement, framePerSecond):
        
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
                            width, height = root.size
                            w,h = sizeRequirement
                            f1 = width / w
                            f2 = height / h
                            f = min(f1,f2)
                            if f1 > f2:
                                # add horizontal padding
                                padding = (width - w*f) / 2
                                kivy.graphics.Translate(padding, 0, 0)
                            else:
                                # add vertical padding
                                padding = (height - h*f) / 2
                                kivy.graphics.Translate(0, padding, 0)                       

                            kivy.graphics.Scale(f, f, 1.0)

                        # build a canvas on the fly based on kivy
                        canvas = CanvasWrapperKivy(kivyCanvas=kivyCanvas)
                        
                        # call the drawing function of the graphic app
                        drawFunction(canvas, timeStamp)
                  
                        kivy.graphics.PopMatrix()

        kivy.clock.Clock.schedule_interval(update, 1.0 / framePerSecond)
        
        # set window size based on size requirement
        window = kivy.core.window.Window
        if sizeRequirement:
            window.size = sizeRequirement 

        # bind keyboard events
        kivy.core.window.Window.bind(on_key_down=self.on_keyboard)

        self.kivi_app.run()
    
    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        # press 'f' to toggle fullscreen
        if codepoint == 'f':
            window.fullscreen = not window.fullscreen
            return True
        return False

    def setTitle(self, title):
        self.kivi_app.title = title

    
class CanvasWrapperKivy(grabst.Canvas):

    def __init__(self, kivyCanvas):
        super().__init__()
        self.kiwyCanvas = kivyCanvas
        self.currentColor = grabst.Palette.WHITE

    def _drawImage(self, image, x0, y0, rotation, verStretch, horStretch):

        # create texture
        texture = kivy.graphics.texture.Texture.create(size=image.size)
        texture.mag_filter = 'nearest'  # or 'linear'
        texture.min_filter = 'nearest'  # or 'linear

        # Convert the PIL Image to a Kivy Texture
        texture.blit_buffer(image.tobytes(), colorfmt='rgba')
        

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
        w=kivy.core.window.Window
        return w.width, w.height
        
    # helper function

    def setColor(self, color, opacity):
        '''Convert from Color to RGBA kivy color'''
        with self.kiwyCanvas:
            r, g, b = [ int(v.hex(),16) / 255.0 for v in color.getRGB()]
            kivy.graphics.Color(r, g, b, opacity)  # Set the color to (RGBA)
            
