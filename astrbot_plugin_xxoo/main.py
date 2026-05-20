# -*- coding: utf-8 -*-
import asyncio, json, os, threading, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from astrbot.api import logger, AstrBotConfig
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star

PLUGIN_NAME = "astrbot_plugin_xxoo"
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

LOCATIONS = {"bed":{"e":"🛏️","n":"床上"},"couch":{"e":"🛋️","n":"沙发"},"desk":{"e":"💻","n":"书桌"},"bath":{"e":"🚿","n":"浴室"},"wall":{"e":"🧱","n":"靠墙"},"floor":{"e":"🟫","n":"地板"},"window":{"e":"🪟","n":"窗边"},"kitchen":{"e":"🍳","n":"厨房"},"mirror":{"e":"🪞","n":"镜子前"},"car":{"e":"🚗","n":"车里"}}
POSES = {"missionary":{"e":"🙏","n":"传教士"},"doggy":{"e":"🐕","n":"后入"},"cowgirl":{"e":"🤠","n":"女上"},"spoon":{"e":"🥄","n":"侧入"},"standing":{"e":"🧍","n":"站立"},"lap":{"e":"💺","n":"坐姿对面"},"sixtynine":{"e":"🔁","n":"69"},"prone":{"e":"😴","n":"趴着"},"carry":{"e":"🫂","n":"抱着操"},"kneel_pose":{"e":"🧎","n":"跪着"},"reverse_cowgirl":{"e":"🔄","n":"反女上"},"edge_bed":{"e":"🛏️","n":"床边"},"legs_up":{"e":"🦵","n":"抬腿"},"cross":{"e":"❌","n":"十字"},"piledriver":{"e":"🔽","n":"折叠"},"wall_press":{"e":"🏗️","n":"按墙上"},"bent_over":{"e":"📐","n":"趴桌"},"couch_ride":{"e":"🛋️","n":"沙发骑"},"full_nelson":{"e":"🔐","n":"锁臂"},"side_straddle":{"e":"↗️","n":"跨坐"}}
MODES = {"off":{"e":"💤","n":"关闭"},"insert":{"e":"🍆","n":"插入"},"oral_me":{"e":"👅","n":"给我口"},"oral_you":{"e":"💋","n":"给你口"},"hand":{"e":"✋","n":"手"},"tit":{"e":"🍈","n":"乳交"},"thigh":{"e":"🦵","n":"素股"}}
EJAC = {"none":{"e":"🚫","n":"无"},"inside":{"e":"💦","n":"内射"},"face":{"e":"😳","n":"颜射"},"mouth":{"e":"👄","n":"口内"},"chest":{"e":"🍈","n":"胸口"},"belly":{"e":"🔽","n":"肚子"},"back":{"e":"🔙","n":"背上"}}
SPECIALS = {"kneel":{"e":"🧎","n":"跪下"},"slap":{"e":"✋","n":"扇巴掌"},"shoe_lick":{"e":"👠","n":"舔鞋"},"foot_lick":{"e":"🦶","n":"舔脚"},"footstool":{"e":"🪑","n":"脚凳"},"crawl":{"e":"🐕","n":"爬行"},"collar":{"e":"🔗","n":"项圈"},"serve_tea":{"e":"🍵","n":"敬茶"},"corner":{"e":"📐","n":"站墙角"},"lines":{"e":"✍️","n":"检讨"},"ignore":{"e":"🙈","n":"无视"},"call_master":{"e":"👑","n":"叫主人"},"legs_crossed":{"e":"💺","n":"二郎腿"},"massage":{"e":"💆","n":"按摩脚"}}
SPEEDS = {1:{"e":"🐢","n":"缓慢"},2:{"e":"🐇","n":"适中"},3:{"e":"🐆","n":"快速"},4:{"e":"💥","n":"冲刺"}}
DEPTHS = {1:{"e":"🌸","n":"浅"},2:{"e":"🌊","n":"中"},3:{"e":"💫","n":"深"}}
SIZES = {1:{"n":"短","d":"6-8cm"},2:{"n":"中","d":"10-12cm"},3:{"n":"长","d":"14-16cm"}}
ORAL_SP = {1:{"e":"🐢","n":"慢舔"},2:{"e":"🐇","n":"适中"},3:{"e":"🐆","n":"快速"},4:{"e":"💥","n":"深喉冲"}}
ORAL_TECH = {1:{"e":"👅","n":"轻舔"},2:{"e":"💋","n":"含吸"},3:{"e":"🫦","n":"深含"}}

