/**
 * Chinese copy for the whole workbench.
 *
 * The shipped glTF metadata is authored in English by the Python modeller, so the
 * viewer translates by exact string or by structural pattern (deck-prefixed labels
 * and descriptions). Anything already Chinese passes through untouched, which keeps
 * this layer valid once the modeller emits Chinese natively.
 */

const SYSTEM_NAMES = {
  SYS_HULL: '主承力结构',
  SYS_COMMAND: '01 甲板 · 指挥与导航',
  SYS_OPERATIONS: '02 甲板 · 运作与科学',
  SYS_HABITAT: '03 甲板 · 居住与生命保障',
  SYS_ENGINEERING: '04 甲板 · 工程与动力',
  SYS_SPINE: '主脊桁架与推进剂',
  SYS_THERMAL: '热辐射系统',
  SYS_CENTRIFUGE: '离心重力环',
  SYS_PROPULSION: '推进系统',
  SYS_SENSORS: '传感与通信',
  SYS_UTILITY: '对接、机库与保障',
};

const DECK_NAMES = {
  '01': '指挥与导航',
  '02': '运作与科学',
  '03': '居住与生命保障',
  '04': '工程与动力',
};

const DECK_COMPONENT_NAMES = {
  'Ceiling Frame & Services': '顶部构架与管线',
  'Deck Plate & Grating': '甲板板与格栅',
  'Hull Band (cutaway)': '船体剖视带',
  'Viewport Band': '舷窗带',
};

const ASSET_CATEGORY_NAMES = {
  'full-ship': '整船',
  deck: '甲板',
  interior: '舱内',
  propulsion: '推进',
};

const ASSET_LABELS = {
  'DSX-01 ISV Kairos Horizon - complete exterior': '整船外观',
  'Deck 01 - Command & Navigation': '01 甲板 · 指挥与导航',
  'Deck 02 - Operations & Science': '02 甲板 · 运作与科学',
  'Deck 03 - Habitat & Life Support': '03 甲板 · 居住与生命保障',
  'Deck 04 - Engineering & Power': '04 甲板 · 工程与动力',
  'Fusion torch drive & propulsion system': '聚变火炬发动机与推进系统',
  'Interior compartment & systems layout': '舱内隔间与系统布置',
};

const MATERIAL_NAMES = {
  CeramicTile: '陶瓷防热瓦',
  CoilCopper: '线圈铜',
  ConsoleBody: '控制台壳体',
  DeckHazard: '甲板警示条',
  DeckPlate: '甲板覆面',
  EngineMetal: '发动机金属',
  FabricBlue: '蓝色织物',
  FabricTeal: '青色织物',
  Glass: '舷窗玻璃',
  GrowLight: '生长灯',
  HullAccent: '船体饰带',
  HullDark: '深色船体',
  HullLight: '浅色船体',
  HullMid: '中性船体',
  HydroGreen: '水培绿',
  InteriorFloor: '舱内地板',
  InteriorTrim: '舱内饰条',
  InteriorWall: '舱内壁面',
  LightStrip: '灯带',
  MedicalWhite: '医疗白',
  NavLightGreen: '导航绿灯',
  NavLightRed: '导航红灯',
  NavLightWhite: '导航白灯',
  PipingSteel: '管路钢',
  PlasmaCore: '等离子体芯',
  RadiatorCool: '冷辐射面板',
  RadiatorHot: '热辐射面板',
  ReactorGlow: '堆体辉光',
  ReactorShield: '堆体屏蔽层',
  RubberBlack: '黑色橡胶',
  ScreenAmber: '琥珀色屏幕',
  ScreenGlow: '屏幕辉光',
  TankSkin: '贮箱外壳',
  TrussMetal: '桁架金属',
  WindowGlow: '舷窗辉光',
};

