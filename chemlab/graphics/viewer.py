import pyglet
pyglet.options['vsync']=False
import numpy as np

from pyglet.gl import *
from pyglet.window import key

from .gletools.transformations import simple_clip_matrix
from .gletools.camera import Camera

class AbstractViewer(object):
    
    def add_renderer(self, renderer):
        pass

class Viewer(pyglet.window.Window, AbstractViewer):
    '''Viewer is an object used to display atoms, molecules and other
    systems. It is responsible to handle the input events and to setup
    the visualization environment (opengl etc.). The public interface
    of Viewer is defined by AbstractViewer.

    '''
    
    def __init__(self):
        super(Viewer, self).__init__(resizable=True)

        # Renderers are responsible for actually drawing stuff
        self._renderers = []
        
        # Ui elements represent user interactions
        self._uis = []
        
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)        
        glEnable(GL_MULTISAMPLE)
        
        # Key pressed handling
        self._keys = key.KeyStateHandler()
        self.push_handlers(self._keys)
        self.camera = Camera()
        self.camera.moveto(np.array([0.0, 0.0, -5.0]))
        
        self._aspectratio = float(self.width) / self.height
        self.fps_display = pyglet.clock.ClockDisplay()
        
    
        self._zoom = 1.5
        # TODO Pretty brutal zoom function
        def zoom(self, inc):
            pos = self.camera.position[2]
            if (( pos < -0.1 and inc > 0) or
                ( pos > -50  and inc < 0)):
                self.camera.zoom(inc*2)

        # Handling keypresses
        angvel = 0.06

        kmap = { key.LEFT : (self.camera.orbit, (-angvel, 0)),
                 key.RIGHT: (self.camera.orbit, ( angvel, 0)),
                 key.UP   : (self.camera.orbit, (0,  angvel)),
                 key.DOWN : (self.camera.orbit, (0, -angvel)),
                 key.PLUS : (zoom,  (self, 0.1)),
                 key.MINUS: (zoom,  (self, -0.1))}
        
        def movement(dt):
            for k, (func, args) in kmap.items():
                if self._keys[k]:
                    func(*args)
                
        pyglet.clock.schedule_interval(movement, 1/60.0)
        
    def on_draw(self):
        from .shaders import default_program
        # Set Background
        glClearColor(1.0, 1.0, 1.0, 1.0)
        #glClearColor(0.0, 0.0, 0.0, 1.0)
        self.clear()
        
        self.fps_display.draw()
        
        # Set Perspective
        self._projection_matrix = simple_clip_matrix(
            self._zoom, 0.1, 100, self._aspectratio)
        
        proj = self._projection_matrix
        cam = self.camera.matrix
        
        self.mvproj = mvproj = np.dot(proj, cam)
        
        default_program.vars.mvproj = np.asmatrix(mvproj)
        self.ldir = ldir =  np.dot(np.asarray(self.camera.rotation[:3,:3].T),
                       np.array([0.3, 0.2, 0.8]))
        
        default_program.vars.lightDir = ldir
        self.camerapos = np.dot(cam[:3, :3].T, self.camera.position)
        default_program.vars.camera = self.camerapos.tolist()
        
        # Draw UI
        self.on_draw_ui()
        
        # Draw World
        with default_program:
            self.on_draw_world()

    def on_resize(self, width, height):
        super(Viewer, self).on_resize(width, height)
        self._aspectratio = float(width) / height
        
        return pyglet.event.EVENT_HANDLED
        
    def on_mouse_motion(self, x, y, dx, dy):
        for ui in self._uis:
            #ui.on_mouse_motion(x, y, dx, dy)
            if ui.is_inside(x, y):
                # I need to transform this to local coordinates
                ui.dispatch_event('on_hover', x, y, dx, dy)
            
    def on_mouse_drag(self, x, y, dx, dy, button, modifiers):
        for ui in self._uis:
            if ui.is_inside(x, y):
                ui.dispatch_event('on_drag', x, y, dx, dy, button, modifiers)

    def on_mouse_press(self, x, y, button, modifiers):
        for ui in self._uis:
            if ui.is_inside(x, y):
                ui.dispatch_event('on_click', x, y, button, modifiers)
        
    def on_key_press(self, symbol, modifiers):
        # Screenshot taking
        if symbol == key.P:
            pyglet.image.get_buffer_manager().get_color_buffer().save('screenshot.png')
        
    def add_renderer(self, klass, *args, **kwargs):
        renderer = klass(*args, **kwargs)
        renderer.set_viewer(self)
        self._renderers.append(renderer)
        return renderer
    
    def add_ui(self, klass, *args, **kwargs):
        ui = klass(*args, **kwargs)
        self._uis.append(ui)
        return ui
    
    def on_draw_ui(self):
        for u in self._uis:
            u.draw()
        
    def on_draw_world(self):
        for r in self._renderers:
            r.draw()

    def schedule(self, function, frequency=None):
        if not frequency:
            pyglet.clock.schedule(lambda t: function())
        else:
            pyglet.clock.schedule_interval(lambda t: function(), frequency)
        
    def run(self):
        pyglet.app.run()