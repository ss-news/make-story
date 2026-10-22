import bpy, math, random, os
from mathutils import Vector
from math import sin, cos, pi

OUT = '/Users/thang/Documents/video/outputs/ong-lao-chan-trau'
os.makedirs(OUT, exist_ok=True)
scene = bpy.data.scenes.new('Ong lao chan trau | Low poly')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
cols = {}
for name in ['01_Ong_lao', '02_Trau', '03_Dong_co', '04_Studio']:
    cols[name] = bpy.data.collections.new(name)
    scene.collection.children.link(cols[name])
current = cols['01_Ong_lao']
random.seed(24)

def mat(name, color, rough=0.85):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = rough
    return m

skin = mat('Da ram nang', (.49,.285,.145))
skin_hi = mat('Da sang', (.62,.385,.21))
shirt = mat('Ao nau', (.17,.075,.027))
shirt_hi = mat('Nep ao nau', (.245,.125,.047))
pants = mat('Quan than', (.105,.115,.108))
cuff = mat('Gau quan xan', (.17,.18,.153))
straw = mat('Non la kho', (.63,.43,.19))
straw_hi = mat('Non la sang', (.76,.57,.29))
straw_dark = mat('Vanh nan non', (.37,.235,.095))
white = mat('Rau toc bac', (.72,.72,.64))
eye = mat('Mat den', (.024,.018,.012), .3)
eye_white = mat('Long mat', (.67,.62,.48))
buff = mat('Trau xam', (.075,.092,.083))
buff_hi = mat('Trau mat sang', (.105,.125,.109))
muzzle = mat('Mom trau', (.052,.066,.058))
horn = mat('Sung trau', (.38,.35,.265))
horn_tip = mat('Dau sung', (.13,.125,.10))
hoof = mat('Mong trau', (.065,.07,.065))
ear = mat('Long tai', (.28,.21,.16))
rope = mat('Day thung', (.57,.38,.15))
grass_mats = [mat('Co %d'%i,c) for i,c in enumerate([(.27,.34,.105),(.37,.43,.14),(.47,.49,.20),(.21,.29,.085)])]
soil = mat('Dat bo ruong', (.25,.19,.11))
rock = mat('Da', (.38,.37,.29))
floor = mat('Nen studio', (.68,.63,.52))

def link(o, name, material=None):
    o.name = name
    for c in list(o.users_collection): c.objects.unlink(o)
    current.objects.link(o)
    if material: o.data.materials.append(material)
    return o

def mesh(name, verts, faces, material):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    current.objects.link(ob)
    if material: me.materials.append(material)
    return ob

def ico(name, pos, scale, material, sub=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1, location=pos)
    ob=link(bpy.context.object, name, material)
    ob.scale=scale
    return ob

def uv(name, pos, scale, material, seg=12, rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1, location=pos)
    ob=link(bpy.context.object,name,material)
    ob.scale=scale
    return ob

def tube(name, points, radii, material, sides=7):
    verts=[]
    for i,p in enumerate(points):
        p=Vector(p)
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(i-1,0)])
        tangent.normalize()
        ref=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
        u=tangent.cross(ref).normalized(); v=tangent.cross(u).normalized()
        for j in range(sides):
            a=2*pi*j/sides
            verts.append(tuple(p+radii[i]*(u*cos(a)+v*sin(a))))
    faces=[tuple(range(sides-1,-1,-1))]
    for i in range(len(points)-1):
        for j in range(sides):
            a=i*sides+j; b=i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces.append(tuple((len(points)-1)*sides+j for j in range(sides)))
    return mesh(name,verts,faces,material)

def ringbody(name, rings, material, sides=10):
    verts=[]
    for x,y,z,rx,ry in rings:
        for j in range(sides):
            a=2*pi*j/sides
            verts.append((x+rx*cos(a),y+ry*sin(a),z))
    faces=[tuple(range(sides-1,-1,-1))]
    for k in range(len(rings)-1):
        for j in range(sides):
            a=k*sides+j; b=k*sides+(j+1)%sides
            faces.extend([(a,b,b+sides),(a,b+sides,a+sides)])
    faces.append(tuple((len(rings)-1)*sides+j for j in range(sides)))
    return mesh(name,verts,faces,material)

