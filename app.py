
import streamlit as st
import pandas as pd
import requests, feedparser, json, os, re, io
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client

st.set_page_config(page_title="阮嘤基金投资工作台 V28", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

HEADERS={"User-Agent":"Mozilla/5.0"}
TZ=ZoneInfo("Asia/Shanghai")
DATA_DIR="data"; os.makedirs(DATA_DIR,exist_ok=True)
RULE_FILE=os.path.join(DATA_DIR,"rules.json")
LOG_FILE=os.path.join(DATA_DIR,"investment_log.csv")
BUDGET_FILE=os.path.join(DATA_DIR,"budget.json")
PORT_FILE=os.path.join(DATA_DIR,"portfolio.csv")
SNAPSHOT_FILE=os.path.join(DATA_DIR,"portfolio_snapshots.csv")
EVENT_FILE=os.path.join(DATA_DIR,"event_calendar.json")


st.markdown("""
<style>
.block-container{padding:.6rem .85rem 2rem;max-width:1680px}
section[data-testid="stSidebar"]{width:275px!important}
section[data-testid="stSidebar"] .block-container{padding:.7rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #e8ecf2;border-radius:12px;padding:10px 12px;box-shadow:0 1px 5px rgba(20,40,80,.04)}
.card{background:#fff;border:1px solid #e7ebf1;border-radius:12px;padding:12px 14px;margin-bottom:9px}
.small{font-size:12px;color:#7b8494}
.tag{display:inline-block;border-radius:6px;padding:2px 7px;font-size:12px;font-weight:700;margin-right:5px}
.r{background:#fff0f0;color:#d9363e}.g{background:#edf9f3;color:#078b57}.y{background:#fff7e6;color:#c97900}.b{background:#edf5ff;color:#1677ff}
h1{font-size:1.55rem!important;margin:.1rem 0!important}h2{font-size:1.12rem!important}
div[data-testid="stDataFrame"]{border:1px solid #edf0f4;border-radius:10px;overflow:hidden}

/* ===== 左侧丝滑连体导航 ===== */
section[data-testid="stSidebar"] div[role="radiogroup"]{
    gap:0!important;
    border:1px solid #e3e8ef;
    border-radius:14px;
    overflow:hidden;
    background:#fff;
    box-shadow:0 2px 10px rgba(30,50,80,.04);
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label{
    min-height:50px!important;
    margin:0!important;
    padding:0 14px!important;
    border-bottom:1px solid #edf0f4!important;
    border-radius:0!important;
    background:#fff!important;
    display:flex!important;
    align-items:center!important;
    font-size:15px!important;
    font-weight:600!important;
    transition:background .18s ease, transform .12s ease, color .18s ease!important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:last-child{
    border-bottom:none!important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover{
    background:#f5f8ff!important;
    color:#1268d9!important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked){
    background:linear-gradient(90deg,#eaf3ff 0%,#f7fbff 100%)!important;
    color:#1268d9!important;
    box-shadow:inset 4px 0 0 #1677ff!important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child{
    margin-right:7px!important;
}
section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"]{
    transform:scale(1.05);
}
section[data-testid="stSidebar"] [data-testid="stMetric"]{
    margin-top:10px;
}


/* ===== V24 专业终端顶部状态条 ===== */
.terminalbar{
 display:grid;grid-template-columns:1.2fr 1fr 1fr 1fr 1.25fr;
 gap:8px;margin:4px 0 12px 0;
}
.terminalcell{
 background:#fff;border:1px solid #e5eaf0;border-radius:11px;
 padding:9px 11px;min-height:58px;box-shadow:0 1px 5px rgba(20,40,80,.035)
}
.terminalcell .k{font-size:11px;color:#8993a4;margin-bottom:3px}
.terminalcell .v{font-size:15px;font-weight:750;color:#172033;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.statusdot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#18a66a;margin-right:5px}
.quickbar{display:flex;gap:7px;flex-wrap:wrap;margin:2px 0 12px}
.quickpill{background:#f6f8fb;border:1px solid #e6eaf0;border-radius:999px;padding:5px 10px;font-size:12px;color:#596579}

/* ===== V27 手机竖屏优化 ===== */
@media(max-width:700px){
  .block-container{padding:.35rem .45rem 1.4rem!important}
  section[data-testid="stSidebar"]{width:86vw!important;max-width:330px!important}
  h1{font-size:1.28rem!important}
  h2{font-size:1.02rem!important}
  [data-testid="stMetric"]{padding:8px 9px!important}
  .terminalbar{grid-template-columns:1fr 1fr!important;gap:6px!important}
  .terminalcell{min-height:50px!important;padding:7px 9px!important}
  .terminalcell .k{font-size:10px!important}
  .terminalcell .v{font-size:13px!important}
  .quickbar{gap:5px!important}
  .quickpill{font-size:11px!important;padding:4px 8px!important}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label{min-height:47px!important;font-size:14px!important}
}

@media(max-width:900px){
 .terminalbar{grid-template-columns:1fr 1fr}
 .terminalcell{min-height:54px}
}

@media(max-width:1100px){
 .block-container{padding:.45rem}
 section[data-testid="stSidebar"]{width:235px!important}
 [data-testid="column"]{min-width:48%!important}
}
@media(max-width:700px){
  [data-testid="stPlotlyChart"]{max-height:440px!important}
  .card{padding:10px 11px!important}
}
</style>
""", unsafe_allow_html=True)


def get_cloud():
    try:
        url=st.secrets["SUPABASE_URL"]
        # Streamlit 是服务端运行环境：优先使用仅保存在 Streamlit Secrets 的服务端密钥。
        # 若未配置，则回退到 Publishable Key（此时受 RLS 限制）。
        key=st.secrets.get("SUPABASE_SERVICE_KEY", st.secrets.get("SUPABASE_KEY"))
        if not key:
            return None
        return create_client(url,key)
    except Exception:
        return None

CLOUD=get_cloud()

def cloud_select(table):
    if not CLOUD:return []
    try:return CLOUD.table(table).select("*").execute().data or []
    except Exception:return []

def cloud_upsert(table,rows,on_conflict=None):
    if not CLOUD:return False
    try:
        q=CLOUD.table(table).upsert(rows,on_conflict=on_conflict) if on_conflict else CLOUD.table(table).upsert(rows)
        q.execute();return True
    except Exception:return False

def cloud_insert(table,rows):
    if not CLOUD:return False
    try:CLOUD.table(table).insert(rows).execute();return True
    except Exception:return False

DEFAULT_RULES={"纳指基础":50,"纳指机会":100,"CPO基础":20,"CPO机会":40,"半导体基础":10,"半导体机会":20,"黄金基础":50,"建信中档":50,"建信机会":100}
DEFAULT_PORT=pd.DataFrame([
["易方达全球成长精选",3626.13,"海外科技/半导体","保留","不新增",0],
["华安黄金ETF联接C",2148.84,"黄金","核心防守","50/日",0],
["德邦鑫星/CPO",1383.63,"CPO/光通信","核心","20/日",0],
["嘉实全球产业升级",1334.24,"全球科技","待迁移","迁往纳指/建信",0],
["建信新兴市场",1207.11,"AI/半导体/HBM","动态核心","0/50/100",0],
["东方人工智能/半导体",875.65,"半导体设备","核心","10/日",0],
["财通景气甄选一年持有",864.11,"A股成长","锁定","等待可赎回",0],
["天弘全球高端制造",847.87,"科技制造","待迁移","迁往纳指/建信",0],
["华夏移动互联",885.89,"海外半导体","接近封顶","约1000停止",1000],
["同泰慧盈混合C",485.94,"待分析","待评估","不新增",0],
["天弘越南市场C",312.79,"越南","卫星","观察",0],
["国泰纳斯达克100",249.79,"纳斯达克100","核心","50/日",0],
],columns=["基金","金额","主要暴露","定位","动作","目标金额"])

def load_json(path,default):
    try:
        with open(path,"r",encoding="utf-8") as f:return {**default,**json.load(f)}
    except:return default.copy()
def save_json(path,obj):
    with open(path,"w",encoding="utf-8") as f:json.dump(obj,f,ensure_ascii=False,indent=2)
def load_port():
    if CLOUD:
        rows=cloud_select("portfolio")
        if rows:
            x=pd.DataFrame(rows).rename(columns={"fund_name":"基金","amount":"金额","position_type":"定位","action":"动作","target_amount":"目标金额"})
            expo=dict(zip(DEFAULT_PORT["基金"],DEFAULT_PORT["主要暴露"]))
            x["主要暴露"]=x["基金"].map(expo).fillna("待分析")
            for c in ["基金","金额","定位","动作","目标金额"]:
                if c not in x.columns:x[c]=None
            return x[["基金","金额","主要暴露","定位","动作","目标金额"]]
    try:return pd.read_csv(PORT_FILE)
    except:return DEFAULT_PORT.copy()

def save_port(df):
    df.to_csv(PORT_FILE,index=False,encoding="utf-8-sig")
    if CLOUD:
        rows=[]
        for _,r in df.iterrows():
            rows.append({"fund_name":str(r["基金"]),"amount":float(r["金额"]) if pd.notna(r["金额"]) else 0,
                         "position_type":str(r["定位"]) if pd.notna(r["定位"]) else "",
                         "action":str(r["动作"]) if pd.notna(r["动作"]) else "",
                         "target_amount":float(r["目标金额"]) if pd.notna(r["目标金额"]) else 0})
        cloud_upsert("portfolio",rows,on_conflict="fund_name")

rules=load_json(RULE_FILE,DEFAULT_RULES)
budget=load_json(BUDGET_FILE,{"月预算":4000})
DEFAULT_EVENTS=[
    {"事件":"美国CPI","日期":"","影响":"美债/纳指/黄金","重要度":5},
    {"事件":"美国非农","日期":"","影响":"美债/纳指/黄金","重要度":5},
    {"事件":"FOMC/美联储","日期":"","影响":"美债/纳指/黄金","重要度":5},
    {"事件":"NVIDIA财报","日期":"","影响":"AI/纳指/建信/CPO","重要度":5},
]
events=load_json(EVENT_FILE,{"events":DEFAULT_EVENTS}).get("events",DEFAULT_EVENTS)

PORT=load_port()


TOP_HOLDINGS={
"德邦鑫星/CPO":[
("中际旭创",9.92),("新易盛",9.81),("东山精密",9.50),("胜宏科技",7.95),("天孚通信",7.93),
("炬光科技",7.68),("剑桥科技",5.57),("长芯博创",5.14),("鼎通科技",4.95),("沪电股份",4.64)],
"东方人工智能/半导体":[
("中科飞测",9.55),("芯源微",9.19),("中微公司",9.12),("华海清科",9.08),("北方华创",8.92),
("精测电子",8.69),("富创精密",7.57),("拓荆科技",7.44),("寒武纪",7.04),("盛美上海",6.87)],
"建信新兴市场":[
("TSMC",9.68),("NVIDIA",9.38),("SK Hynix",8.94),("Samsung",7.80),("SanDisk",7.16),
("Broadcom",4.18),("Western Digital",4.18),("Micron",3.99),("Lumentum",3.56),("Corning",3.35)],
"华夏移动互联":[
("Micron",8.16),("SanDisk",6.53),("Onto Innovation",5.55),("AMD",5.30),("Intel",4.94),
("Kioxia",4.59),("Lumentum",4.43),("TSMC",4.30),("STMicroelectronics",4.28),("Astera Labs",3.47)],
"易方达全球成长精选":[
("Lam Research",6.41),("Kioxia",5.89),("TSMC",5.54),("AMD",4.96),("新易盛",4.68),
("中际旭创",4.61),("SanDisk",4.46),("Intel",4.26),("源杰科技",3.34),("ASML",3.33)],
"天弘全球高端制造":[
("Kioxia",6.0),("胜宏科技",5.5),("中际旭创",5.2),("NVIDIA",5.0),("TSMC",4.8),
("华虹宏力",4.5),("Corning",4.2),("Nitto Boseki",4.0),("东山精密",3.8),("源杰科技",3.5)]
}
HOLDINGS_ASOF="2026Q2"

FUND_MAP={
"CPO/光通信":["德邦鑫星/CPO","易方达全球成长精选","建信新兴市场"],
"AI/算力":["国泰纳斯达克100","建信新兴市场","易方达全球成长精选"],
"HBM/存储":["建信新兴市场","华夏移动互联","易方达全球成长精选"],
"半导体设备":["东方人工智能/半导体"],
"黄金/宏观":["华安黄金ETF联接C","国泰纳斯达克100","建信新兴市场"],
"美股宏观":["国泰纳斯达克100","建信新兴市场"],
"A股政策":["德邦鑫星/CPO","东方人工智能/半导体"],
"创新药":[],"机器人":[],"有色/铜":[],"电力/电网":[],"消费/白酒":[],"券商":[]
}

BASKETS={
"CPO/光通信":[("中际旭创","300308.SZ","sz300308"),("新易盛","300502.SZ","sz300502"),("天孚通信","300394.SZ","sz300394"),("光迅科技","002281.SZ","sz002281")],
"半导体设备":[("北方华创","002371.SZ","sz002371"),("中微公司","688012.SS","sh688012"),("拓荆科技","688072.SS","sh688072"),("芯源微","688037.SS","sh688037")],
"创新药":[("恒瑞医药","600276.SS","sh600276"),("百济神州","688235.SS","sh688235")],
"机器人":[("三花智控","002050.SZ","sz002050"),("绿的谐波","688017.SS","sh688017"),("拓普集团","601689.SS","sh601689")],
"有色/铜":[("紫金矿业","601899.SS","sh601899"),("洛阳钼业","603993.SS","sh603993"),("江西铜业","600362.SS","sh600362")],
"电力/电网":[("国电南瑞","600406.SS","sh600406"),("许继电气","000400.SZ","sz000400"),("平高电气","600312.SS","sh600312")],
"消费/白酒":[("贵州茅台","600519.SS","sh600519"),("五粮液","000858.SZ","sz000858")],
"券商":[("中信证券","600030.SS","sh600030"),("东方财富","300059.SZ","sz300059")],
}

POS=["增长","超预期","上调","订单","获批","扩产","growth","beat","record","raise","surge","upgrade","expands"]
NEG=["限制","制裁","禁令","关税","下调","调查","restrict","sanction","ban","tariff","cut","miss","weak","probe"]

def get_json(url,params=None):
    try:
        r=requests.get(url,params=params,headers=HEADERS,timeout=4);r.raise_for_status();return r.json()
    except:return None
def yahoo(symbol,range_="5d"):
    j=get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",{"range":range_,"interval":"1d"})
    try:
        r=j["chart"]["result"][0]
        closes=[float(x) for x in r["indicators"]["quote"][0]["close"] if x is not None]
        return closes[-1],(closes[-1]/closes[-2]-1)*100,closes
    except:return None,None,[]
def eastmoney(secid):
    j=get_json("https://push2.eastmoney.com/api/qt/stock/get",{"secid":secid,"fields":"f43,f170"})
    try:return j["data"]["f43"]/100,j["data"]["f170"]/100
    except:return None,None
def tencent(code):
    try:
        r=requests.get(f"https://qt.gtimg.cn/q={code}",headers=HEADERS,timeout=4);r.encoding="gbk"
        p=r.text.split('="',1)[1].rsplit('"',1)[0].split("~");cur,pre=float(p[3]),float(p[4]);return cur,(cur/pre-1)*100
    except:return None,None
def fallback(*fns):
    for fn in fns:
        try:
            p,c=fn()
            if p is not None and c is not None:return p,c
        except:pass
    return None,None

@st.cache_data(ttl=60)
def markets():
    specs=[
        ("上证",lambda:fallback(lambda:eastmoney("1.000001"),lambda:tencent("sh000001"),lambda:yahoo("000001.SS")[:2])),
        ("创业板",lambda:fallback(lambda:eastmoney("0.399006"),lambda:tencent("sz399006"),lambda:yahoo("399006.SZ")[:2])),
        ("科创50",lambda:fallback(lambda:eastmoney("1.000688"),lambda:tencent("sh000688"),lambda:yahoo("000688.SS")[:2])),
        ("纳斯达克",lambda:yahoo("^IXIC")[:2]),("标普500",lambda:yahoo("^GSPC")[:2]),("SOX",lambda:yahoo("^SOX")[:2]),
        ("VIX",lambda:yahoo("^VIX")[:2]),("美债10Y",lambda:yahoo("^TNX")[:2]),("黄金",lambda:yahoo("GC=F")[:2])
    ]
    rows=[]
    with ThreadPoolExecutor(max_workers=9) as ex:
        futs={ex.submit(fn):n for n,fn in specs}
        for fut in as_completed(futs):
            n=futs[fut]
            try:p,c=fut.result()
            except Exception:p,c=None,None
            rows.append([n,p,c])
    order={n:i for i,(n,_) in enumerate(specs)}
    rows.sort(key=lambda r:order[r[0]])
    return pd.DataFrame(rows,columns=["市场","价格","涨跌"])

@st.cache_data(ttl=180)
def sectors():
    def one_sector(item):
        sec,stocks=item
        vals=[];detail=[]
        with ThreadPoolExecutor(max_workers=min(6,len(stocks))) as ex:
            futs={ex.submit(tencent,tcode):name for name,ysym,tcode in stocks}
            for fut in as_completed(futs):
                name=futs[fut]
                try:_,p=fut.result()
                except Exception:p=None
                if p is not None:
                    vals.append(p);detail.append(f"{name} {p:+.1f}%")
        return [sec,sum(vals)/len(vals) if vals else None," ｜ ".join(detail) if detail else "数据暂不可用"]
    with ThreadPoolExecutor(max_workers=8) as ex:
        rows=list(ex.map(one_sector,BASKETS.items()))
    return pd.DataFrame(rows,columns=["板块","涨跌","核心成分"])

@st.cache_data(ttl=300)
def sector_history(secname):
    rows=[]
    for name,ysym,tcode in BASKETS[secname]:
        _,_,closes=yahoo(ysym,"1mo")
        if closes:
            base=closes[0]
            for i,c in enumerate(closes):
                rows.append([i,name,(c/base-1)*100])
    return pd.DataFrame(rows,columns=["交易日序号","股票","累计涨跌%"])

def topic_from_title(lo):
    if any(x in lo for x in ["cpo","optical module","光模块","1.6t","800g"]):return "CPO/光通信"
    if any(x in lo for x in ["hbm","micron","hynix","samsung","dram","nand","存储"]):return "HBM/存储"
    if any(x in lo for x in ["nvidia","英伟达","ai data","gpu","blackwell","rubin"]):return "AI/算力"
    if any(x in lo for x in ["北方华创","中微公司","拓荆科技","半导体设备"]):return "半导体设备"
    if any(x in lo for x in ["gold","黄金","fed","treasury","美债"]):return "黄金/宏观"
    if any(x in lo for x in ["cpi","nonfarm","非农","inflation","通胀","fomc"]):return "美股宏观"
    if any(x in lo for x in ["a股","中国股市","证监会","政策"]):return "A股政策"
    if any(x in lo for x in ["创新药","biotech","fda","license-out"]):return "创新药"
    if any(x in lo for x in ["robot","机器人","humanoid"]):return "机器人"
    if any(x in lo for x in ["copper","铜","紫金矿业","洛阳钼业"]):return "有色/铜"
    if any(x in lo for x in ["电网","储能","grid","power equipment"]):return "电力/电网"
    if any(x in lo for x in ["白酒","消费","consumer"]):return "消费/白酒"
    if any(x in lo for x in ["券商","brokerage","证券"]):return "券商"
    return "其他"

def source_grade(title):
    lo=title.lower()
    if any(x in lo for x in ["reuters","路透","federal reserve","sec.gov","公司公告","交易所"]):return "A"
    if any(x in lo for x in ["bloomberg","彭博","cnbc","financial times","证券时报","中国证券报","上海证券报","第一财经","财联社"]):return "B"
    return "C"

def parse_dt(s):
    try:return pd.to_datetime(s,utc=True).tz_convert(TZ)
    except:return pd.NaT

def summary_cn(title,topic,score):
    direction="利好" if score>=60 else "利空" if score<=40 else "中性"
    if topic=="CPO/光通信":
        impact="主要影响光模块/CPO景气预期与相关基金。"
    elif topic=="HBM/存储":
        impact="主要影响建信、华夏移动互联等存储/HBM暴露。"
    elif topic=="AI/算力":
        impact="主要影响纳指、建信及全球科技持仓。"
    elif topic=="半导体设备":
        impact="主要影响国产半导体设备核心仓。"
    elif topic=="黄金/宏观":
        impact="主要通过利率、美元和避险情绪影响黄金与科技估值。"
    else:
        impact="属于观察信息，暂不单独改变核心定投计划。"
    return f"{direction}倾向。{impact}"

@st.cache_data(ttl=600)
def getnews(mode="lite"):
    # V28：首屏只取核心新闻，新闻中心再加载完整新闻库，避免手机首次打开被几十个RSS请求阻塞。
    full_queries=[
        "NVIDIA AI data center when:3d","OpenAI data center when:3d","Microsoft Meta Google AI capex when:3d","Blackwell Rubin GPU demand when:7d",
        "1.6T optical module CPO when:7d","800G optical module China when:7d","中际旭创 新易盛 光模块 when:7d","Lumentum optical transceiver when:7d",
        "HBM Micron SK Hynix Samsung when:7d","DRAM NAND memory price when:7d","Kioxia SanDisk memory when:7d",
        "中国 半导体设备 北方华创 中微公司 when:7d","国产半导体设备 when:7d",
        "gold Federal Reserve Treasury yield when:3d","CPI nonfarm FOMC US stocks when:7d","US 10 year yield tech stocks when:3d",
        "中国 光模块 出口管制 when:7d","US China semiconductor export control when:7d","A股 政策 证监会 科技股 when:3d",
        "创新药 license-out FDA when:7d","人形机器人 humanoid robot when:7d","铜 紫金矿业 洛阳钼业 when:7d","电网 储能 电力设备 when:7d",
        "白酒 消费 A股 when:7d","券商 东方财富 中信证券 when:7d"
    ]
    lite_queries=[
        "NVIDIA AI data center when:3d","1.6T optical module CPO when:7d",
        "HBM Micron SK Hynix Samsung when:7d","中国 半导体设备 北方华创 中微公司 when:7d",
        "gold Federal Reserve Treasury yield when:3d","US China semiconductor export control when:7d",
        "A股 政策 证监会 科技股 when:3d"
    ]
    queries = full_queries if mode=="full" else lite_queries

    def fetch_one(q):
        out=[]
        try:
            url=f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
            r=requests.get(url,headers=HEADERS,timeout=5)
            r.raise_for_status()
            feed=feedparser.parse(r.content)
            for e in feed.entries[:8]:
                title=e.get("title","").strip()
                if title:
                    out.append((title,e.get("published",""),e.get("link","")))
        except Exception:
            pass
        return out

    rows=[]; seen=set()
    # 并发抓取，避免25个RSS串行等待。
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs=[ex.submit(fetch_one,q) for q in queries]
        for fut in as_completed(futs):
            for title,pub,link in fut.result():
                key=re.sub(r"\s+"," ",title.lower())
                if key in seen: continue
                seen.add(key)
                lo=title.lower()
                score=50+sum(8 for x in POS if x.lower() in lo)-sum(10 for x in NEG if x.lower() in lo)
                topic=topic_from_title(lo); grade=source_grade(title)
                importance=min(5,max(1,2+round(abs(score-50)/10)+(1 if grade=="A" else 0)))
                rows.append([topic,max(0,min(100,score)),grade,importance,title,pub,link,parse_dt(pub)])

    df=pd.DataFrame(rows,columns=["主题","分数","可信度","重要度","新闻","时间","链接","发布时间"])
    if not df.empty:
        df["摘要"]=df.apply(lambda r:summary_cn(r["新闻"],r["主题"],r["分数"]),axis=1)
        df["影响基金"]=df["主题"].apply(lambda t:"、".join(FUND_MAP.get(t,[])) or "无直接核心基金映射")
        df=df.sort_values(["发布时间","重要度"],ascending=[False,False],na_position="last")
    return df

def compute():
    m=markets();sec=sectors();news=getnews("lite")
    def v(name,field,default=0):
        x=m[m["市场"]==name]
        return float(x.iloc[0][field]) if len(x) and pd.notna(x.iloc[0][field]) else default
    nas=v("纳斯达克","涨跌");vix=v("VIX","价格",20);tnx=v("美债10Y","价格",4.3);sox=v("SOX","涨跌")
    cp=sec.loc[sec["板块"]=="CPO/光通信","涨跌"];cp=float(cp.iloc[0]) if len(cp) and pd.notna(cp.iloc[0]) else 0
    sp=sec.loc[sec["板块"]=="半导体设备","涨跌"];sp=float(sp.iloc[0]) if len(sp) and pd.notna(sp.iloc[0]) else 0
    policy_bad=False if news.empty else ((news["新闻"].str.contains("限制|制裁|禁令|出口管制|restrict|sanction|ban",case=False,regex=True,na=False)) & news["可信度"].isin(["A","B"])).any()
    risk=45+(15 if tnx>=4.6 else 8 if tnx>=4.1 else 0)+(15 if vix>=30 else 8 if vix>=22 else 0)+(12 if policy_bad else 0)+(8 if nas<=-2 else 0)
    risk=min(100,risk)
    nasb=rules["纳指机会"] if nas<=-2.5 and tnx<4.6 and vix<32 else rules["纳指基础"]
    cpob=rules["CPO机会"] if cp<=-2 and not policy_bad else rules["CPO基础"]
    semib=rules["半导体机会"] if sp<=-2 else rules["半导体基础"]
    goldb=rules["黄金基础"]
    jxb=0 if policy_bad or tnx>=4.6 else rules["建信机会"] if nas<=-2 and vix<30 else rules["建信中档"]
    total=nasb+cpob+semib+goldb+jxb
    state="🔴 风险偏高" if risk>=75 else "🔵 回撤关注" if (nas<=-2 or cp<=-2 or sp<=-2) else "🟢 正常执行"
    return m,sec,news,dict(nas=nas,vix=vix,tnx=tnx,sox=sox,cp=cp,sp=sp,policy_bad=policy_bad,risk=risk,nasb=nasb,cpob=cpob,semib=semib,goldb=goldb,jxb=jxb,total=total,state=state)

m,sec,news,S=compute()

with st.sidebar:
    st.markdown("## 📊 阮嘤基金")
    st.caption("V28 · 手机极速版")
    page=st.radio("功能导航",[
        "🏠 今日驾驶舱","📈 市场看板","▦ 板块中心","💼 基金中心","📰 新闻中心",
        "🔥 机会与风险","🧠 决策大脑","📅 事件日历","🔗 重合度分析","🧬 底层穿透",
        "🎯 仓位目标","🛰 数据健康","💰 资金计划","🩺 组合体检","📒 投资日志",
        "☁️ 云端同步","🧾 持仓管理","⚙️ 投资规则"
    ],label_visibility="collapsed")
    st.markdown("---")
    st.metric("今日建议",f"¥{S['total']}")
    st.caption(f"纳指{S['nasb']} · 黄金{S['goldb']} · CPO{S['cpob']} · 半导体{S['semib']} · 建信{S['jxb']}")
    if st.button("🔄 立即刷新",use_container_width=True):
        st.cache_data.clear();st.rerun()
    st.caption("自动刷新：180秒 · 可手动立即刷新")
    st.caption("新闻库：" + (f"🟢 {len(news)} 条" if not news.empty else "🔴 暂不可用"))
    st.caption("云端同步：" + ("🟢 已连接" if CLOUD else "🟠 未连接"))

def render_news_cards(df,limit=20,prefix="n"):
    if df.empty:
        st.caption("暂无匹配新闻")
        return
    for i,(_,r) in enumerate(df.head(limit).iterrows()):
        lab="🟢 利好" if r["分数"]>=60 else "🔴 利空" if r["分数"]<=40 else "🟡 中性"
        pub=r["发布时间"].strftime("%m-%d %H:%M") if pd.notna(r["发布时间"]) else r["时间"]
        with st.container(border=True):
            st.markdown(f"**{lab}｜{r['主题']}｜重要度 {'★'*int(r['重要度'])}｜可信度 {r['可信度']}**")
            st.write(r["新闻"])
            st.caption(r["摘要"])
            st.caption(f"{pub} ｜ 影响基金：{r['影响基金']}")
            if r["链接"]:
                st.link_button("打开原文 ↗",r["链接"],key=f"{prefix}_{i}_{r.name}")


def top_terminal(S, news):
    now=datetime.now(TZ)
    ncount=len(news) if news is not None and not news.empty else 0
    health="正常" if ncount>0 else "部分数据异常"
    state=S["state"].replace("🟢 ","").replace("🔵 ","").replace("🔴 ","")
    st.markdown(f"""
    <div class="terminalbar">
      <div class="terminalcell"><div class="k">市场状态</div><div class="v">{state}</div></div>
      <div class="terminalcell"><div class="k">今日建议投入</div><div class="v">¥{S['total']}</div></div>
      <div class="terminalcell"><div class="k">风险温度</div><div class="v">{S['risk']} / 100</div></div>
      <div class="terminalcell"><div class="k">新闻情报</div><div class="v">{ncount} 条</div></div>
      <div class="terminalcell"><div class="k">数据状态</div><div class="v"><span class="statusdot"></span>{health}</div></div>
    </div>
    <div class="quickbar">
      <span class="quickpill">纳指 ¥{S['nasb']}</span>
      <span class="quickpill">黄金 ¥{S['goldb']}</span>
      <span class="quickpill">CPO ¥{S['cpob']}</span>
      <span class="quickpill">半导体 ¥{S['semib']}</span>
      <span class="quickpill">建信 ¥{S['jxb']}</span>
      <span class="quickpill">北京时间 {now.strftime('%H:%M:%S')}</span>
    </div>
    """,unsafe_allow_html=True)


def decision_reason_cards(S):
    items=[
        ("纳指",S["nasb"],[
            ("纳指跌幅",S["nas"]),
            ("VIX",S["vix"]),
            ("美债10Y",S["tnx"])
        ]),
        ("CPO",S["cpob"],[
            ("CPO代理涨跌",S["cp"]),
            ("政策风险",1 if S["policy_bad"] else 0)
        ]),
        ("半导体",S["semib"],[
            ("半导体代理涨跌",S["sp"]),
            ("SOX",S["sox"])
        ]),
        ("建信",S["jxb"],[
            ("纳指跌幅",S["nas"]),
            ("VIX",S["vix"]),
            ("美债10Y",S["tnx"])
        ])
    ]
    rows=[]
    for name,amount,signals in items:
        if name=="纳指":
            reason="回撤足够且风险可控→机会档；否则基础档"
        elif name=="CPO":
            reason="明显回撤且无高可信政策利空→机会档"
        elif name=="半导体":
            reason="明显回撤→机会档；否则基础档"
        else:
            reason="政策风险/高美债→0；普通环境→50；明显回撤且风险可控→100"
        rows.append([name,amount,reason," / ".join(f"{k}:{v:.2f}" if isinstance(v,(int,float)) else f"{k}:{v}" for k,v in signals)])
    return pd.DataFrame(rows,columns=["对象","今日金额","规则解释","关键输入"])

def news_impact_table(news):
    if news is None or news.empty:
        return pd.DataFrame(columns=["主题","新闻面","影响基金","强度"])
    rows=[]
    for topic,g in news.groupby("主题"):
        avg=float(g["分数"].mean())
        cnt=len(g)
        grade_bonus=(g["可信度"].isin(["A","B"])).mean()
        strength=min(100,round(abs(avg-50)*1.4 + cnt*2 + grade_bonus*20))
        face="🟢 利好" if avg>=60 else "🔴 利空" if avg<=40 else "🟡 中性"
        funds="、".join(FUND_MAP.get(topic,[])) or "观察"
        rows.append([topic,face,funds,strength])
    return pd.DataFrame(rows,columns=["主题","新闻面","影响基金","强度"]).sort_values("强度",ascending=False)

def overlap_matrix():
    exposure = {
        "易方达全球成长精选":{"AI":1,"半导体":1,"CPO":1,"存储":1},
        "建信新兴市场":{"AI":1,"半导体":1,"CPO":1,"存储":1},
        "华夏移动互联":{"AI":1,"半导体":1,"CPO":0.5,"存储":1},
        "德邦鑫星/CPO":{"AI":1,"半导体":0.5,"CPO":1,"存储":0},
        "东方人工智能/半导体":{"AI":0.5,"半导体":1,"CPO":0,"存储":0},
        "国泰纳斯达克100":{"AI":1,"半导体":0.8,"CPO":0.3,"存储":0.5},
        "华安黄金ETF联接C":{"AI":0,"半导体":0,"CPO":0,"存储":0},
    }
    names=list(exposure)
    mat=[]
    for a in names:
        row=[]
        va=exposure[a]
        for b in names:
            vb=exposure[b]
            dot=sum(va[k]*vb[k] for k in va)
            na=sum(va[k]**2 for k in va)**0.5
            nb=sum(vb[k]**2 for k in vb)**0.5
            sim=0 if na==0 or nb==0 else dot/(na*nb)
            row.append(round(sim*100))
        mat.append(row)
    return pd.DataFrame(mat,index=names,columns=names)


def true_holding_overlap():
    funds=[f for f in TOP_HOLDINGS if f in PORT["基金"].tolist()]
    sets={f:set(x[0] for x in TOP_HOLDINGS[f]) for f in funds}
    matrix=[]
    for a in funds:
        row=[]
        for b in funds:
            A,B=sets[a],sets[b]
            union=len(A|B)
            score=0 if union==0 else round(len(A&B)/union*100)
            row.append(score)
        matrix.append(row)
    return pd.DataFrame(matrix,index=funds,columns=funds)

def aggregate_underlying():
    amount_map=dict(zip(PORT["基金"],PORT["金额"]))
    rows=[]
    total_port=float(PORT["金额"].sum())
    for fund,hs in TOP_HOLDINGS.items():
        famount=float(amount_map.get(fund,0))
        for stock,w in hs:
            est=famount*w/100
            rows.append([stock,fund,w,est])
    df=pd.DataFrame(rows,columns=["底层资产","基金","基金内权重%","估算金额"])
    if df.empty:return df,pd.DataFrame()
    agg=df.groupby("底层资产",as_index=False).agg(估算金额=("估算金额","sum"),出现基金数=("基金","nunique"))
    agg["占组合估算%"]=agg["估算金额"]/total_port*100 if total_port else 0
    agg=agg.sort_values("估算金额",ascending=False)
    return df,agg

def portfolio_exposure_view():
    mapping={
        "德邦鑫星/CPO":"CPO/光通信","东方人工智能/半导体":"半导体设备",
        "建信新兴市场":"海外AI/半导体","易方达全球成长精选":"海外科技/半导体",
        "华夏移动互联":"海外半导体","华安黄金ETF联接C":"黄金",
        "国泰纳斯达克100":"纳斯达克100","嘉实全球产业升级":"待迁移科技",
        "天弘全球高端制造":"待迁移科技","天弘越南市场C":"越南",
        "财通景气甄选一年持有":"锁定A股","同泰慧盈混合C":"其他"
    }
    x=PORT[["基金","金额"]].copy()
    x["风险桶"]=x["基金"].map(mapping).fillna("其他")
    g=x.groupby("风险桶",as_index=False)["金额"].sum()
    g["占比%"]=g["金额"]/g["金额"].sum()*100
    return g.sort_values("占比%",ascending=False)

def data_health_table(m,sec,news):
    rows=[]
    rows.append(["全球行情", "正常" if m[m["市场"].isin(["纳斯达克","标普500","VIX"])][["价格"]].notna().any().any() else "异常", "60秒缓存", "Yahoo Finance"])
    rows.append(["A股指数", "正常" if m[m["市场"].isin(["上证","创业板","科创50"])]["价格"].notna().any() else "部分异常", "60秒缓存", "东方财富/腾讯/Yahoo回退"])
    rows.append(["板块代理", "正常" if sec["涨跌"].notna().any() else "异常", "180秒缓存", "腾讯核心成分代理"])
    rows.append(["新闻情报", f"正常（{len(news)}条）" if news is not None and not news.empty else "异常", "600秒缓存", "Google News RSS"])
    rows.append(["基金底层持仓", f"静态快照 {HOLDINGS_ASOF}", "季度更新", "已知基金季报数据"])
    rows.append(["本地日志/规则", "可用但非永久云存储", "即时", "Streamlit实例本地文件"])
    return pd.DataFrame(rows,columns=["模块","状态","刷新频率","来源/说明"])

def export_backup_bytes():
    import zipfile, io
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        for fname in ["investment_log.csv","portfolio.csv","portfolio_snapshots.csv","rules.json","budget.json","event_calendar.json"]:
            fp=os.path.join(DATA_DIR,fname)
            if os.path.exists(fp):
                z.write(fp,arcname=fname)
    buf.seek(0)
    return buf.getvalue()

def save_snapshot(port):
    now=datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    tmp=port[["基金","金额"]].copy()
    tmp["日期"]=now
    tmp.to_csv(SNAPSHOT_FILE,mode="a",header=not os.path.exists(SNAPSHOT_FILE),index=False,encoding="utf-8-sig")

@st.fragment(run_every="180s")
def render(page):


    m,sec,news,S=compute()
    now=datetime.now(TZ)
    st.markdown(f"# {page}")
    top_terminal(S,news)
    st.caption(f"数据每60秒自动刷新 ｜ 最近刷新：{now.strftime('%Y-%m-%d %H:%M:%S')}（北京时间）")

    if page=="🏠 今日驾驶舱":
        st.info(f"今日执行：固定核心继续定投；动态仓根据风险调整。当前建议合计 ¥{S['total']}。")
        A,B=st.columns([1,1.4])
        with A:
            fig=go.Figure(go.Indicator(mode="gauge+number",value=S["risk"],title={"text":"市场风险温度"},gauge={"axis":{"range":[0,100]},"bar":{"thickness":.22},"steps":[{"range":[0,45]},{"range":[45,70]},{"range":[70,100]}]}))
            fig.update_layout(height=220,margin=dict(l=10,r=10,t=40,b=5))
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
            x,y,z=st.columns(3);x.metric("VIX",f"{S['vix']:.1f}");y.metric("美债10Y",f"{S['tnx']:.2f}");z.metric("SOX",f"{S['sox']:+.2f}%")
            st.subheader("今天不要做什么")
            st.warning("不追涨单日大涨板块；不在高可信基本面利空下机械抄底；不动用未来定投资金凑满仓。")
        with B:
            st.subheader("📰 今日重点新闻")
            render_news_cards(news.head(8) if not news.empty else news,8,"home")
        st.subheader("🧭 新闻影响速览")
        nit=news_impact_table(news)
        if not nit.empty:
            st.dataframe(nit.head(8),hide_index=True,use_container_width=True)
        C,D=st.columns(2)
        with C:
            st.subheader("📊 板块涨跌")
            show=sec.copy()
            show["判断"]=show["涨跌"].apply(lambda x:"🔵 回撤关注" if pd.notna(x) and x<=-2 else "🟡 不追涨" if pd.notna(x) and x>=3 else "🟢 正常")
            st.dataframe(show[["板块","涨跌","判断","核心成分"]],hide_index=True,use_container_width=True,height=360)
        with D:
            st.subheader("🔥 机会与风险")
            opp=sec.dropna(subset=["涨跌"]).copy();opp["机会分"]=opp["涨跌"].apply(lambda x:85 if x<=-2 else 60 if x<1 else 50)
            st.dataframe(opp.sort_values("机会分",ascending=False).head(5)[["板块","涨跌","机会分","核心成分"]],hide_index=True,use_container_width=True)
            st.info(f"风险TOP：美债10Y {S['tnx']:.2f} / VIX {S['vix']:.1f} / 政策风险 {'触发' if S['policy_bad'] else '未触发'}")

    elif page=="📈 市场看板":
        cols=st.columns(3)
        for i,(_,r) in enumerate(m.iterrows()):
            if pd.notna(r["价格"]): cols[i%3].metric(r["市场"],f'{r["价格"]:.2f}',f'{r["涨跌"]:+.2f}%')
            else: cols[i%3].metric(r["市场"],"暂不可用")
        st.subheader("市场风险解释")
        st.dataframe(pd.DataFrame([
            ["VIX",S["vix"],"波动率","<20偏低，>30风险明显"],
            ["美债10Y",S["tnx"],"科技估值压力",">=4.6时减少动态仓"],
            ["SOX",S["sox"],"AI硬件风险偏好","观察半导体强弱"]
        ],columns=["指标","当前","作用","规则"]),hide_index=True,use_container_width=True)

    elif page=="▦ 板块中心":
        chosen=st.selectbox("选择板块",list(BASKETS.keys()))
        r=sec[sec["板块"]==chosen].iloc[0]
        a,b,c=st.columns(3)
        a.metric("代理涨跌","—" if pd.isna(r["涨跌"]) else f'{r["涨跌"]:+.2f}%')
        b.metric("风险温度",f"{S['risk']}/100")
        c.metric("状态","回撤关注" if pd.notna(r["涨跌"]) and r["涨跌"]<=-2 else "观察")
        st.subheader("近1个月核心成分走势")
        hist=sector_history(chosen)
        if hist.empty:
            st.caption("历史行情暂不可用")
        else:
            st.plotly_chart(px.line(hist,x="交易日序号",y="累计涨跌%",color="股票"),use_container_width=True)
        st.subheader("核心成分"); st.write(r["核心成分"])
        key="CPO" if "CPO" in chosen else "半导体" if "半导体" in chosen else chosen
        rel=news[news["主题"].str.contains(key,na=False)] if not news.empty else pd.DataFrame()
        st.subheader("相关新闻")
        render_news_cards(rel,20,"sector")
        if chosen=="CPO/光通信": st.info(f"基础 {rules['CPO基础']} 元；明显回撤且逻辑未坏 → {rules['CPO机会']} 元。")
        elif chosen=="半导体设备": st.info(f"基础 {rules['半导体基础']} 元；机会档 {rules['半导体机会']} 元。")
        else: st.caption("战术观察池，不自动挤占核心定投资金。")

    elif page=="💼 基金中心":
        chosen=st.selectbox("选择我的基金",PORT["基金"].tolist())
        r=PORT[PORT["基金"]==chosen].iloc[0]
        a,b,c,d=st.columns(4)
        a.metric("当前金额",f'¥{r["金额"]:,.2f}'); b.metric("定位",r["定位"]); c.metric("主要暴露",r["主要暴露"]); d.metric("动作",r["动作"])
        target=float(r.get("目标金额",0) or 0)
        if target>0:
            st.subheader("目标仓位进度")
            st.progress(min(1,float(r["金额"])/target))
            st.caption(f'当前 ¥{r["金额"]:.0f} / 目标 ¥{target:.0f}，剩余约 ¥{max(0,target-float(r["金额"])):.0f}')
        if r["定位"]=="待迁移": st.warning("迁移仓：只减不加；优先转向纳指/建信。")
        elif r["定位"]=="锁定": st.warning("锁定仓：未到可赎回日前不新增。")
        else: st.info("按当前定位执行。")
        keys=r["主要暴露"].replace("海外","").split("/")
        rel=news[news["主题"].apply(lambda x:any(k and k.lower() in x.lower() for k in keys))] if not news.empty else pd.DataFrame()
        st.subheader("相关新闻")
        render_news_cards(rel,20,"fund")

    elif page=="📰 新闻中心":
        news=getnews("full")
        if news.empty:
            st.warning("新闻源暂不可用")
        else:
            st.metric("当前新闻库",f"{len(news)} 条")
            a,b,c=st.columns(3)
            topic=a.selectbox("主题",["全部"]+sorted(news["主题"].unique().tolist()))
            grades=b.multiselect("可信度",["A","B","C"],default=["A","B","C"])
            days=c.selectbox("时间范围",["全部","24小时","3天","7天"],index=2)
            x=news.copy()
            if topic!="全部": x=x[x["主题"]==topic]
            x=x[x["可信度"].isin(grades)]
            if days!="全部":
                hours={"24小时":24,"3天":72,"7天":168}[days]
                cutoff=datetime.now(TZ)-pd.Timedelta(hours=hours)
                x=x[(x["发布时间"].isna())|(x["发布时间"]>=cutoff)]
            col1,col2=st.columns(2)
            with col1:
                st.subheader("最新新闻")
                render_news_cards(x.sort_values("发布时间",ascending=False,na_position="last"),30,"latest")
            with col2:
                st.subheader("重大新闻")
                render_news_cards(x.sort_values(["重要度","分数"],ascending=[False,False]),30,"major")

    elif page=="🔥 机会与风险":
        L,R=st.columns(2)
        with L:
            st.subheader("🔥 机会 TOP5")
            x=sec.dropna(subset=["涨跌"]).copy(); x["机会分"]=x["涨跌"].apply(lambda z:85 if z<=-2 else 65 if z<=0 else 50)
            st.dataframe(x.sort_values("机会分",ascending=False).head(5)[["板块","涨跌","机会分","核心成分"]],hide_index=True,use_container_width=True)
        with R:
            st.subheader("🚨 风险 TOP5")
            risks=pd.DataFrame([
                ["美债收益率",S["tnx"],90 if S["tnx"]>=4.6 else 60],
                ["VIX",S["vix"],90 if S["vix"]>=30 else 55],
                ["政策风险","触发" if S["policy_bad"] else "未触发",95 if S["policy_bad"] else 30],
                ["纳指单日",S["nas"],80 if S["nas"]<=-2.5 else 40],
                ["CPO单日",S["cp"],80 if S["cp"]<=-3 else 40],
            ],columns=["风险","当前","风险分"])
            st.dataframe(risks.sort_values("风险分",ascending=False),hide_index=True,use_container_width=True)
        st.subheader("🧯 下跌预案")
        st.dataframe(pd.DataFrame([
            ["纳指","≤-2.5%","AI逻辑正常+VIX可控",f"{rules['纳指基础']}→{rules['纳指机会']}"],
            ["CPO","≤-2%","无重大政策利空",f"{rules['CPO基础']}→{rules['CPO机会']}"],
            ["半导体","≤-2%","产业逻辑正常",f"{rules['半导体基础']}→{rules['半导体机会']}"],
            ["基本面恶化","任何跌幅","高可信重大利空","不机械抄底"]
        ],columns=["对象","触发","确认","动作"]),hide_index=True,use_container_width=True)

    elif page=="🧠 决策大脑":
        st.subheader("今天为什么这样买")
        st.dataframe(decision_reason_cards(S),hide_index=True,use_container_width=True)
        st.subheader("新闻对我的钱有什么影响")
        nit=news_impact_table(news)
        if nit.empty:
            st.caption("暂无可用新闻影响数据")
        else:
            st.dataframe(nit,hide_index=True,use_container_width=True)
        st.subheader("今天不该做什么")
        stop=[]
        if S["tnx"]>=4.6: stop.append("美债压力高：不要把纳指/建信直接打到满档。")
        if S["vix"]>=30: stop.append("VIX偏高：不要把单日大跌机械当成便宜。")
        if S["policy_bad"]: stop.append("存在高可信政策风险：CPO动态仓优先收缩。")
        if not stop: stop.append("没有触发重大禁区，但仍不要追涨单日大涨板块。")
        for x in stop: st.warning(x)
        st.subheader("下一步触发器")
        st.dataframe(pd.DataFrame([
            ["纳指","跌到≤-2.5%且VIX<32、美债<4.6",f"提高到¥{rules['纳指机会']}"],
            ["CPO","跌到≤-2%且无高可信政策利空",f"提高到¥{rules['CPO机会']}"],
            ["半导体","跌到≤-2%且产业逻辑正常",f"提高到¥{rules['半导体机会']}"],
            ["建信","纳指≤-2%、VIX<30、美债<4.6",f"提高到¥{rules['建信机会']}"],
        ],columns=["对象","触发条件","动作"]),hide_index=True,use_container_width=True)

    elif page=="📅 事件日历":
        st.subheader("未来重要事件")
        ev=pd.DataFrame(events)
        if not ev.empty:
            st.dataframe(ev,hide_index=True,use_container_width=True)
        st.caption("日期为空的事件不会被工作台伪造；你可以在下面手动维护可靠日期。")
        edited=st.data_editor(ev,use_container_width=True,hide_index=True,num_rows="dynamic")
        if st.button("保存事件日历"):
            save_json(EVENT_FILE,{"events":edited.to_dict("records")})
            st.success("已保存事件日历")
        st.subheader("事件影响规则")
        st.dataframe(pd.DataFrame([
            ["CPI/非农/FOMC","美债、纳指、黄金","重大事件前不提前打满动态仓"],
            ["NVIDIA财报","纳指、建信、CPO","财报前控制机会仓，财报后再看订单/CapEx"],
            ["出口管制","CPO、国产半导体","高可信确认后停止机械抄底"],
        ],columns=["事件","主要影响","规则"]),hide_index=True,use_container_width=True)

    elif page=="🔗 重合度分析":
        tab1,tab2=st.tabs(["真实重仓股重合","风险暴露相似度"])
        with tab1:
            st.subheader(f"重仓股交集矩阵 · 数据截至 {HOLDINGS_ASOF}")
            mat=true_holding_overlap()
            if mat.empty:
                st.caption("暂无可计算的重仓股数据")
            else:
                fig=px.imshow(mat,text_auto=True,aspect="auto",zmin=0,zmax=100)
                fig.update_layout(height=560)
                st.plotly_chart(fig,use_container_width=True)
                st.info("这里按已知Top10重仓股名称交集计算，是真实持仓快照层面的重合，不代表全部持仓实时重合率。")
        with tab2:
            st.subheader("风险暴露相似度")
            mat=overlap_matrix()
            fig=px.imshow(mat,text_auto=True,aspect="auto",zmin=0,zmax=100)
            fig.update_layout(height=560)
            st.plotly_chart(fig,use_container_width=True)
            st.info("该矩阵按AI/半导体/CPO/存储等风险因子近似，用来观察风格相关性。")
        st.subheader("组合结构提醒")
        st.write("多只科技基金底层仍高度集中在AI硬件、半导体、存储与光通信链条；黄金承担主要低相关防守作用。")

    elif page=="🧬 底层穿透":
        st.subheader(f"基金底层持仓穿透 · 已知数据截至 {HOLDINGS_ASOF}")
        raw,agg=aggregate_underlying()
        if agg.empty:
            st.caption("暂无可穿透数据")
        else:
            c1,c2,c3=st.columns(3)
            c1.metric("可穿透基金数",len(TOP_HOLDINGS))
            c2.metric("识别底层资产",agg["底层资产"].nunique())
            c3.metric("多基金重复资产",int((agg["出现基金数"]>=2).sum()))
            st.subheader("组合底层资产 TOP20")
            st.dataframe(agg.head(20),hide_index=True,use_container_width=True)
            fig=px.bar(agg.head(15).sort_values("估算金额"),x="估算金额",y="底层资产",orientation="h")
            st.plotly_chart(fig,use_container_width=True)
            repeated=agg[agg["出现基金数"]>=2].head(20)
            st.subheader("重复暴露")
            if repeated.empty:
                st.caption("Top10快照中没有重复资产")
            else:
                st.dataframe(repeated,hide_index=True,use_container_width=True)
            st.caption("估算金额 = 当前基金金额 × 季报重仓权重，仅用于看穿透方向，不等同于实时净值中的真实金额。")
        chosen=st.selectbox("查看单只基金Top10",list(TOP_HOLDINGS.keys()))
        h=pd.DataFrame(TOP_HOLDINGS[chosen],columns=["重仓资产","权重%"])
        st.dataframe(h,hide_index=True,use_container_width=True)

    elif page=="🎯 仓位目标":
        st.subheader("当前组合风险桶")
        exp=portfolio_exposure_view()
        a,b=st.columns([1,1])
        with a:
            st.dataframe(exp,hide_index=True,use_container_width=True)
        with b:
            st.plotly_chart(px.pie(exp,names="风险桶",values="金额",hole=.48),use_container_width=True)
        st.subheader("仓位管理清单")
        x=PORT[["基金","金额","定位","动作","目标金额"]].copy()
        x["目标进度%"]=x.apply(lambda r: round(r["金额"]/r["目标金额"]*100,1) if pd.notna(r["目标金额"]) and r["目标金额"]>0 else None,axis=1)
        st.dataframe(x,hide_index=True,use_container_width=True)
        st.subheader("结构性提醒")
        tech=float(exp[~exp["风险桶"].isin(["黄金","越南","其他","锁定A股"])]["金额"].sum())
        total=float(exp["金额"].sum())
        tech_pct=tech/total*100 if total else 0
        st.metric("科技/成长相关仓估算占比",f"{tech_pct:.1f}%")
        if tech_pct>=70:
            st.warning("科技成长相关暴露较高。新增资金优先考虑不要继续重复堆叠同一条AI硬件风险链。")
        else:
            st.info("当前科技成长暴露尚未触发本页70%的高集中提醒。")

    elif page=="🛰 数据健康":
        st.subheader("数据源健康检查")
        health=data_health_table(m,sec,news)
        st.dataframe(health,hide_index=True,use_container_width=True)
        ok=(health["状态"].str.contains("正常")).sum()
        a,b,c=st.columns(3)
        a.metric("正常模块",f"{ok}/{len(health)}")
        b.metric("新闻数量",len(news) if news is not None else 0)
        c.metric("持仓快照",HOLDINGS_ASOF)
        st.subheader("刷新与数据边界")
        st.info("页面180秒轻量自动刷新；行情缓存60秒；板块180秒；新闻600秒。基金持仓不是实时数据，按季报快照展示。板块涨跌是核心成分代理，不冒充官方行业指数。")
        st.warning("Streamlit Community Cloud 的本地文件可能在重启/重新部署后丢失，所以日志、规则、持仓修改不能视为永久云存储。")
        st.subheader("一键备份")
        st.download_button("下载全部工作台数据备份 ZIP",export_backup_bytes(),"ruanying_dashboard_backup.zip","application/zip",use_container_width=True)
        st.caption("备份包含已存在的投资日志、持仓、持仓快照、规则、预算和事件日历。")

    elif page=="💰 资金计划":
        newbudget=st.number_input("本月最大投资预算",min_value=0,value=int(budget["月预算"]),step=500)
        if st.button("保存月预算"): save_json(BUDGET_FILE,{"月预算":newbudget}); st.success("已保存")
        spent=0
        if os.path.exists(LOG_FILE):
            try:
                lg=pd.read_csv(LOG_FILE); lg["日期"]=pd.to_datetime(lg["日期"]); now=datetime.now(TZ)
                this=lg[(lg["日期"].dt.year==now.year)&(lg["日期"].dt.month==now.month)]
                cols=[c for c in this.columns if c.startswith("实际_")]; spent=float(this[cols].sum().sum()) if cols else 0
            except: pass
        rem=max(0,newbudget-spent)
        a,b,c=st.columns(3); a.metric("月预算",f"¥{newbudget:,.0f}"); b.metric("已记录投入",f"¥{spent:,.0f}"); c.metric("剩余预算",f"¥{rem:,.0f}")
        st.progress(min(1,spent/newbudget) if newbudget else 0)
        daily=max(1,S["total"]); st.caption(f"按今天 ¥{S['total']} 的节奏，剩余预算理论上可支持约 {int(rem/daily)} 个交易日。")
        amount=st.select_slider("额外资金",options=[0,500,1000,2000,5000],value=500)
        cash=.55 if S["risk"]>=70 else .4
        if amount:
            w={"纳指":.20,"CPO":.15,"半导体":.10,"其他机会":max(0,1-cash-.45),"现金":cash}
            al=pd.DataFrame(w.items(),columns=["去向","比例"]); al["金额"]=(al["比例"]*amount).round(-1).astype(int)
            st.dataframe(al[["去向","金额"]],hide_index=True,use_container_width=True)

    elif page=="🩺 组合体检":
        exp=portfolio_exposure_view()
        total=float(PORT["金额"].sum())
        gold=float(PORT.loc[PORT["基金"]=="华安黄金ETF联接C","金额"].sum())
        pending=float(PORT.loc[PORT["定位"].isin(["待迁移","锁定","待评估"]),"金额"].sum())
        gold_score=min(100,round((gold/total*100)*4)) if total else 0
        pending_score=max(0,100-round(pending/total*100*2)) if total else 0
        a,b,c,d=st.columns(4)
        a.metric("科技集中度","高" if total and (1-gold/total)>0.75 else "中")
        b.metric("基金数量",len(PORT))
        c.metric("黄金防守",f"{gold_score}/100")
        d.metric("可管理性",f"{pending_score}/100")
        ex=pd.DataFrame([["AI/半导体",29],["CPO/光通信",18],["黄金",15],["海外科技",17],["其他/待迁移",19],["越南",2]],columns=["行业","占比"])
        L,R=st.columns(2); L.plotly_chart(px.pie(ex,names="行业",values="占比",hole=.5),use_container_width=True)
        with R:
            st.warning("主要问题：多只基金底层集中在 AI硬件、半导体和光通信。")
            st.dataframe(PORT[PORT["定位"].isin(["待迁移","接近封顶","锁定","待评估"])][["基金","定位","动作"]],hide_index=True,use_container_width=True)
        st.subheader("全部持仓")
        st.dataframe(PORT,hide_index=True,use_container_width=True)

    elif page=="📒 投资日志":
        actual={}
        for k,dft in [("纳指",S["nasb"]),("黄金",S["goldb"]),("CPO",S["cpob"]),("半导体",S["semib"]),("建信",S["jxb"])]:
            actual[k]=st.number_input(k,min_value=0,value=int(dft),step=10,key="log"+k)
        if st.button("保存今日投资记录"):
            rec={"日期":datetime.now(TZ).strftime("%Y-%m-%d %H:%M"),"市场状态":S["state"],"建议总额":S["total"],
                 **{f"建议_{k}":v for k,v in {"纳指":S["nasb"],"黄金":S["goldb"],"CPO":S["cpob"],"半导体":S["semib"],"建信":S["jxb"]}.items()},
                 **{f"实际_{k}":v for k,v in actual.items()}}
            duplicate=False
            if os.path.exists(LOG_FILE):
                try:
                    oldlog=pd.read_csv(LOG_FILE)
                    if len(oldlog):
                        last=oldlog.iloc[-1]
                        same_day=str(last.get("日期",""))[:10]==rec["日期"][:10]
                        same_actual=all(float(last.get(f"实际_{k}",-1))==float(v) for k,v in actual.items())
                        # 同一天、同一组实际金额，视为重复点击，不再次写入。
                        duplicate=same_day and same_actual
                except Exception:
                    duplicate=False
            if duplicate:
                st.warning("检测到今天已有相同投资记录，本次未重复保存。")
            else:
                pd.DataFrame([rec]).to_csv(LOG_FILE,mode="a",header=not os.path.exists(LOG_FILE),index=False,encoding="utf-8-sig")
                if CLOUD:
                    suggested={"纳指":S["nasb"],"黄金":S["goldb"],"CPO":S["cpob"],"半导体":S["semib"],"建信":S["jxb"]}
                    cloud_insert("investment_logs",[{"log_date":datetime.now(TZ).strftime("%Y-%m-%d"),"fund_name":k,"suggested_amount":float(suggested[k]),"actual_amount":float(v),"note":S["state"]} for k,v in actual.items()])
                st.success("已保存；云端连接正常时会自动同步")
        if os.path.exists(LOG_FILE):
            lg=pd.read_csv(LOG_FILE)
            st.dataframe(lg.tail(30),hide_index=True,use_container_width=True)
            if "建议总额" in lg.columns:
                c1,c2,c3=st.columns(3)
                c1.metric("累计建议投入",f"¥{lg['建议总额'].sum():,.0f}")
                c2.metric("记录次数",len(lg))
                actual_cols=[c for c in lg.columns if c.startswith("实际_")]
                if actual_cols:
                    c3.metric("累计实际投入",f"¥{lg[actual_cols].sum().sum():,.0f}")
            st.download_button("下载投资日志 CSV",lg.to_csv(index=False).encode("utf-8-sig"),"investment_log.csv","text/csv")
        else: st.caption("保存第一条记录后开始形成历史。")

    elif page=="☁️ 云端同步":
        st.subheader("云端同步状态")
        a,b,c=st.columns(3)
        a.metric("Supabase","已连接" if CLOUD else "未连接")
        b.metric("当前持仓",len(PORT))
        c.metric("云端快照",len(cloud_select("portfolio_snapshots")) if CLOUD else 0)
        if CLOUD:
            if "SUPABASE_SERVICE_KEY" in st.secrets:
                st.success("已使用服务端密钥连接 Supabase，可跨设备持久化保存。")
            else:
                st.info("已使用 Publishable Key 连接；由于 RLS 已开启，写入可能被数据库拒绝。")
            if st.button("把当前持仓同步到云端",use_container_width=True):
                save_port(PORT);st.success("已发起同步")
        else:
            st.warning("没有读取到 SUPABASE_URL / SUPABASE_KEY。")
        st.info("手机、iPad、电脑访问同一个网址时，云端数据会保持一致。")

    elif page=="🧾 持仓管理":
        st.subheader("编辑当前持仓")
        edited=st.data_editor(PORT,use_container_width=True,hide_index=True,num_rows="dynamic")
        if st.button("保存持仓修改"):
            save_port(edited)
            save_snapshot(edited)
            if CLOUD:
                cloud_insert("portfolio_snapshots",[{"snapshot_time":datetime.now(TZ).isoformat(),"fund_name":str(r["基金"]),"amount":float(r["金额"])} for _,r in edited.iterrows()])
            st.success("已保存；云端连接正常时会同步到其他设备")
        st.download_button("下载持仓备份 CSV",edited.to_csv(index=False).encode("utf-8-sig"),"portfolio_backup.csv","text/csv")
        uploaded=st.file_uploader("恢复持仓备份",type=["csv"])
        if uploaded is not None:
            up=pd.read_csv(uploaded)
            st.dataframe(up,use_container_width=True)
            if st.button("确认恢复这份持仓"):
                save_port(up); st.success("已恢复，刷新页面后生效")
        if os.path.exists(SNAPSHOT_FILE):
            st.subheader("持仓变化记录")
            snap=pd.read_csv(SNAPSHOT_FILE)
            st.dataframe(snap.tail(40),hide_index=True,use_container_width=True)

    elif page=="⚙️ 投资规则":
        edited={}
        for k,v0 in rules.items():
            edited[k]=st.number_input(k,min_value=0,max_value=500,value=int(v0),step=10,key="rr"+k)
        if st.button("保存投资规则"): save_json(RULE_FILE,edited); st.success("已保存。")
        st.info("核心原则：价格下跌 ≠ 自动抄底。只有回撤 + 基本面未明显恶化，才进入机会档。")

render(page)
st.caption("V27：新增手机竖屏优化与 Supabase 云端同步基础。")
