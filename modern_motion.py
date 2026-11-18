"""A real-time 3D stage for the local pixel cinematic renderer."""
import math
import random
import subprocess

import moderngl as gl
import numpy as np

WIDTH, HEIGHT, FPS = 960, 540, 24
KEY = (3.5, 10.0, -6.0)

VERTEX = """
#version 330
in vec3 vert;
in vec3 norm;
in vec3 pos;
in vec3 size;
in vec4 tint;
in float spin;
uniform mat4 view_proj;
uniform mat4 light_proj;
out vec3 world;
out vec3 normal;
out vec3 local;
out vec4 material;
out vec4 shadow_pos;
void main() {
    mat2 rotation = mat2(cos(spin), -sin(spin), sin(spin), cos(spin));
    vec3 p = vert * size;
    p.xz = rotation * p.xz;
    world = p + pos;
    normal = vec3(0);
    normal.xz = rotation * norm.xz;
    normal.y = norm.y;
    local = vert * size;
    material = tint;
    shadow_pos = light_proj * vec4(world, 1.0);
    gl_Position = view_proj * vec4(world, 1.0);
}
"""
FRAGMENT = """
#version 330
in vec3 world;
in vec3 normal;
in vec3 local;
in vec4 material;
in vec4 shadow_pos;
uniform sampler2D shadow_map;
uniform vec3 eye;
uniform vec3 accent;
uniform vec3 practical;
uniform vec3 horizon;
out vec4 color;

float shadow(vec3 n, vec3 l) {
    vec3 p = shadow_pos.xyz / shadow_pos.w * 0.5 + 0.5;
    if (min(p.x,p.y) < 0.0 || max(p.x,p.y) > 1.0) return 1.0;
    float visibility = 0.0;
    float bias = 0.0015 + 0.0016 * (1.0 - max(0.0,dot(n,l)));
    for(int x=-1;x<=1;x++) for(int y=-1;y<=1;y++){
        float depth = texture(shadow_map,p.xy + vec2(x,y)/1024.0).r;
        visibility += step(p.z - bias, depth);
    }
    return visibility / 9.0;
}
void main() {
    vec3 n = normalize(normal);
    vec3 l = normalize(vec3(3.5, 10, -6) - world);
    vec3 v = normalize(eye-world);
    vec3 fill = normalize(vec3(-6, 4, 5) - world);
    vec3 p = floor(local * 27.0);
    float grain = fract(sin(dot(p,vec3(41.32,17.91,83.67))) * 17345.17);
    vec3 base = pow(material.rgb, vec3(1.55)) * (0.88 + grain * 0.22);
    float diffuse = max(dot(n,l),0.0);
    float visibility = shadow(n,l);
    if(material.a < 0.0) {
        vec2 slab = abs(fract(world.xz * 1.15) - 0.5);
        base *= mix(1.0,0.59,smoothstep(0.467,0.493,max(slab.x,slab.y)));
    }
    float ambient_floor = mix(0.52,1.0,smoothstep(0.0,1.65,world.y));
    vec3 ambient = vec3(0.37,0.43,0.64) * ambient_floor;
    vec3 lit = base * (ambient + vec3(1.40,1.03,0.76)*diffuse*visibility
        + accent * max(0.0,dot(fill,n))*0.91);
    vec3 h = normalize(l+v);
    float gloss = pow(max(0.0,dot(h,n)),material.a < 0.0 ? 34.0 : 23.0);
    lit += gloss * visibility * (material.a < 0.0 ? 0.34 : 0.18) * vec3(1,0.84,0.66);
    vec3 to_lamp = practical - world;
    float d2 = max(0.16,dot(to_lamp,to_lamp));
    vec3 lamp_dir = normalize(to_lamp);
    lit += (base + 0.11) * accent * max(0.12,dot(n,lamp_dir)) * 1.8 / (0.6 + d2);
    lit += base * max(0.0,material.a);
    float rim = pow(1.0-max(0.0,dot(n,v)),3.0);
    lit += vec3(0.09,0.15,0.25)*rim*max(0.0,dot(n,fill));
    float distance_to_camera = distance(eye,world);
    float fog = 1.0 - exp(-pow(max(0.0,distance_to_camera-3.0)*0.042,1.55));
    lit = mix(lit,horizon * 0.48,clamp(fog,0.0,0.84));
    color = vec4(pow(lit/(lit+0.62),vec3(0.75)),1.0);
}
"""
SKY_VERTEX = """
#version 330
out vec2 uv;
void main() {
    vec2 point = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    uv = point;
    gl_Position = vec4(point*2.0-1.0,0.0,1.0);
}
"""
SKY_FRAGMENT = """
#version 330
in vec2 uv;
uniform vec3 sky_tint;
out vec4 color;
void main() {
    vec3 zenith = vec3(0.022,0.044,0.105);
    vec3 horizon = sky_tint*0.68 + vec3(0.13,0.084,0.13);
    vec3 sky = mix(horizon,zenith,smoothstep(0.02,0.90,uv.y));
    float glow = exp(-length((uv-vec2(0.72,0.20))*vec2(1.0,1.9))*4.0);
    sky += glow*vec3(0.16,0.12,0.075);
    color = vec4(sky,1.0);
}
"""
DEPTH_VERTEX = """
#version 330
in vec3 vert;
in vec3 pos;
in vec3 size;
in float spin;
uniform mat4 light_proj;
void main() {
    vec3 p = vert * size;
    p.xz = mat2(cos(spin), -sin(spin), sin(spin), cos(spin))*p.xz;
    gl_Position = light_proj * vec4(p+pos,1);
}
"""


