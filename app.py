
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

st.set_page_config(page_title="阮嘤基金投资工作台 V34", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

HEADERS={"User-Agent":"Mozilla/5.0"}
TZ=ZoneInfo("Asia/Shanghai")
DATA_DIR="data"; os.makedirs(DATA_DIR,exist_ok=True)
RULE_FILE=os.path.join(DATA_DIR,"rules.json")
LOG_FILE=os.path.join(DATA_DIR,"investment_log.csv")
BUDGET_FILE=os.path.join(DATA_DIR,"budget.json")
PORT_FILE=os.path.join(DATA_DIR,"portfolio.csv")
SNAPSHOT_FILE=os.path.join(DATA_DIR,"portfolio_snapshots.csv")
EVENT_FILE=os.path.join(DATA_DIR,"event_calendar.json")
HOLDINGS_FILE=os.path.join(DATA_DIR,"fund_holdings.json")


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



/* ===== V31 顶部二级导航 ===== */
div[role="radiogroup"][aria-label="二级导航"]{
  display:flex!important;flex-wrap:wrap!important;gap:6px!important;margin:2px 0 10px!important;
}
div[role="radiogroup"][aria-label="二级导航"] > label{
  min-height:36px!important;padding:4px 10px!important;border:1px solid #e3e8ef!important;
  border-radius:999px!important;background:#fff!important;
}
div[role="radiogroup"][aria-label="二级导航"] > label:has(input:checked){
  background:#eaf3ff!important;border-color:#b8d5ff!important;color:#1268d9!important;
}

/* ===== V30 iPad 专项布局 ===== */
@media (min-width:701px) and (max-width:1366px){
  .block-container{padding:.55rem .72rem 1.8rem!important;max-width:1180px!important}
  section[data-testid="stSidebar"]{width:245px!important}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label{
    min-height:48px!important;font-size:14px!important;padding:0 12px!important
  }
  .terminalbar{grid-template-columns:1fr 1fr!important;gap:7px!important}
  .terminalcell{min-height:54px!important;padding:8px 10px!important}
  .terminalcell .v{font-size:14px!important}
  [data-testid="stMetric"]{padding:8px 10px!important}
  [data-testid="stMetricValue"]{font-size:1.55rem!important}
  div[data-testid="stHorizontalBlock"]{gap:.5rem!important}
  [data-testid="stPlotlyChart"]{max-height:430px!important}
  .card{padding:10px 12px!important}
}

/* 今日建议大卡片 */
.advice-hero{
  background:#ffffff;
  border:1px solid #dfe6ef;
  border-radius:14px;
  padding:14px 16px;
  margin:6px 0 12px 0;
  box-shadow:0 2px 10px rgba(20,40,80,.045);
}
.advice-title{font-size:17px;font-weight:800;color:#172033;margin-bottom:4px}
.advice-sub{font-size:12px;color:#7d8796;margin-bottom:10px}
.advice-grid{
  display:grid;grid-template-columns:1fr 1fr;gap:8px;
}
.advice-item{
  border:1px solid #edf0f4;border-radius:10px;padding:9px 10px;background:#fbfcfe;
}
.advice-item .name{font-size:12px;color:#7b8494}
.advice-item .amt{font-size:20px;font-weight:800;color:#172033}
.advice-item .why{font-size:12px;color:#596579;line-height:1.45;margin-top:3px}
@media(max-width:700px){
  .advice-grid{grid-template-columns:1fr!important}
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


@st.cache_resource
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


def cloud_table_exists(table):
    if not CLOUD:return False
    try:
        CLOUD.table(table).select("*").limit(1).execute()
        return True
    except Exception:
        return False

@st.cache_data(ttl=120)
def cloud_kv_get(key):
    if not CLOUD:return None
    try:
        rows=CLOUD.table("dashboard_kv").select("value").eq("key",key).limit(1).execute().data or []
        return rows[0]["value"] if rows else None
    except Exception:
        return None

def cloud_kv_set(key,value):
    if not CLOUD:return False
    try:
        CLOUD.table("dashboard_kv").upsert(
            {"key":key,"value":value,"updated_at":datetime.now(TZ).isoformat()},
            on_conflict="key"
        ).execute()
        cloud_kv_get.clear()
        return True
    except Exception:
        return False

def cloud_decision_insert(payload):
    if not CLOUD:return False
    try:
        CLOUD.table("decision_history").insert({
            "created_at":payload.get("time"),
            "market_state":payload.get("market_state"),
            "risk":payload.get("risk"),
            "vix":payload.get("vix"),
            "us10y":payload.get("us10y"),
            "nasdaq_change":payload.get("nasdaq_change"),
            "cpo_proxy":payload.get("cpo_proxy"),
            "semi_proxy":payload.get("semi_proxy"),
            "plan_total":payload.get("plan_total"),
            "payload":payload
        }).execute()
        return True
    except Exception:
        return False

DEFAULT_RULES={"纳指基础":50,"纳指机会":100,"CPO基础":20,"CPO机会":40,"半导体基础":10,"半导体机会":20,"黄金基础":50,"建信中档":50,"建信机会":100}
DEFAULT_PORT=pd.DataFrame([
["易方达全球成长精选",3531.83,"海外科技/半导体","动态持有","每日重评：可加/持/减",0],
["华安黄金ETF联接C",2308.43,"黄金","核心防守","基础50/日+动态重评",0],
["德邦鑫星/CPO",1367.42,"CPO/光通信/PCB","核心成长","基础20/日+动态重评",0],
["建信新兴市场",1303.94,"AI/半导体/HBM","动态核心","每日重评：0/50/100或减仓",0],
["华夏移动互联",907.77,"海外半导体/存储","动态持有","基础10/日+动态重评",1000],
["东方人工智能/半导体",820.49,"国产半导体设备","核心成长","基础10/日+动态重评",0],
["嘉实全球产业升级",737.59,"全球科技","动态优化","每日重评：可加/持/减",0],
["天弘全球高端制造",620.09,"科技制造","动态优化","每日重评：可加/持/减",0],
["同泰慧盈混合C",474.02,"有色金属","机会仓","每日重评：可加/持/减",0],
["天弘越南市场C",308.69,"越南","卫星","每日重评：可加/持/减",0],
["国泰纳斯达克100",401.06,"纳斯达克100","核心","基础50/日+动态重评",0],
],columns=["基金","金额","主要暴露","定位","动作","目标金额"])

def cloud_delete_ids(table, ids):
    if not CLOUD or not ids:
        return False
    ok=True
    for rid in ids:
        try:
            CLOUD.table(table).delete().eq("id", int(rid)).execute()
        except Exception:
            ok=False
    return ok



def _setting_key_from_path(path):
    name=os.path.basename(path)
    return {
        "rules.json":"rules",
        "budget.json":"budget",
        "event_calendar.json":"events"
    }.get(name)

def load_json(path,default):
    key=_setting_key_from_path(path)
    if key:
        cloud_value=cloud_kv_get(key)
        if isinstance(cloud_value,dict):
            return {**default,**cloud_value}
    try:
        with open(path,"r",encoding="utf-8") as f:
            return {**default,**json.load(f)}
    except:
        return default.copy()

def save_json(path,obj):
    with open(path,"w",encoding="utf-8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)
    key=_setting_key_from_path(path)
    if key:
        cloud_kv_set(key,obj)
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



def normalize_holdings_dict(raw):
    out={}
    for fund,rows in (raw or {}).items():
        clean=[]
        for row in rows or []:
            try:
                if isinstance(row,dict):
                    name=str(row.get("name") or row.get("asset") or "").strip()
                    weight=float(row.get("weight") or row.get("weight_pct") or 0)
                else:
                    name=str(row[0]).strip()
                    weight=float(row[1])
                if name:
                    clean.append((name,weight))
            except Exception:
                pass
        if clean:
            out[str(fund)]=clean
    return out

def save_holdings_store(store, asof=None):
    payload={
        "asof":asof or datetime.now(TZ).strftime("%Y-%m-%d"),
        "funds":{k:[{"name":n,"weight":w} for n,w in v] for k,v in store.items()}
    }
    with open(HOLDINGS_FILE,"w",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,indent=2)
    cloud_kv_set("fund_holdings",payload)

def load_holdings_store(default_store, default_asof):
    cloud_raw=cloud_kv_get("fund_holdings")
    if isinstance(cloud_raw,dict):
        funds=normalize_holdings_dict(cloud_raw.get("funds",{}))
        if funds:
            return funds, cloud_raw.get("asof") or default_asof
    try:
        with open(HOLDINGS_FILE,"r",encoding="utf-8") as f:
            raw=json.load(f)
        funds=normalize_holdings_dict(raw.get("funds",{}))
        if funds:
            return funds, raw.get("asof") or default_asof
    except Exception:
        pass
    return default_store, default_asof

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
TOP_HOLDINGS,HOLDINGS_ASOF=load_holdings_store(TOP_HOLDINGS,HOLDINGS_ASOF)

FUND_MAP={
"CPO/光通信":["德邦鑫星/CPO","易方达全球成长精选","建信新兴市场"],
"AI/算力":["国泰纳斯达克100","建信新兴市场","易方达全球成长精选"],
"HBM/存储":["建信新兴市场","华夏移动互联","易方达全球成长精选"],
"半导体设备":["东方人工智能/半导体"],
"黄金/宏观":["华安黄金ETF联接C","国泰纳斯达克100","建信新兴市场"],
"美股宏观":["国泰纳斯达克100","建信新兴市场"],
"A股政策":["德邦鑫星/CPO","东方人工智能/半导体"],
"创新药":[],"机器人":[],"有色/铜":["同泰慧盈混合C"],"电力/电网":[],"消费/白酒":[],"券商":[],
"红利/央企":[],"银行/保险":[],"能源/煤炭":[]
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
"红利/央企":[("中国神华","601088.SS","sh601088"),("长江电力","600900.SS","sh600900"),("中国移动","600941.SS","sh600941")],
"银行/保险":[("工商银行","601398.SS","sh601398"),("招商银行","600036.SS","sh600036"),("中国平安","601318.SS","sh601318")],
"能源/煤炭":[("中国神华","601088.SS","sh601088"),("兖矿能源","600188.SS","sh600188"),("陕西煤业","601225.SS","sh601225")],
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
    if any(x in lo for x in ["红利","高股息","央企","dividend","state-owned"]):return "红利/央企"
    if any(x in lo for x in ["银行","保险","bank","insurance"]):return "银行/保险"
    if any(x in lo for x in ["煤炭","能源","coal","energy"]):return "能源/煤炭"
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
        "白酒 消费 A股 when:7d","券商 东方财富 中信证券 when:7d",
        "A股 红利 高股息 央企 when:7d","银行 保险 A股 when:7d","煤炭 能源 中国神华 when:7d"
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
            r=requests.get(url,headers=HEADERS,timeout=3.5)
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
    # V34：行情、板块、核心新闻并行冷启动，减少 Streamlit 休眠唤醒后的等待。
    with ThreadPoolExecutor(max_workers=3) as ex:
        fm=ex.submit(markets)
        fs=ex.submit(sectors)
        fn=ex.submit(getnews,"lite")
        try:m=fm.result()
        except Exception:m=pd.DataFrame(columns=["市场","价格","涨跌"])
        try:sec=fs.result()
        except Exception:sec=pd.DataFrame(columns=["板块","涨跌","核心成分"])
        try:news=fn.result()
        except Exception:news=pd.DataFrame()

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
    st.caption("V35.2 · 主动轮动增强版")
    page=st.radio("功能导航",[
        "🎯 今日决策","📊 市场研究","💼 组合分析","🧾 交易与资金","⚙️ 管理与设置"
    ],label_visibility="collapsed")
    st.caption("左侧只保留5个大类，具体功能在页面顶部切换。")
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



def weighted_holding_overlap():
    funds=[f for f in TOP_HOLDINGS if f in PORT["基金"].tolist()]
    weight_maps={f:{n:float(w) for n,w in TOP_HOLDINGS[f]} for f in funds}
    mat=[]
    for a in funds:
        row=[]
        for b in funds:
            names=set(weight_maps[a])|set(weight_maps[b])
            if not names:
                row.append(0); continue
            shared=sum(min(weight_maps[a].get(n,0),weight_maps[b].get(n,0)) for n in names)
            base=max(1e-9,min(sum(weight_maps[a].values()),sum(weight_maps[b].values())))
            row.append(round(shared/base*100,1))
        mat.append(row)
    return pd.DataFrame(mat,index=funds,columns=funds)

def aggregate_company_exposure():
    amount_map=dict(zip(PORT["基金"],pd.to_numeric(PORT["金额"],errors="coerce").fillna(0)))
    total=float(pd.to_numeric(PORT["金额"],errors="coerce").fillna(0).sum())
    rows=[]
    for fund,hs in TOP_HOLDINGS.items():
        famount=float(amount_map.get(fund,0))
        for stock,w in hs:
            est=famount*float(w)/100
            rows.append([stock,fund,float(w),famount,est])
    raw=pd.DataFrame(rows,columns=["底层资产","基金","基金内权重%","基金金额","估算底层金额"])
    if raw.empty:
        return raw,pd.DataFrame()
    agg=raw.groupby("底层资产",as_index=False).agg(
        估算底层金额=("估算底层金额","sum"),
        出现基金数=("基金","nunique")
    )
    agg["占组合估算%"]=agg["估算底层金额"]/total*100 if total else 0
    agg=agg.sort_values(["估算底层金额","出现基金数"],ascending=[False,False])
    return raw,agg

def exposure_alerts_from_holdings():
    raw,agg=aggregate_company_exposure()
    alerts=[]
    if agg.empty:return alerts
    for _,r in agg.head(10).iterrows():
        if r["占组合估算%"]>=5:
            alerts.append(f"{r['底层资产']} 通过已知重仓股估算约占组合 {r['占组合估算%']:.1f}%")
        elif r["出现基金数"]>=3:
            alerts.append(f"{r['底层资产']} 同时出现在 {int(r['出现基金数'])} 只基金的已知重仓中")
    return alerts[:6]

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


def latest_topic_news(news, topic, limit=2):
    if news is None or news.empty:
        return pd.DataFrame()
    x=news[news["主题"]==topic].copy()
    if x.empty:
        return x
    return x.sort_values(["重要度","发布时间"],ascending=[False,False],na_position="last").head(limit)

def source_lines_for_asset(asset, m, sec, news, S):
    lines=[]
    if asset=="纳指":
        lines.append(f"行情：纳斯达克 {S['nas']:+.2f}%｜VIX {S['vix']:.1f}｜美债10Y {S['tnx']:.2f}（Yahoo Finance）")
        rel=pd.concat([latest_topic_news(news,"AI/算力",1),latest_topic_news(news,"美股宏观",1)],ignore_index=True)
    elif asset=="黄金":
        gold=m[m["市场"]=="黄金"]
        gp=float(gold.iloc[0]["涨跌"]) if len(gold) and pd.notna(gold.iloc[0]["涨跌"]) else 0
        lines.append(f"行情：黄金 {gp:+.2f}%｜美债10Y {S['tnx']:.2f}（Yahoo Finance）")
        rel=latest_topic_news(news,"黄金/宏观",2)
    elif asset=="CPO":
        lines.append(f"板块代理：CPO/光通信 {S['cp']:+.2f}%（腾讯核心成分股代理）")
        rel=latest_topic_news(news,"CPO/光通信",2)
    elif asset=="半导体":
        lines.append(f"板块代理：半导体设备 {S['sp']:+.2f}%｜SOX {S['sox']:+.2f}%（腾讯/Yahoo）")
        rel=latest_topic_news(news,"半导体设备",2)
    else:
        lines.append(f"环境：纳指 {S['nas']:+.2f}%｜VIX {S['vix']:.1f}｜美债10Y {S['tnx']:.2f}")
        rel=pd.concat([latest_topic_news(news,"AI/算力",1),latest_topic_news(news,"HBM/存储",1)],ignore_index=True)

    links=[]
    if rel is not None and not rel.empty:
        for _,r in rel.iterrows():
            links.append((r["新闻"],r["链接"],r["可信度"],int(r["重要度"])))
    return lines,links

def build_today_advice(m, sec, news, S):
    # 规则层：保留用户固定核心节奏，只允许“机会档”在回撤+风险可控时提升。
    items=[]
    items.append(("纳指",S["nasb"],
                  "基础定投继续；仅在明显回撤且VIX/美债没有同步恶化时提高到机会档。"))
    items.append(("黄金",S["goldb"],
                  "继续作为防守仓；不因为单日上涨追高，也不因科技反弹取消基础配置。"))
    items.append(("CPO",S["cpob"],
                  "回撤时分批，不追涨。若出现高可信出口限制/政策利空，动态仓优先收缩。"))
    items.append(("半导体",S["semib"],
                  "基础仓保持；明显回撤时小幅提高，避免与CPO/海外半导体同时重仓叠加。"))
    items.append(("建信",S["jxb"],
                  "动态仓。美债偏高或政策风险触发时降到0；回撤且AI/HBM逻辑未坏时再提高。"))
    return items

def render_today_advice(m, sec, news, S):
    st.markdown("## 🎯 今日操作建议")
    items=build_today_advice(m,sec,news,S)
    html=['<div class="advice-hero"><div class="advice-title">今日执行方案</div>',
          '<div class="advice-sub">建议由实时行情、板块代理涨跌、风险指标和高可信新闻共同决定；默认不因为单条新闻改变长期核心定投。</div>',
          '<div class="advice-grid">']
    for name,amt,why in items:
        html.append(f'<div class="advice-item"><div class="name">{name}</div><div class="amt">¥{amt}</div><div class="why">{why}</div></div>')
    html.append('</div></div>')
    st.markdown("".join(html),unsafe_allow_html=True)

    with st.expander("📚 展开：今天为什么这样操作（含来源）",expanded=True):
        for name,amt,why in items:
            st.markdown(f"**{name}｜建议 ¥{amt}**")
            st.caption(why)
            lines,links=source_lines_for_asset(name,m,sec,news,S)
            for line in lines:
                st.caption("• "+line)
            for j,(title,url,grade,importance) in enumerate(links):
                c1,c2=st.columns([5,1])
                with c1:
                    st.caption(f"• 新闻：{title}｜可信度 {grade}｜重要度 {'★'*importance}")
                with c2:
                    if url:
                        st.link_button("来源 ↗",url,key=f"advice_src_{name}_{j}")
            st.markdown("---")



# ===== V32 持仓驱动决策层 =====
def safe_num(x,default=0.0):
    try:
        if pd.isna(x): return default
        return float(x)
    except Exception:
        return default

def portfolio_total():
    try:return float(PORT["金额"].fillna(0).sum())
    except Exception:return 0.0

def portfolio_weights():
    p=PORT.copy()
    p["金额"]=pd.to_numeric(p["金额"],errors="coerce").fillna(0)
    total=max(p["金额"].sum(),1)
    p["权重"]=p["金额"]/total
    return p.sort_values("权重",ascending=False)

def news_for_fund(fund,news,limit=3):
    if news is None or news.empty:return pd.DataFrame()
    mask=news["影响基金"].fillna("").str.contains(re.escape(str(fund)),regex=True)
    return news[mask].sort_values(["重要度","发布时间"],ascending=[False,False],na_position="last").head(limit)

def confidence_for_asset(name,S,news):
    # 不是“预测准确率”，而是“当前证据一致性”：数据越齐、方向越一致，分数越高。
    score=55
    if name=="纳指":
        score += 8 if S["nas"]<0 else 2
        score += 6 if S["vix"]<25 else -8
        score += 5 if S["tnx"]<4.6 else -7
        topics=["AI/算力","美股宏观"]
    elif name=="黄金":
        score += 6 if S["vix"]>=20 else 2
        score += 4 if S["tnx"]<4.6 else -2
        topics=["黄金/宏观"]
    elif name=="CPO":
        score += 8 if S["cp"]<0 else 1
        score += -12 if S["policy_bad"] else 5
        topics=["CPO/光通信"]
    elif name=="半导体":
        score += 7 if S["sp"]<0 else 1
        score += 4 if S["sox"]>=-2 else -5
        topics=["半导体设备"]
    else:
        score += 5 if S["nas"]<0 and S["vix"]<30 else 0
        score += -8 if S["tnx"]>4.7 else 3
        topics=["AI/算力","HBM/存储"]

    if news is not None and not news.empty:
        rel=news[news["主题"].isin(topics)]
        if len(rel):
            hi=rel[rel["可信度"]=="A"]
            score += min(8,len(hi)*2)
    return max(30,min(90,int(score)))

def action_condition(name,amount,S):
    if name=="纳指":
        return "若纳指继续明显回撤、VIX未失控且美债收益率不继续快速上冲，可临时提高；若VIX>30则不机械加倍。"
    if name=="黄金":
        return "基础防守仓保持；若金价急涨不追高，若实际利率/美债收益率明显上行则只保留基础档。"
    if name=="CPO":
        return "只有“板块回撤 + AI资本开支逻辑未坏 + 无新增高可信政策利空”同时满足，才提高动态仓。"
    if name=="半导体":
        return "回撤时小幅提高；若CPO和海外半导体已同时加仓，则这里避免继续叠加高相关风险。"
    return "只有AI/HBM链条回撤而基本面新闻未恶化时提高；美债偏高、政策风险或高波动时降至0。"

def build_decision_table(m,sec,news,S):
    base={"纳指":50,"黄金":50,"CPO":20,"半导体":10,"建信":0}
    cur={"纳指":S["nasb"],"黄金":S["goldb"],"CPO":S["cpob"],"半导体":S["semib"],"建信":S["jxb"]}
    rows=[]
    for name in ["纳指","黄金","CPO","半导体","建信"]:
        diff=cur[name]-base[name]
        if diff>0: change=f"↑ +¥{diff}"
        elif diff<0: change=f"↓ ¥{diff}"
        else: change="＝ 基础档"
        rows.append([name,base[name],cur[name],change,confidence_for_asset(name,S,news),action_condition(name,cur[name],S)])
    return pd.DataFrame(rows,columns=["方向","基础金额","今日建议","相对基础","证据一致性","改变条件"])

def portfolio_alerts(S,news):
    alerts=[]
    pw=portfolio_weights()
    total=portfolio_total()
    if total:
        top=pw.iloc[0]
        if top["权重"]>=0.30:
            alerts.append(("🔴","单基金集中",f"{top['基金']} 占组合 {top['权重']:.1%}，单基金集中度偏高。"))
    if S["vix"]>=30: alerts.append(("🔴","高波动",f"VIX {S['vix']:.1f}，不建议机械抄底。"))
    elif S["vix"]>=22: alerts.append(("🟠","波动升温",f"VIX {S['vix']:.1f}，动态仓需要更谨慎。"))
    if S["tnx"]>=4.7: alerts.append(("🟠","估值压力",f"美债10Y {S['tnx']:.2f}，对高估值科技资产不友好。"))
    if S["policy_bad"]: alerts.append(("🔴","政策风险","新闻中检测到出口限制/制裁相关高风险关键词，CPO和海外科技动态仓收缩。"))
    if S["cp"]<=-3: alerts.append(("🟡","CPO大幅回撤",f"CPO核心成分代理 {S['cp']:+.2f}%，先判断是情绪回撤还是逻辑变化。"))
    if not alerts: alerts.append(("🟢","暂无重大异常","当前没有触发工作台的主要风险阈值，按基础计划执行即可。"))
    return alerts

def render_v32_decision_core(m,sec,news,S):
    st.markdown("## 🧠 今日决策核心")
    total=portfolio_total()
    a,b,c,d=st.columns(4)
    a.metric("今日计划",f"¥{S['total']}")
    b.metric("组合金额",f"¥{total:,.0f}")
    bconf=int(build_decision_table(m,sec,news,S)["证据一致性"].mean())
    c.metric("证据一致性",f"{bconf}/100")
    d.metric("风险温度",f"{S['risk']}/100")

    dt=build_decision_table(m,sec,news,S)
    st.dataframe(
        dt[["方向","基础金额","今日建议","相对基础","证据一致性"]],
        hide_index=True,use_container_width=True
    )
    with st.expander("为什么这样操作 / 什么情况下改变",expanded=True):
        for _,r in dt.iterrows():
            st.markdown(f"**{r['方向']}｜¥{int(r['今日建议'])}｜证据一致性 {int(r['证据一致性'])}/100**")
            st.caption(r["改变条件"])

def render_alert_center(S,news):
    st.markdown("### 🚨 今日异常")
    for icon,title,detail in portfolio_alerts(S,news):
        st.markdown(f"**{icon} {title}**")
        st.caption(detail)

def render_personal_news(news,limit=10):
    st.markdown("### 🧷 与我的持仓直接相关")
    if news is None or news.empty:
        st.caption("暂无新闻数据")
        return
    x=news[news["影响基金"].fillna("")!="无直接核心基金映射"].head(limit)
    if x.empty:
        st.caption("当前没有识别到直接关联持仓的新闻。")
        return
    for i,(_,r) in enumerate(x.iterrows()):
        with st.container(border=True):
            st.markdown(f"**{r['主题']}｜{'★'*int(r['重要度'])}｜可信度 {r['可信度']}**")
            st.write(r["新闻"])
            st.caption(f"影响：{r['影响基金']}")
            st.caption(r["摘要"])
            if r["链接"]:
                st.link_button("查看来源 ↗",r["链接"],key=f"personal_news_{i}")


# ===== V35.2 主动轮动、全持仓决策与全市场机会雷达 =====
FUND_DYNAMIC_MAP={
    "易方达全球成长精选":"海外科技","华安黄金ETF联接C":"黄金","德邦鑫星/CPO":"CPO",
    "建信新兴市场":"建信","华夏移动互联":"海外科技","东方人工智能/半导体":"半导体",
    "嘉实全球产业升级":"海外科技","天弘全球高端制造":"海外科技","同泰慧盈混合C":"有色/铜",
    "天弘越南市场C":"越南","国泰纳斯达克100":"纳指"
}
BASE_DAILY={"国泰纳斯达克100":50,"华安黄金ETF联接C":50,"德邦鑫星/CPO":20,"东方人工智能/半导体":10,"华夏移动互联":10}

SECTOR_TOOLS={
    "CPO/光通信":"已有：德邦鑫星/CPO；新增可搜索：光通信/CPO主题指数或ETF联接",
    "半导体设备":"已有：东方人工智能；新增可搜索：半导体设备/芯片设备主题基金",
    "创新药":"可搜索：中证创新药、港股创新药ETF联接",
    "机器人":"可搜索：中证机器人ETF联接、机器人主题指数基金",
    "有色/铜":"已有：同泰慧盈；新增可搜索：有色金属/矿业/铜产业主题基金",
    "电力/电网":"可搜索：电力ETF联接、电网设备/央企电力主题基金",
    "消费/白酒":"可搜索：招商中证白酒指数C、消费ETF联接",
    "券商":"可搜索：证券公司ETF联接C",
    "红利/央企":"可搜索：红利低波ETF联接、央企红利ETF联接",
    "银行/保险":"可搜索：银行ETF联接、保险主题指数基金",
    "能源/煤炭":"可搜索：煤炭ETF联接、能源ETF联接",
}

SECTOR_PROFILE={
    "CPO/光通信":dict(vol=24,horizon="3–12个月",maxw=18,kind="高弹性科技"),
    "半导体设备":dict(vol=22,horizon="6–18个月",maxw=16,kind="国产替代成长"),
    "创新药":dict(vol=24,horizon="6–18个月",maxw=10,kind="事件驱动成长"),
    "机器人":dict(vol=26,horizon="6–18个月",maxw=10,kind="高波动主题"),
    "有色/铜":dict(vol=18,horizon="3–12个月",maxw=12,kind="周期资源"),
    "电力/电网":dict(vol=12,horizon="6–24个月",maxw=14,kind="稳健成长/防御"),
    "消费/白酒":dict(vol=16,horizon="6–24个月",maxw=12,kind="价值修复"),
    "券商":dict(vol=20,horizon="1–9个月",maxw=8,kind="高Beta周期"),
    "红利/央企":dict(vol=10,horizon="6–24个月",maxw=18,kind="低波红利"),
    "银行/保险":dict(vol=12,horizon="6–24个月",maxw=15,kind="价值/股息"),
    "能源/煤炭":dict(vol=16,horizon="3–18个月",maxw=10,kind="周期/股息"),
}

def topic_signal(news,topics):
    if news is None or news.empty:return 50,0
    x=news[news["主题"].isin(topics)].head(30)
    if x.empty:return 50,0
    w=x["重要度"].clip(lower=1) * x["可信度"].map({"A":1.3,"B":1.0,"C":0.65}).fillna(.65)
    return float((x["分数"]*w).sum()/max(w.sum(),1)),len(x)

def portfolio_exposure_weights():
    total=max(safe_num(PORT["金额"].sum()),1)
    expo={}
    for _,r in PORT.iterrows():
        typ=FUND_DYNAMIC_MAP.get(str(r["基金"]),"其他")
        expo[typ]=expo.get(typ,0)+safe_num(r["金额"])/total*100
    return expo

def regime_label(S):
    if S["risk"]>=75 or S["vix"]>=30:return "防守优先"
    if S["nas"]>=1 and S["vix"]<22 and S["tnx"]<4.5:return "风险偏好"
    return "均衡轮动"

def dynamic_scenario(score,vol):
    edge=(score-50)/50
    base_mid=edge*vol*.45
    base_lo=base_mid-vol*.30; base_hi=base_mid+vol*.30
    bull_hi=max(base_hi,vol*.75); bull_lo=max(2,base_hi*.6)
    bear_lo=-vol*.85; bear_hi=-max(4,vol*.35)
    return f"{base_lo:+.0f}%~{base_hi:+.0f}%",f"{bull_lo:+.0f}%~{bull_hi:+.0f}%",f"{bear_lo:+.0f}%~{bear_hi:+.0f}%"

def fund_topics(typ):
    return {
      "纳指":["AI/算力","HBM/存储","美股宏观"],"海外科技":["AI/算力","HBM/存储","美股宏观"],
      "建信":["AI/算力","HBM/存储","美股宏观"],"黄金":["黄金/宏观","美股宏观"],
      "CPO":["CPO/光通信","AI/算力","A股政策"],"半导体":["半导体设备","A股政策"],
      "有色/铜":["有色/铜","A股政策"],"越南":["美股宏观"]
    }.get(typ,["A股政策"])

def fund_long_profile(f,typ):
    custom={
      "国泰纳斯达克100":("核心成长","6–36个月","估值/利率显著恶化或组合科技暴露过高"),
      "华安黄金ETF联接C":("防守对冲","3–24个月","实际利率持续上行、美元强势且避险需求下降"),
      "德邦鑫星/CPO":("高弹性核心卫星","3–12个月","出口限制恶化、订单/景气证据转弱或单一板块过度集中"),
      "东方人工智能/半导体":("国产设备成长","6–18个月","国产替代/资本开支逻辑转弱或估值严重透支"),
      "建信新兴市场":("HBM/亚洲半导体机会仓","3–12个月","存储周期转弱、科技估值压力上升"),
      "易方达全球成长精选":("保留观察/优化重复","3–12个月","与现有科技仓重复度高且持续跑输替代品"),
      "华夏移动互联":("存量观察","1–9个月","风格漂移/重复暴露继续偏高"),
      "嘉实全球产业升级":("等待优化","1–9个月","反弹后资金效率仍低则逐步切换"),
      "天弘全球高端制造":("等待优化","1–9个月","反弹后资金效率仍低则逐步切换"),
      "同泰慧盈混合C":("有色机会仓","3–12个月","商品周期和供需逻辑转弱"),
      "天弘越南市场C":("小卫星仓","6–24个月","区域风险/流动性恶化或仓位占比超限"),
    }
    return custom.get(f,("观察仓","3–12个月","基本面或风险收益比恶化"))

def dynamic_fund_decisions(S,news):
    rows=[]; total=max(safe_num(PORT["金额"].sum()),1); expo=portfolio_exposure_weights()
    for _,r in PORT.iterrows():
        f=str(r["基金"]); amt=safe_num(r["金额"]); typ=FUND_DYNAMIC_MAP.get(f,"其他"); base=BASE_DAILY.get(f,0); weight=amt/total*100
        score=50; reasons=[]
        ns,n=topic_signal(news,fund_topics(typ)); score+=(ns-50)*.25; reasons.append(f"相关新闻{n}条/新闻分{ns:.0f}")
        if typ in ["纳指","海外科技","建信"]:
            score += 8 if S["nas"]<=-2 else (-6 if S["nas"]>=2.5 else 1)
            score += 6 if S["vix"]<25 else (-14 if S["vix"]>=30 else -4)
            score += 6 if S["tnx"]<4.4 else (-12 if S["tnx"]>=4.7 else -4)
        elif typ=="黄金":
            score += 9 if S["vix"]>=22 else 1; score += 6 if S["tnx"]<4.4 else -5
        elif typ=="CPO":
            score += 11 if S["cp"]<=-2 else (-8 if S["cp"]>=3 else 2); score += -20 if S["policy_bad"] else 4
        elif typ=="半导体":
            score += 10 if S["sp"]<=-2 else (-6 if S["sp"]>=3 else 2)
        elif typ=="有色/铜":
            score += 4 if regime_label(S)!="风险偏好" else 0
        elif typ=="越南":
            score += 2 if S["risk"]<65 else -6
        # 组合过度集中时自动降低继续加仓优先级
        if typ in ["纳指","海外科技","建信"] and sum(expo.get(x,0) for x in ["纳指","海外科技","建信"])>50:
            score-=7; reasons.append("海外科技总暴露偏高")
        if weight>25: score-=10; reasons.append("单基金占比偏高")
        if S["risk"]>=80:score-=8
        score=max(0,min(100,score))
        if score>=76: action="加仓"; delta=max(base,50 if amt>=1000 else 30)
        elif score>=63: action="小幅加仓"; delta=max(base,20) if base else 20
        elif score>=42: action="持有/按基础"; delta=base
        elif score>=30: action="小幅减仓"; delta=-min(100,max(20,round(amt*.05/10)*10))
        else: action="减仓"; delta=-min(300,max(50,round(amt*.10/10)*10))
        pos,horizon,exit_rule=fund_long_profile(f,typ)
        add_trigger="新闻与行业信号继续改善，且出现2%~5%回撤时分批加"
        reduce_trigger=exit_rule
        vol=22 if typ in ["纳指","海外科技","建信","CPO","半导体"] else 16 if typ in ["有色/铜","越南"] else 10
        base_s,bull_s,bear_s=dynamic_scenario(score,vol)
        rows.append([f,amt,weight,typ,int(round(score)),action,int(delta),horizon,base_s,bull_s,bear_s,add_trigger,reduce_trigger,"；".join(reasons),pos])
    return pd.DataFrame(rows,columns=["基金","当前持仓","组合占比%","暴露","机会分","今日动作","建议金额","参考周期","基准情景","乐观情景","悲观情景","加仓触发","减仓/失效条件","证据摘要","中长期定位"]).sort_values("机会分",ascending=False)

def opportunity_radar(sec,news,S):
    rows=[]; regime=regime_label(S)
    defensive={"红利/央企","银行/保险","电力/电网","能源/煤炭","消费/白酒"}
    growth={"CPO/光通信","半导体设备","创新药","机器人"}
    for _,r in sec.iterrows():
        name=r["板块"]; ch=safe_num(r["涨跌"]); ns,n=topic_signal(news,[name]); score=50
        score += 9 if -4<=ch<=-1 else -7 if ch>=3 else 2
        score += (ns-50)*.30
        if name=="CPO/光通信" and S["policy_bad"]:score-=20
        if regime=="防守优先" and name in defensive:score+=10
        if regime=="防守优先" and name in growth:score-=7
        if regime=="风险偏好" and name in growth:score+=6
        if regime=="风险偏好" and name in defensive:score-=2
        score=max(0,min(100,score)); profile=SECTOR_PROFILE.get(name,dict(vol=18,horizon="3–12个月",maxw=10,kind="主题"))
        base_s,bull_s,bear_s=dynamic_scenario(score,profile["vol"])
        if score>=72:act="分2–3笔建仓/加仓"
        elif score>=60:act="小仓试错，回撤再加"
        elif score>=45:act="观察，不追涨"
        else:act="暂不参与/降低优先级"
        why=f"代理涨跌{ch:+.1f}%；新闻分{ns:.0f}；当前市场={regime}"
        invalid="新闻/基本面转弱、政策风险上升或板块快速涨至拥挤"
        rows.append([name,ch,int(round(score)),act,profile["kind"],profile["horizon"],base_s,bull_s,bear_s,profile["maxw"],SECTOR_TOOLS.get(name,"搜索对应指数ETF联接"),why,invalid,n])
    return pd.DataFrame(rows,columns=["板块","今日代理涨跌%","机会分","当前动作","类型","参考周期","基准情景","乐观情景","悲观情景","组合上限%","可买工具/搜索关键词","为什么现在","失效条件","相关新闻数"]).sort_values("机会分",ascending=False)

def render_dynamic_all_funds(S,news):
    st.markdown("## 💰 全持仓今日买卖清单")
    st.caption("每只基金每天都重算：定投=基础动作，动态建议=当天真实买卖判断；非定投基金同样会加/减仓。")
    d=dynamic_fund_decisions(S,news)
    st.dataframe(d[["基金","当前持仓","组合占比%","机会分","今日动作","建议金额","参考周期","基准情景","悲观情景"]],hide_index=True,use_container_width=True)
    buy=d[d["建议金额"]>0]["建议金额"].sum(); sell=-d[d["建议金额"]<0]["建议金额"].sum()
    a,b,c,d1=st.columns(4);a.metric("建议买入",f"¥{buy:.0f}");b.metric("建议减仓",f"¥{sell:.0f}");c.metric("净投入",f"¥{buy-sell:.0f}");d1.metric("市场模式",regime_label(S))
    for _,r in d.iterrows():
        with st.expander(f"{r['基金']}｜{r['今日动作']} {r['建议金额']:+.0f}元｜机会分 {r['机会分']}/100",expanded=False):
            st.write(f"**为什么：** {r['证据摘要']}")
            st.write(f"**中长期定位：** {r['中长期定位']}｜参考周期 {r['参考周期']}")
            st.write(f"**情景：** 基准 {r['基准情景']}｜乐观 {r['乐观情景']}｜悲观 {r['悲观情景']}")
            st.write(f"**继续加仓条件：** {r['加仓触发']}")
            st.write(f"**减仓/逻辑失效：** {r['减仓/失效条件']}")

def render_opportunity_radar(sec,news,S):
    st.markdown("## 🧭 全市场机会雷达")
    st.caption("不仅追踪科技；市场转弱时红利、银行、电力、能源等传统价值方向会自动提高比较权重。收益区间是情景规划，不是承诺。")
    x=opportunity_radar(sec,news,S)
    st.metric("当前市场模式",regime_label(S))
    st.dataframe(x,hide_index=True,use_container_width=True)
    if len(x):
        best=x.iloc[0];st.success(f"当前优先级最高：{best['板块']}｜{best['当前动作']}｜工具：{best['可买工具/搜索关键词']}｜周期 {best['参考周期']}｜基准 {best['基准情景']}。")

def render_new_money(sec,news,S):
    st.markdown("## 💵 我的下一笔钱放哪里")
    st.caption("先比较现有基金和新板块，再决定新增资金；资金可以全部或部分留现金。")
    x=opportunity_radar(sec,news,S); d=dynamic_fund_decisions(S,news)
    budget=st.segmented_control("本次新增资金",[100,300,500,1000,2000],default=500,key="v352_new_money")
    cand=[]
    for _,r in d[d["机会分"]>=63].head(4).iterrows():
        cand.append(dict(方向=r["基金"],分数=r["机会分"],类型="现有基金",工具=r["基金"],周期=r["参考周期"],基准=r["基准情景"],悲观=r["悲观情景"]))
    for _,r in x[x["机会分"]>=60].head(5).iterrows():
        cand.append(dict(方向=r["板块"],分数=r["机会分"],类型="新板块",工具=r["可买工具/搜索关键词"],周期=r["参考周期"],基准=r["基准情景"],悲观=r["悲观情景"]))
    if not cand:
        st.warning(f"当前没有达到试仓阈值的机会。建议 ¥{budget} 全部保留现金。")
        return
    z=pd.DataFrame(cand).sort_values("分数",ascending=False).drop_duplicates("方向").head(4)
    # 高风险时至少留20%现金；普通环境保留5%机动资金。
    cash_rate=.20 if S["risk"]>=70 else .05
    invest=float(budget)*(1-cash_rate); scores=(z["分数"]-50).clip(lower=1); alloc=(scores/scores.sum()*invest).round(-1)
    out=z.copy();out["建议投入"]=alloc.values;out["执行方式"]="首笔50%，回撤/确认后再补第二笔"
    st.dataframe(out[["方向","类型","建议投入","工具","周期","基准","悲观","执行方式"]],hide_index=True,use_container_width=True)
    st.info(f"保留现金约 ¥{float(budget)-alloc.sum():.0f}。这部分用于突发回撤或第二笔确认，不强行花完。")

def render_mid_long_strategy(S,news):
    st.markdown("## 🧭 未来1–6个月怎么处理")
    d=dynamic_fund_decisions(S,news).copy()
    st.dataframe(d[["基金","当前持仓","组合占比%","机会分","中长期定位","参考周期","基准情景","悲观情景","减仓/失效条件"]],hide_index=True,use_container_width=True)
    st.caption("长期处理与今天的短期买卖分开：短期好不代表长期核心，长期看好也不代表任何价格都值得加。")

def render_buyable_pool(sec,news,S):
    st.markdown("## 🛒 可买工具池")
    st.caption("把机会落到可搜索、可申购的基金类别；下单前仍需在支付宝确认当日限购、申赎状态与费率。")
    x=opportunity_radar(sec,news,S).copy()
    st.dataframe(x[["板块","机会分","当前动作","可买工具/搜索关键词","参考周期","基准情景","悲观情景","组合上限%","失效条件"]],hide_index=True,use_container_width=True)
    chosen=st.selectbox("我想进一步看哪个方向",x["板块"].tolist(),key="v352_pool_chosen")
    r=x[x["板块"]==chosen].iloc[0]
    st.write(f"**可以买的原因：** {r['为什么现在']}")
    st.write(f"**建议执行：** {r['当前动作']}；组合上限建议 {r['组合上限%']}%。")
    st.write(f"**产品搜索：** {r['可买工具/搜索关键词']}")
    st.write(f"**风险退出：** {r['失效条件']}")

CATEGORY_PAGES={
    "🎯 今日决策":["💰 全持仓买卖","🎯 今日建议","💵 新钱去哪","🧭 未来1-6月策略","🏠 今日驾驶舱","🔥 机会与风险","🧠 决策大脑","📅 事件日历"],
    "📊 市场研究":["🧭 全市场机会雷达","🛒 可买工具池","📈 市场看板","▦ 板块中心","📰 新闻中心"],
    "💼 组合分析":["💼 基金中心","🔗 重合度分析","🧬 底层穿透","🧾 持仓穿透管理","🎯 仓位目标","🩺 组合体检"],
    "🧾 交易与资金":["📒 投资日志","💰 资金计划","🧾 持仓管理"],
    "⚙️ 管理与设置":["☁️ 云端同步","🛰 数据健康","⚙️ 投资规则"],
}

def choose_subpage(category):
    pages=CATEGORY_PAGES[category]
    return st.radio(
        "二级导航",
        pages,
        horizontal=True,
        label_visibility="collapsed",
        key=f"subnav_{category}"
    )

@st.fragment(run_every="180s")
def render(page):
    category=page
    page=choose_subpage(category)
    m,sec,news,S=compute()
    now=datetime.now(TZ)
    st.caption(f"{category}  ›  {page}")
    st.markdown(f"# {page}")
    top_terminal(S,news)
    st.caption(f"页面每180秒刷新 ｜ 行情缓存60秒 ｜ 最近刷新：{now.strftime('%Y-%m-%d %H:%M:%S')}（北京时间）")

    if page=="💰 全持仓买卖":
        full_news=getnews("full")
        render_dynamic_all_funds(S,full_news)
        st.markdown("### 今日执行顺序")
        d=dynamic_fund_decisions(S,full_news)
        st.dataframe(d.sort_values("机会分",ascending=False)[["基金","今日动作","建议金额","机会分","证据摘要","中长期定位"]],hide_index=True,use_container_width=True)
    elif page=="💵 新钱去哪":
        full_news=getnews("full")
        render_new_money(sec,full_news,S)
        st.markdown("### 全市场候选方向")
        st.dataframe(opportunity_radar(sec,full_news,S),hide_index=True,use_container_width=True)
    elif page=="🧭 未来1-6月策略":
        full_news=getnews("full")
        render_mid_long_strategy(S,full_news)
    elif page=="🎯 今日建议":
        render_dynamic_all_funds(S,news)
        render_v32_decision_core(m,sec,news,S)
        render_alert_center(S,news)
        render_today_advice(m,sec,news,S)
        st.subheader("今日关键风险")
        risk_rows=pd.DataFrame([
            ["美债10Y",S["tnx"],"高于4.6时压制科技估值，动态仓降低"],
            ["VIX",S["vix"],"高于30时避免把大跌机械当便宜"],
            ["纳指单日",S["nas"],"明显回撤才考虑机会档"],
            ["CPO代理",S["cp"],"回撤+无重大政策利空时才提高"],
            ["政策风险","触发" if S["policy_bad"] else "未触发","触发时CPO/建信动态仓收缩"]
        ],columns=["观察项","当前","解释"])
        st.dataframe(risk_rows,hide_index=True,use_container_width=True)
        st.subheader("今日不要做")
        st.warning("不追涨；不因为一条低可信新闻改变长期配置；不同时把CPO、半导体、海外AI三条高相关风险链一起打到机会档。")

    elif page=="🏠 今日驾驶舱":
        render_alert_center(S,news)
        render_today_advice(m,sec,news,S)
        st.info(f"今日执行：固定核心继续定投；动态仓根据风险调整。当前建议合计 ¥{S['total']}。")
        A,B=st.columns([1,1.4])
        with A:
            fig=go.Figure(go.Indicator(mode="gauge+number",value=S["risk"],title={"text":"市场风险温度"},gauge={"axis":{"range":[0,100]},"bar":{"thickness":.22},"steps":[{"range":[0,45]},{"range":[45,70]},{"range":[70,100]}]}))
            fig.update_layout(height=185,margin=dict(l=5,r=5,t=34,b=2))
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

    elif page=="🧭 全市场机会雷达":
        full_news=getnews("full")
        render_opportunity_radar(sec,full_news,S)

    elif page=="🛒 可买工具池":
        full_news=getnews("full")
        render_buyable_pool(sec,full_news,S)

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
        if chosen in TOP_HOLDINGS:
            st.subheader(f"已知重仓股 · {HOLDINGS_ASOF}")
            hh=pd.DataFrame(TOP_HOLDINGS[chosen],columns=["重仓资产","权重%"])
            st.dataframe(hh,hide_index=True,use_container_width=True,height=280)
        st.subheader("相关新闻")
        render_news_cards(rel,20,"fund")

    elif page=="📰 新闻中心":
        news=getnews("full")
        render_personal_news(news,10)
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
        tab1,tab2,tab3=st.tabs(["重仓股交集","权重重合度","风险暴露相似度"])
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
            st.subheader("按重仓权重计算的重合度")
            wmat=weighted_holding_overlap()
            if wmat.empty:
                st.caption("暂无可计算数据")
            else:
                fig=px.imshow(wmat,text_auto=True,aspect="auto",zmin=0,zmax=100)
                fig.update_layout(height=560)
                st.plotly_chart(fig,use_container_width=True)
                st.info("使用已知重仓股权重计算：共同重仓越多、权重越接近，分数越高。比单纯看股票名称交集更有参考价值。")
        with tab3:
            st.subheader("风险暴露相似度")
            mat=overlap_matrix()
            fig=px.imshow(mat,text_auto=True,aspect="auto",zmin=0,zmax=100)
            fig.update_layout(height=560)
            st.plotly_chart(fig,use_container_width=True)
            st.info("该矩阵按AI/半导体/CPO/存储等风险因子近似，用来观察风格相关性。")
        st.subheader("组合结构提醒")
        st.write("多只科技基金底层仍高度集中在AI硬件、半导体、存储与光通信链条；黄金承担主要低相关防守作用。")

    elif page=="🧬 底层穿透":
        st.subheader(f"基金底层持仓穿透 · 数据截至 {HOLDINGS_ASOF}")
        raw2,agg2=aggregate_company_exposure()
        if not agg2.empty:
            a1,a2,a3,a4=st.columns(4)
            a1.metric("可穿透基金",len([f for f in TOP_HOLDINGS if f in PORT["基金"].tolist()]))
            a2.metric("底层资产",agg2["底层资产"].nunique())
            a3.metric("重复资产",int((agg2["出现基金数"]>=2).sum()))
            a4.metric("TOP1底层占比",f"{agg2.iloc[0]['占组合估算%']:.1f}%")
            st.subheader("组合底层公司暴露 TOP20")
            st.dataframe(agg2.head(20),hide_index=True,use_container_width=True)
            alerts=exposure_alerts_from_holdings()
            if alerts:
                st.subheader("重复/集中提醒")
                for t in alerts:
                    st.warning(t)
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

    elif page=="🧾 持仓穿透管理":
        st.subheader("基金底层持仓管理")
        st.caption("这里维护基金最新季报/披露的重仓股。更新后，重合度、底层穿透和集中度会自动使用新数据。")
        st.info(f"当前数据日期：{HOLDINGS_ASOF}")

        chosen=st.selectbox("选择基金",sorted(TOP_HOLDINGS.keys()),key="holdings_mgr_fund")
        cur=pd.DataFrame(TOP_HOLDINGS.get(chosen,[]),columns=["重仓资产","权重%"])
        edited=st.data_editor(cur,hide_index=True,use_container_width=True,num_rows="dynamic",key="holdings_editor")

        c1,c2=st.columns([1,1])
        with c1:
            asof=st.text_input("数据日期/季度",value=str(HOLDINGS_ASOF),placeholder="例如 2026Q3")
        with c2:
            st.metric("当前Top权重合计",f"{pd.to_numeric(edited['权重%'],errors='coerce').fillna(0).sum():.1f}%")

        if st.button("保存这只基金的底层持仓",use_container_width=True):
            clean=[]
            for _,r in edited.iterrows():
                name=str(r.get("重仓资产","")).strip()
                try:w=float(r.get("权重%",0))
                except:w=0
                if name and w>0:
                    clean.append((name,w))
            store=dict(TOP_HOLDINGS)
            store[chosen]=clean
            save_holdings_store(store,asof)
            st.success("已保存。重新刷新后，穿透/重合度会使用新数据。")

        st.markdown("---")
        st.subheader("批量导入 / 导出")
        template_rows=[]
        for fund,hs in TOP_HOLDINGS.items():
            for name,w in hs:
                template_rows.append([fund,name,w,HOLDINGS_ASOF])
        export_df=pd.DataFrame(template_rows,columns=["基金","重仓资产","权重%","数据日期"])
        st.download_button(
            "下载当前底层持仓 CSV",
            export_df.to_csv(index=False).encode("utf-8-sig"),
            "fund_holdings.csv","text/csv",use_container_width=True
        )
        uploaded=st.file_uploader("上传底层持仓CSV",type=["csv"],key="holdings_csv_upload")
        if uploaded is not None:
            try:
                up=pd.read_csv(uploaded)
                st.dataframe(up.head(30),hide_index=True,use_container_width=True)
                required={"基金","重仓资产","权重%"}
                if required.issubset(set(up.columns)):
                    if st.button("确认导入底层持仓",use_container_width=True):
                        store={}
                        for fund,g in up.groupby("基金"):
                            rows=[]
                            for _,r in g.iterrows():
                                try:w=float(r["权重%"])
                                except:w=0
                                name=str(r["重仓资产"]).strip()
                                if name and w>0: rows.append((name,w))
                            if rows: store[str(fund)]=rows
                        d=str(up["数据日期"].dropna().iloc[0]) if "数据日期" in up.columns and len(up["数据日期"].dropna()) else datetime.now(TZ).strftime("%Y-%m-%d")
                        save_holdings_store(store,d)
                        st.success("导入成功，刷新页面后生效。")
                else:
                    st.error("CSV至少需要：基金、重仓资产、权重% 三列。")
            except Exception as e:
                st.error(f"读取CSV失败：{e}")

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
        hist_file=os.path.join(DATA_DIR,"decision_history.jsonl")
        if os.path.exists(hist_file):
            with open(hist_file,"rb") as f:
                st.download_button("下载决策历史 JSONL",f.read(),"decision_history.jsonl","application/json",use_container_width=True)
        st.subheader("稳定性与云端持久化")
        kv_ok=cloud_table_exists("dashboard_kv")
        dh_ok=cloud_table_exists("decision_history")
        q1,q2,q3,q4=st.columns(4)
        q1.metric("Supabase","已连接" if CLOUD else "未连接")
        q2.metric("设置云端","正常" if kv_ok else "待升级")
        q3.metric("决策历史云端","正常" if dh_ok else "待升级")
        q4.metric("自动刷新","5分钟")
        if CLOUD and kv_ok and dh_ok:
            st.success("持仓、规则、预算、事件、底层穿透数据和决策历史具备云端持久化能力。重新部署后可恢复。")
        elif CLOUD:
            st.warning("Supabase 已连接，但 V34 的两个新表还没有建立。请运行压缩包中的 supabase_v34_upgrade.sql；不运行也能继续使用，只是部分新数据仍以本地文件为后备。")
        else:
            st.warning("当前未连接 Supabase，工作台仍可运行，但本地文件不能视为永久存储。")
        st.caption("Streamlit Community Cloud 休眠属于托管平台行为；V34不能禁止休眠，但已减少唤醒后的网络阻塞和iPad频繁重绘。")

        st.subheader("数据源健康检查")
        health=data_health_table(m,sec,news)
        st.dataframe(health,hide_index=True,use_container_width=True)
        ok=(health["状态"].str.contains("正常")).sum()
        a,b,c=st.columns(3)
        a.metric("正常模块",f"{ok}/{len(health)}")
        b.metric("新闻数量",len(news) if news is not None else 0)
        c.metric("持仓快照",HOLDINGS_ASOF)
        st.subheader("刷新与数据边界")
        st.info("页面300秒轻量自动刷新；行情缓存60秒；板块180秒；新闻600秒。基金持仓不是实时数据，按季报快照展示。板块涨跌是核心成分代理，不冒充官方行业指数。")
        st.info("V34优先使用Supabase保存关键设置与决策历史；本地文件继续作为断网/迁移时的后备。交易持仓仍沿用原有portfolio与investment_logs云端表。")
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
        st.subheader("真实持仓权重")
        pw=portfolio_weights()
        pshow=pw[["基金","金额","定位","主要暴露","权重"]].copy()
        pshow["权重"]=pshow["权重"].map(lambda x:f"{x:.1%}")
        st.dataframe(pshow,hide_index=True,use_container_width=True)
        render_alert_center(S,news)
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
        st.subheader("今日基金交易记录")
        st.caption("每只基金都可以单独加仓、减仓或不操作；保存后会自动更新持仓。")

        tx_rows=[]
        for i,(_,pr) in enumerate(PORT.iterrows()):
            fund=str(pr["基金"])
            current=float(pr["金额"]) if pd.notna(pr["金额"]) else 0.0
            with st.container(border=True):
                c1,c2,c3=st.columns([1.7,1,1])
                with c1:
                    st.markdown(f"**{fund}**")
                    st.caption(f"当前持仓：¥{current:,.2f} ｜ {pr['定位']}")
                with c2:
                    action=st.selectbox("操作",["不操作","加仓","减仓"],key=f"tx_action_{i}",label_visibility="collapsed")
                with c3:
                    amount=st.number_input("金额",min_value=0.0,value=0.0,step=10.0,key=f"tx_amount_{i}",label_visibility="collapsed")
                note=st.text_input("备注",placeholder="例如：回撤加仓 / 止盈 / 调仓 / 今天不动",key=f"tx_note_{i}")

                delta=0.0
                if action=="加仓":
                    delta=float(amount)
                elif action=="减仓":
                    delta=-float(amount)

                new_amount=max(0.0,current+delta)
                if action!="不操作" and amount>0:
                    st.caption(f"保存后持仓：¥{new_amount:,.2f}")
                    tx_rows.append({
                        "基金":fund,"操作":action,"金额":float(amount),"变动":delta,
                        "原持仓":current,"新持仓":new_amount,"备注":note
                    })

        common_note=st.text_area("今日总备注",placeholder="可选：记录今天整体判断。",key="today_common_note")

        if st.button("💾 保存今日投资记录",use_container_width=True):
            if not tx_rows:
                st.warning("今天还没有填写任何加仓或减仓。")
            else:
                now_dt=datetime.now(TZ)
                batch_id=now_dt.strftime("%Y%m%d%H%M%S")
                new_port=PORT.copy()

                for tx in tx_rows:
                    idxs=new_port.index[new_port["基金"]==tx["基金"]]
                    if len(idxs):
                        new_port.loc[idxs[0],"金额"]=tx["新持仓"]

                save_port(new_port)

                local_rows=[]
                for tx in tx_rows:
                    local_rows.append({
                        "记录ID":f"{batch_id}-{tx['基金']}",
                        "日期":now_dt.strftime("%Y-%m-%d %H:%M"),
                        "基金":tx["基金"],
                        "操作":tx["操作"],
                        "交易金额":tx["金额"],
                        "持仓变动":tx["变动"],
                        "交易前持仓":tx["原持仓"],
                        "交易后持仓":tx["新持仓"],
                        "备注":tx["备注"],
                        "今日总备注":common_note,
                        "市场状态":S["state"]
                    })

                tx_file=os.path.join(DATA_DIR,"fund_transactions.csv")
                pd.DataFrame(local_rows).to_csv(
                    tx_file,mode="a",header=not os.path.exists(tx_file),
                    index=False,encoding="utf-8-sig"
                )

                if CLOUD:
                    cloud_rows=[]
                    for tx in tx_rows:
                        cloud_rows.append({
                            "log_date":now_dt.strftime("%Y-%m-%d"),
                            "fund_name":tx["基金"],
                            "suggested_amount":0,
                            "actual_amount":tx["变动"],
                            "note":f"{tx['操作']} ¥{tx['金额']:.2f}｜{tx['备注']}｜{common_note}".strip("｜")
                        })
                    cloud_insert("investment_logs",cloud_rows)
                    cloud_insert("portfolio_snapshots",[
                        {"snapshot_time":now_dt.isoformat(),"fund_name":str(r["基金"]),"amount":float(r["金额"])}
                        for _,r in new_port.iterrows()
                    ])

                # 同时保存“当时为什么这么做”，供未来5/10/20日复盘
                try:
                    decision_file=os.path.join(DATA_DIR,"decision_history.jsonl")
                    snap={
                        "time":now_dt.isoformat(),
                        "market_state":S["state"],
                        "risk":S["risk"],
                        "vix":S["vix"],
                        "us10y":S["tnx"],
                        "nasdaq_change":S["nas"],
                        "cpo_proxy":S["cp"],
                        "semi_proxy":S["sp"],
                        "plan_total":S["total"],
                        "trades":tx_rows
                    }
                    with open(decision_file,"a",encoding="utf-8") as f:
                        f.write(json.dumps(snap,ensure_ascii=False)+"\n")
                    cloud_decision_insert(snap)
                except Exception:
                    pass
                st.success(f"已保存 {len(tx_rows)} 笔交易，并自动更新持仓；同时保存了当时的决策环境。")
                st.rerun()

        st.markdown("---")
        st.subheader("历史投资记录")

        tx_file=os.path.join(DATA_DIR,"fund_transactions.csv")
        local_tx=pd.DataFrame()
        if os.path.exists(tx_file):
            try:
                local_tx=pd.read_csv(tx_file)
            except Exception:
                local_tx=pd.DataFrame()

        cloud_tx=pd.DataFrame()
        if CLOUD:
            try:
                cr=cloud_select("investment_logs")
                if cr:
                    cloud_tx=pd.DataFrame(cr)
            except Exception:
                pass

        tab1,tab2=st.tabs(["新版逐基金记录","云端历史记录"])

        with tab1:
            if local_tx.empty:
                st.caption("还没有新版逐基金交易记录。")
            else:
                show=local_tx.iloc[::-1].reset_index(drop=True)
                st.dataframe(show,hide_index=True,use_container_width=True,height=360)

                st.subheader("删除记录")
                options=[]
                for idx,row in show.iterrows():
                    label=f"{idx+1}. {row.get('日期','')}｜{row.get('基金','')}｜{row.get('操作','')} ¥{row.get('交易金额',0)}｜{row.get('备注','')}"
                    options.append((label,str(row.get("记录ID",""))))

                selected=st.multiselect("选择要删除的记录",[x[0] for x in options],placeholder="可一次选择多条")
                if st.button("🗑️ 删除选中记录",type="secondary",use_container_width=True):
                    if not selected:
                        st.warning("请先选择要删除的记录。")
                    else:
                        ids={rid for label,rid in options if label in selected}
                        remain=local_tx[~local_tx["记录ID"].astype(str).isin(ids)].copy()
                        remain.to_csv(tx_file,index=False,encoding="utf-8-sig")
                        st.success(f"已删除 {len(ids)} 条记录。")
                        st.rerun()

                st.download_button(
                    "下载逐基金交易记录 CSV",
                    local_tx.to_csv(index=False).encode("utf-8-sig"),
                    "fund_transactions.csv","text/csv",
                    use_container_width=True
                )

        with tab2:
            if cloud_tx.empty:
                st.caption("暂无云端历史记录，或当前没有读取权限。")
            else:
                rename_map={
                    "id":"ID","log_date":"日期","fund_name":"基金",
                    "suggested_amount":"建议金额","actual_amount":"实际变动",
                    "note":"备注","created_at":"创建时间"
                }
                cshow=cloud_tx.rename(columns=rename_map)
                cols=[c for c in ["ID","日期","基金","实际变动","备注","创建时间"] if c in cshow.columns]
                st.dataframe(cshow[cols].sort_values("ID",ascending=False),hide_index=True,use_container_width=True,height=360)

                if "ID" in cshow.columns:
                    delete_ids=st.multiselect("选择要从云端删除的记录 ID",cshow["ID"].astype(int).tolist(),key="cloud_delete_ids")
                    if st.button("🗑️ 删除云端选中记录",use_container_width=True):
                        if not delete_ids:
                            st.warning("请先选择记录 ID。")
                        elif cloud_delete_ids("investment_logs",delete_ids):
                            st.success("已删除选中的云端记录。")
                            st.rerun()
                        else:
                            st.error("云端删除失败，可能是 RLS 权限限制。")

        st.info("删除历史记录不会自动撤销已经发生的持仓变化；如果交易填错，请同时到“持仓管理”修正当前持仓。")

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