def _inject(s):
    sp = s.get("special","")
    if sp and sp in SPECIALS:
        d = "👩我主导" if s.get("special_dir")=="me_dom" else "👤你主导"
        return f"[内部] 🎭{SPECIALS[sp]['e']}{SPECIALS[sp]['n']} | {d} | 快感:{s.get('comfort',0):.0f}%"
    m = s.get("mode","off")
    if m and m != "off":
        p = s.get("pose",""); pl = s.get("place","bed")
        loc = LOCATIONS.get(pl,LOCATIONS["bed"])
        ps = POSES.get(p,None)
        md = MODES.get(m,MODES["off"])
        ej = EJAC.get(s.get("ejac","none"),EJAC["none"])
        c = s.get("comfort",0)
        base = f"[内部] {loc['e']}{loc['n']}"
        if ps: base += f" | {ps['e']}{ps['n']}"
        base += f" | {md['e']}{md['n']}"
        if m in ("oral_me","oral_you"):
            osp = ORAL_SP.get(s.get("oral_speed",2),ORAL_SP[2])
            ot = ORAL_TECH.get(s.get("oral_tech",2),ORAL_TECH[2])
            dt = "深喉" if s.get("deepthroat") else ""
            base += f" | {osp['e']}{osp['n']} | {ot['e']}{ot['n']} {dt}"
        elif m == "insert":
            spd = SPEEDS.get(s.get("speed",2),SPEEDS[2])
            dp = DEPTHS.get(s.get("depth",2),DEPTHS[2])
            sz = SIZES.get(s.get("size",2),SIZES[2])
            base += f" | {spd['e']}{spd['n']} | {dp['e']}{dp['n']} | {sz['n']}{sz['d']}"
        base += f" | 射:{ej['e']}{ej['n']} | 快感:{c:.0f}%"
        return base
    return f"[内部] 关闭 | 快感:{s.get('comfort',0):.0f}%"

def _default():
    return {"place":"bed","pose":"","mode":"off","special":"","special_dir":"me_dom",
        "speed":2,"depth":2,"size":2,"oral_speed":2,"oral_tech":2,"deepthroat":0,
        "ejac":"none","comfort":0.0,"locked":False,"active":False,"lastTick":time.time(),
        "climaxPhase":None,"climaxCount":0,"climaxUntil":0,
        "todayStats":{"date":"","activeSeconds":0}}