def rgb(color):
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def norm(vector):
    return vector / np.linalg.norm(vector)


def view(eye, target):
    forward = norm(np.array(target) - eye)
    right = norm(np.cross(forward, (0, 1, 0)))
    upward = np.cross(right, forward)
    basis = np.array((right, upward, -forward))
    result = np.identity(4)
    result[:3, :3] = basis
    result[:3, 3] = -basis @ eye
    return result


def projection(fov):
    f = 1 / math.tan(math.radians(fov) / 2)
    near, far = 0.10, 95
    return np.array(((f * HEIGHT / WIDTH, 0, 0, 0), (0, f, 0, 0),
                     (0, 0, (far + near) / (near - far), 2 * far * near / (near - far)),
                     (0, 0, -1, 0)))


def matrix_bytes(matrix):
    return matrix.astype("f4").T.tobytes()


def cube_vertices():
    vertices = []
    for axis in range(3):
        for side in (-1, 1):
            normal = [0, 0, 0]
            normal[axis] = side
            corners = []
            for a, b in ((-1, -1), (-1, 1), (1, 1), (1, -1)):
                point = [0.0, 0.0, 0.0]
                point[axis] = side * 0.5
                point[(axis + 1) % 3] = a * 0.5
                point[(axis + 2) % 3] = b * 0.5
                corners.append(point)
            for index in (0, 1, 2, 0, 2, 3):
                vertices.append(corners[index] + normal)
    return np.array(vertices, dtype="f4")


class Blocks:
    def __init__(self):
        self.data = []

    def add(self, x, y, z, w, h, d, color, glow=0, spin=0):
        self.data.append((x, y, z, w, h, d, *rgb(color), glow, spin))

    def character(self, origin, angle):
        cos, sin = math.cos(angle), math.sin(angle)

        def part(x, y, z, w, h, d, color, glow=0):
            self.add(origin[0] + x * cos + z * sin, origin[1] + y,
                     origin[2] - x * sin + z * cos, w, h, d, color, glow, angle)
        return part