def loop(name, center, rx, ry, z, material, radius=.01, n=32):
    return tube(name,[(center[0]+rx*cos(2*pi*i/n),center[1]+ry*sin(2*pi*i/n),z) for i in range(n+1)],[radius]*(n+1),material,5)

# Elderly Vietnamese herder. Front is -Y.
X=-1.25
ringbody('Ao | than va vat ao',[(X,0,1.05,.255,.17),(X,0,1.24,.27,.18),(X,.035,1.62,.25,.16),(X,.025,1.83,.30,.16),(X,.015,1.9,.17,.13)],shirt)
tube('Co',[(X,0,1.8),(X,-.015,2.04)],[.10,.085],skin,9)
for s in [-1,1]:
    x=X+s*.14
    ringbody('Ong quan '+str(s),[(x,0,.44,.105,.105),(x,.025,.62,.13,.125),(x,.025,1.13,.145,.145)],pants,8)
    ringbody('Gau quan xan '+str(s),[(x,-.005,.43,.12,.12),(x,-.005,.53,.125,.125)],cuff,8)
    tube('Cang chan '+str(s),[(x,0,.47),(x,-.045,.17)],[.065,.057],skin,7)
    uv('Ban chan '+str(s),(x,-.105,.115),(.09,.18,.065),skin,10,6)
    uv('De dep '+str(s),(x,-.105,.065),(.10,.19,.028),straw_dark,10,4)
    tube('Quai dep '+str(s),[(x-.075,-.08,.13),(x,-.14,.16),(x+.075,-.08,.13)],[.018]*3,shirt_hi,5)
    # Sleeves curve down from shoulders.
    shoulder=(X+s*.27,.015,1.79)
    ico('Vai ao noi kin '+str(s),(X+s*.27,.015,1.77),(.15,.145,.145),shirt,2)
    elbow=(X+s*.36,-.015,1.43)
    wrist=(X+s*.35,-.13,1.13) if s<0 else (X+.44,-.31,1.25)
    tube('Tay ao '+str(s),[shoulder,elbow,tuple(Vector(elbow).lerp(Vector(wrist),.18))],[.135,.105,.105],shirt,8)
    tube('Nep tay ao '+str(s),[elbow,tuple(Vector(elbow).lerp(Vector(wrist),.18))],[.112,.11],shirt_hi,8)
    tube('Canh tay '+str(s),[tuple(Vector(elbow).lerp(Vector(wrist),.15)),wrist],[.068,.047],skin,8)
    hand=Vector(wrist)+Vector((0,-.01,-.08))
    uv('Ban tay '+str(s),hand,(.065,.052,.095),skin_hi,8,6)
    for j in range(4):
        p=hand+Vector(((j-1.5)*.026,-.025,-.045))
        tube('Ngon tay %s %s'%(s,j),[p,p+Vector((.005,-.025,-.075)),p+Vector((.006,.002,-.09))],[.015,.013,.008],skin,5)
    tube('Ngon cai '+str(s),[hand+Vector((-.05,0,.03)),hand+Vector((-.075,-.045,-.02))],[.025,.017],skin,6)

# Front seam, fabric folds and toggle buttons.
tube('Nep ao giua',[(X,-.184,1.07),(X,-.189,1.42),(X,-.16,1.77)],[.014,.013,.011],shirt_hi,4)
for z in [1.23,1.41,1.59,1.74]:
    tube('Khuy ao',[(X-.045,-.19,z),(X+.045,-.19,z)],[.009,.009],straw_dark,5)
    ico('Nut ao',(X+.043,-.2,z),(.014,.012,.014),straw,1)