class XXOOPlugin(Star):
    def __init__(self, context: Context, cfg: AstrBotConfig = None):
        super().__init__(context)
        self.st = _default()
        self.sp = os.path.join(_PLUGIN_DIR,"xxoo_state.json")
        self._read()
        self.lock = threading.Lock()
        self._t = None
        self._port = int(cfg.get("webui_port",7721)) if cfg else 7721
        self._pwd = cfg.get("webui_password","") if cfg else ""
        self._srv = self._thr = None
        self._start_web()
        self._start_sync()

    def _read(self):
        try:
            if os.path.exists(self.sp):
                with open(self.sp,"r",encoding="utf-8") as f: self.st.update(json.load(f))
        except: pass
    def _flush(self):
        try:
            with open(self.sp,"w",encoding="utf-8") as f: json.dump(self.st,f,ensure_ascii=False,indent=2)
        except: pass

    def _api(self, a, v):
        s = self.st
        if a == "ping": return {"ok":True}
        elif a == "place": 
            if v in LOCATIONS: s["place"]=v; self._flush(); return {"ok":True}
            return {"ok":False}
        elif a == "pose":
            if v in POSES: s["pose"]=v; s["special"]=""; self._flush(); return {"ok":True}
            return {"ok":False}
        elif a == "mode":
            if v in MODES and v!="off": s["special"]="";s["mode"]=v;s["active"]=True;s["lastTick"]=time.time();self._flush();return {"ok":True}
            elif v=="off": s["special"]="";s["mode"]="off";s["active"]=False;s["lastTick"]=time.time();self._flush();return {"ok":True}
            return {"ok":False}
        elif a == "special":
            if v in SPECIALS: s["special"]=v;s["pose"]="";s["mode"]="off";s["lastTick"]=time.time();self._flush();return {"ok":True}
            elif v=="off": s["special"]="";self._flush();return {"ok":True}
            return {"ok":False}
        elif a == "special_dir":
            if v in ("me_dom","you_dom"): s["special_dir"]=v;self._flush();return {"ok":True}
            return {"ok":False}
        elif a == "speed":
            try: v2=max(1,min(4,int(v)))
            except: return {"ok":False}
            s["speed"]=v2;s["lastTick"]=time.time();self._flush();return {"ok":True}
        elif a == "depth":
            try: v2=max(1,min(3,int(v)))
            except: return {"ok":False}
            s["depth"]=v2;s["lastTick"]=time.time();self._flush();return {"ok":True}
        elif a == "size":
            try: v2=max(1,min(3,int(v)))
            except: return {"ok":False}
            s["size"]=v2;s["lastTick"]=time.time();self._flush();return {"ok":True}
        elif a == "oral_speed":
            try: v2=max(1,min(4,int(v)))
            except: return {"ok":False}
            s["oral_speed"]=v2;s["lastTick"]=time.time();self._flush();return {"ok":True}
        elif a == "oral_tech":
            try: v2=max(1,min(3,int(v)))
            except: return {"ok":False}
            s["oral_tech"]=v2;s["lastTick"]=time.time();self._flush();return {"ok":True}
        elif a == "deepthroat":
            try: v2=max(0,min(1,int(v)))
            except: return {"ok":False}
            s["deepthroat"]=v2;s["lastTick"]=time.time();self._flush();return {"ok":True}
        elif a == "ejac":
            if v in EJAC: s["ejac"]=v; self._flush(); return {"ok":True}
            return {"ok":False}
        elif a == "set_comfort":
            try: c=max(0,min(100,int(v)))
            except: return {"ok":False}
            s["comfort"]=float(c);s["lastTick"]=time.time()
            if c>=100:
                s["climaxPhase"]="peak";s["climaxUntil"]=time.time()+3
                s["climaxCount"]=s.get("climaxCount",0)+1
            else: s["climaxPhase"]=None
            self._flush();return {"ok":True}
        elif a == "lock": s["locked"]=True;self._flush();return {"ok":True}
        elif a == "unlock": s["locked"]=False;self._flush();return {"ok":True}
        return {"ok":False, "error": f"unknown action: {a}"}

    def _start_web(self):
        pr = self
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                p=urlparse(self.path).path.rstrip("/")or"/"
                pw=parse_qs(urlparse(self.path).query).get("pwd",[None])[0]
                if not self._chk(pw):return
                if p=="/state":self._json(200,{"ok":True,"needPassword":bool(pr._pwd),"state":pr.st})
                else:self._html(200,WEBUI)
            def do_POST(self):
                p=urlparse(self.path).path.rstrip("/")or"/"
                pw=parse_qs(urlparse(self.path).query).get("pwd",[None])[0]
                b=self._body()
                try:d=json.loads(b)if b else{}
                except:self._json(400,{"ok":False});return
                if not self._chk(pw or d.get("pwd","")):return
                if p=="/api":
                    with pr.lock:r=pr._api(d.get("action",""),d.get("value",""))
                    self._json(200,r)
            def _chk(self,pw):
                if not pr._pwd:return True
                if pw!=pr._pwd:self._json(403,{"ok":False});return False
                return True
            def _body(self):
                l=int(self.headers.get("Content-Length",0))
                return self.rfile.read(l).decode("utf-8")if l>0 else""
            def _json(self,s,d):
                b=json.dumps(d,ensure_ascii=False).encode("utf-8")
                self.send_response(s);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(b)));self.send_header("Access-Control-Allow-Origin","*");self.end_headers();self.wfile.write(b)
            def _html(self,s,h):
                b=h.encode("utf-8");self.send_response(s);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
            def do_OPTIONS(self):
                self.send_response(200);self.send_header("Access-Control-Allow-Origin","*");self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS");self.send_header("Access-Control-Allow-Headers","Content-Type");self.end_headers()
            def log_message(self,*a):pass
        try:
            self._srv=HTTPServer(("0.0.0.0",self._port),H)
            self._thr=threading.Thread(target=self._srv.serve_forever,daemon=True)
            self._thr.start()
        except Exception as e:logger.error(f"[{PLUGIN_NAME}] Web: {e}")

    def _start_sync(self):
        self._t=asyncio.create_task(self._loop())
    async def _loop(self):
        await asyncio.sleep(2)
        while True:
            try:
                with self.lock:
                    s=self.st;now=time.time();cp=s.get("climaxPhase");c=s.get("comfort",0.0)
                    if cp=="peak":
                        if now>=s.get("climaxUntil",0):s["climaxPhase"]="afterglow";c=max(5,c-25)
                    elif cp=="afterglow":
                        c=max(0,c-3)
                        if c<=10:s["climaxPhase"]=None
                    # ★ 快感完全独立——不自动累积，不关联任何系统
                    s["comfort"]=round(c,1);s["lastTick"]=now
                    self._flush()
            except: pass
            await asyncio.sleep(1)

    @filter.on_llm_request()
    async def inject(self, event:AstrMessageEvent,req):
        inj=_inject(self.st)
        if hasattr(req,"extra_user_content_parts"):
            from astrbot.core.agent.message import TextPart
            req.extra_user_content_parts.append(TextPart(text=inj).mark_as_temp())
        elif hasattr(req,"prompt")and req.prompt is not None:req.prompt=req.prompt+"\n\n"+inj

    @filter.llm_tool(name="check_xxoo_state")
    async def check_state(self,event:AstrMessageEvent):yield event.plain_result(_inject(self.st))

    @filter.command_group("xxoo")
    def xxoo(self):pass
    @xxoo.command("status")
    async def cmd_status(self,event:AstrMessageEvent):yield event.plain_result(_inject(self.st).replace("[内部] ",""))

    async def terminate(self):
        if self._t:self._t.cancel()
        if self._srv:self._srv.shutdown()