def stage(setting, seed, accent):
    rng = random.Random(seed)
    blocks = Blocks()
    add = blocks.add
    add(0, -0.15, 0, 50, 0.27, 46, "#293347", -1)
    add(0, -0.01, 2.15, 22, 0.028, 0.08, accent, 0.42)
    add(0, -0.01, -2.15, 22, 0.028, 0.08, accent, 0.20)
    for x in (-7.5, -3.75, 0, 3.75, 7.5):
        add(x, 2.05, 3.2, 0.10, 4.1, 0.12, "#557286")
        add(x, 3.8, 3.2, 0.36, 0.065, 0.21, accent, 0.8)
        add(x, 4.1, 0, 0.16, 0.12, 6.6, "#30465e")
    add(0, 4.1, 3.2, 18, 0.13, 0.11, "#7896a7")
    add(0, 1.0, 3.2, 18, 0.08, 0.09, "#547889")
    for x in (-5.6, -1.9, 1.9, 5.6):
        add(x, 3.92, 0.5, 2.1, .09, .19, "#33354d")
        add(x, 3.86, 0.5, 1.93, .06, .10, "#f6bb8b", 1.4)
        add(x, 1.05, 3.17, 1.83, .023, .04, accent, .68)
    for x in (-5.9, -3.2, 3.6, 6.1):
        add(x, 0.28, 2.72, 1.68, 0.55, 0.65, "#515068")
        add(x, 0.55, 2.72, 1.52, 0.13, 0.59, "#483c4b")
        for j in range(5):
            plant(blocks, x - .64 + j * .28, 2.70 + rng.uniform(-.18,.18), rng.uniform(.40,.83), .60)
    for x in (-6.4, 5.9):
        add(x, 0.62, 0.40, 1.55, 1.20, .68, "#384558")
        add(x, 1.22, 0.34, 1.68, .08, .81, "#8a6170")
        add(x, 0.82, 0.02, .92, .09, .025, accent, .62)
        for dx in (-.43, .12, .46):
            add(x+dx,1.39,.31,.24,.25,.25,"#8c8b8b")
    if setting == "station":
        add(0, 3.23, 3.0, 15, .10, .34, "#ddad65", .20)
        for x in (-5.3, 5.3):
            add(x,.64,1.8,1.7,1.2,.12,"#273949")
            add(x,.9,1.73,1.34,.40,.025,"#f6b369",.35)
    elif setting == "market":
        for x in (-4.8, 4.8):
            for j in range(9):
                add(x-1.2+j*.30,2.75,1.1,.29,.105,1.4,
                    "#dd8a62" if j%2 else "#67395e")
    for _ in range(29):
        x, z = rng.uniform(-30, 30), rng.uniform(7, 24)
        h = rng.uniform(1.5, 9.5)
        add(x, h / 2 - 0.6, z, rng.uniform(.85,2.4), h, rng.uniform(.6,2), "#263753")
        for y in np.arange(0.7, h - 0.35, .70):
            if rng.random() < .72:
                add(x + rng.uniform(-.42,.42), float(y), z - .99, .25, .13, .04,
                    rng.choice(("#67c7d5", "#f7b385", "#817af2")), .63)
    return blocks.data


def plant(blocks, x, z, height, base=0):
    blocks.add(x, base + height/2, z, .068, height, .068, "#42845f")
    blocks.add(x - .115, base + height*.61, z, .252, .09, .16, "#57a583")
    blocks.add(x + .12, base + height*.82, z, .24, .085, .13, "#71b98b")
    blocks.add(x + .02, base + height, z, .17, .13, .17, "#a7c990")


def courier(blocks, x, yaw, t, walking, gesture, shocked, talking, cast):
    stride = math.sin(t * 12) * (.02 + walking * .27)
    bob = abs(stride) * .26
    body = blocks.character((x, bob, 0.05), yaw)
    for side in (-1, 1):
        z = stride * side
        body(side*.19,.32,z,.27,.55,.27,"#405677")
        lift = max(0.0,math.cos(t*12)*side)*walking*.11
        body(side*.19,.10+lift,z-.09,.31,.19,.42,"#deeced")
        y = 1.11 + .28 * gesture * (side == 1)
        body(side*.44,y,z*.66-.13*gesture,.24,.40-.08*gesture,.25,cast.coat)
        body(side*.44,y-.20+.17*gesture,z*.66-.18*gesture,
             .21,.17,.24,"#c3886e")
    body(0,1.02,0,.65,.66,.37,cast.coat)
    body(0,1.06,-.194,.11,.48,.018,"#2f354c")
    body(0,1.36,0,.61,.14,.42,cast.scarf)
    body(-.14,1.39,.23 + .035 * math.sin(t*6),.21,.14,.29,cast.scarf)
    body(0,1.70,0,.56,.54,.46,"#c68b72")
    body(0,1.91,.025,.61,.18,.55,"#3e3049")
    body(0,2.00,.01,.62,.14,.60,cast.scarf)
    body(0,1.91,-.25,.58,.065,.32,cast.scarf)
    body(-.29,1.67,.01,.085,.16,.11,"#d28c70")
    body(.29,1.67,.01,.085,.16,.11,"#d28c70")
    for side in (-1, 1):
        body(side * .14,1.73,-.235,.082,.085 if shocked else .048,.012,"#22253d")
        body(side * .14-.015,1.747,-.245,.02,.02,.005,"#cce6df",.2)
    mouth = .055 + .04 * (t * 12 % 1) if talking or shocked else .024
    body(0,1.58,-.238,.13,mouth,.02,"#53394b")


