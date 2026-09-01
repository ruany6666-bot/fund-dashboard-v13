import streamlit as st
import pandas as pd
import requests, feedparser
import plotly.express as px
from urllib.parse import quote
from datetime import datetime

st.set_page_config(page_title="泡泡基金投资工作台 V13", page_icon="📊", layout="wide")

HEADERS={"User-Agent":"Mozilla/5.0"}

PORTFOLIO=pd.DataFrame([
["易方达全球成长精选",3626.13,"保留仓"],
["华安黄金ETF联接C",2148.84,"核心防守"],
["德邦鑫星/CPO",1383.63,"核心进攻"],
["嘉实全球产业升级",1334.24,"待迁移"],
["建信新兴市场",1207.11,"动态核心"],
["东方人工智能/半导体",875.65,"核心进攻"],
["财通景气甄选一年持有",864.11,"锁定"],
["天弘全球高端制造",847.87,"待迁移"],
["华夏移动互联",885.89,"接近封顶"],
["同泰慧盈混合C",485.94,"待评估"],
["天弘越南市场C",312.79,"卫星"],
["国泰纳斯达克100",249.79,"核心"]
],columns=["基金","金额","定位"])

TOPIC_RULES={
"AI/纳指":{"keywords":["nvidia","英伟达","gpu","ai data center","blackwell","rubin"],"funds":["国泰纳斯达克100","建信新兴市场","易方达全球成长精选"]},
"CPO":{"keywords":["1.6t","800g","cpo","optical module","光模块","光通信","中际旭创","新易盛","lumentum"],"funds":["德邦鑫星/CPO","易方达全球成长精选","建信新兴市场"]},
"半导体":{"keywords":["hbm","micron","sk hynix","samsung","北方华创","中微公司","半导体设备","存储"],"funds":["建信新兴市场","华夏移动互联","东方人工智能/半导体"]},
"黄金":{"keywords":["gold","黄金","federal reserve","fed","treasury yield","美债","降息","加息"],"funds":["华安黄金ETF联接C"]},
"政策风险":{"keywords":["export control","出口管制","sanction","制裁","restriction","限制","tariff","关税","禁令"],"funds":["德邦鑫星/CPO","易方达全球成长精选","东方人工智能/半导体"]}
}
POS=["growth","record","raise","upgrade","order","beat","surge","增长","超预期","上调","扩产","订单"]
NEG=["ban","restrict","sanction","cut","weak","miss","tariff","限制","制裁","下调","禁令","关税"]