const PART_LABELS = {
  'Auxiliary Louvre Radiators': '辅助百叶辐射器',
  'Bow Section & Sensor Nose': '前段船体与传感器鼻锥',
  Bridge: '舰桥',
  'Bridge & Command Centre': '舰桥与指挥中心',
  'Bridge Observation Blister': '舰桥观察泡',
  "Captain's Ready Room": '舰长起居室',
  'Centrifuge Habitat Ring R-1': '离心居住环 R-1',
  'Communications Vault': '通信防护舱',
  'Crew Quarters': '船员舱室',
  'Docking Collars (x4)': '对接环（4 组）',
  'Dorsal Spine Conduit': '背侧脊管',
  'Drive Control & Electronics Bay': '发动机控制与电子舱',
  'EVA Airlock & Suit Room': '出舱气闸与航天服室',
  'EVA Services & Maintenance Access': '出舱保障与检修通道',
  'Engine Heat Exchangers & Plumbing': '发动机热交换器与管路',
  'Engineering Core & Reactor Shielding': '工程核心与反应堆屏蔽',
  'Fusion Chamber & Confinement Coils': '聚变室与约束线圈',
  'Gimbal Mount & Thrust Yoke': '万向节座与推力轭架',
  'Hull Plating Strakes & Deck Lines': '船体蒙皮覆条与甲板线',
  'Hull Surface Systems & Greebles': '船体表面设备与细节构件',
  'Hydroponics Bay': '水培舱',
  'Injector Assembly & Fuel Manifold': '喷注器组与燃料歧管',
  'Life Support & Hydroponics Plant': '生命保障与水培装置',
  'Machine Shop': '机械车间',
  'Machine Shop & Stores': '机械车间与物料库',
  'Magnetic Nozzle & Exhaust Bell': '磁喷嘴与扩张段',
  'Main Engineering': '主工程舱',
  'Main Fusion Torch Nozzles (x3)': '主聚变火炬喷管（3 台）',
  'Main High-Gain Antenna (15 m)': '主高增益天线（15 m）',
  'Main Spine Truss': '主脊桁架',
  'Maneuvering Thruster Pod (detail)': '姿态推力舱（细节）',
  'Maneuvering Thruster Pods (x6)': '姿态推力舱（6 组）',
  'Medical Bay': '医疗舱',
  'Mission Operations Centre': '任务运行中心',
  'Navigation & Flight Control': '导航与飞行控制',
  'Navigation & Strobe Lights': '航行灯与闪光灯',
  'Pressure Hull - Habitable Block': '耐压壳体 — 居住段',
  'Primary Radiator Wings': '主辐射翼',
  'Propellant Handling': '推进剂转运',
  'Propellant Tank Clusters': '推进剂贮箱组',
  'Reactor Shielding & Louvres': '反应堆屏蔽与百叶',
  'Ring Spokes & Bearing Hub': '环辐条与轴承毂',
  'Science Laboratory': '科学实验室',
  'Segmented Armour Belt': '分段式装甲带',
  'Sensor Arrays & Interferometer Booms': '传感器阵与干涉仪桁杆',
  'Service Corridor & Access Spurs': '服务走廊与支线通道',
  'Service Platform & Scale Figure': '检修平台与比例人形',
  'Shuttle Hangar': '穿梭机库',
  'Shuttle Hangar Ventral Doors': '机库腹舱门',
  'Stores & Cryo Bay': '物料与低温舱',
  'Thermal Management Fins': '热管理鳍片',
  'Thrust Structure & Gimbal Mounts': '推力结构与万向节座',
  'Transverse Frame Rings': '横向框架环',
  'Turbopumps & Propellant Feed': '涡轮泵与推进剂供给',
  'Wardroom & Galley': '军官餐厅与厨房',
  'Whipple Meteoroid Shield': '微流星防护盾',
};

