
import streamlit as st
import pandas as pd
import requests, feedparser, json, os
from urllib.parse import quote
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="阮嘤基金投资工作台 V17",page_icon="📊",layout="wide",initial_sidebar_state="expanded")
H={"User-Agent":"Mozilla/5.0"}

st.markdown("""
<style>
.block-container{padding:1rem 1.25rem 2rem;max-width:1800px}
section[data-testid="stSidebar"]{width:220px!important}
section[data-testid="stSidebar"] .block-container{padding:.8rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #e9edf3;border-radius:12px;padding:10px 12px;box-shadow:0 1px 5px rgba(20,40,80,.04)}
.card{background:#fff;border:1px solid #e7ebf1;border-radius:14px;padding:14px 16px;margin-bottom:12px;box-shadow:0 2px 8px rgba(20,40,80,.045)}
.kpi{font-size:27px;font-weight:800;line-height:1.1}.muted{color:#7b8494;font-size:12px}
.good{color:#0a9b61}.bad{color:#e64b4b}.warn{color:#e58a00}.blue{color:#1677ff}
.tag{display:inline-block;border-radius:6px;padding:2px 7px;font-size:12px;font-weight:700;margin-right:5px}
.tag-r{background:#fff0f0;color:#d9363e}.tag-g{background:#edf9f3;color:#078b57}.tag-y{background:#fff7e6;color:#c97900}.tag-b{background:#edf5ff;color:#1677ff}
hr{border:none;border-top:1px solid #eef1f5;margin:8px 0}
div[data-testid="stDataFrame"]{border:1px solid #edf0f4;border-radius:10px;overflow:hidden}
h1{font-size:1.65rem!important;margin-bottom:.15rem!important} h2{font-size:1.12rem!important}
@media(max-width:900px){
 section[data-testid="stSidebar"]{width:190px!important}
 .block-container{padding:.6rem}
 [data-testid="column"]{min-width:48%!important}
}
</style>
""",unsafe_allow_html=True)

BASKETS={
"CPO/光通信":[("中际旭创","sz300308"),("新易盛","sz300502"),("天孚通信","sz300394")],
"半导体设备":[("北方华创","sz002371"),("中微公司","sh688012"),("拓荆科技","sh688072")],
"创新药":[("恒瑞医药","sh600276"),("百济神州","sh688235")],
"机器人":[("三花智控","sz002050"),("绿的谐波","sh688017")],
"有色/铜":[("紫金矿业","sh601899"),("洛阳钼业","sh603993")],
"电力/电网":[("国电南瑞","sh600406"),("许继电气","sz000400")],
"消费/白酒":[("贵州茅台","sh600519"),("五粮液","sz000858")],
"券商":[("中信证券","sh600030"),("东方财富","sz300059")]
}
PORT=pd.DataFrame([
["华安黄金ETF联接C",2148.84,"核心防守"],["德邦鑫星/CPO",1383.63,"核心进攻"],["建信新兴市场",1207.11,"动态核心"],
["东方人工智能/半导体",875.65,"核心进攻"],["国泰纳斯达克100",249.79,"核心"],["易方达全球成长精选",3626.13,"保留"],
["嘉实全球产业升级",1334.24,"待迁移"],["天弘全球高端制造",847.87,"待迁移"],["华夏移动互联",885.89,"接近封顶"],
["财通景气甄选一年持有",864.11,"锁定"],["同泰慧盈混合C",485.94,"待评估"],["天弘越南市场C",312.79,"卫星"]
],columns=["基金","金额","状态"])

def gj(url,params=None):
    try:
        r=requests.get(url,params=params,headers=H,timeout=7);r.raise_for_status();return r.json()
    except:return None
def yahoo(s):
    j=gj(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(s)}",{"range":"5d","interval":"1d"})
    try:
        a=[float(x) for x in j["chart"]["result"][0]["indicators"]["quote"][0]["close"] if x is not None]
        return a[-1],(a[-1]/a[-2]-1)*100,a
    except:return None,None,[]
def tq(code):
    try:
        r=requests.get(f"https://qt.gtimg.cn/q={code}",headers=H,timeout=7);r.encoding="gbk"
        p=r.text.split('="',1)[1].rsplit('"',1)[0].split("~");a,b=float(p[3]),float(p[4]);return a,(a/b-1)*100
    except:return None,None

