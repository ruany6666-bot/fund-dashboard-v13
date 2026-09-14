
import streamlit as st
import pandas as pd
import requests, feedparser, json, os, re, io, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client

st.set_page_config(page_title="阮嘤基金投资工作台 V44", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

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
V43_COST_FILE=os.path.join(DATA_DIR,"v43_cost_basis.json")
V43_HISTORY_KEY="v43_decision_history"
V44_NEWS_FILE=os.path.join(DATA_DIR,"v44_news_validation.json")
V44_NEWS_HISTORY_KEY="v44_news_validation"


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


/* ===== V40 全局市场状态条 ===== */
.market-strip{
 display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:6px;margin:0 0 13px 0;
}
.market-chip{
 background:#fff;border:1px solid #e5eaf0;border-radius:10px;padding:8px 9px;min-width:0;
}
.market-chip .mk{font-size:10px;color:#8a94a3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.market-chip .mv{font-size:14px;font-weight:800;color:#172033;white-space:nowrap}
.market-chip .mc{font-size:11px;font-weight:700;margin-top:1px}
.up{color:#d9363e}.down{color:#078b57}.flat{color:#7b8494}
@media(max-width:1100px){.market-strip{grid-template-columns:repeat(4,minmax(0,1fr))}}
@media(max-width:700px){.market-strip{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* ===== V37 iPad Pro 11 极简布局：更大顶部安全区 + 去重复摘要 ===== */
.block-container{max-width:1440px!important;padding-top:.35rem!important}
/* 主内容顶部留出稳定空间，避免 Streamlit 工具栏覆盖二级导航 */
[data-testid="stMainBlockContainer"]{padding-top:3.15rem!important}
/* 二级导航改成清晰的紧凑网格，不再挤成一条长横排 */
div[role="radiogroup"][aria-label="二级导航"]{
 display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;
 gap:7px!important;width:100%!important;margin:.45rem 0 1.0rem!important;
 position:relative!important;z-index:1!important;
}
div[role="radiogroup"][aria-label="二级导航"] > label{
 width:100%!important;min-width:0!important;min-height:38px!important;
 justify-content:center!important;padding:5px 8px!important;border-radius:9px!important;
 border:1px solid #e7eaf0!important;background:#fff!important;box-shadow:none!important;
 font-size:13px!important;font-weight:600!important;white-space:nowrap!important;overflow:hidden!important;
}
div[role="radiogroup"][aria-label="二级导航"] > label:has(input:checked){
 background:#f1f6ff!important;border-color:#cbdcff!important;color:#155fc2!important;
}
/* 收敛页面层级和空白 */
h1{font-size:1.42rem!important;margin:.15rem 0 .55rem!important}
h2{font-size:1.08rem!important;margin-top:.7rem!important}
[data-testid="stMetric"]{border-radius:10px!important;box-shadow:none!important}
.card,.advice-hero{border-radius:10px!important;box-shadow:none!important}
.quickbar{margin-bottom:8px!important}.quickpill{padding:4px 9px!important}
/* iPad Pro 11 横屏：侧栏更窄，主区更宽 */
@media (min-width:900px) and (max-width:1366px){
 section[data-testid="stSidebar"]{width:218px!important}
 .block-container{max-width:1120px!important;padding:.45rem .7rem 1.5rem!important}
 [data-testid="stMainBlockContainer"]{padding-top:3.45rem!important}
 div[role="radiogroup"][aria-label="二级导航"]{grid-template-columns:repeat(4,minmax(0,1fr))!important}
 section[data-testid="stSidebar"] div[role="radiogroup"] > label{min-height:44px!important;font-size:13px!important}
}
/* iPad 竖屏/较窄窗口：二级导航自动两列 */
@media (min-width:701px) and (max-width:899px){
 div[role="radiogroup"][aria-label="二级导航"]{grid-template-columns:repeat(2,minmax(0,1fr))!important}
}
@media(max-width:700px){
 div[role="radiogroup"][aria-label="二级导航"]{grid-template-columns:repeat(2,minmax(0,1fr))!important}
 div[role="radiogroup"][aria-label="二级导航"] > label{font-size:12px!important}
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

def _local_json_load(path, default):
    try:
        if os.path.exists(path):
            with open(path,"r",encoding="utf-8") as f:return json.load(f)
    except Exception:pass
    return default

def _local_json_save(path, value):
    try:
        with open(path,"w",encoding="utf-8") as f:json.dump(value,f,ensure_ascii=False,indent=2)
        return True
    except Exception:return False

def get_cost_basis_map():
    cloud=cloud_kv_get("v43_cost_basis")
    if isinstance(cloud,dict):return cloud
    local=_local_json_load(V43_COST_FILE,{})
    return local if isinstance(local,dict) else {}

def save_cost_basis_map(value):
    _local_json_save(V43_COST_FILE,value)
    cloud_kv_set("v43_cost_basis",value)

def get_v43_history():
    merged={}
    cloud=cloud_kv_get(V43_HISTORY_KEY)
    if isinstance(cloud,list):
        for x in cloud:
            if isinstance(x,dict) and x.get("date"):merged[x["date"]]=x
    try:
        if os.path.exists(V37_DECISION_FILE):
            with open(V37_DECISION_FILE,"r",encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        x=json.loads(line)
                        if x.get("date"):merged[x["date"]]=x
    except Exception:pass
    return [merged[k] for k in sorted(merged)]

def save_v43_history_item(payload):
    hist=get_v43_history()
    bydate={x.get("date"):x for x in hist if x.get("date")}
    bydate[payload.get("date")]=payload
    out=[bydate[k] for k in sorted(bydate)][-400:]
    cloud_kv_set(V43_HISTORY_KEY,out)
    return out

def _news_event_key(title):
    base=clean_news_title(title).lower()
    base=re.sub(r"[^0-9a-z\u4e00-\u9fff]+"," ",base)
    base=re.sub(r"\s+"," ",base).strip()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

def get_v44_news_history():
    cloud=cloud_kv_get(V44_NEWS_HISTORY_KEY)
    if isinstance(cloud,list): return cloud
    local=_local_json_load(V44_NEWS_FILE,[])
    return local if isinstance(local,list) else []

def save_v44_news_history(value):
    value=value[-350:]
    _local_json_save(V44_NEWS_FILE,value)
    cloud_kv_set(V44_NEWS_HISTORY_KEY,value)
    return value

def _proxy_close(symbol):
    try:
        p,_,_=yahoo(symbol,"1mo")
        return float(p) if p is not None else None
    except Exception:return None

def update_news_validation_history(df):
    """每天为高价值新闻留一个市场快照；后续按首次记录后的1/3/5天做真实事后验证。"""
    if df is None or df.empty:return []
    hist=get_v44_news_history(); by={x.get("key"):x for x in hist if isinstance(x,dict) and x.get("key")}
    today=datetime.now(TZ).strftime("%Y-%m-%d")
    top=rank_global_news(df)
    top=top[(top["可信度"].isin(["A","B"])) & (top["全球重要分"]>=60)].head(18)
    for _,r in top.iterrows():
        key=_news_event_key(r.get("新闻","")); topic=r.get("主题","其他")
        if not key:continue
        ev=by.get(key) or {"key":key,"title":r.get("新闻",""),"topic":topic,"source":r.get("来源",""),
                            "score":int(r.get("全球重要分",0) or 0),"sentiment":int(r.get("分数",50) or 50),
                            "first_seen":today,"observations":[]}
        obs=ev.setdefault("observations",[])
        if not any(o.get("date")==today for o in obs):
            prices={}
            for label,symbol,_ in TOPIC_PROXY.get(topic,[]):
                prices[label]=_proxy_close(symbol)
            obs.append({"date":today,"prices":prices})
        ev["last_seen"]=today; ev["score"]=max(int(ev.get("score",0)),int(r.get("全球重要分",0) or 0))
        by[key]=ev
    out=sorted(by.values(),key=lambda x:(x.get("last_seen",""),x.get("score",0)))[-350:]
    return save_v44_news_history(out)

def _event_horizon_returns(ev):
    obs=ev.get("observations",[]) or []
    if not obs:return {}
    try: base_date=pd.Timestamp(obs[0]["date"])
    except Exception:return {}
    base_prices=obs[0].get("prices",{}) or {}; out={}
    for horizon in [1,3,5]:
        candidates=[]
        for o in obs[1:]:
            try: days=(pd.Timestamp(o["date"])-base_date).days
            except Exception:continue
            if days>=horizon:candidates.append((days,o))
        if not candidates:continue
        _,o=min(candidates,key=lambda z:z[0])
        vals=[]
        for label,p0 in base_prices.items():
            p1=(o.get("prices",{}) or {}).get(label)
            if p0 and p1: vals.append((label,(p1/p0-1)*100))
        if vals:out[horizon]=vals
    return out

def render_news_validation_ledger(df):
    hist=update_news_validation_history(df)
    if not hist:return
    rows=[]
    for ev in sorted(hist,key=lambda x:(x.get("last_seen",""),x.get("score",0)),reverse=True):
        hrs=_event_horizon_returns(ev)
        if not hrs:continue
        def fmt(h):
            vals=hrs.get(h,[])
            return "—" if not vals else " / ".join(f"{n} {v:+.1f}%" for n,v in vals)
        rows.append({"新闻":ev.get("title",""),"主题":ev.get("topic",""),"首次记录":ev.get("first_seen",""),
                     "1日后":fmt(1),"3日后":fmt(3),"5日后":fmt(5)})
        if len(rows)>=12:break
    if rows:
        st.markdown("### 新闻事后验证")
        st.caption("以工作台首次记录新闻时的代理资产收盘价为基准，随后按1/3/5天留痕；这是事后验证，不是当前滚动涨跌。")
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

def portfolio_cost_state():
    mp=get_cost_basis_map(); rows=[]
    for _,r in PORT.iterrows():
        name=r["基金"]; mv=float(r["金额"]); rec=mp.get(name,{}) if isinstance(mp,dict) else {}
        invested=float(rec.get("累计投入",0) or 0)
        pnl=mv-invested if invested>0 else None
        ret=(pnl/invested*100) if invested>0 else None
        rows.append({"基金":name,"当前市值":mv,"累计投入":invested,"累计盈亏":pnl,"累计收益率%":ret})
    return pd.DataFrame(rows)

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
        ("VIX",lambda:yahoo("^VIX")[:2]),("美债10Y",lambda:yahoo("^TNX")[:2]),("黄金",lambda:yahoo("GC=F")[:2]),
        ("Brent原油",lambda:yahoo("BZ=F")[:2]),("铜",lambda:yahoo("HG=F")[:2]),("美元指数",lambda:yahoo("DX-Y.NYB")[:2])
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
    # V40：全球重要性优先，不以当前持仓为筛选前提。
    if any(x in lo for x in ["election","president","prime minister","government collapse","coup","大选","总统","首相","政府危机","政变"]):return "全球政治"
    if any(x in lo for x in ["war","missile","attack","ceasefire","sanction","geopolit","战争","袭击","停火","制裁","中东","乌克兰","俄罗斯"]):return "地缘政治"
    if any(x in lo for x in ["imf","world bank","global growth","gdp","recession","全球经济","经济增长","衰退"]):return "全球经济"
    if any(x in lo for x in ["ecb","boj","bank of japan","bank of england","pboc","央行","欧洲央行","日本央行","英国央行","人民银行"]):return "全球央行"
    if any(x in lo for x in ["tariff","trade war","trade deal","wto","关税","贸易战","贸易协议"]):return "贸易政策"
    if any(x in lo for x in ["earnings","profit","revenue","guidance","财报","营收","利润","业绩指引"]):return "全球公司/财报"
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

AUTH_A=["reuters","路透","federal reserve","federalreserve.gov","sec.gov","csrc.gov.cn","证监会","上交所","深交所","hkex","nasdaq","nyse","公司公告","交易所",
        "ecb.europa.eu","european central bank","bank of japan","boj.or.jp","bank of england","bankofengland.co.uk",
        "pbc.gov.cn","中国人民银行","bls.gov","bea.gov","treasury.gov","whitehouse.gov","imf.org","worldbank.org",
        "iea.org","opec.org","wto.org","欧盟委员会","ec.europa.eu","ap news","associated press"]
AUTH_B=["bloomberg","彭博","financial times","cnbc","证券时报","中国证券报","上海证券报","第一财经","财联社"]

def source_name(title):
    # Google News RSS 标题通常以“ - 来源”结尾；单独展示，避免把转载标题误当来源。
    parts=re.split(r"\s+-\s+",str(title))
    return parts[-1].strip() if len(parts)>1 else "来源待核验"

def clean_news_title(title):
    parts=re.split(r"\s+-\s+",str(title))
    return " - ".join(parts[:-1]).strip() if len(parts)>1 else str(title).strip()

def source_grade(title):
    lo=str(title).lower()
    if any(x in lo for x in AUTH_A):return "A"
    if any(x in lo for x in AUTH_B):return "B"
    return "C"

def parse_dt(s):
    try:return pd.to_datetime(s,utc=True).tz_convert(TZ)
    except:return pd.NaT

def summary_cn(title,topic,score):
    direction="利好" if score>=60 else "利空" if score<=40 else "中性"
    if topic=="地缘政治":
        impact="可能通过能源、避险、通胀、汇率和全球风险偏好影响多类资产。"
    elif topic=="全球经济":
        impact="可能影响全球增长预期、周期资产、利率和股票风险偏好。"
    elif topic=="全球央行":
        impact="可能影响全球利率、汇率、债券和股票估值。"
    elif topic=="贸易政策":
        impact="可能影响全球供应链、出口企业、通胀与跨国公司盈利预期。"
    elif topic=="全球公司/财报":
        impact="可能影响相关行业盈利预期与全球市场风险偏好。"
    elif topic=="CPO/光通信":
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

GLOBAL_TOPIC_WEIGHT={
    "地缘政治":27,"全球政治":25,"全球央行":26,"全球经济":24,"贸易政策":23,
    "美股宏观":26,"黄金/宏观":21,"全球公司/财报":18,"AI/算力":19,"CPO/光通信":16,
    "HBM/存储":16,"半导体设备":17,"有色/铜":17,"能源/煤炭":18,"A股政策":19,
    "电力/电网":13,"创新药":12,"机器人":12,"消费/白酒":10,"券商":10,"红利/央企":10,"银行/保险":10,"其他":6,
}
CRITICAL_NEWS_WORDS=[
    "emergency","war","attack","ceasefire","rate hike","rate cut","inflation","cpi","jobs","nonfarm",
    "tariff","sanction","ban","default","bank failure","oil supply","opec","earthquake","missile",
    "紧急","战争","袭击","停火","加息","降息","通胀","非农","关税","制裁","禁令","违约","银行危机","原油供应","导弹"
]

def global_news_score(topic,grade,published,title):
    score=GLOBAL_TOPIC_WEIGHT.get(topic,6)
    score += 34 if grade=="A" else 20 if grade=="B" else 0
    now=datetime.now(TZ)
    if pd.notna(published):
        try:
            hrs=max(0,(now-published).total_seconds()/3600)
            score += 25 if hrs<=24 else 16 if hrs<=72 else 8 if hrs<=168 else 0
        except Exception: pass
    lo=str(title).lower()
    score += min(15,5*sum(1 for x in CRITICAL_NEWS_WORDS if x in lo))
    return int(max(0,min(100,score)))

def rank_global_news(df):
    if df is None or df.empty:return df
    x=df.copy()
    if "全球重要分" not in x.columns:
        x["全球重要分"]=x.apply(lambda r:global_news_score(r.get("主题","其他"),r.get("可信度","C"),r.get("发布时间",pd.NaT),r.get("新闻","")),axis=1)
    return x.sort_values(["全球重要分","发布时间","重要度"],ascending=[False,False,False],na_position="last")

@st.cache_data(ttl=600)
def getnews(mode="lite"):
    # V28：首屏只取核心新闻，新闻中心再加载完整新闻库，避免手机首次打开被几十个RSS请求阻塞。
    full_queries=[
        # 全球重大事件：不要求与当前持仓直接相关
        "Reuters world markets breaking news when:2d","Reuters global economy recession growth when:3d",
        "Reuters Federal Reserve inflation jobs Treasury when:3d","Reuters ECB BOJ Bank of England central bank when:5d",
        "Reuters China economy policy markets when:3d","Reuters Europe economy markets when:3d","Reuters Japan economy yen BOJ when:3d",
        "Reuters Middle East oil conflict when:3d","Reuters Russia Ukraine war sanctions when:3d","Reuters tariffs trade policy US China EU when:3d",
        "Reuters OPEC oil Brent natural gas when:3d","Reuters gold copper commodities mining when:3d",
        "Reuters major company earnings guidance markets when:3d","Reuters banking financial stability when:3d",
        # 科技与产业
        "NVIDIA AI data center when:3d","OpenAI data center when:3d","Microsoft Meta Google AI capex when:3d","Blackwell Rubin GPU demand when:7d",
        "1.6T optical module CPO when:7d","800G optical module China when:7d","中际旭创 新易盛 光模块 when:7d","Lumentum optical transceiver when:7d",
        "HBM Micron SK Hynix Samsung when:7d","DRAM NAND memory price when:7d","Kioxia SanDisk memory when:7d",
        "中国 半导体设备 北方华创 中微公司 when:7d","国产半导体设备 when:7d",
        # A股、政策与资源
        "A股 政策 证监会 科技股 when:3d","证监会 官方 政策 when:7d","中国 央行 货币政策 when:7d",
        "创新药 license-out FDA when:7d","人形机器人 humanoid robot when:7d","铜 紫金矿业 洛阳钼业 when:7d","电网 储能 电力设备 when:7d",
        "白酒 消费 A股 when:7d","券商 东方财富 中信证券 when:7d","A股 红利 高股息 央企 when:7d","银行 保险 A股 when:7d","煤炭 能源 中国神华 when:7d"
    ]
    lite_queries=[
        "Reuters world markets breaking news when:2d","Reuters Federal Reserve inflation jobs Treasury when:3d",
        "Reuters Middle East oil conflict when:3d","Reuters China economy policy markets when:3d",
        "NVIDIA AI data center when:3d","1.6T optical module CPO when:7d",
        "HBM Micron SK Hynix Samsung when:7d","中国 半导体设备 北方华创 中微公司 when:7d",
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
        df["来源"]=df["新闻"].apply(source_name)
        df["新闻"]=df["新闻"].apply(clean_news_title)
        df["摘要"]=df.apply(lambda r:summary_cn(r["新闻"],r["主题"],r["分数"]),axis=1)
        df["影响基金"]=df["主题"].apply(lambda t:"、".join(FUND_MAP.get(t,[])) or "无直接核心基金映射")
        df["全球重要分"]=df.apply(lambda r:global_news_score(r["主题"],r["可信度"],r["发布时间"],r["新闻"]),axis=1)
        df=rank_global_news(df)
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
    st.caption("V44 · 情报闭环增强版")
    page=st.radio("功能导航",[
        "🎯 今日决策","📰 市场资讯","📊 市场研究","💼 组合分析","⚙️ 资金与管理"
    ],label_visibility="collapsed")
    st.caption("5 个主区 · 全球新闻按重要性排序")
    st.markdown("---")
    st.metric("今日建议",f"¥{S['total']}")
    st.caption(f"纳指{S['nasb']} · 黄金{S['goldb']} · CPO{S['cpob']} · 半导体{S['semib']} · 建信{S['jxb']}")
    if st.button("🔄 立即刷新",use_container_width=True):
        st.cache_data.clear();st.rerun()
    st.caption("自动刷新：180秒 · 可手动立即刷新")
    st.caption("新闻库：" + (f"🟢 {len(news)} 条" if not news.empty else "🔴 暂不可用"))
    st.caption("云端同步：" + ("🟢 已连接" if CLOUD else "🟠 未连接"))

def news_priority(score):
    try: score=int(score)
    except Exception: score=0
    if score>=82:return "🔴 必须知道"
    if score>=68:return "🟠 重要"
    return "🟡 值得关注"

def news_age_hours(dt):
    if pd.isna(dt): return 9999
    try:return max(0,(datetime.now(TZ)-dt).total_seconds()/3600)
    except Exception:return 9999

def dedupe_news_events(df):
    """轻量事件去重：同主题+标题核心词高度重合只保留权威/重要分更高的一条。"""
    if df is None or df.empty:return df
    x=rank_global_news(df).copy()
    kept=[]; sigs=[]
    stop={"the","a","an","of","to","in","on","for","and","with","says","after","as","at","from","new","最新","报道","消息","宣布","表示"}
    for idx,r in x.iterrows():
        words=set(re.findall(r"[a-zA-Z]{3,}|[\u4e00-\u9fff]{2,}",str(r.get("新闻","" )).lower()))-stop
        duplicate=False
        for topic,old in sigs:
            if topic!=r.get("主题"):continue
            union=len(words|old); inter=len(words&old)
            if union and inter/union>=0.48:
                duplicate=True;break
        if not duplicate:
            kept.append(idx);sigs.append((r.get("主题"),words))
    return x.loc[kept]

OFFICIAL_HINTS=[
    "federalreserve.gov","bls.gov","bea.gov","treasury.gov","sec.gov","csrc.gov.cn","pbc.gov.cn",
    "ecb.europa.eu","boj.or.jp","bankofengland.co.uk","imf.org","worldbank.org","iea.org","opec.org","wto.org",
    "上交所","深交所","港交所","中国人民银行","证监会","federal reserve","european central bank","bank of japan"
]

def source_type_label(source):
    lo=str(source).lower()
    if any(x in lo for x in OFFICIAL_HINTS): return "🏛️ 一手官方"
    if any(x in lo for x in ["reuters","路透","associated press","ap news"]): return "📰 权威通讯社"
    if any(x in lo for x in ["bloomberg","彭博","financial times","cnbc"]): return "🗞️ 主流财经媒体"
    return "🔎 来源待复核"

def market_reaction_text(topic):
    """把新闻叙事和真实行情放在一起，避免只看标题做判断。"""
    try:
        parts=[]
        def mm(name,label=None):
            x=m[m["市场"]==name]
            if len(x) and pd.notna(x.iloc[0]["涨跌"]):
                parts.append(f"{label or name} {float(x.iloc[0]['涨跌']):+.2f}%")
        def ss(name,label=None):
            x=sec[sec["板块"]==name]
            if len(x) and pd.notna(x.iloc[0]["涨跌"]):
                parts.append(f"{label or name} {float(x.iloc[0]['涨跌']):+.2f}%")
        if topic in ["美股宏观","全球央行","全球经济","全球政治","贸易政策"]:
            mm("纳斯达克","纳指"); mm("美债10Y","美债10Y"); mm("美元指数","美元"); mm("VIX","VIX")
        elif topic in ["地缘政治","能源/煤炭"]:
            mm("Brent原油","Brent"); mm("黄金","黄金"); mm("VIX","VIX")
        elif topic in ["黄金/宏观"]:
            mm("黄金","黄金"); mm("美元指数","美元"); mm("美债10Y","美债10Y")
        elif topic in ["有色/铜"]:
            mm("铜","铜"); mm("美元指数","美元")
        elif topic in ["AI/算力","HBM/存储","全球公司/财报"]:
            mm("纳斯达克","纳指"); mm("SOX","SOX")
        elif topic=="CPO/光通信":
            ss("CPO/光通信"); mm("纳斯达克","纳指")
        elif topic=="半导体设备":
            ss("半导体设备"); mm("上证","上证")
        elif topic=="A股政策":
            mm("上证","上证"); mm("创业板","创业板")
        else:
            mm("纳斯达克","纳指"); mm("上证","上证")
        return " ｜ ".join(parts[:4]) if parts else "暂无可用行情验证"
    except Exception:
        return "暂无可用行情验证"

TOPIC_PROXY={
    "美股宏观":[("纳指","^IXIC",-1),("美债10Y","^TNX",1),("美元","DX-Y.NYB",1)],
    "全球央行":[("纳指","^IXIC",-1),("美债10Y","^TNX",1),("美元","DX-Y.NYB",1)],
    "全球经济":[("纳指","^IXIC",1),("铜","HG=F",1),("Brent","BZ=F",1)],
    "地缘政治":[("Brent","BZ=F",1),("黄金","GC=F",1),("VIX","^VIX",1)],
    "能源/煤炭":[("Brent","BZ=F",1)],
    "黄金/宏观":[("黄金","GC=F",1),("美元","DX-Y.NYB",-1)],
    "有色/铜":[("铜","HG=F",1),("美元","DX-Y.NYB",-1)],
    "AI/算力":[("纳指","^IXIC",1),("SOX","^SOX",1)],
    "HBM/存储":[("SOX","^SOX",1)],
    "全球公司/财报":[("纳指","^IXIC",1),("SOX","^SOX",1)],
    "CPO/光通信":[("纳指","^IXIC",1)],
    "半导体设备":[("上证","000001.SS",1)],
    "A股政策":[("上证","000001.SS",1),("创业板","399006.SZ",1)],
}

@st.cache_data(ttl=1800)
def market_multi_period(topic):
    rows=[]
    for label,symbol,_ in TOPIC_PROXY.get(topic,[("纳指","^IXIC",1),("上证","000001.SS",1)]):
        vals=[]
        for lb in [1,3,5]:
            vals.append(_range_return(symbol,lb,"1mo"))
        rows.append((label,*vals))
    return rows

def news_confirmation(topic, sentiment_score=50):
    proxies=TOPIC_PROXY.get(topic,[])
    if not proxies:return "⚪ 暂无明确验证","代理不足"
    # 情绪为利好时按预期方向检查，利空时方向反转；中性只看是否有明显市场动作。
    sign=1 if sentiment_score>=60 else -1 if sentiment_score<=40 else 0
    checks=[]
    for label,symbol,expected in proxies:
        r=_range_return(symbol,1,"1mo")
        if r is None:continue
        if sign==0: checks.append(abs(r)>=0.8)
        else: checks.append((r*expected*sign)>0.15)
    if not checks:return "⚪ 暂无明确验证","行情数据不足"
    ratio=sum(checks)/len(checks)
    if ratio>=0.67:return "✅ 市场确认",f"{sum(checks)}/{len(checks)} 个代理方向一致"
    if ratio>=0.34:return "⚠️ 部分确认",f"{sum(checks)}/{len(checks)} 个代理方向一致"
    return "❌ 尚未确认",f"仅 {sum(checks)}/{len(checks)} 个代理方向一致"

def format_multi_period(topic):
    rows=market_multi_period(topic)
    out=[]
    for label,r1,r3,r5 in rows:
        def f(v):return "—" if v is None else f"{v:+.2f}%"
        out.append(f"{label} 1日 {f(r1)} / 3日 {f(r3)} / 5日 {f(r5)}")
    return " ｜ ".join(out) if out else "暂无多周期代理数据"

def market_regime_summary(S):
    reasons=[]
    if S.get("vix",20)>=30:reasons.append("VIX高位")
    elif S.get("vix",20)>=22:reasons.append("VIX偏高")
    if S.get("tnx",4.3)>=4.6:reasons.append("美债收益率偏高")
    if S.get("nas",0)<=-2:reasons.append("科技回撤")
    if S.get("policy_bad"):reasons.append("政策/限制风险")
    regime=regime_label(S)
    return regime,(" + ".join(reasons) if reasons else "风险指标暂未出现明显异常")

def render_market_regime_bar(S):
    regime,why=market_regime_summary(S)
    st.info(f"**全球市场状态：{regime}** ｜ {why}")

def render_news_intelligence_summary(df):
    if df is None or df.empty:return
    x=rank_global_news(df)
    critical=int((x["全球重要分"]>=82).sum())
    recent24=int((x["发布时间"].apply(news_age_hours)<=24).sum())
    official=int(x["来源"].apply(lambda z: source_type_label(z)=="🏛️ 一手官方").sum())
    a,b,c,d=st.columns(4)
    a.metric("🔴 必须知道",critical)
    b.metric("24小时内",recent24)
    c.metric("一手官方",official)
    d.metric("权威/A级",int((x["可信度"]=="A").sum()))
    top=x.head(3)
    if len(top):
        st.markdown("### 今日情报主线")
        for _,r in top.iterrows():
            st.markdown(f"- **{r['主题']}**｜{r['新闻']}  ")
            st.caption(f"市场验证：{market_reaction_text(r['主题'])}")

def render_news_cards(df,limit=20,prefix="n"):
    if df is None or df.empty:
        st.caption("暂无匹配的权威资讯")
        return
    df=rank_global_news(df)
    for i,(_,r) in enumerate(df.head(limit).iterrows()):
        lab="🟢 利好" if r["分数"]>=60 else "🔴 利空" if r["分数"]<=40 else "🟡 中性"
        pub=r["发布时间"].strftime("%m-%d %H:%M") if pd.notna(r["发布时间"]) else r["时间"]
        gscore=int(r.get("全球重要分",0) or 0)
        priority=news_priority(gscore)
        age=news_age_hours(r.get("发布时间",pd.NaT))
        with st.container(border=True):
            stype=source_type_label(r.get("来源","待核验"))
            st.markdown(f"**{priority}｜{r['主题']}｜{lab}**")
            st.caption(f"{stype} ｜ 来源：{r.get('来源','待核验')}")
            st.caption(f"全球重要度 {gscore}/100 ｜ 距今约 {age:.0f} 小时")
            st.markdown(f"**事实：** {r['新闻']}")
            st.caption(f"发布时间：{pub} ｜ 可信度：{r['可信度']}")
            st.markdown(f"**工作台判断：** {r['摘要']}")
            st.caption(f"📈 市场验证：{market_reaction_text(r['主题'])}")
            if r.get("影响基金","无直接核心基金映射")!="无直接核心基金映射":
                st.caption(f"关联持仓：{r['影响基金']}")
            if r["链接"]:
                st.link_button("查看报道 / 来源 ↗",r["链接"],key=f"{prefix}_{i}_{r.name}")


def render_global_market_strip(m):
    names=["纳斯达克","上证","黄金","Brent原油","铜","美债10Y","VIX","美元指数"]
    label={"纳斯达克":"纳指","上证":"上证","黄金":"黄金","Brent原油":"Brent","铜":"铜","美债10Y":"美债10Y","VIX":"VIX","美元指数":"美元"}
    cells=[]
    for n in names:
        x=m[m["市场"]==n]
        if len(x) and pd.notna(x.iloc[0]["价格"]):
            p=float(x.iloc[0]["价格"]); c=x.iloc[0]["涨跌"]
            c=float(c) if pd.notna(c) else 0.0
            cls="up" if c>0 else "down" if c<0 else "flat"
            cells.append(f'<div class="market-chip"><div class="mk">{label[n]}</div><div class="mv">{p:,.2f}</div><div class="mc {cls}">{c:+.2f}%</div></div>')
        else:
            cells.append(f'<div class="market-chip"><div class="mk">{label[n]}</div><div class="mv">—</div><div class="mc flat">暂不可用</div></div>')
    st.markdown('<div class="market-strip">'+''.join(cells)+'</div>',unsafe_allow_html=True)


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
    d=dynamic_fund_decisions(S,news).copy()
    st.dataframe(d[["基金","当前持仓","组合占比%","机会分","中长期定位","参考周期","基准情景","悲观情景","减仓/失效条件"]],hide_index=True,use_container_width=True)
    st.caption("长期处理与今天的短期买卖分开：短期好不代表长期核心，长期看好也不代表任何价格都值得加。")

def render_buyable_pool(sec,news,S):
    st.caption("把机会落到可搜索、可申购的基金类别；下单前仍需在支付宝确认当日限购、申赎状态与费率。")
    x=opportunity_radar(sec,news,S).copy()
    st.dataframe(x[["板块","机会分","当前动作","可买工具/搜索关键词","参考周期","基准情景","悲观情景","组合上限%","失效条件"]],hide_index=True,use_container_width=True)
    chosen=st.selectbox("我想进一步看哪个方向",x["板块"].tolist(),key="v352_pool_chosen")
    r=x[x["板块"]==chosen].iloc[0]
    st.write(f"**可以买的原因：** {r['为什么现在']}")
    st.write(f"**建议执行：** {r['当前动作']}；组合上限建议 {r['组合上限%']}%。")
    st.write(f"**产品搜索：** {r['可买工具/搜索关键词']}")
    st.write(f"**风险退出：** {r['失效条件']}")


# ===== V37 自适应资产配置：资金轮动 / 取现 / 决策验证 =====
V37_DECISION_FILE=os.path.join(DATA_DIR,"v37_daily_decisions.jsonl")
PROXY_SYMBOLS={
    "纳指":"^IXIC","海外科技":"^SOX","建信":"^SOX","黄金":"GC=F",
    "有色/铜":"COPX","越南":"VNM"
}

def _range_return(symbol, lookback, range_="6mo"):
    try:
        _,_,closes=yahoo(symbol,range_)
        if len(closes)>lookback:
            return (closes[-1]/closes[-1-lookback]-1)*100
    except Exception:
        pass
    return None

def _basket_range_return(secname,lookback):
    vals=[]
    for _,ysym,_ in BASKETS.get(secname,[]):
        try:
            _,_,closes=yahoo(ysym,"6mo")
            if len(closes)>lookback:
                vals.append((closes[-1]/closes[-1-lookback]-1)*100)
        except Exception:
            pass
    return sum(vals)/len(vals) if vals else None

@st.cache_data(ttl=1800)
def proxy_returns_table():
    rows=[]
    mapping={
        "纳指":"纳指","海外科技":"海外科技","建信":"建信","黄金":"黄金",
        "CPO":"CPO/光通信","半导体":"半导体设备","有色/铜":"有色/铜","越南":"越南"
    }
    for typ,label in mapping.items():
        vals=[]
        for lb in [5,20,60]:
            if typ in ["CPO","半导体"]:
                v=_basket_range_return("CPO/光通信" if typ=="CPO" else "半导体设备",lb)
            elif typ in PROXY_SYMBOLS:
                v=_range_return(PROXY_SYMBOLS[typ],lb)
            else:v=None
            vals.append(v)
        rows.append([label,*vals])
    return pd.DataFrame(rows,columns=["方向","5日代理收益%","20日代理收益%","60日代理收益%"])

def v37_daily_snapshot(S,news):
    d=dynamic_fund_decisions(S,news)
    payload={
        "date":datetime.now(TZ).strftime("%Y-%m-%d"),
        "time":datetime.now(TZ).isoformat(),
        "market_state":S["state"],"risk":S["risk"],"vix":S["vix"],"us10y":S["tnx"],
        "fund_decisions":d[["基金","机会分","今日动作","建议金额","暴露"]].to_dict("records")
    }
    # 同一天只保存一次；同时维护一个云端历史列表，避免 Streamlit 休眠后本地历史丢失。
    try:
        old=get_v43_history()
        if not any(x.get("date")==payload["date"] for x in old):
            with open(V37_DECISION_FILE,"a",encoding="utf-8") as f:
                f.write(json.dumps(payload,ensure_ascii=False)+"\n")
            cloud_kv_set(f"v37_decision_{payload['date']}",payload)
            save_v43_history_item(payload)
    except Exception:
        pass
    return payload

def rotation_plan(sec,news,S,max_rotate_pct=8):
    d=dynamic_fund_decisions(S,news).copy()
    radar=opportunity_radar(sec,news,S).copy()
    costs=portfolio_cost_state().set_index("基金") if len(PORT) else pd.DataFrame()
    protected={"华安黄金ETF联接C","国泰纳斯达克100","德邦鑫星/CPO","东方人工智能/半导体"}
    sources=d[d["机会分"]<40].sort_values("机会分")
    held_targets=d[d["机会分"]>=65].sort_values("机会分",ascending=False)
    sector_targets=radar[radar["机会分"]>=62].sort_values("机会分",ascending=False)
    targets=[]
    for _,r in held_targets.iterrows():targets.append((r["基金"],"现有基金",int(r["机会分"]),r["参考周期"]))
    for _,r in sector_targets.iterrows():targets.append((r["板块"],"新板块",int(r["机会分"]),r["参考周期"]))
    targets=sorted(targets,key=lambda x:x[2],reverse=True)
    rows=[]
    for _,src in sources.iterrows():
        if not targets:break
        tgt=targets[0];gap=tgt[2]-int(src["机会分"])
        # V43：必须有明显赔率差，核心仓门槛更高，减少来回折腾。
        min_gap=28 if src["基金"] in protected else 22
        if gap<min_gap:continue
        base=min(300,max(50,round(src["当前持仓"]*max_rotate_pct/100/10)*10))
        pnl=None
        try:pnl=float(costs.loc[src["基金"],"累计收益率%"] )
        except Exception:pass
        # 浮亏较大时不机械割肉；除非赔率差特别大。
        if pnl is not None and pnl<=-12 and gap<35:continue
        if src["基金"] in protected:base=min(base,150)
        reason=f"机会分差 {gap} 分；先小比例验证，避免为换仓而换仓"
        if pnl is not None:reason+=f"；当前累计收益率 {pnl:+.1f}%"
        rows.append([src["基金"],base,tgt[0],tgt[1],tgt[2],tgt[3],reason])
    return pd.DataFrame(rows,columns=["资金来源","建议转出","目标方向","目标类型","目标机会分","参考周期","理由"])

def render_rotation(sec,news,S):
    st.caption("只在目标赔率明显高于现有持仓时建议迁移；不是为了每天换仓。")
    pct=st.segmented_control("单次最多动用低效持仓",[5,8,10,15],default=8,format_func=lambda x:f"{x}%",key="v37_rotate_pct")
    x=rotation_plan(sec,news,S,pct)
    if x.empty:
        st.success("当前没有达到‘值得换仓’的机会分差，暂不为了轮动而轮动。")
    else:
        st.dataframe(x,hide_index=True,use_container_width=True)
        st.warning("执行时建议分批：先转出建议金额的50%，目标方向确认后再转剩余部分。")

def render_withdraw_cash(S,news):
    st.caption("需要用钱时，不平均卖出。优先从低机会分、重复度高、非核心持仓中释放资金。")
    need=st.number_input("需要取出多少钱（元）",min_value=100.0,max_value=50000.0,value=1000.0,step=100.0,key="v37_withdraw")
    d=dynamic_fund_decisions(S,news).copy().sort_values(["机会分","组合占比%"],ascending=[True,False])
    remain=float(need);rows=[]
    protected={"华安黄金ETF联接C","国泰纳斯达克100","德邦鑫星/CPO","东方人工智能/半导体"}
    # 先非核心，再核心；单只默认不卖超过其持仓30%。
    d["保护级"]=d["基金"].isin(protected).astype(int)
    d=d.sort_values(["保护级","机会分"])
    for _,r in d.iterrows():
        if remain<=0:break
        cap=r["当前持仓"]*(0.20 if r["保护级"] else 0.35)
        sell=min(remain,max(0,round(cap/10)*10))
        if sell<10:continue
        rows.append([r["基金"],sell,r["机会分"],r["中长期定位"],"非核心/低赔率优先" if not r["保护级"] else "资金仍不足时才动核心仓"])
        remain-=sell
    st.dataframe(pd.DataFrame(rows,columns=["建议卖出基金","建议金额","机会分","定位","顺序逻辑"]),hide_index=True,use_container_width=True)
    if remain>0:st.warning(f"按当前风险保护规则仍差约 ¥{remain:.0f}。如必须足额取现，再提高单只卖出比例。")
    else:st.success(f"预计可释放约 ¥{need:.0f}，优先保护长期核心仓。")

def render_validation(S,news):
    v37_daily_snapshot(S,news)
    st.caption("V44 会把每日决策同时保存到本地与 dashboard_kv 云端历史。5/20/60日后才评价当时建议，避免用今天的涨跌冒充历史命中率。")
    p=proxy_returns_table()
    st.dataframe(p,hide_index=True,use_container_width=True)
    hist=get_v43_history()
    a,b,c,d=st.columns(4)
    a.metric("已积累决策日",len(hist))
    b.metric("5日验证","可用" if len(hist)>=5 else f"还差 {max(0,5-len(hist))} 日")
    c.metric("20日验证","可用" if len(hist)>=20 else f"还差 {max(0,20-len(hist))} 日")
    d.metric("60日验证","可用" if len(hist)>=60 else f"还差 {max(0,60-len(hist))} 日")
    if hist:
        latest=hist[-1]
        st.caption(f"最近保存：{latest.get('date')}｜风险 {latest.get('risk')}｜{latest.get('market_state')}｜云端历史 {'已启用' if CLOUD else '未连接，当前仅本地'}")
        with st.expander("查看最近10个决策日"):
            vv=pd.DataFrame([{"日期":x.get("date"),"市场状态":x.get("market_state"),"风险":x.get("risk"),"VIX":x.get("vix"),"美债10Y":x.get("us10y")} for x in hist[-10:]])
            st.dataframe(vv,hide_index=True,use_container_width=True)
    st.info("新闻卡片中的1/3/5日是当前滚动代理表现；真正的‘这条历史建议后来是否正确’仍只在对应观察窗口成熟后计入。")

def render_v37_command_center(sec,news,S):
    d=dynamic_fund_decisions(S,news); r=opportunity_radar(sec,news,S)
    buy=d[d["建议金额"]>0]["建议金额"].sum(); sell=-d[d["建议金额"]<0]["建议金额"].sum()
    topfund=d.iloc[0] if len(d) else None; topsec=r.iloc[0] if len(r) else None
    c1,c2,c3,c4=st.columns(4)
    c1.metric("今日买入",f"¥{buy:.0f}")
    c2.metric("今日减仓",f"¥{sell:.0f}")
    c3.metric("净投入",f"¥{buy-sell:.0f}")
    c4.metric("市场模式",regime_label(S))
    if topfund is not None and topsec is not None:
        st.success(f"优先检查：现有基金 **{topfund['基金']}**（{topfund['机会分']}/100）｜新方向 **{topsec['板块']}**（{topsec['机会分']}/100）。")
    rp=rotation_plan(sec,news,S,8)
    if len(rp):st.warning(f"发现 {len(rp)} 个资金效率改善候选，进入「🔄 资金轮动」查看具体从哪里卖、转到哪里。")
    else:st.info("当前没有足够大的赔率差，不建议为了活跃而换仓。")

CATEGORY_PAGES={
    "🎯 今日决策":["⚡ 今日决策","💰 买卖与资金","🧭 中期策略","📅 事件与计划"],
    "📰 市场资讯":["⭐ 今日必看","🌐 全球重大新闻","📊 市场与产业"],
    "📊 市场研究":["📊 市场与机会","🧪 决策验证","▦ 板块深度"],
    "💼 组合分析":["💼 我的基金","🩺 组合诊断","🧬 底层持仓"],
    "⚙️ 资金与管理":["💼 持仓与资金","📒 交易记录","⚙️ 系统与规则"],
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
    st.markdown(f"# {page}")
    render_global_market_strip(m)
    render_market_regime_bar(S)

    if page=="⚡ 今日决策":
        full_news=rank_global_news(getnews("full"))
        v37_daily_snapshot(S,full_news)
        d=dynamic_fund_decisions(S,full_news)
        rr=opportunity_radar(sec,full_news,S)

        st.markdown("## ① 今天发生什么")
        topn=full_news[full_news["可信度"].isin(["A","B"])].head(5) if not full_news.empty else full_news
        render_news_cards(topn,5,"v40_today_news")

        st.markdown("## ② 今天怎么做")
        c1,c2,c3,c4=st.columns(4)
        buy=d[d["建议金额"]>0]["建议金额"].sum() if len(d) else 0
        sell=-d[d["建议金额"]<0]["建议金额"].sum() if len(d) else 0
        c1.metric("建议买入",f"¥{buy:.0f}")
        c2.metric("建议减仓",f"¥{sell:.0f}")
        c3.metric("净投入",f"¥{buy-sell:.0f}")
        c4.metric("市场模式",regime_label(S))
        if len(d): st.dataframe(d[["基金","今日动作","建议金额","机会分","证据摘要"]].head(10),hide_index=True,use_container_width=True)

        st.markdown("## ③ 最大机会 / 最大风险")
        L,R=st.columns(2)
        with L:
            st.markdown("### 🔥 机会")
            if len(rr): st.dataframe(rr[["板块","机会分","当前动作","参考周期","为什么现在"]].head(5),hide_index=True,use_container_width=True)
        with R:
            st.markdown("### 🚨 风险")
            risks=pd.DataFrame([
                ["美债10Y",S["tnx"],90 if S["tnx"]>=4.6 else 60],
                ["VIX",S["vix"],90 if S["vix"]>=30 else 55],
                ["政策风险","触发" if S["policy_bad"] else "未触发",95 if S["policy_bad"] else 30],
                ["纳指单日",S["nas"],80 if S["nas"]<=-2.5 else 40],
                ["CPO单日",S["cp"],80 if S["cp"]<=-3 else 40],
            ],columns=["风险","当前","风险分"])
            st.dataframe(risks.sort_values("风险分",ascending=False),hide_index=True,use_container_width=True)

        st.markdown("## ④ 详细依据")
        with st.expander("展开决策规则、新闻影响与触发条件"):
            st.dataframe(decision_reason_cards(S),hide_index=True,use_container_width=True)
            nit=news_impact_table(full_news)
            if not nit.empty: st.dataframe(nit.head(10),hide_index=True,use_container_width=True)

    elif page=="💰 买卖与资金":
        full_news=getnews("full")
        t1,t2,t3,t4=st.tabs(["全持仓买卖","资金轮动","新钱配置","取钱方案"])
        with t1: render_dynamic_all_funds(S,full_news)
        with t2: render_rotation(sec,full_news,S)
        with t3: render_new_money(sec,full_news,S)
        with t4: render_withdraw_cash(S,full_news)

    elif page=="🧭 中期策略":
        full_news=getnews("full")
        render_mid_long_strategy(S,full_news)
        st.markdown("### 当前市场机会排序")
        st.dataframe(opportunity_radar(sec,full_news,S).head(10),hide_index=True,use_container_width=True)

    elif page=="📅 事件与计划":
        ev=pd.DataFrame(events)
        st.subheader("未来重要事件")
        if not ev.empty: st.dataframe(ev,hide_index=True,use_container_width=True)
        else: st.caption("暂无已确认事件")
        st.caption("只维护可靠日期；CPI、非农、FOMC、重要财报和政策事件作为动态仓位前置风险条件。")

    elif page in ["⭐ 今日必看","🌐 全球重大新闻","📊 市场与产业"]:
        full_news=rank_global_news(getnews("full"))
        x=full_news[full_news["可信度"].isin(["A","B"])].copy() if not full_news.empty else full_news
        if x is not None and not x.empty:
            x=x[x["发布时间"].apply(news_age_hours)<=168]
            x=dedupe_news_events(x)
        topic_map={
            "🌐 全球重大新闻":["全球政治","地缘政治","全球经济","全球央行","贸易政策","全球公司/财报"],
            "📊 市场与产业":["美股宏观","黄金/宏观","全球经济","全球央行","贸易政策","A股政策","AI/算力","CPO/光通信","HBM/存储","半导体设备","创新药","机器人","有色/铜","能源/煤炭","电力/电网","消费/白酒","券商","红利/央企","银行/保险"],
        }
        if page in topic_map and not x.empty: x=x[x["主题"].isin(topic_map[page])]
        if page=="⭐ 今日必看":
            if not x.empty:
                strong=x[x["全球重要分"]>=60]
                x=(strong if len(strong)>=5 else x).head(12)
            st.info("只看近7天 A/B 级高质量资讯，并按全球影响排序；全球重大事件优先，不以持仓为筛选前提。来源待核验的新闻不进入今日必看。同一事件自动去重，事实与工作台判断严格分开；V44 还会为重要新闻保存首次记录时的市场快照，后续做1/3/5日事后验证。")
        if page=="⭐ 今日必看" and x is not None and not x.empty:
            render_news_intelligence_summary(x)
        a,b,c=st.columns(3)
        if not x.empty:
            a.metric("权威资讯",len(x))
            b.metric("最高重要分",int(x["全球重要分"].max()))
            c.metric("A 级来源",int((x["可信度"]=="A").sum()))
        render_news_cards(x,30,"v44_news")
        if page=="⭐ 今日必看" and x is not None and not x.empty:
            with st.expander("查看新闻1/3/5日事后验证",expanded=False):
                render_news_validation_ledger(x)

    elif page=="📊 市场与机会":
        full_news=getnews("full")
        render_opportunity_radar(sec,full_news,S)
        with st.expander("可买工具池"):
            render_buyable_pool(sec,full_news,S)
        st.markdown("### 全球核心市场")
        cols=st.columns(4)
        for i,(_,r) in enumerate(m.iterrows()):
            cols[i%4].metric(r["市场"],"暂不可用" if pd.isna(r["价格"]) else f'{r["价格"]:.2f}',None if pd.isna(r["涨跌"]) else f'{r["涨跌"]:+.2f}%')

    elif page=="🧪 决策验证":
        render_validation(S,getnews("full"))

    elif page=="▦ 板块深度":
        chosen=st.selectbox("选择板块",list(BASKETS.keys()),key="v40_sector")
        r=sec[sec["板块"]==chosen].iloc[0]
        a,b=st.columns(2)
        a.metric("代理涨跌","—" if pd.isna(r["涨跌"]) else f'{r["涨跌"]:+.2f}%')
        b.metric("风险温度",f"{S['risk']}/100")
        hist=sector_history(chosen)
        if not hist.empty: st.plotly_chart(px.line(hist,x="交易日序号",y="累计涨跌%",color="股票"),use_container_width=True)
        st.write("核心成分：",r["核心成分"])

    elif page=="💼 我的基金":
        cost_state=portfolio_cost_state()
        known=cost_state[cost_state["累计投入"]>0].copy()
        if not known.empty:
            total_mv=float(known["当前市值"].sum()); total_inv=float(known["累计投入"].sum()); total_pnl=total_mv-total_inv
            aa,bb,cc,dd=st.columns(4)
            aa.metric("已录成本基金",f"{len(known)}/{len(PORT)}")
            bb.metric("已录成本合计",f"¥{total_inv:,.2f}")
            cc.metric("对应当前市值",f"¥{total_mv:,.2f}")
            dd.metric("对应累计盈亏",f"¥{total_pnl:+,.2f}",f"{(total_pnl/total_inv*100):+.2f}%" if total_inv>0 else None)
        else:
            st.info("尚未录入任何真实累计投入。工作台不会用持仓金额反推成本。")
        chosen=st.selectbox("选择我的基金",PORT["基金"].tolist(),key="v44_fund")
        r=PORT[PORT["基金"]==chosen].iloc[0]
        costs=get_cost_basis_map(); rec=costs.get(chosen,{}) if isinstance(costs,dict) else {}
        invested=float(rec.get("累计投入",0) or 0); mv=float(r["金额"])
        pnl=(mv-invested) if invested>0 else None; ret=(pnl/invested*100) if invested>0 else None
        a,b,c,d=st.columns(4)
        a.metric("当前市值",f'¥{mv:,.2f}')
        b.metric("累计投入","未录入" if invested<=0 else f'¥{invested:,.2f}')
        c.metric("累计盈亏","—" if pnl is None else f'¥{pnl:+,.2f}')
        d.metric("累计收益率","—" if ret is None else f'{ret:+.2f}%')
        st.caption(f"定位：{r['定位']} ｜ 主要暴露：{r['主要暴露']} ｜ 当前动作框架：{r['动作']}")
        with st.expander("录入 / 修改真实累计投入"):
            val=st.number_input("累计实际投入金额（元）",min_value=0.0,value=float(invested),step=100.0,key=f"cost_{chosen}")
            if st.button("保存成本数据",key=f"save_cost_{chosen}"):
                costs[chosen]={"累计投入":float(val),"updated_at":datetime.now(TZ).isoformat()}
                save_cost_basis_map(costs); st.success("已保存；云端可用时会同步。")
                st.rerun()
            st.caption("这里不猜成本。只有你录入真实累计投入后，工作台才计算盈亏。")
        if chosen in TOP_HOLDINGS: st.dataframe(pd.DataFrame(TOP_HOLDINGS[chosen],columns=["重仓资产","权重%"]),hide_index=True,use_container_width=True)

    elif page=="🩺 组合诊断":
        st.dataframe(portfolio_weights()[["基金","金额","定位","主要暴露","权重"]],hide_index=True,use_container_width=True)
        render_alert_center(S,news)
        st.markdown("### 重合度与风险暴露")
        mat=weighted_holding_overlap()
        if not mat.empty: st.plotly_chart(px.imshow(mat,text_auto=True,aspect="auto",zmin=0,zmax=100),use_container_width=True)
        st.markdown("### 仓位结构")
        st.dataframe(portfolio_exposure_view(),hide_index=True,use_container_width=True)

    elif page=="🧬 底层持仓":
        raw2,agg2=aggregate_company_exposure()
        if not agg2.empty: st.dataframe(agg2.head(25),hide_index=True,use_container_width=True)
        st.caption(f"底层持仓数据截至 {HOLDINGS_ASOF}；用于穿透和集中度判断，不冒充实时持仓。")

    elif page=="💼 持仓与资金":
        t1,t2=st.tabs(["持仓管理","资金计划"])
        with t1:
            edited=st.data_editor(PORT,use_container_width=True,hide_index=True,num_rows="dynamic",key="v40_port")
            if st.button("保存持仓",key="v40_save_port"): save_port(edited);save_snapshot(edited);st.success("已保存")
        with t2:
            st.metric("本月预算",f'¥{budget["月预算"]:,.0f}')
            st.caption(f"今日建议投入 ¥{S['total']}；资金配置由今日决策页动态判断。")

    elif page=="📒 交易记录":
        tx_file=os.path.join(DATA_DIR,"fund_transactions.csv")
        if os.path.exists(tx_file):
            try: st.dataframe(pd.read_csv(tx_file).tail(80),hide_index=True,use_container_width=True)
            except: st.caption("交易记录暂不可读取")
        else: st.caption("暂无本地交易记录")

    elif page=="⚙️ 系统与规则":
        t1,t2,t3=st.tabs(["投资规则","云端同步","数据健康"])
        with t1:
            edited={k:st.number_input(k,min_value=0,max_value=500,value=int(v0),step=10,key="v40_rule_"+k) for k,v0 in rules.items()}
            if st.button("保存投资规则",key="v40_rules_save"): save_json(RULE_FILE,edited);st.success("已保存")
        with t2:
            st.success("Supabase 已连接") if CLOUD else st.warning("当前未连接 Supabase")
            st.caption("持仓、规则、预算与关键决策数据优先云端持久化。")
        with t3:
            st.dataframe(data_health_table(m,sec,news),hide_index=True,use_container_width=True)

render(page)
st.caption("V44 · 情报闭环增强版｜权威新闻留痕｜1/3/5日事后验证｜全球市场状态｜真实盈亏框架")