const DESCRIPTIONS = {
  '12 m magnetically confined fusion chamber, six superconducting coil pairs, borated composite shielding and lithium cooling jacket.':
    '直径 12 m 磁约束聚变室，六对超导线圈，含硼复合屏蔽层与锂冷却夹套。',
  '15 m parabolic high-gain antenna on a two-axis gimbal, providing the primary laser/RF link back to the inner system.':
    '15 m 抛物面高增益天线，装于两轴万向节，提供返回内太阳系的主激光/射频链路。',
  '178 m Warren lattice spine carrying propellant, radiators, the centrifuge bearing and the main thrust load path into the hull.':
    '178 m 沃伦式格构主脊，承载推进剂、辐射器、离心环轴承，并把主推力载荷传入船体。',
  '359 m pressurised service corridor with access spurs, cable raceways and compartment status panels.':
    '359 m 加压服务走廊，含支线通道、电缆线槽与舱室状态面板。',
  '37-element coaxial injector head feeding the D/He-3 manifold at 42 MPa, with a pilot plasma torch for restart.':
    '37 单元同轴喷注头，以 42 MPa 向氘/氦-3 歧管供料，配有用于复点的引燃等离子火炬。',
  '450 mm composite deck plate with removable gratings, cable trenches and hazard edging.':
    '450 mm 复合甲板板，带可拆卸格栅、电缆沟与危险区镶边。',
  '46 m radius rotating habitat ring at 1.6 rpm providing ~0.13 g for long duration crew health, with 48 illuminated cabins.':
    '半径 46 m 的旋转居住环，以 1.6 转/分提供约 0.13 g 重力，保障长期乘组健康，含 48 间照明舱室。',
  '9-stage magnetic nozzle expanding the plasma from a 2.6 m throat to a 13 m exit, cryostat-cooled to 20 K.':
    '9 级磁喷嘴，把等离子体从 2.6 m 喉部扩张至 13 m 出口，低温容器冷却至 20 K。',
  'Armoured engineering core: reactor shielding drum, power conditioning and the thrust structure that carries the main drive.':
    '装甲化工程核心：反应堆屏蔽鼓、电力调节装置，以及承载主发动机的推力结构。',
  'Armoured observation blister above the bridge with 220 degree glazing, electrochromic shutters and the manual helm position.':
    '舰桥上方的装甲观察泡，220 度观景玻璃，电致变色快门，并设手动操舵位。',
  'Borated composite shielding drum around the fusion core with emergency dump louvres and maintenance access ports.':
    '聚变核心外围的含硼复合屏蔽鼓，带应急泄放百叶与检修进入口。',
  'Double-height bay for two survey shuttles, overhead crane rail, drone charging racks and ventral doors.':
    '双层净高的机库舱段，可停放两架勘测穿梭机，配桥式吊车轨道、无人机充电架与腹舱门。',
  'Eight navigation workstations, the star-chart holo-table and redundant flight computers on shock-isolated racks.':
    '八个导航工作站、星图全息桌，以及装在隔振机架上的冗余飞行计算机。',
  'External cable and coolant raceway running the length of the habitable block, with maintenance crawlers every 20 m.':
    '沿居住段全长敷设的外部电缆与冷却剂线槽，每 20 m 设检修爬行器。',
  'External hand-rails, two EVA airlocks, tether points and the ventral maintenance crawler rail.':
    '外部扶手、两道出舱气闸、系缆点与腹侧检修爬行器轨道。',
  'External hull plating seams marking each pressure deck, plus the directorate livery stripe and registry markings.':
    '标示各承压甲板的外部船体蒙皮接缝，另有局属涂装饰带与注册标识。',
  'Exposed transverse frames every 7 m: eight-member belt beams standing proud of the plating with bolted corner gussets.':
    '每 7 m 一道外露横向框架：八段环梁凸出蒙皮，角部以螺栓固定加强肘板。',
  'Segmented ceramic-composite armour over both flanks and the dorsal spine, with bolted plate edges, hazard markings and offset seams.':
    '两舷与背脊覆盖的分段陶瓷复合装甲，带螺栓压边、危险标识与错缝排布。',
  'Vents, junction boxes, cable ducts, inspection hatches, sensor pods and cargo pods fitted tight to the outer skin.':
    '紧贴外壳的通风口、接线箱、电缆槽、检修口、传感器吊舱与货舱吊舱。',
  'External life support heat exchangers, CO2 scrubber intakes and the illuminated hydroponics growth racks visible through the hull glazing.':
    '外部生命保障热交换器、二氧化碳洗涤进气口，以及透过船体玻璃可见的水培生长架照明。',
  'Five cryogenic tanks: two forward 9.5 m spheres for deuterium/helium-3 and three aft 8 m tanks for reaction mass, with insulated feed lines.':
    '五只低温贮箱：前部两只 9.5 m 球形氘/氦-3 箱，后部三只 8 m 工作质量箱，配绝热供料管线。',
  'Five growth racks under magenta LED arrays, nutrient loop piping and the atmosphere scrubber interface.':
    '五组生长架置于品红发光二极管阵列下，配营养液循环管路与大气洗涤接口。',
  'Four auxiliary dishes, a 68 m long baseline optical interferometer and the astronavigation mast for pulsar-referenced positioning.':
    '四面副反射面天线、68 m 长基线光学干涉仪，以及用于脉冲星定位的航天导航桅。',
  'Four deployable droplet-free radiator wings, 40 m x 27 m each, rejecting 940 MW of waste heat. Forward pair runs hot (reactor loop), aft pair runs cool (electronics and habitat loop).':
    '四面可展开无液滴辐射翼，单面 40 m × 27 m，排散 940 MW 废热。前一对走高温的堆回路，后一对走低温的电子与居住回路。',
  'Four turbopumps (two main, two pilot) drawing from the aft tank cluster, with insulated feed lines and burst discs.':
    '四台涡轮泵（两台主泵、两台引燃泵）从后部贮箱组抽吸，配绝热供料管线与爆破片。',
  'Four-deck pressurised habitable block, 140 m long, chamfered hexagonal cross-section 64 m x 28 m. Whipple shield and meteoroid bumper forward.':
    '四层加压居住段，长 140 m，倒角六边形截面 64 m × 28 m。前部为微流星防护盾与缓冲板。',
  'Galley counter with food printer, three mess tables, wardroom display and the medical cabinet station.':
    '带食物打印机的配餐台、三张餐桌、军官室显示屏与药品柜工作站。',
  'Laser/RF transceiver racks, the 40 kW transmitter coil and the encrypted data core.':
    '激光/射频收发机架、40 kW 发射线圈与加密数据核心。',
  'Lithium heat pipes and ammonia exchangers moving drive waste heat to the aft radiator loop, with emergency dump valves.':
    '锂热管与氨换热器把发动机废热送至后部辐射回路，配应急泄放阀。',
  'Maintenance walkway with hand-rails, ladder and a 1.8 m reference figure for scale.':
    '带扶手与梯子的检修走道，并设 1.8 m 参照人形用于比对尺度。',
  'Nine operator positions, surface operations wall display and the survey drone control bench.':
    '九个操作员席位、地表作业墙面显示屏与勘测无人机控制台。',
  'Port red, starboard green and white anti-collision strobes at the bow, stern, ring apex and radiator tips.':
    '左舷红灯、右舷绿灯，艏部、艉部、环顶与辐射翼尖设白色防撞闪光灯。',
  'Primary flight deck: five helm/console positions, two command chairs, tactical holo-table and the aft mission display wall.':
    '主飞行甲板：五个操舵与控制台位、两张指挥座椅、战术全息桌与后部任务显示墙。',
  'Primary thrust structure transferring 3.45 MN of continuous thrust into the spine, with three gimbal rings and 18 tension struts.':
    '主推力结构，把 3.45 MN 持续推力传入主脊，含三个万向环与 18 根受拉杆。',
  'Reactor control drum, four turbopumps, drive console row and the overhead coolant raceway.':
    '反应堆控制鼓、四台涡轮泵、发动机控制台列与顶部冷却剂线槽。',
  'Redundant drive controllers, ignition sequencer, sensor harness and the local maintenance console.':
    '冗余发动机控制器、点火时序器、传感器线束与就地检修控制台。',
  'Secondary louvre radiators for burst heat rejection during manoeuvres.':
    '机动期间用于短时排热的辅助百叶辐射器。',
  'Single reaction-control pod: 60 kN thrust, twin turbopumps, regeneratively cooled bell and hazard-marked service panel.':
    '单台姿控推力舱：60 kN 推力、双涡轮泵、再生冷却喷管，服务面板带危险标识。',
  'Six RCS pods (four stern, two bow) for attitude control, docking and station keeping, each with redundant injectors.':
    '六台姿控推力舱（艉四、艏二），用于姿态控制、对接与定点保持，各配冗余喷注器。',
  'Six pressurised spokes with elevator cars and the superconducting magnetic bearing that decouples the ring from the spine.':
    '六根加压辐条含升降舱，超导磁轴承把环体与主脊解耦。',
  'Stand-off bumper shield ahead of the habitable block, spaced 3 m from the pressure hull to break up hypervelocity particles.':
    '居住段前方的间隔缓冲盾，与耐压壳体相距 3 m，用于击散超高速粒子。',
  'Tapered bow housing the long baseline sensor suite, astronavigation package and the Whipple shield stand-off structure.':
    '锥形艏段，容纳长基线传感器组、航天导航组件与微流星防护盾的间隔支撑结构。',
  'Three 3.45 MN fusion torch drives with 7-stage superconducting magnetic nozzles, gimbal mounted +/- 6 degrees for thrust vectoring.':
    '三台 3.45 MN 聚变火炬发动机，配 7 级超导磁喷嘴，万向安装可 ±6 度偏转实现推力矢量。',
  'Three auto-doc berths, diagnostic cabinet, isolation pod and the sickbay console.':
    '三个自主诊疗铺位、诊断柜、隔离舱与医务台。',
  'Three work benches, spare-parts racks, containerised stores and the heavy maintenance hoist.':
    '三个工作台、备件架、集装箱化物料与重型检修吊车。',
  'Translucent cutaway of the pressure hull for this deck. Toggle it in the viewer to look inside the fitted compartments.':
    '本甲板耐压壳体的半透明剖视。在查看器中切换，可观察已装配的舱室内部。',
  'Transverse deck beams, longitudinal girders and the service raceway carrying power, data and atmosphere ducts above the ceiling.':
    '横向甲板梁、纵向龙骨，以及天花板上方承载电力、数据与大气管道的服务线槽。',
  'Twelve berths in two tiers, personal storage, exercise equipment and the inboard EVA airlock.':
    '双层十二个铺位、个人储物、锻炼器械与内侧出舱气闸。',
  'Twelve lithium heat-pipe fin pairs dumping drive waste heat into the aft radiator loop.':
    '十二对锂热管鳍片，把发动机废热排入后部辐射回路。',
  'Two axial and two lateral universal docking collars for tenders, surface landers and station transfer.':
    '两个轴向与两个横向通用对接环，用于保障船、地表着陆器与站点转运。',
  'Two-axis gimbal carrying +/- 6 degrees of thrust vectoring, with four electro-hydrostatic actuators and a failsafe lock-out ring.':
    '两轴万向节提供 ±6 度推力矢量，配四台电静液作动器与故障安全锁定环。',
  'Two-chamber EVA airlock with six suit hard-points, suit purge controls and the dust mitigation shower.':
    '双腔出舱气闸，六个航天服硬挂点、航天服吹除控制与除尘淋洗。',
  'Two-leaf ventral hangar doors, 54 m x 30 m clear opening, with hydraulic rams and a magnetic capture rail for shuttle recovery.':
    '双叶腹侧机库门，净开口 54 m × 30 m，配液压作动筒与用于穿梭机回收的磁捕获轨。',
  'Wet and dry benches, sample containment glove-box, spectroscopy rack and the geology analysis bay.':
    '湿式与干式工作台、样品隔离手套箱、光谱仪架与地质分析工位。',
};