def get_json(url, params=None):
    try:
        r=requests.get(url,params=params,headers=HEADERS,timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

@st.cache_data(ttl=60)
def markets():
    out=[]
    for secid,name in [("1.000001","上证"),("0.399006","创业板"),("1.000688","科创50")]:
        j=get_json("https://push2.eastmoney.com/api/qt/stock/get",
                   {"secid":secid,"fields":"f43,f58,f170"})
        try:
            d=j["data"]; out.append([name,d["f43"]/100,d["f170"]/100])
        except: out.append([name,None,None])
    for symbol,name in [("^IXIC","纳斯达克"),("^GSPC","标普500"),("GC=F","黄金")]:
        j=get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",
                   {"interval":"1d","range":"5d"})
        try:
            q=j["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            q=[x for x in q if x is not None]; last,prev=q[-1],q[-2]
            out.append([name,last,(last/prev-1)*100])
        except: out.append([name,None,None])
    return pd.DataFrame(out,columns=["市场","价格","涨跌幅"])

@st.cache_data(ttl=300)
def sectors():
    j=get_json("https://push2.eastmoney.com/api/qt/clist/get",
        {"pn":1,"pz":15,"po":1,"np":1,"fltt":2,"invt":2,"fid":"f3",
         "fs":"m:90+t:2","fields":"f14,f3,f8,f62"})
    try:
        return pd.DataFrame([{
            "板块":r.get("f14"),"涨跌幅":r.get("f3"),
            "换手率":r.get("f8"),"主力净额":r.get("f62")
        } for r in j["data"]["diff"]])
    except:
        return pd.DataFrame(columns=["板块","涨跌幅","换手率","主力净额"])

def classify(title):
    text=title.lower(); topics=[]; funds=[]; score=50
    for topic,rule in TOPIC_RULES.items():
        if any(k.lower() in text for k in rule["keywords"]):
            topics.append(topic); funds += rule["funds"]
    for k in POS:
        if k.lower() in text: score+=6
    for k in NEG:
        if k.lower() in text: score-=8
    if "政策风险" in topics: score-=8
    score=max(0,min(100,score))
    return "/".join(topics) or "其他",score,"、".join(sorted(set(funds)))

@st.cache_data(ttl=900)
def news():
    queries=["NVIDIA AI data center","1.6T optical module CPO",
             "HBM Micron SK Hynix Samsung","中国 半导体设备",
             "gold Federal Reserve Treasury yields","中国 光模块 出口管制"]
    rows=[]; seen=set()
    for q in queries:
        try:
            f=feedparser.parse(f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans")
            for e in f.entries[:8]:
                title=e.get("title","")
                if not title or title in seen: continue
                seen.add(title)
                topic,score,funds=classify(title)
                rows.append([topic,score,funds,title,e.get("link","")])
        except: pass
    return pd.DataFrame(rows,columns=["主题","评分","影响基金","新闻","链接"])

def topic_score(ndf, key):
    if ndf.empty: return 50
    x=ndf[ndf["主题"].str.contains(key,na=False)]
    return round(x["评分"].mean(),1) if len(x) else 50

def decision(nas_pct,bond,ai,cn,policy,scores):
    nas,cpo,semi,gold,jx=50,20,10,50,50
    notes=[]
    if policy or scores["政策风险"]<38:
        jx=0; notes.append("政策风险偏高，建信0")
    elif ai<=1 or scores["AI"]<35:
        jx=0; notes.append("AI偏弱，建信0")
    elif bond>=3 and nas_pct>-1 and scores["AI"]<65:
        jx=0; notes.append("利率压力高，建信0")
    elif nas_pct<=-2 and ai>=3 and bond<=2 and scores["AI"]>=55:
        jx=100; notes.append("纳指回撤且AI逻辑未坏，建信100")
    else:
        notes.append("建信50")

    if scores["AI"]<30 and bond>=3: nas=30
    elif nas_pct<=-2.5 and scores["AI"]>=60 and bond<=2: nas=100

    if policy or scores["CPO"]<30: cpo=10
    elif cn>=3 and ai>=2 and scores["CPO"]>=60: cpo=40

    if scores["半导体"]<30: semi=0
    elif cn>=3 and scores["半导体"]>=60: semi=20

    return {"纳指":nas,"CPO":cpo,"半导体":semi,"黄金":gold,"建信":jx,
            "总投入":nas+cpo+semi+gold+jx,"说明":"；".join(notes)}

st.title("📊 泡泡基金投资工作台 V13")
st.caption("一键上线版 · 打开网址即可使用，不需要 FastAPI、不需要数据库、不需要自己启动后台。")

with st.sidebar:
    st.header("⚙️ 今日校准")
    bond=st.slider("美债压力",0,4,2)
    ai=st.slider("AI基本面",0,4,3)
    cn=st.slider("A股科技回撤",0,4,2)
    policy=st.toggle("重大政策风险",False)
    if st.button("🔄 立即刷新"):
        st.cache_data.clear(); st.rerun()

m=markets()
st.subheader("🌍 市场")
cols=st.columns(6)
for col,(_,r) in zip(cols,m.iterrows()):
    if pd.notna(r["价格"]):
        col.metric(r["市场"],f'{r["价格"]:.2f}',f'{r["涨跌幅"]:+.2f}%')
    else: col.metric(r["市场"],"暂不可用")

s=sectors()
st.subheader("🧭 A股板块")
if not s.empty:
    a,b=st.columns([1,1])
    a.dataframe(s,use_container_width=True,hide_index=True)
    b.plotly_chart(px.bar(s.sort_values("涨跌幅"),x="涨跌幅",y="板块",orientation="h"),use_container_width=True)
else: st.warning("板块接口暂不可用。")

n=news()
scores={
"AI":topic_score(n,"AI"),
"CPO":topic_score(n,"CPO"),
"半导体":topic_score(n,"半导体"),
"黄金":topic_score(n,"黄金"),
"政策风险":topic_score(n,"政策风险")
}
st.subheader("🧠 新闻决策分")
cs=st.columns(5)
for c,(k,v) in zip(cs,scores.items()):
    c.metric(k,f"{v:.0f}分","偏利好" if v>=65 else "偏利空" if v<40 else "中性")

nasrow=m[m["市场"]=="纳斯达克"]
nas_pct=float(nasrow.iloc[0]["涨跌幅"]) if len(nasrow) and pd.notna(nasrow.iloc[0]["涨跌幅"]) else 0
d=decision(nas_pct,bond,ai,cn,policy,scores)
st.subheader("🎯 今天怎么买")
c=st.columns(5)
for col,k in zip(c,["纳指","CPO","半导体","黄金","建信"]):
    col.metric(k,f'{d[k]}元')
st.success(f'今日建议总投入：{d["总投入"]}元。{d["说明"]}')

st.subheader("📰 与持仓有关的新闻")
if not n.empty:
    st.dataframe(n[["主题","评分","影响基金","新闻"]].head(30),use_container_width=True,hide_index=True)
else: st.warning("新闻源暂不可用。")

st.subheader("💼 当前持仓")
x,y=st.columns([1,1])
x.dataframe(PORTFOLIO,use_container_width=True,hide_index=True)
y.plotly_chart(px.pie(PORTFOLIO,names="基金",values="金额",hole=.45),use_container_width=True)

st.caption("公开行情/新闻接口可能延迟或暂时不可用；页面会明确显示不可用，不会虚构实时数据。投资金额是规则化辅助建议，不代表收益保证。")
