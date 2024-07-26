import helix
import random

GAME_ASSET_DIR:str = "assets\\char\\playable\\bunny\\"

FPS:int=144
SLIDING:bool = False
SLIDE_SPEED:int = 500 # pixel value
JUMP_HEIGHT:int = -350 # pixel value
SLIDE_MAX:float = 80.0 # pixel value
SLIDE_DIST:float = 0.0 # pixel value

class BunnyGame:
    controls:dict = {
        "Left": helix.events.Keyboard.A,
        "Right": helix.events.Keyboard.D,
        "Down": helix.events.Keyboard.S,
        "Up": helix.events.Keyboard.W,
        "Slide": helix.events.Keyboard.Shift,
        "Jump": helix.events.Keyboard.Space,
        "Zoom-In": helix.events.Mouse.WheelUp,
        "Zoom-Out": helix.events.Mouse.WheelDown
    }

    def __init__(self):
        self.running:bool = True
        self.clock:helix.clock.HXclock = helix.clock.HXclock(target=FPS, fixed_step=1.0/60)
        self.window:helix.gui.HXwindow = helix.gui.HXwindow(color=[137, 93, 93])
        world_bounds = self.window.dimensions[0]*3, self.window.dimensions[1]*3
        self.phys_subsys = helix.physics.HXphysics()
        self.phys_subsys.set_friction(16000)
        self.renderer:helix.HXrenderer=helix.HXrenderer(3)
        self.cursor:helix.events.HXcursor = helix.events.HXcursor()
        self.camera:helix.HXcamera=helix.HXcamera(self.window.display, world_bounds)
        self.grid:helix.HXsgrid = helix.HXsgrid(*world_bounds, helix.math.vec2(300, 300))
        self.event_handler:helix.events.HXevents = helix.events.HXevents()

        helix.gui.hide_mouse()

        self.init_entities()
        self.configure_entities()
        self.event_handler.register_controller("default", self.default_controller)

    def init_entities(self):
        self.player = helix.HXobject(sgrid=self.grid)
        
        self.player.add_component(
            helix.components.HXanim,
            dimensions=[32,32],
            flip_speed=16,
            loop_delay=True,
            sheet_path="assets\\char\\playable\\bunny\\idle_sheet.png"
        )
        self.player.add_component(helix.components.HXtransform, location=[64, 25])
        self.player.add_component(helix.components.HXcollider, dimensions=[32, 32])
        self.player.add_component(helix.components.HXactiongraph)

        self.player_anim:helix.components.HXanim = self.player.components[helix.components.HXanim]
        self.player_collider:helix.components.HXcollider = self.player.components[helix.components.HXcollider]
        self.player_transform:helix.components.HXtransform = self.player.components[helix.components.HXtransform]
        self.player_actiongraph:helix.components.HXactiongraph = self.player.components[helix.components.HXactiongraph]

        self.player_transform.dynamic = True
        self.player_transform.set_speed(200)

        self.tiles = []
        for i in range(100):
            for j in range(5):
                tile = helix.HXobject(sgrid=self.grid)
                tile.add_component(
                    helix.components.HXanim,
                    dimensions=[32,32],
                    flip_speed=6,
                    loop=True,
                    sheet_path="assets\\tiles\\anim\\grassy_rock_sheet.png"
                )
                tile.add_component(helix.components.HXtransform, size=[32, 32], location=[32*i, 200*(j+1)])
                tile.add_component(helix.components.HXcollider, dimensions=[32, 32])
                self.tiles.append(tile)

        self.camera.set_target(self.player)
        self.renderer.add_to_layer(self.player)
        [self.renderer.add_to_layer(tile) for tile in self.tiles]

    def configure_entities(self) -> None:
        def idle_callback():
            self.player.set_component(
                helix.components.HXanim,
                dimensions=[32,32],
                flip_speed=16,
                loop_delay=True,
                sheet_path=f"{GAME_ASSET_DIR}idle_sheet.png"
            )
        self.player_actiongraph.add_action(
            action="idle",
            callback=idle_callback
        )

        def idle_con() -> bool:
            global SLIDING
            if int(self.player_transform.velocity.x) == 0 and self.player_transform.velocity.y == 0.0:
                SLIDING = False
                return True
            return False
        self.player_actiongraph.add_condition("idle", idle_con)

        def run_callback():
            self.player.set_component(
                helix.components.HXanim,
                dimensions=[32,32],
                flip_speed=6,
                loop=True,
                sheet_path=f"{GAME_ASSET_DIR}run_sheet.png"
            )
        self.player_actiongraph.add_action(
            action="run",
            callback=run_callback
        )

        def run_con() -> bool:
            if int(self.player_transform.velocity.x) != 0 and self.player_transform.velocity.y == 0.0 and not SLIDING:
                return True
            return False
        self.player_actiongraph.add_condition("run", run_con)

        def jump_callback():
            self.player.set_component(
                helix.components.HXanim,
                dimensions=[32,32],
                flip_speed=4,
                sheet_path=f"{GAME_ASSET_DIR}jump_sheet.png"
            )
        self.player_actiongraph.add_action(
            action="jump",
            callback=jump_callback
        )
        
        def jump_con() -> bool:
            global SLIDING
            if self.event_handler.is_key_triggered(self.controls["Jump"]) and int(self.player_transform.velocity.y) < 0 or int(self.player_transform.velocity.y) > 50:
                SLIDING = False
                return True
            return False
        self.player_actiongraph.add_condition("jump", jump_con)

        def slide_callback():
            self.player.set_component(
                helix.components.HXanim,
                dimensions=[32,32],
                flip_speed=100,
                loop=True,
                sheet_path=f"{GAME_ASSET_DIR}slide_sheet.png"
            )
        self.player_actiongraph.add_action(
            action="slide",
            callback=slide_callback
        )

        def slide_con() -> bool:
            global SLIDING
            if self.event_handler.is_key_triggered(self.controls["Slide"]):
                SLIDING = True
                return True
            return False
        self.player_actiongraph.add_condition("slide", slide_con)

    def default_controller(self):
        # keyboard controls
        def left_con() -> bool:
            if self.event_handler.is_key_pressed(self.controls["Left"]) and not SLIDING:
                self.facing_left = -1
                return True
            return False
        
        def right_con() -> bool:
            if self.event_handler.is_key_pressed(self.controls["Right"]) and not SLIDING:
                self.facing_left = 1
                return True
            return False

        self.player_transform.move(
            delta_time=self.clock.delta_time,
            left=left_con(),
            right=right_con()
        )

        # zoom
        if self.event_handler.mouse_wheelu:
            self.camera.zoom -= 0.1
        if self.event_handler.mouse_wheeld:
            self.camera.zoom += 0.1

        # slide
        global SLIDING
        global SLIDE_MAX
        global SLIDE_DIST
        if SLIDING and SLIDE_DIST != SLIDE_MAX:
            if self.player_transform.negx:
                self.player_transform.set_velocity(-SLIDE_SPEED, self.player_transform.velocity.y)
            else:
                self.player_transform.set_velocity(SLIDE_SPEED, self.player_transform.velocity.y)
            SLIDE_DIST += 1
        if SLIDE_DIST >= SLIDE_MAX:
            SLIDE_DIST = 0.0
            SLIDING = False

        # jump
        if self.event_handler.is_key_triggered(self.controls["Jump"]):
            self.player_transform.set_velocity(self.player_transform.velocity.x, JUMP_HEIGHT)

        if self.event_handler.is_key_pressed(self.controls["Left"]): self.player_transform.negx = True
        if self.event_handler.is_key_pressed(self.controls["Right"]): self.player_transform.negx = False

    def run(self, *args, **kwargs):
        while not self.event_handler.process():

            self.clock.tick()
            self.camera.update(self.clock.delta_time)
            self.cursor.update(self.camera.zoom, offset=self.camera.get_location())
            
            while self.clock.get_fupdate():
                self.phys_subsys.update(snodes=self.grid.query_nodes(self.player_transform), dt=self.clock.delta_time)
                self.clock.reset_fupdate()

            self.player.update(
                delta_time=self.clock.delta_time, 
                offset=self.camera.get_location()
            )

            # TODO: delete this test
            [ tile.update(
                delta_time=self.clock.delta_time, 
                offset=self.camera.get_location()
                ) for tile in self.tiles ]

            self.renderer.render(
                self.grid,
                self.cursor,
                self.window,
                self.camera.zoom,
                self.camera.get_location(),
                show_rects=False, show_nodes=False, show_grid=True, show_colliders=True
            )
        self.running = False


if __name__ == '__main__':
    BunnyGame().run()
