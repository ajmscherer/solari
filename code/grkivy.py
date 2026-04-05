import grabst

import kivy
import kivy.app
import kivy.uix.widget
import kivy.graphics
import kivy.graphics.texture
import kivy.clock
import kivy.core.window

import datetime


class CanvasWrapperKivy(grabst.Canvas):

    def __init__(self, kivyCanvas, width, height):
        super().__init__()
        self.kiwyCanvas = kivyCanvas
        self.width = width
        self.height = height
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
        return self.width, self.height
        
    # helper function

    def setColor(self, color, opacity):
        '''Convert from Color to RGBA kivy color'''
        with self.kiwyCanvas:
            r, g, b = [ int(v.hex(),16) / 255.0 for v in color.getRGB()]
            kivy.graphics.Color(r, g, b, opacity)  # Set the color to (RGBA)
            

class KMainWidget(kivy.uix.widget.Widget):
    def __init__(self, app:grabst.App, framePerSecond,  **kwargs):
        super(KMainWidget, self).__init__(**kwargs)

        # store drawingMethod
        self.app = app
        self.rotation = 0

        # schedule redraw at regular interval
        kivy.clock.Clock.schedule_interval(self.update, 1.0 / framePerSecond)


    def update(self, timeInterval):

        # get a timeStamp for the drawing request
        timeStamp = datetime.datetime.now()

        # retrieve the Kivy canvas
        kivyCanvas = self.canvas

        if kivyCanvas:

            # clear the Kivy object canvas
            kivyCanvas.clear()
            
            # retrieve size of the Widget
            width, height = self.size


            # calculate scale factor based on required space
            widthRequired, heightRequired = self.app.sizeRequirement
            scaleFactor = min(width/widthRequired, height/heightRequired)

            with kivyCanvas:

                '''
                s = (datetime.datetime.now().second * 4) % 100
                kivy.graphics.Line(points=(s,s,width-s,height-s))
                kivy.graphics.Line(points=(s,height-s,width-s,s))
                '''

                kivy.graphics.PushMatrix()
                self.scale=kivy.graphics.Scale(scaleFactor)


            # build a canvas on the fly based on kivy
            canvas = CanvasWrapperKivy(kivyCanvas=kivyCanvas, width=width/scaleFactor, height=height/scaleFactor)
            
            # call the drawing function of the graphic app
            self.app.drawMainWindow(canvas, timeStamp)

            with kivyCanvas:
                kivy.graphics.PopMatrix()



class KApp(kivy.app.App):

    def __init__(self, graphicApp, **kwargs):
        super().__init__(**kwargs)
        self.graphicApp = graphicApp

    def build(self):
        app = self.graphicApp
        widget =  KMainWidget(app, app.framePerSecond)
        window = kivy.core.window.Window
        srs = 'sizeRequirement'
        if srs in app.__dict__:
            width, height = app.__dict__[srs]
            window.size = width, height
        else:
            window.fullscreen = True
        kivy.core.window.Window.bind(on_resize=self.on_window_resize)
        return widget

    def on_window_resize(self, window, width, height):
        # You can add logic here to handle window resize events if needed
        pass


class KivyApp(grabst.App):

    def __init__(self, framePerSecond, sizeRequirement, title) -> None:
        super().__init__(framePerSecond, sizeRequirement)
        self.title = title
        self.kapp = KApp(self)
        self.kapp.title = self.title
   
    def _run(self):
        '''Implementation of abstract _run method'''
        self.kapp.run()


class KivyFactory(grabst.Factory):
    APP = KivyApp




    