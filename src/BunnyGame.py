import helix
import random
import xml.etree.ElementTree as ET

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


def readTSX(path: str) -> dict:
    print(f"READING TSX FROM SRC {f'map_data/{path}'}")
    tree = ET.parse(f"map_data/{path}")
    root = tree.getroot()
    
    tileset_src = root.find('image').get('source')
    tilewidth = int(root.get('tilewidth'))
    tileheight = int(root.get('tileheight'))
    tile_dim = helix.math.vec2(tilewidth, tileheight)

    print(tileset_src, tile_dim)
    return {'src': tileset_src, 'tile_dim': tile_dim}

def readTMX(path: str, renderer, grid) -> dict[str, list[helix.HXobject]]:
    print(f"READING TMX FROM SRC {path}")
    tree = ET.parse(path)
    root = tree.getroot()
    
    map_width = int(root.get('width'))
    map_height = int(root.get('height'))
    tilewidth = int(root.get('tilewidth'))
    tileheight = int(root.get('tileheight'))

    tileset = root.find('tileset')
    firstgid = int(tileset.get('firstgid'))
    tileset_source = tileset.get('source')
    tileset_data = readTSX(tileset_source)

    layers = root.findall('layer')
    tile_layers = {'collision': [], 'fill': []}

    tiles = 0
    colliders = 0
    for layer in layers:
        layer_name = layer.get('name')
        if layer_name in tile_layers:
            data = layer.find('data').text.strip().split(',')
            for row in range(map_height):
                for col in range(map_width):
                    tile_id = int(data[row * map_width + col])
                    if tile_id > 0:
                        # Calculate the position
                        x = col * tilewidth
                        y = row * tileheight

                        # Create and configure the tile entity
                        tiles+=1
                        tile = helix.HXobject(sgrid=grid)
                        tile.add_component(helix.components.HXtexture, size=[tilewidth, tileheight], path=f"map_data/{tileset_data['src']}")
                        tile.add_component(helix.components.HXtransform, location=[x, y])
                        tile_transform = tile.components[helix.components.HXtransform]
                        tile_transform.dynamic = False
                        if layer_name == 'collision':
                            colliders+=1
                            tile.add_component(helix.components.HXcollider, dimensions=[tilewidth, tileheight])

                        # Add to renderer
                        renderer.add_to_layer(tile)
                        tile_layers[layer_name].append(tile)

    print(f"NUM TILES {tiles} NUM COLLIDERS {colliders}")
    return tile_layers

def load_map_tiled(path:str, renderer:helix.HXrenderer, grid:helix.HXsgrid) -> dict[str, list[helix.HXobject]]:
    return readTMX(path, renderer, grid)

def load_map_tiled(path:str, renderer:helix.HXrenderer, grid:helix.HXsgrid):
    return readTMX(path, renderer, grid)

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
        self.camera:helix.HXcamera=helix.HXcamera(self.window.display, world_bounds)
        self.grid:helix.HXsgrid = helix.HXsgrid(*world_bounds, helix.math.vec2(300, 300))
        self.event_handler:helix.events.HXevents = helix.events.HXevents()

        helix.gui.hide_mouse()

        self.init_entities()
        self.configure_entities()
        self.event_handler.register_controller("default", self.default_controller)

        self.tiles_layer_data = load_map_tiled(f"{MAP_DATA_DIR}map_iguess.tmx", self.renderer, self.grid)

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

        # attack
        self.player_anim:helix.components.HXanim = self.player.components[helix.components.HXanim]
        if ATTACKING:
            if int(self.player_anim.nframe)+1 == self.player_anim.nframes: 
                ATTACKING = False

    def run(self, *args, **kwargs):
        while not self.event_handler.process():
            helix.pg.display.set_caption(f"FPS: {self.clock.current}")
            self.clock.tick()
            self.camera.update(self.clock.delta_time)
            self.cursor.update(self.camera.zoom, offset=self.camera.get_location())
            
            self.slide_cd.update(self.clock.delta_time)
            self.attack_cd.update(self.clock.delta_time)

            while self.clock.get_fupdate():
                self.phys_subsys.update(snodes=self.grid.query_nodes(self.player_transform), dt=self.clock.delta_time)
                self.clock.reset_fupdate()

            self.player.update(
                delta_time=self.clock.delta_time, 
                offset=self.camera.get_location()
            )
            
            # self.dummy.update(
            #     delta_time=self.clock.delta_time, 
            #     offset=self.camera.get_location()
            # )

            [ tile.update(
                delta_time=self.clock.delta_time, 
                offset=self.camera.get_location()
                ) for layer in self.tiles_layer_data for tile in self.tiles_layer_data['collision'] ]

            # TODO: make the renderer configurable, with custom pre and post rendering logic (ui, fx, etc...)
            self.renderer.render(
                self.grid,
                self.cursor,
                self.window,
                self.camera.zoom,
                self.camera.get_location(),
                show_rects=False, show_nodes=False, show_grid=False, show_colliders=True
            )
            
        self.running = False


if __name__ == '__main__':
    BunnyGame().run()