def robot(blocks, x, yaw, t, gesture, shocked, talking, cast):
    bob = math.sin(t * 5.2) * .085 + .17
    part = blocks.character((x,bob,.16), yaw)
    part(0,1.08,0,.76,.6,.51,cast.casing)
    part(0,1.17,-.267,.57,.39,.055,"#253653")
    part(0,.77,0,.61,.16,.39,"#635478")
    part(0,.675,0,.25,.105,.24,"#a5eeed",.90)
    for side in (-1,1):
        part(side*.19,.59,.025,.08,.13+(.05*math.sin(t*18+side)),.065,"#83dce4",.65)
        part(side*.112,1.23,-.298,.065,.102 if shocked else .062,.018,"#a3f5ed",.6)
        part(side*.47,1.02+.20*gesture*(side==-1),.01,.18,.15,.30,cast.casing)
    if talking:
        part(0,1.105,-.30,.11+.054*(t*11%1),.04,.02,"#93e9ef",.55)
    part(.14,1.53,.03,.05,.29,.052,"#c2ced3")
    part(.14,1.69,.03,.15,.105,.11,"#f8be7a",.9)


def prop_blocks(blocks, name, x, y, opened, t):
    if not opened:
        blocks.add(x,y,0,.55,.37,.46,"#ab6859")
        blocks.add(x,y+.19,0,.56,.05,.47,"#e5ac7f")
        blocks.add(x,y+.025,-.239,.075,.38,.015,"#f1c586")
    elif name == "cloud":
        for dx,dy,dz,w,h,d in ((-.22,0,0,.35,.23,.38),(.02,.095,0,.40,.34,.50),
                                (.24,-.022,.025,.40,.27,.33),(0,-.095,-.035,.56,.19,.36)):
            blocks.add(x+dx,y+dy,dz,w,h,d,"#ced0f0",.13)
        for drop in range(28):
            age = (t * (2.3 + drop % 3 * .36) + drop * .29) % 1
            blocks.add(x + (drop*13%43-21)*.018 - age*.23, max(.04,y-.21-age*1.45),
                       (drop*19%29-13)*.035,.015,.07+.08*age,.015,"#83ccf6",.45)
    elif name == "moon":
        for layer in range(-2,3):
            width = .32 + .12 * (2-abs(layer))
            blocks.add(x,y+layer*.098,0,width,.10,width,"#ffcb86",.64,t*.8)
    elif name == "kettle":
        blocks.add(x,y,0,.39,.35,.34,"#d98568")
        blocks.add(x-.25,y+.035,0,.16,.13,.13,"#e7a873")
        blocks.add(x+.25,y+.06,0,.10,.25,.25,"#f4bf81")
        for side in (-1,1):
            blocks.add(x+side*.12,y-.22+.055*math.sin(t*16+side),0,.078,.16,.08,"#e3ad82")
    else:
        blocks.add(x,y,0,.31,.28,.28,"#d89864")
        plant(blocks,x,0,.27,y+.14)


def smooth(v):
    v = max(0,min(1,v))
    return v*v*(3-2*v)


