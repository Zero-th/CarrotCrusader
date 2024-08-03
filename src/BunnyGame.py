import helix
import random, json

MAP_DATA_DIR:str = "map_data\\"
GAME_ASSET_DIR:str = "assets\\char\\playable\\bunny\\"

FPS:int=144
SLIDING:bool = False
ATTACKING:bool = False
SLIDE_SPEED:int = 300 # pixel value
JUMP_HEIGHT:int = -380 # pixel value
SLIDE_MAX:float = 80.0 # pixel value
SLIDE_DIST:float = 0.0 # pixel value

class HXcooldown:
    def __init__(self, duration:float) -> None:
        self.time:float=0.0
        self.cooling:bool=False
        self.duration:float=duration

    def cool(self) -> None:
        if self.time == 0.0:
            self.cooling = True

    def update(self, dt:float, *args, **kwargs) -> None:
        if self.cooling and self.time != self.duration:
            self.time+=dt
        if self.cooling and self.time >= self.duration: 
            self.time = 0
            self.cooling = False

def loadWF2Map(path: str, renderer, grid) -> dict[str, list[helix.HXobject]]:
    with open(path, 'r') as file:
        map_data = json.load(file)

    map_info = map_data["mapInfo"]
    tile_size = map_info["tilesize"]
    
    layers = ['background', 'midground', 'foreground']
    tile_layers = {layer: [] for layer in layers}
    
    for layer in layers:
        if layer in map_data:
            for key, value in map_data[layer].items():
                x, y = map(float, key.split(';'))
                x = int(x)
                y = int(y)
                
                tile_id = value["id"]
                asset_path = value["asset"]
                collisions = value["properties"]["collisions"]
                tile_set = helix.gui.load_image_sheet(asset_path, [tile_size, tile_size])

                # Create and configure the tile entity
                tile = helix.HXobject(sgrid=grid)
                tile.add_component(helix.components.HXtexture, size=[tile_size, tile_size])
                tile.get_component(helix.components.HXtexture).set(tile_set[int(tile_id)])
                tile.add_component(helix.components.HXtransform, location=[x, y])
                tile_transform = tile.components[helix.components.HXtransform]
                tile_transform.dynamic = False

                if collisions:
                    tile.add_component(helix.components.HXcollider, dimensions=[tile_size, tile_size])

                # Add to renderer
                renderer.add_to_layer(tile)
                tile_layers[layer].append(tile)

    return tile_layers