for s in [-1,1]:
    tube('Co ao '+str(s),[(X+s*.12,-.09,1.91),(X+s*.075,-.175,1.79),(X,-.17,1.84)],[.025,.022,.012],shirt_hi,5)
    tube('Nep vai '+str(s),[(X+s*.22,-.11,1.68),(X+s*.18,-.17,1.5),(X+s*.22,-.17,1.31)],[.012,.008,.002],shirt_hi,3)

uv('Dau | guong mat ong lao',(X,-.045,2.145),(.172,.153,.235),skin_hi,12,9)
for s in [-1,1]:
    uv('Tai '+str(s),(X+s*.177,-.025,2.15),(.044,.033,.075),skin,8,6)
    ico('Go ma '+str(s),(X+s*.105,-.166,2.09),(.073,.045,.065),skin,1)
    uv('Long mat '+str(s),(X+s*.069,-.181,2.185),(.044,.013,.023),eye_white,8,6)
    uv('Mat '+str(s),(X+s*.068,-.194,2.184),(.018,.009,.019),eye,8,6)
    ico('Anh mat '+str(s),(X+s*.063,-.203,2.191),(.005,.003,.005),white,1)
    tube('Long may bac '+str(s),[(X+s*.026,-.192,2.227),(X+s*.068,-.196,2.239),(X+s*.117,-.174,2.227)],[.012,.017,.008],white,5)
    tube('Nep mat '+str(s),[(X+s*.10,-.179,2.162),(X+s*.14,-.153,2.148)],[.006,.003],skin,3)
    tube('Toc mai '+str(s),[(X+s*.155,-.006,2.27),(X+s*.166,-.038,2.13)],[.035,.022],white,5)
ico('Song mui',(X,-.204,2.14),(.037,.054,.085),skin_hi,2)
ico('Dau mui',(X,-.242,2.115),(.045,.028,.027),skin,1)
tube('Mieng cuoi',[(X-.065,-.184,2.047),(X,-.205,2.033),(X+.065,-.184,2.047)],[.006,.009,.006],shirt,5)
for s in [-1,1]:
    tube('Ria bac '+str(s),[(X,-.214,2.077),(X+s*.045,-.213,2.064),(X+s*.085,-.179,2.054)],[.022,.023,.004],white,5)
ringbody('Rau cam bac',[(X,-.118,1.923,.012,.013),(X,-.147,1.985,.047,.028),(X,-.163,2.038,.073,.038)],white,7)

# Authentic shallow Vietnamese conical hat with radial panels, rim and chin strap.
hat_z=2.40
verts=[(X,.015,hat_z+.18)]
N=20
for j in range(N):
    a=2*pi*j/N
    verts.append((X+.49*cos(a),.015+.49*sin(a),hat_z-.105))
hat=mesh('Non la | 20 mui',verts,[(0,j+1,(j+1)%N+1) for j in range(N)],straw)
hat.data.materials.append(straw_hi)
for p in hat.data.polygons: p.material_index = 1 if p.index%4 in [0,1] else 0
loop('Vanh non',(X,.015),.49,.49,hat_z-.105,straw_dark,.014,40)
for r in [.24,.37]:
    loop('Nan non',(X,.015),r,r,hat_z+.18-(r/.49)*.285,straw_hi,.005,40)
tube('Quai non',[(X-.19,.015,2.30),(X-.16,-.035,2.03),(X,-.07,1.96),(X+.16,-.035,2.03),(X+.19,.015,2.30)],[.009]*5,shirt,5)