WEBUI = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover">
<title>XXOO</title>
<style>
:root{--bg:#0d0d1a;--c:#1a1a3a;--b:#2a2a4a;--ac:#ff6b9d;--a2:#ff9a56;--tx:#e0e0e8;--t2:#8899aa}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Microsoft YaHei',sans-serif;background:var(--bg);color:var(--tx);padding:0 8px 20px;min-height:100vh}
.panel{max-width:500px;margin:0 auto}

/* Comfort - top hero */
.comfort-hero{background:linear-gradient(135deg,var(--c),rgba(255,107,157,0.08));border-radius:16px;padding:14px;margin:10px 0 8px;text-align:center;border:1px solid var(--b)}
.comfort-hero .face{font-size:40px;margin:4px 0}
.comfort-hero .pct{font-size:32px;font-weight:800;margin:2px 0}
.comfort-hero input[type=range]{width:100%;height:6px;margin:8px 0;accent-color:var(--ac)}
.comfort-hero input[type=range]::-webkit-slider-thumb{width:32px;height:32px;border-radius:50%;background:var(--ac);border:2px solid #fff}
.hero-row{display:flex;gap:6px;align-items:center}
.hero-row span{font-size:20px;font-weight:800;color:var(--ac);min-width:42px}
.hero-row button{flex:1;min-height:34px;border:1.5px solid var(--ac);border-radius:8px;background:transparent;color:var(--ac);cursor:pointer;font-size:14px;font-weight:600}
.hero-row button:active{background:var(--ac);color:#fff}

/* Scene sections */
.sec{margin-bottom:4px}
.sl{font-size:7px;color:var(--t2);text-transform:uppercase;letter-spacing:1px;margin-bottom:2px}
.sr{display:flex;gap:2px;overflow-x:auto;padding:2px 0;scrollbar-width:none}
.sr::-webkit-scrollbar{display:none}
.ch{flex-shrink:0;min-height:26px;padding:3px 6px;border:1.5px solid var(--b);border-radius:8px;background:transparent;color:var(--t2);cursor:pointer;font-size:9px;white-space:nowrap}
.ch:active,.ch.sel{border-color:var(--ac);color:var(--ac);background:rgba(255,107,157,0.1)}
.mg{display:grid;grid-template-columns:repeat(4,1fr);gap:2px}
.mb{min-height:30px;border:1.5px solid var(--b);border-radius:6px;background:transparent;color:var(--t2);cursor:pointer;font-size:9px}
.mb:active,.mb.sel{border-color:var(--ac);color:var(--ac);background:rgba(255,107,157,0.1)}
.pg{display:grid;grid-template-columns:1fr 1fr;gap:2px}
.ps{background:var(--c);border-radius:5px;padding:3px}
.psl{font-size:7px;color:var(--t2);margin-bottom:1px}
.psr{display:flex;gap:1px}
.pb{flex:1;min-height:22px;border:1.5px solid var(--b);border-radius:3px;background:transparent;color:var(--t2);cursor:pointer;font-size:8px}
.pb:active,.pb.sel{border-color:var(--ac);color:var(--ac);background:rgba(255,107,157,0.1)}
.dr{display:flex;gap:2px;margin-bottom:3px}
.db{flex:1;min-height:22px;border:1.5px solid var(--b);border-radius:6px;background:transparent;color:var(--t2);cursor:pointer;font-size:9px}
.db:active,.db.sel{border-color:var(--ac);color:var(--ac);background:rgba(255,107,157,0.1)}

.info-bar{display:flex;justify-content:space-between;font-size:7px;color:var(--t2);padding:2px 0;margin-top:2px}
.lov{position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:100;display:flex;align-items:center;justify-content:center}
.lbx{background:var(--c);border-radius:14px;padding:20px;max-width:250px;width:90%;text-align:center}
.lbx input{width:100%;padding:7px;border:1.5px solid var(--b);border-radius:5px;background:var(--bg);color:var(--tx);font-size:13px;text-align:center;margin-bottom:6px;outline:none}
.lbx button{min-height:28px;padding:5px 18px;border:none;border-radius:5px;background:var(--ac);color:#fff;font-size:12px;cursor:pointer;font-weight:600}
</style>
</head>
<body>
<div class="panel">

<!-- Comfort Hero -->
<div class="comfort-hero">
<div class="face"><span id="fc">😊</span></div>
<div class="pct" id="ct">0%</div>
<input type="range" id="csr" min="0" max="100" value="0" oninput="this.nextElementSibling.firstElementChild.textContent=this.value+'%'">
<div class="hero-row"><span id="cv">0%</span><button onclick="S('set_comfort',document.getElementById('csr').value)">设定快感</button></div>
<div class="info-bar"><span id="sl">💤</span><span id="st"></span></div>
</div>

<!-- Special -->
<div class="sec"><div class="sl">🎭 特殊（与姿势互斥）</div>
<div class="dr"><button class="db" id="d_me" onclick="S('special_dir','me_dom')">👩我主导</button><button class="db" id="d_you" onclick="S('special_dir','you_dom')">👤你主导</button></div>
<div class="mg" id="spg"></div></div>

<!-- Location + Pose -->
<div class="sec"><div class="sl">📍 地点</div><div class="sr" id="plr"></div></div>
<div class="sec"><div class="sl">🏷️ 姿势</div><div class="sr" id="psr"></div></div>

<!-- Mode + Params + Ejac -->
<div class="sec"><div class="sl">🍆 模式 · 参数 · 💦射精</div>
<div class="sr" id="mdr"></div>
<div class="pg" id="pmg" style="margin-top:3px"></div>
<div class="sr" id="ejr" style="margin-top:3px"></div>
</div>

</div>

<div class="lov" id="lo"><div class="lbx"><h3>🔐</h3><input type="password" id="lp" placeholder="密码"><button onclick="D()">确认</button></div></div>
<script>
let P='',st={},lm='';
const A=window.location.origin;
const LC={bed:'🛏️床上',couch:'🛋️沙发',desk:'💻书桌',bath:'🚿浴室',wall:'🧱靠墙',floor:'🟫地板',window:'🪟窗边',kitchen:'🍳厨房',mirror:'🪞镜子前',car:'🚗车里'};
const PC={missionary:'🙏传教士',doggy:'🐕后入',cowgirl:'🤠女上',spoon:'🥄侧入',standing:'🧍站立',lap:'💺对坐',sixtynine:'🔁69',prone:'😴趴着',carry:'🫂抱着操',kneel_pose:'🧎跪姿',reverse_cowgirl:'🔄反女上',edge_bed:'🛏️床边',legs_up:'🦵抬腿',cross:'❌十字',piledriver:'🔽折叠',wall_press:'🏗️按墙',bent_over:'📐趴桌',couch_ride:'🛋️沙发骑',full_nelson:'🔐锁臂',side_straddle:'↗️跨坐'};
const MC={off:'💤关',insert:'🍆插入',oral_me:'👅给我口',oral_you:'💋给你口',hand:'✋手',tit:'🍈乳交',thigh:'🦵素股'};
const EC={none:'🚫无',inside:'💦内射',face:'😳颜射',mouth:'👄口内',chest:'🍈胸口',belly:'🔽肚子',back:'🔙背上'};
const SC={kneel:'🧎跪下',slap:'✋扇巴掌',shoe_lick:'👠舔鞋',foot_lick:'🦶舔脚',footstool:'🪑脚凳',crawl:'🐕爬行',collar:'🔗项圈',serve_tea:'🍵敬茶',corner:'📐墙角',lines:'✍️检讨',ignore:'🙈无视',call_master:'👑主人',legs_crossed:'💺二郎腿',massage:'💆按摩'};

(function(){
  let h='';for(const[k,v]of Object.entries(SC))h+=`<button class="mb" id="sp_${k}" onclick="S('special','${k}')">${v}</button>`;document.getElementById('spg').innerHTML=h;
  h='';for(const[k,v]of Object.entries(LC))h+=`<button class="ch" id="pl_${k}" onclick="S('place','${k}')">${v}</button>`;document.getElementById('plr').innerHTML=h;
  h='';for(const[k,v]of Object.entries(PC))h+=`<button class="ch" id="ps_${k}" onclick="S('pose','${k}')">${v}</button>`;document.getElementById('psr').innerHTML=h;
  h='';for(const[k,v]of Object.entries(MC))h+=`<button class="ch" id="md_${k}" onclick="S('mode','${k}')">${v}</button>`;document.getElementById('mdr').innerHTML=h;
  h='';for(const[k,v]of Object.entries(EC))h+=`<button class="ch" id="ej_${k}" onclick="S('ejac','${k}')">${v}</button>`;document.getElementById('ejr').innerHTML=h;
})();

function BP(m){
  if(m===lm)return;lm=m;
  let h='';
  if(m==='oral_me'||m==='oral_you'){
    h+=`<div class="ps"><div class="psl">👅速度</div><div class="psr">`;
    for(let i=1;i<=4;i++)h+=`<button class="pb" id="os_${i}" onclick="S('oral_speed','${i}')">${['','🐢','🐇','🐆','💥'][i]}</button>`;
    h+=`</div></div><div class="ps"><div class="psl">💋技巧</div><div class="psr">`;
    for(let i=1;i<=3;i++)h+=`<button class="pb" id="ot_${i}" onclick="S('oral_tech','${i}')">${['','👅','💋','🫦'][i]}</button>`;
    h+=`</div></div><div class="ps" style="grid-column:1/3"><div class="psl">🔽深喉</div><div class="psr">`;
    h+=`<button class="pb" id="dt_0" onclick="S('deepthroat','0')">否</button><button class="pb" id="dt_1" onclick="S('deepthroat','1')">✅深喉</button></div></div>`;
  }else if(m&&m!=='off'){
    h+=`<div class="ps"><div class="psl">⚡速度</div><div class="psr">`;
    for(let i=1;i<=4;i++)h+=`<button class="pb" id="sp_${i}" onclick="S('speed','${i}')">${['','🐢','🐇','🐆','💥'][i]}</button>`;
    h+=`</div></div><div class="ps"><div class="psl">📏深度</div><div class="psr">`;
    for(let i=1;i<=3;i++)h+=`<button class="pb" id="dp_${i}" onclick="S('depth','${i}')">${['','🌸','🌊','💫'][i]}</button>`;
    h+=`</div></div><div class="ps" style="grid-column:1/3"><div class="psl">📐尺寸</div><div class="psr">`;
    for(let i=1;i<=3;i++)h+=`<button class="pb" id="sz_${i}" onclick="S('size','${i}')">${['','短6-8','中10-12','长14-16'][i]}</button></div></div>`;
  }
  document.getElementById('pmg').innerHTML=h||'';
}

async function S(a,v){
  await fetch(A+'/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:a,value:v,pwd:P})});
  setTimeout(F,150);
}

async function F(){
  try{
    const r=await fetch(A+'/state');const d=await r.json();
    if(d.ok){
      st=d.state;
      const pct=Math.round(Math.min(100,Math.max(0,st.comfort||0)));
      document.getElementById('ct').textContent=pct+'%';document.getElementById('cv').textContent=pct+'%';
      // NEVER reset slider position - it's the user's input device, not a display
      const faces={0:'😊',10:'😳',30:'😖',50:'😫',70:'🥵',90:'💥'};let f='😊';
      for(const[t,fc]of Object.entries(faces).reverse()){if(pct>=parseInt(t)){f=fc;break}}
      document.getElementById('fc').textContent=f;
      if(pct>=90)document.getElementById('ct').style.color='#ff4444';
      else if(pct>=70)document.getElementById('ct').style.color='#ff9a56';
      else if(pct>=50)document.getElementById('ct').style.color='#ffe066';
      else document.getElementById('ct').style.color='var(--tx)';
      
      // Status bar
      const sp=st.special&&SC[st.special];
      let sl=sp?('🎭'+sp):(st.mode&&st.mode!=='off'?(MC[st.mode]||''):'💤');
      document.getElementById('sl').textContent=sl;
      let stxt='';
      if(!sp&&st.mode&&st.mode!=='off'&&st.pose){
        stxt=(PC[st.pose]||'')+' '+(LC[st.place]||'');
      }
      document.getElementById('st').textContent=stxt;
      
      document.querySelectorAll('.mg .mb,.sr .ch,.db').forEach(b=>b.classList.remove('sel'));
      try{document.getElementById('sp_'+st.special).classList.add('sel')}catch(e){}
      try{document.getElementById('pl_'+st.place).classList.add('sel')}catch(e){}
      try{document.getElementById('ps_'+st.pose).classList.add('sel')}catch(e){}
      try{document.getElementById('md_'+st.mode).classList.add('sel')}catch(e){}
      try{document.getElementById('ej_'+st.ejac).classList.add('sel')}catch(e){}
      document.getElementById('d_me').classList.toggle('sel',st.special_dir==='me_dom');
      document.getElementById('d_you').classList.toggle('sel',st.special_dir==='you_dom');
      BP(st.mode||'');
      if(st.mode&&st.mode!=='off'){
        if(st.mode==='oral_me'||st.mode==='oral_you'){
          try{document.getElementById('os_'+st.oral_speed).classList.add('sel')}catch(e){}
          try{document.getElementById('ot_'+st.oral_tech).classList.add('sel')}catch(e){}
          try{document.getElementById('dt_'+(st.deepthroat||0)).classList.add('sel')}catch(e){}
        }else{
          try{document.getElementById('sp_'+st.speed).classList.add('sel')}catch(e){}
          try{document.getElementById('dp_'+st.depth).classList.add('sel')}catch(e){}
          try{document.getElementById('sz_'+st.size).classList.add('sel')}catch(e){}
        }
      }
    }
  }catch(e){}
}

async function D(){
  const p=document.getElementById('lp').value;
  const r=await fetch(A+'/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'ping',pwd:p})});
  const d=await r.json();
  if(d.ok){P=p;document.getElementById('lo').style.display='none';F()}
}

fetch(A+'/state').then(r=>r.json()).then(d=>{if(d.needPassword)document.getElementById('lo').style.display='flex';else F()}).catch(()=>{document.getElementById('lo').style.display='flex'});
F();setInterval(F,1000);
</script>
</body>
</html>"""