class BunnyGame:
    controls:dict = {
        "Left": helix.events.Keyboard.A,
        "Right": helix.events.Keyboard.D,
        "Down": helix.events.Keyboard.S,
        "Up": helix.events.Keyboard.W,
        "Slide": helix.events.Keyboard.Shift,
        "Jump": helix.events.Keyboard.Space,
        "Attack": helix.events.Mouse.LeftClick,
        "Zoom-In": helix.events.Mouse.WheelUp,
        "Zoom-Out": helix.events.Mouse.WheelDown
    }

    def __init__(self):
        self.running:bool = True
        self.clock:helix.clock.HXclock = helix.clock.HXclock(target=FPS, fixed_step=1.0/60)
        self.window:helix.gui.HXwindow = helix.gui.HXwindow(color=[137, 93, 93], size=[1400, 800])
        world_bounds = self.window.dimensions[0]*3, self.window.dimensions[1]*3
        self.phys_subsys = helix.physics.HXphysics()
        self.phys_subsys.set_friction(9999)
        self.renderer:helix.HXrenderer=helix.HXrenderer(3)
        self.cursor:helix.events.HXcursor = helix.events.HXcursor()
        self.camera:helix.HXcam2D=helix.HXcam2D(self.window, [0,0], world_bounds, 30.0)
        # self.camera:helix.HXcamera=helix.HXcamera(self.window.display, world_bounds)
        self.grid:helix.HXsgrid = helix.HXsgrid(*world_bounds, helix.math.vec2(300, 300))
        self.event_handler:helix.events.HXevents = helix.events.HXevents()

        helix.gui.hide_mouse()

        self.init_entities()
        self.configure_entities()
        self.event_handler.register_controller("default", self.default_controller)

        self.tiles_layer_data = loadWF2Map(f"{MAP_DATA_DIR}\\testbed\\testbed.wf2", self.renderer, self.grid)

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

        self.dummy = helix.HXobject(sgrid=self.grid)
        self.dummy.add_component(helix.components.HXtexture, size=[32, 64])
        self.dummy.add_component(helix.components.HXtransform, location=[100, 25])
        self.dummy_transform:helix.components.HXtransform = self.dummy.components[helix.components.HXtransform]
        self.dummy_transform.dynamic = True
        self.dummy_transform.set_speed(200)
        self.dummy.add_component(helix.components.HXcollider, dimensions=[32, 64])

        self.slide_cd = HXcooldown(5.0)
        self.attack_cd = HXcooldown(0.8)

        self.camera.set_target(self.player)
        self.renderer.add_to_layer(self.dummy)
        self.renderer.add_to_layer(self.player)

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
            if not ATTACKING and int(self.player_transform.velocity.x) == 0 and self.player_transform.velocity.y == 0.0:
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
                flip_speed=50,
                loop=True,
                sheet_path=f"{GAME_ASSET_DIR}slide_sheet.png"
            )
        self.player_actiongraph.add_action(
            action="slide",
            callback=slide_callback
        )

        def slide_con() -> bool:
            global SLIDING
            if self.event_handler.is_key_triggered(self.controls["Slide"]) and not self.slide_cd.cooling:
                self.slide_cd.cool()
                SLIDING = True
                return True
            return False
        self.player_actiongraph.add_condition("slide", slide_con)

        def atk_callback():
            if self.player_transform.negx:
                self.player.set_component(
                    helix.components.HXanim,
                    dimensions=[96,96],
                    flip_speed=20,
                    loop=False,
                    image_offset=[38,30],
                    sheet_path=f"{GAME_ASSET_DIR}whip_sheet.png"
                )
            else:
                self.player.set_component(
                    helix.components.HXanim,
                    dimensions=[96,96],
                    flip_speed=20,
                    loop=False,
                    image_offset=[25,30],
                    sheet_path=f"{GAME_ASSET_DIR}whip_sheet.png"
                )
        self.player_actiongraph.add_action(
            action="attack",
            callback=atk_callback
        )

        def atk_con() -> bool:
            # attack
            if self.event_handler.is_mouse_triggered(self.controls["Attack"]) and not self.attack_cd.cooling:
                self.attack_cd.cool()
                self.player_transform.set_velocity(0,0)
                if int(self.player_transform.velocity.x) == 0 and self.player_transform.velocity.y == 0.0 or self.event_handler.is_mouse_triggered(self.controls["Attack"]) and int(self.player_transform.velocity.x) == 0 and self.player_transform.velocity.y < 50.0:
                    global ATTACKING
                    ATTACKING = True
                    return True
            return False
        self.player_actiongraph.add_condition("attack", atk_con)

    def default_controller(self):
        global ATTACKING

        # keyboard controls
        def left_con() -> bool:
            if not ATTACKING and self.event_handler.is_key_pressed(self.controls["Left"]) and not SLIDING:
                self.facing_left = -1
                self.player_transform.negx = True
                return True
            return False
        
        def right_con() -> bool:
            if not ATTACKING and self.event_handler.is_key_pressed(self.controls["Right"]) and not SLIDING:
                self.facing_left = 1
                self.player_transform.negx = False
                return True
            return False

        self.player_transform.move(
            delta_time=self.clock.delta_time,
            left=left_con(),
            right=right_con()
        )

        # zoom
        if self.event_handler.mouse_wheelu:
            self.camera.zoom_value -= 0.1
        if self.event_handler.mouse_wheeld:
            self.camera.zoom_value += 0.1

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

        # attack
        self.player_anim:helix.components.HXanim = self.player.components[helix.components.HXanim]
        if ATTACKING:
            if int(self.player_anim.nframe)+1 == self.player_anim.nframes: 
                ATTACKING = False

    def run(self, *args, **kwargs):
        while not self.event_handler.process():
            helix.pg.display.set_caption(f"FPS: {self.clock.current}")
            self.clock.tick()
            self.camera.camera_system(self.player, self.clock.delta_time)
            self.cursor.update(self.camera.zoom, offset=self.camera.position)
            
            self.slide_cd.update(self.clock.delta_time)
            self.attack_cd.update(self.clock.delta_time)

            while self.clock.get_fupdate():
                self.phys_subsys.update(snodes=self.grid.query_nodes(self.player_transform), dt=self.clock.delta_time)
                self.clock.reset_fupdate()

            self.player.update(
                delta_time=self.clock.delta_time,
                offset=self.camera.position
            )
            
            self.dummy.update(
                delta_time=self.clock.delta_time, 
                offset=self.camera.position
            )

            [ tile.update(
                delta_time=self.clock.delta_time, 
                offset=self.camera.position
                ) for layer in self.tiles_layer_data for tile in self.tiles_layer_data[layer] if tile.has_component(helix.HXcollider)]

            self.renderer.render(
                self.grid,
                self.cursor,
                self.window,
                self.camera.zoom_value,
                self.camera.position,
                show_rects=True, show_nodes=False, show_grid=True, show_colliders=True
            )
            
        self.running = False


if __name__ == '__main__':
    BunnyGame().run()