# Water buffalo: long barrel, lowered neck, broad forehead and muzzle.
current=cols['02_Trau']
B=.72
uv('Than trau',(B,.65,1.25),(.64,1.04,.63),buff,14,9)
uv('Vai trau',(B,-.05,1.29),(.53,.56,.61),buff,12,8)
uv('Co trau',(B,-.42,1.27),(.40,.51,.46),buff,12,7)
uv('Dau trau',(B,-.73,1.38),(.36,.37,.40),buff_hi,12,8)
uv('Tran trau',(B,-.65,1.62),(.37,.27,.24),buff,10,6)
uv('Mom rong',(B,-1.035,1.20),(.32,.22,.21),muzzle,12,7)
uv('Ham duoi',(B,-.99,1.07),(.25,.19,.075),buff_hi,10,5)
for s in [-1,1]:
    uv('Lo mui '+str(s),(B+s*.145,-1.233,1.25),(.061,.016,.037),eye,9,5)
    uv('Mat trau vien '+str(s),(B+s*.273,-.932,1.52),(.075,.035,.068),muzzle,10,6)
    uv('Mat trau '+str(s),(B+s*.279,-.957,1.526),(.042,.014,.044),eye,10,6)
    ico('Diem sang mat trau '+str(s),(B+s*.27,-.971,1.542),(.011,.004,.012),eye_white,1)
    tube('Mi mat trau '+str(s),[(B+s*.22,-.958,1.56),(B+s*.28,-.958,1.589),(B+s*.333,-.91,1.562)],[.018,.023,.012],buff,6)
    # Pointed lateral ears.
    earverts=[(B+s*.30,-.64,1.59),(B+s*.51,-.64,1.65),(B+s*.76,-.59,1.49),(B+s*.54,-.72,1.43),(B+s*.34,-.69,1.47),(B+s*.50,-.76,1.53)]
    mesh('Tai trau '+str(s),earverts,[(0,1,5),(1,2,5),(2,3,5),(3,4,5),(4,0,5),(0,4,3,2,1)],buff)
    mesh('Long tai trau '+str(s),[(B+s*.37,-.716,1.54),(B+s*.66,-.65,1.50),(B+s*.52,-.756,1.47)],[(0,1,2)],ear)
    pts=[(B+s*.29,-.56,1.74),(B+s*.46,-.54,1.79),(B+s*.69,-.49,1.82),(B+s*.89,-.40,1.91),(B+s*1.01,-.31,2.09),(B+s*1.00,-.28,2.25),(B+s*.91,-.32,2.38)]
    h=tube('Sung cong '+str(s),pts,[.125,.12,.104,.082,.055,.03,.002],horn,7)
    h.data.materials.append(horn_tip)
    for p in h.data.polygons:
        if p.index>29: p.material_index=1
    for y in [-.03,1.25]:
        x=B+s*.42
        ico('Bap chan trau %s %s'%(s,y),(B+s*.40,y,1.05),(.19,.23,.33),buff,2)
        tube('Chan trau %s %s'%(s,y),[(x,y,1.27),(x+s*.015,y+.055,.68),(x+s*.025,y-.015,.23)],[.16,.105,.078],buff,7)
        ico('Khop chan',(x+s*.015,y+.055,.64),(.115,.115,.13),buff_hi,1)
        for t in [-1,1]:
            uv('Mong che doi',(x+s*.025+t*.052,y-.055,.145),(.048,.14,.10),hoof,8,5)
tube('Duoi trau',[(B,1.58,1.47),(B+.13,1.79,1.22),(B+.16,1.91,.79),(B+.26,1.89,.60)],[.048,.033,.021,.015],buff,6)
ico('Chum long duoi',(B+.27,1.90,.55),(.064,.055,.14),muzzle,1)

# Halter around muzzle and cheeks; loose rope terminates at the man's right hand.
loop('Vong day mom',(B,-.96),.325,.205,1.245,rope,.016,24)
for s in [-1,1]:
    tube('Day ma '+str(s),[(B+s*.29,-1.035,1.25),(B+s*.34,-.76,1.46),(B+s*.30,-.56,1.69)],[.014]*3,rope,5)
pts=[(-.80,-.34,1.20),(-.62,-.49,1.08),(-.40,-.65,.99),(-.17,-.83,.98),(.08,-.99,1.07),(B-.30,-1.07,1.25)]
tube('Day dat trau',pts,[.018]*len(pts),rope,6)
pts=[]
for i in range(33):
    a=2*pi*i/32
    pts.append((-.80+.075*cos(a),-.355,.99+.18*sin(a)))
tube('Vong day trong tay',pts,[.014]*len(pts),rope,5)