@st.cache_data(ttl=60)
def market():
    mp={"上证":"000001.SS","创业板":"399006.SZ","科创50":"000688.SS","纳斯达克":"^IXIC","标普500":"^GSPC","SOX":"^SOX","VIX":"^VIX","美债10Y":"^TNX","黄金":"GC=F"}
    rows=[]
    for n,s in mp.items():
        p,c,h=yahoo(s);rows.append([n,p,c,h])
    return pd.DataFrame(rows,columns=["市场","价格","涨跌","历史"])

@st.cache_data(ttl=180)
def sectors():
    rows=[]
    for sec,ls in BASKETS.items():
        vals=[];ds=[]
        for n,c in ls:
            _,p=tq(c)
            if p is not None:vals.append(p);ds.append(f"{n}{p:+.1f}%")
        rows.append([sec,sum(vals)/len(vals) if vals else None," / ".join(ds)])
    return pd.DataFrame(rows,columns=["板块","涨跌","成分"])

POS=["增长","超预期","上调","订单","surge","growth","beat","record","raise","expands"]
NEG=["限制","制裁","禁令","关税","下调","restrict","sanction","ban","tariff","cut","miss"]
@st.cache_data(ttl=900)
def news():
    qs=["NVIDIA AI data center","1.6T optical module CPO","HBM Micron SK Hynix","中国 半导体设备","gold Fed Treasury","中国 光模块 出口管制"]
    rows=[];seen=set()
    for q in qs:
        try:
            f=feedparser.parse(f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans")
            for e in f.entries[:6]:
                t=e.get("title","")
                if not t or t in seen:continue
                seen.add(t);lo=t.lower();score=50
                score+=sum(8 for x in POS if x.lower() in lo);score-=sum(10 for x in NEG if x.lower() in lo)
                topic="CPO/光通信" if any(x in lo for x in ["cpo","optical","光模块","1.6t"]) else "HBM/存储" if any(x in lo for x in ["hbm","micron","hynix"]) else "AI/算力" if any(x in lo for x in ["nvidia","英伟达","ai data"]) else "黄金/宏观" if any(x in lo for x in ["gold","fed","treasury","黄金"]) else "半导体"
                grade="A" if any(x in lo for x in ["reuters","路透","federal reserve","公告"]) else "B" if any(x in lo for x in ["bloomberg","彭博","cnbc","证券时报","财联社"]) else "C"
                rows.append([topic,max(0,min(100,score)),grade,t,e.get("published","")])
        except:pass
    return pd.DataFrame(rows,columns=["主题","分数","可信度","新闻","时间"])

m=market();s=sectors();n=news()
def row(name):
    x=m[m["市场"]==name]
    return x.iloc[0] if len(x) else None
def pct(name):
    r=row(name);return float(r["涨跌"]) if r is not None and pd.notna(r["涨跌"]) else 0
def val(name,default=0):
    r=row(name);return float(r["价格"]) if r is not None and pd.notna(r["价格"]) else default

nas=pct("纳斯达克");vix=val("VIX",20);tnx=val("美债10Y",4.3);sox=pct("SOX")
cp=s.loc[s["板块"]=="CPO/光通信","涨跌"];cp=float(cp.iloc[0]) if len(cp) and pd.notna(cp.iloc[0]) else 0
sp=s.loc[s["板块"]=="半导体设备","涨跌"];sp=float(sp.iloc[0]) if len(sp) and pd.notna(sp.iloc[0]) else 0
policy_bad=False
if not n.empty:
    risk=n[n["新闻"].str.contains("限制|制裁|禁令|出口管制|restrict|sanction|ban",case=False,regex=True,na=False)]
    policy_bad=len(risk)>0 and risk["可信度"].isin(["A","B"]).any()
risk_score=50
risk_score+=15 if tnx>=4.6 else 8 if tnx>=4.1 else 0
risk_score+=15 if vix>=30 else 8 if vix>=22 else 0
risk_score+=10 if policy_bad else 0
risk_score+=8 if nas<=-2 else 0
risk_score=max(0,min(100,risk_score))

nas_buy=100 if nas<=-2.5 and tnx<4.6 and vix<32 else 50
cpo_buy=40 if cp<=-2 and not policy_bad else 20
semi_buy=20 if sp<=-2 else 10
gold_buy=50
jx_buy=0 if policy_bad or tnx>=4.6 else 100 if nas<=-2 and vix<30 else 50
total=nas_buy+cpo_buy+semi_buy+gold_buy+jx_buy
state="风险偏高，控制动态仓" if risk_score>=75 else "正常定投，不追涨" if risk_score>=55 else "环境温和，按计划执行"

with st.sidebar:
    st.markdown("## 📊 阮嘤基金")
    st.caption("投资工作台 · V17")
    st.markdown("---")
    for x in ["🏠 市场驾驶舱","📈 市场看板","💼 我的持仓","▦ 板块分析","🔥 机会追踪","🌍 全球市场","📰 新闻中心","📅 事件日历","💰 资金计划","⚙️ 投资规则","🩺 组合体检","📒 投资日志"]:
        st.markdown(f"**{x}**" if "市场驾驶舱" in x else x)
    st.markdown("---")
    st.caption("今日定投计划")
    st.markdown(f"<div class='kpi blue'>¥{total}</div>",unsafe_allow_html=True)
    st.caption(f"纳指 ¥{nas_buy} · 黄金 ¥50<br>CPO ¥{cpo_buy} · 半导体 ¥{semi_buy}<br>建信 ¥{jx_buy}",unsafe_allow_html=True)
    if st.button("🔄 刷新数据",use_container_width=True):st.cache_data.clear();st.rerun()

st.markdown(f"# 阮嘤基金投资工作台 V17　<span class='tag tag-b'>专业终端版</span>",unsafe_allow_html=True)
st.caption(f"● 市场状态：{state}　　更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 第一行三大区
A,B,C=st.columns([1.15,1.15,1.05],gap="small")
with A:
    st.markdown("### 🔥 市场情绪与风险")
    gauge=go.Figure(go.Indicator(mode="gauge+number",value=risk_score,title={"text":"风险温度"},
        gauge={"axis":{"range":[0,100]},"bar":{"thickness":.22},"steps":[{"range":[0,45]},{"range":[45,70]},{"range":[70,100]}]}))
    gauge.update_layout(height=210,margin=dict(l=20,r=20,t=35,b=10))
    st.plotly_chart(gauge,use_container_width=True,config={"displayModeBar":False})
    x1,x2,x3=st.columns(3);x1.metric("VIX",f"{vix:.1f}");x2.metric("美债10Y",f"{tnx:.2f}");x3.metric("SOX",f"{sox:+.2f}%")
    st.caption("风险越高越应减少动态仓；基础定投与机会仓分开管理。")
with B:
    st.markdown("### 📰 今日重大新闻")
    if n.empty:st.warning("新闻源暂不可用")
    else:
        for _,r in n.head(6).iterrows():
            lab="重大利好" if r["分数"]>=60 else "重大利空" if r["分数"]<=40 else "中性"
            cls="tag-g" if r["分数"]>=60 else "tag-r" if r["分数"]<=40 else "tag-y"
            st.markdown(f"<span class='tag {cls}'>{lab}</span><b>{r['新闻'][:55]}</b><br><span class='muted'>{r['主题']} · 来源等级 {r['可信度']}</span><hr>",unsafe_allow_html=True)
with C:
    st.markdown("### 📊 板块涨跌与利好利空")
    vv=s.copy()
    vv["新闻面"]=vv["板块"].apply(lambda x:"🔴 风险" if x=="CPO/光通信" and policy_bad else "🟢 利好" if (x in ["CPO/光通信","半导体设备"] and sox>=0) else "🟡 中性")
    vv["判断"]=vv.apply(lambda r:"回调机会" if pd.notna(r["涨跌"]) and r["涨跌"]<=-2 and r["新闻面"]!="🔴 风险" else "不追涨" if pd.notna(r["涨跌"]) and r["涨跌"]>=3 else "观察",axis=1)
    st.dataframe(vv[["板块","涨跌","新闻面","判断"]],hide_index=True,use_container_width=True,height=300)

# 第二行
D,E,F=st.columns([1,1.15,1.05],gap="small")
with D:
    st.markdown("### 🏆 今日机会 TOP3")
    opp=vv.copy()
    opp["分"]=opp.apply(lambda r:80 if r["判断"]=="回调机会" else 65 if r["新闻面"]=="🟢 利好" else 50,axis=1)
    for i,(_,r) in enumerate(opp.sort_values("分",ascending=False).head(3).iterrows(),1):
        st.markdown(f"<div class='card'><b>{i}　{r['板块']}</b><span style='float:right' class='blue'>{r['分']}分</span><br><span class='muted'>今日 {r['涨跌']:+.2f}% · {r['新闻面']} · {r['判断']}</span></div>",unsafe_allow_html=True)
with E:
    st.markdown("### 🧠 为什么这么买？")
    why=pd.DataFrame([
    ["NVIDIA/AI需求","产业趋势","支持核心仓"],["SOX半导体",f"{sox:+.2f}%","观察强弱"],
    ["美债10Y",f"{tnx:.2f}","限制科技加仓" if tnx>=4.6 else "压力可控"],
    ["VIX",f"{vix:.1f}","风险偏高" if vix>=30 else "正常"],
    ["CPO代理",f"{cp:+.2f}%","回撤关注" if cp<=-2 else "正常"],
    ["政策风险","有" if policy_bad else "未触发","暂停动态仓" if policy_bad else "正常执行"]],columns=["关注项","当前状态","对策略影响"])
    st.dataframe(why,hide_index=True,use_container_width=True)
    st.info(f"综合结论：{state}。基础计划继续，动态仓根据风险温度调整。")
with F:
    st.markdown("### 🧯 如果今天继续跌怎么办？")
    plan=pd.DataFrame([
    ["纳指","≤ -2.5%","AI逻辑正常且VIX可控",f"加到 {100}元"],
    ["CPO","≤ -2%","无重大政策利空",f"加到 {40}元"],
    ["半导体","≤ -2%","产业逻辑正常",f"加到 {20}元"],
    ["重大风险","触发","官方/高可信利空","动态仓 0元"]],columns=["板块","条件","确认项","动作"])
    st.dataframe(plan,hide_index=True,use_container_width=True)

# 第三行
st.markdown("### 🌍 全球市场速览")
cols=st.columns(6)
for col,name in zip(cols,["纳斯达克","标普500","SOX","黄金","VIX","美债10Y"]):
    r=row(name)
    if r is not None and pd.notna(r["价格"]):
        col.metric(name,f"{r['价格']:.2f}",f"{r['涨跌']:+.2f}%")
    else:col.metric(name,"暂不可用")

G,H1,I=st.columns([1,1,1.15],gap="small")
with G:
    st.markdown("### 🎯 我的真实行业暴露")
    ex=pd.DataFrame([["AI/半导体",29],["CPO/光通信",18],["黄金",15],["海外科技",17],["其他/待迁移",19],["越南",2]],columns=["行业","占比"])
    fig=px.pie(ex,names="行业",values="占比",hole=.52);fig.update_layout(height=270,margin=dict(l=5,r=5,t=5,b=5),showlegend=True)
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
with H1:
    st.markdown("### 💼 我的持仓概览")
    st.metric("持仓基金数",len(PORT));st.metric("估算总市值",f"¥{PORT['金额'].sum():,.0f}")
    st.dataframe(PORT[["基金","金额","状态"]].head(7),hide_index=True,use_container_width=True,height=220)
with I:
    st.markdown("### 💸 额外资金分配建议")
    amount=st.select_slider("如果今天有额外资金",options=[0,500,1000,2000],value=500)
    if amount:
        cash=.35 if risk_score<70 else .55
        alloc=pd.DataFrame([["纳指",.25],["CPO",.18],["半导体",.10],["其他机会",1-cash-.53],["现金",cash]],columns=["去向","比例"])
        alloc["金额"]=(alloc["比例"]*amount).round(-1).astype(int)
        st.dataframe(alloc[["去向","金额"]],hide_index=True,use_container_width=True)
    else:st.caption("无额外资金，不强行加仓。")

st.caption("说明：行情与新闻来自公开数据源，可能延迟或限流；板块数据为核心成分股代理涨跌，不冒充官方行业指数。工作台用于个人投研辅助，不保证收益。")