const PRESET_LABELS = {
  hero: '总览',
  starboard: '右舷',
  bow: '艏部',
  stern: '艉部',
  top: '俯视',
  ring: '重力环',
};

const UI = {
  title: 'DSX-01「凯洛斯地平线」号 — 三维工作台',
  tagline: '深空探索飞船 · 交互式三维工作台',
  'panel.assets': '模型',
  'panel.systems': '系统',
  'panel.view': '视图',
  'control.explode': '分解',
  'control.wireframe': '线框',
  'control.grid': '网格',
  'control.autoRotate': '自动旋转',
  'control.spinRing': '转动重力环',
  'control.starfield': '星空',
  'control.cutaway': '剖视模式',
  'hud.hint': '拖动旋转 · 滚轮缩放 · 点击部件查看详情',
  'hud.triangles': '三角面',
  'hud.meshes': '网格',
  'hud.materials': '材质',
  'info.field.partId': '部件编号',
  'info.field.system': '所属系统',
  'info.field.deck': '所在甲板',
  'info.field.triangles': '三角面数',
  'info.field.size': '外形尺寸（m）',
  'info.empty': '未选中部件',
  'info.close': '关闭',
  loading: '模型加载中…',
  loadError: '模型加载失败',
  unknownComponent: '未命名部件',
  notApplicable: '暂无',
};