# Low-poly landscape plinth with triangulated irregular surface.
current=cols['03_Dong_co']
N=40
verts=[(-.08,.30,.015),(-.08,.30,.10)]
for j in range(N):
    a=2*pi*j/N; f=random.uniform(.97,1.03)
    verts.append((-.08+2.28*cos(a)*f,.30+2.03*sin(a)*f,.025))
for j in range(N):
    a=2*pi*j/N; f=random.uniform(.97,1.03)
    verts.append((-.08+2.28*cos(a)*f,.30+2.03*sin(a)*f,-.16))
faces=[]
for j in range(N):
    faces.append((1,2+j,2+(j+1)%N))
    faces.append((2+j,2+N+j,2+N+(j+1)%N,2+(j+1)%N))
base=mesh('Be dat da giac',verts,faces,grass_mats[0])
for m in grass_mats[1:]+[soil]: base.data.materials.append(m)
for p in base.data.polygons: p.material_index=random.randrange(4) if p.index%2==0 else 4

def tuft(x,y,z=.04):
    verts=[]; faces=[]
    for k in range(random.randint(3,6)):
        a=random.uniform(0,2*pi); w=random.uniform(.015,.027); h=random.uniform(.09,.23)
        dx,dy=cos(a),sin(a); start=len(verts)
        verts.extend([(x-w*dy,y+w*dx,z),(x+w*dy,y-w*dx,z),(x+dx*.06,y+dy*.06,z+h)])
        faces.append((start,start+1,start+2))
    return mesh('Touffe co',verts,faces,random.choice(grass_mats))
for i in range(115):
    x=random.uniform(-2.22,2.10); y=random.uniform(-1.55,2.18)
    if ((x+.08)/2.18)**2+((y-.30)/1.95)**2>1: continue
    if abs(x-X)<.32 and -.35<y<.3: continue
    if abs(x-B)<.65 and -.35<y<1.55: continue
    tuft(x,y)
for x,y,s in [(-1.8,.9,.14),(1.8,.25,.16),(-.3,-1.30,.11),(1.4,1.7,.18),(-1.7,-.8,.08)]:
    ico('Da dong',(x,y,.045),(s,s*.75,s*.65),rock,1)

current=cols['04_Studio']
bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-.19))
link(bpy.context.object,'Nen studio',floor)
world=bpy.data.worlds.new('Anh sang am')
world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.70,.78,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.5
scene.world=world

def area(name, pos, energy, size, color):
    data=bpy.data.lights.new(name,'AREA'); data.energy=energy; data.shape='DISK'; data.size=size; data.color=color
    ob=bpy.data.objects.new(name,data); current.objects.link(ob); ob.location=pos
    ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
area('Key | mat troi',( -3,-4,7),750,5,(1,.83,.61))
area('Fill',(4,-2,4),450,4,(.73,.84,1))
area('Rim',(1,4,5),850,3,(1,.88,.65))
camdata=bpy.data.cameras.new('Camera Diorama'); cam=bpy.data.objects.new('Camera Diorama',camdata); current.objects.link(cam)
cam.location=(4.5,-8.5,4.0)
cam.rotation_euler=(Vector((-.12,.25,1.03))-cam.location).to_track_quat('-Z','Y').to_euler()
camdata.type='ORTHO'; camdata.ortho_scale=5.35
scene.camera=cam
scene.render.engine='CYCLES'; scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1400; scene.render.resolution_y=1400; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=OUT+'/ong-lao-chan-trau.png'
scene.view_settings.view_transform='AgX'
scene['Description']='Vietnamese elderly buffalo herder - approved low-poly direction. Static editable meshes, no rig.'
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        a.spaces.active.region_3d.view_perspective='CAMERA'
        a.spaces.active.shading.color_type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/ong-lao-chan-trau.blend')
result={'file':bpy.data.filepath,'scene':scene.name,'objects':len(scene.objects),'mesh_faces':sum(len(o.data.polygons) for o in scene.objects if o.type=='MESH')}