def frame_objects(plot, cast, event, index, t, duration, clock, speaking):
    p = t / duration
    motion = smooth(p * 1.11)
    moves = event in {"walk","escape","catch"}
    x, rx = -1.02, .92
    px, py = .03, .28
    if event == "walk":
        x, rx = -3.25+2.34*motion, -1.35+2.34*motion
    if event == "open":
        py += .68 * smooth((p-.33)*3)
    if event == "read" and "open" in plot.events[:index]:
        py = .92 + math.sin(clock*4)*.06
    if event == "escape":
        px, py = -.12+2.33*motion, .89+1.19*motion+.16*math.sin(t*5)
        x, rx = -.92+1.38*motion, .76+2.00*motion
    if event == "catch":
        px, py = 2.73-2.33*motion, 2.20-1.22*motion
        x, rx = -1.03+1.25*motion, 2.28-1.10*motion
    opened = any(mark in {"open","escape"} for mark in plot.events[:index])
    opened |= event in {"catch","finish","escape"} or (event == "open" and p > .35)
    if event == "finish":
        px, py = .1, 1.16+.096*math.sin(clock*3)
    if plot.prop == "kettle" and event in {"catch","escape"}:
        py = .3 + abs(math.sin(clock*7))*.20
    blocks = Blocks()
    gaze = .36+.23*math.sin(p*2.2)
    step = min(smooth(p*6), smooth((1-p)*5)) if moves else 0.0
    gesture = smooth(p*5)*smooth((1-p)*5)
    courier(blocks,x,gaze-1.5*step,t,step,gesture if event in {"catch","open","finish"} else 0,
            event=="escape",speaking and index%2==0,cast)
    robot(blocks,rx,-gaze-.48*step,t,gesture if event in {"read","catch"} else 0,
          event=="escape",speaking and index%2==1,cast)
    prop_blocks(blocks,plot.prop,px,py,opened,clock)
    if event == "finish" and plot.prop=="cloud":
        blocks.add(.08,.25,.84,1.24,.46,.56,"#8e656b")
        for k in range(7):
            plant(blocks,-.44+k*.165,.84+(k%2)*.11,.23+.49*smooth(p*2.2+k*.03),.50)
    for k in range(12):
        angle = clock*.52 + math.tau*k/12
        radius = .44 + (k%4)*.14
        blocks.add(px+math.cos(angle)*radius,py+.15+math.sin(angle*2)*.23,
                   .42*math.sin(angle),.024,.024,.024,"#f5d2a8",.65)
    return blocks.data, (x,rx), (px,py,0)


def camera(event, p, cast_x, action_x, variant):
    x, rx = cast_x
    center = (x+rx) / 2
    shift = (variant - 1)*.30
    motion = smooth(p)
    if event == "walk":
        return (center+1.35-2.2*motion+shift,3.08,-7.2), (center,.94,.20), 38
    if event == "read":
        return (2.69-1.55*motion+shift,2.08,-4.9), (.32,1.18,0), 42
    if event == "open":
        return (-2.37+1.82*motion+shift,2.71,-5.2+.75*motion), (.0,1.12,.09), 42
    if event == "escape":
        return (center-1.91+2.7*motion+shift,2.00,-5.7-.63*motion), (center+.25,1.20,.05), 51
    if event == "catch":
        return (1.51-3.0*motion+shift,1.64+1.00*motion,-5.2), ((x+rx+action_x)/3,1.02,.15), 43
    return (2.1-1.3*motion+shift,2.6+.32*motion,-6.7+.6*motion), (center,.97,.28), 40