const DECK_LABEL = /^Deck (0\d) - (.+) - (.+)$/;
const DECK_DESCRIPTION = /^(.+) - Deck (0\d) - (.+)\.$/;
const VIEWPORT_DESCRIPTION =
  /^Illuminated viewport band and radiation shutters for deck (0\d) - (.+)\.$/;
const DECK_NAME_LOOKUP = {
  'Command & Navigation': '01',
  'Operations & Science': '02',
  'Habitat & Life Support': '03',
  'Engineering & Power': '04',
};

function deckName(code, fallback) {
  return DECK_NAMES[code] ?? DECK_NAME_LOOKUP[fallback] ?? fallback;
}

/** Deck-scoped labels such as "Deck 03 - Habitat & Life Support - Viewport Band". */
function patternedPartLabel(text) {
  const match = DECK_LABEL.exec(text);
  if (!match) return null;
  const [, code, deck, component] = match;
  const parts = [deckName(code, deck), DECK_COMPONENT_NAMES[component]];
  return parts.every(Boolean) ? `${code} 甲板 · ${parts[0]} — ${parts[1]}` : null;
}

function patternedDescription(text) {
  const viewport = VIEWPORT_DESCRIPTION.exec(text);
  if (viewport) {
    const [, code, deck] = viewport;
    const name = deckName(code, deck);
    return name ? `${code} 甲板 · ${name}的照明舷窗带与防辐射快门。` : null;
  }
  const match = DECK_DESCRIPTION.exec(text);
  if (!match) return null;
  const [, subject, code, deck] = match;
  const name = deckName(code, deck);
  const translated = PART_LABELS[subject];
  return name && translated ? `${translated} — ${code} 甲板 · ${name}。` : null;
}