class Renderer:
    def __init__(self, plot, seed, palette):
        self.ctx = gl.create_standalone_context(require=330)
        self.program = self.ctx.program(vertex_shader=VERTEX,fragment_shader=FRAGMENT)
        self.depth = self.ctx.program(vertex_shader=DEPTH_VERTEX,fragment_shader="#version 330\nvoid main(){}")
        geometry = self.ctx.buffer(cube_vertices().tobytes())
        self.instances = self.ctx.buffer(reserve=3000*11*4, dynamic=True)
        self.vao = self.ctx.vertex_array(self.program,[(geometry,"3f 3f","vert","norm"),
                    (self.instances,"3f 3f 4f 1f /i","pos","size","tint","spin")])
        self.depth_vao = self.ctx.vertex_array(self.depth,[(geometry,"3f 12x","vert"),
                          (self.instances,"3f 3f 16x 1f /i","pos","size","spin")])
        self.shadow = self.ctx.depth_texture((1024,1024))
        self.shadow.compare_func = ""
        self.shadow.repeat_x = self.shadow.repeat_y = False
        self.shadow_buffer = self.ctx.framebuffer(depth_attachment=self.shadow)
        self.canvas = self.ctx.simple_framebuffer((WIDTH,HEIGHT),components=3,samples=4)
        self.resolved = self.ctx.simple_framebuffer((WIDTH,HEIGHT),components=3)
        sky_program = self.ctx.program(vertex_shader=SKY_VERTEX,fragment_shader=SKY_FRAGMENT)
        sky_program["sky_tint"] = rgb(palette[1])
        self.sky = self.ctx.vertex_array(sky_program,[])
        light = np.diag([1/10,1/8,-2/34,1.0])
        light[2,3] = -.20
        light_proj = light @ view(KEY,(0,0,0))
        self.program["light_proj"].write(matrix_bytes(light_proj))
        self.depth["light_proj"].write(matrix_bytes(light_proj))
        self.program["accent"] = rgb(palette[6])
        self.program["horizon"] = rgb(palette[1])
        self.stage = stage(plot.setting,seed,palette[6])

    def pixels(self, objects, shot_camera, practical):
        eye,target,fov = shot_camera
        data = np.array(self.stage+objects,dtype="f4")
        self.instances.write(data.tobytes())
        self.ctx.enable(gl.DEPTH_TEST)
        self.shadow_buffer.use()
        self.shadow_buffer.clear()
        self.depth_vao.render(instances=len(data))
        self.canvas.use()
        self.canvas.clear(0.0,0.0,0.0,1.0)
        self.ctx.disable(gl.DEPTH_TEST)
        self.sky.render(vertices=3)
        self.ctx.enable(gl.DEPTH_TEST)
        self.shadow.use(0)
        self.program["shadow_map"] = 0
        self.program["view_proj"].write(matrix_bytes(projection(fov) @ view(eye,target)))
        self.program["eye"] = eye
        self.program["practical"] = practical
        self.vao.render(instances=len(data))
        self.ctx.copy_framebuffer(self.resolved,self.canvas)
        return self.resolved.read(components=3,alignment=1)

    def close(self):
        self.ctx.release()


def render_motion(renderer, tool, output, plot, cast, variant, index, duration, elapsed, cues):
    filters = "vflip,scale=1280:720:flags=bicubic"
    if index == 0:
        filters += ",fade=t=in:d=0.25"
    if index == len(plot.events) - 1:
        filters += f",fade=t=out:st={duration-0.60}:d=0.60"
    event = plot.events[index]

    def draw(t):
        speaking = any(start <= t < end for start, end, _ in cues)
        objects, actors, practical = frame_objects(plot, cast, event, index, t, duration, elapsed+t, speaking)
        return renderer.pixels(objects, camera(event, t/duration, actors, practical[0], variant), practical)

    encode_frames(tool, output, duration, draw, filters)


def encode_frames(tool, output, duration, draw, filters="vflip,scale=1280:720:flags=bicubic"):
    command = [tool,"-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24",
               "-s",f"{WIDTH}x{HEIGHT}","-r",str(FPS),"-i","pipe:0","-vf",
               filters,"-an","-c:v","libx264","-threads","4",
               "-preset","veryfast","-pix_fmt","yuv420p",str(output)]
    with (output.parent / "motion.log").open("w+b") as errors:
        with subprocess.Popen(command,stdin=subprocess.PIPE,stderr=errors) as encoder:
            try:
                for frame in range(duration*FPS):
                    encoder.stdin.write(draw(frame / FPS))
            except BrokenPipeError:
                pass
            finally:
                encoder.stdin.close()
            if encoder.wait():
                errors.seek(0)
                raise RuntimeError(errors.read().decode("utf-8","replace"))