function pick(table, text) {
  return Object.prototype.hasOwnProperty.call(table, text) ? table[text] : null;
}

export function translateSystem(id) {
  return pick(SYSTEM_NAMES, id) ?? id;
}

export function translateAssetLabel(label) {
  return pick(ASSET_LABELS, label) ?? label;
}

export function translateAssetCategory(category) {
  return pick(ASSET_CATEGORY_NAMES, category) ?? category;
}

export function translatePart(label) {
  if (!label) return '';
  return pick(PART_LABELS, label) ?? patternedPartLabel(label) ?? label;
}

export function translateDescription(description) {
  if (!description) return '';
  return pick(DESCRIPTIONS, description) ?? patternedDescription(description) ?? description;
}

export function translateMaterial(name) {
  return pick(MATERIAL_NAMES, name) ?? name;
}

export function deckLabel(index) {
  const code = String(index).padStart(2, '0');
  return pick(DECK_NAMES, code) ?? UI.notApplicable;
}

export function presetLabel(name) {
  return pick(PRESET_LABELS, name) ?? name;
}

export function ui(key, params) {
  const value = pick(UI, key);
  if (value == null) return key;
  if (!params) return value;
  return value.replace(/\{(\w+)\}/g, (whole, name) =>
    Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : whole,
  );
}
