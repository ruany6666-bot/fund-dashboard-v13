
import streamlit as st
import pandas as pd
import requests, feedparser, json, os
from urllib.parse import quote
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="阮嘤基金投资工作台 V18",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

HEADERS={"User-Agent":"Mozilla/5.0"}
DATA_DIR="data"
os.makedirs(DATA_DIR,exist_ok=True)
RULE_FILE=os.path.join(DATA_DIR,"rules.json")
LOG_FILE=os.path.join(DATA_DIR,"investment_log.csv")

# =========================
# 样式：V17 终端视觉 + V16 功能密度
# =========================
st.markdown("""
<style>
.block-container{padding:1rem 1.2rem 2rem;max-width:1850px}
section[data-testid="stSidebar"]{width:225px!important}
section[data-testid="stSidebar"] .block-container{padding:.8rem}
[data-testid="stMetric"]{
    background:#fff;border:1px solid #e7ebf1;border-radius:12px;
    padding:10px 12px;box-shadow:0 1px 5px rgba(20,40,80,.04)
}
.card{
    background:#fff;border:1px solid #e7ebf1;border-radius:14px;
    padding:13px 15px;margin-bottom:10px;box-shadow:0 2px 8px rgba(20,40,80,.04)
}
.soft{background:#f7f9fc;border-radius:12px;padding:12px}
.kpi{font-size:27px;font-weight:800;line-height:1.1}
.muted{color:#7b8494;font-size:12px}
.good{color:#0a9b61}.bad{color:#e64b4b}.warn{color:#e58a00}.blue{color:#1677ff}
.tag{display:inline-block;border-radius:6px;padding:2px 7px;font-size:12px;font-weight:700;margin-right:5px}
.tag-r{background:#fff0f0;color:#d9363e}
.tag-g{background:#edf9f3;color:#078b57}
.tag-y{background:#fff7e6;color:#c97900}
.tag-b{background:#edf5ff;color:#1677ff}
hr{border:none;border-top:1px solid #eef1f5;margin:8px 0}
div[data-testid="stDataFrame"]{border:1px solid #edf0f4;border-radius:10px;overflow:hidden}
h1{font-size:1.7rem!important;margin-bottom:.15rem!important}
h2{font-size:1.12rem!important}
@media(max-width:900px){
    section[data-testid="stSidebar"]{width:190px!important}
    .block-container{padding:.6rem}
    [data-testid="column"]{min-width:48%!important}
}
</style>
""",unsafe_allow_html=True)

# =========================
# 投资规则中心（来自 V16）
# =========================
DEFAULT_RULES={
    "纳指基础":50,"纳指机会":100,
    "CPO基础":20,"CPO机会":40,
    "半导体基础":10,"半导体机会":20,
    "黄金基础":50,
    "建信中档":50,"建信机会":100
}
def load_rules():
    try:
        with open(RULE_FILE,"r",encoding="utf-8") as f:
            return {**DEFAULT_RULES,**json.load(f)}
    except:
        return DEFAULT_RULES.copy()

def save_rules(r):
    with open(RULE_FILE,"w",encoding="utf-8") as f:
        json.dump(r,f,ensure_ascii=False,indent=2)

rules=load_rules()

# =========================
# 当前持仓
# =========================
PORTFOLIO=pd.DataFrame([
["易方达全球成长精选",3626.13,"保留仓","保留，不新增"],
["华安黄金ETF联接C",2148.84,"核心防守","50元/日"],
["德邦鑫星/CPO",1383.63,"核心进攻","20元/日"],
["嘉实全球产业升级",1334.24,"待迁移","逐步迁出"],
["建信新兴市场",1207.11,"动态核心","0/50/100"],
["东方人工智能/半导体",875.65,"核心进攻","10元/日"],
["财通景气甄选一年持有",864.11,"锁定","等待可赎回"],
["天弘全球高端制造",847.87,"待迁移","逐步迁出"],
["华夏移动互联",885.89,"接近封顶","约1000元停止新增"],
["同泰慧盈混合C",485.94,"待评估","暂不新增"],
["天弘越南市场C",312.79,"卫星","小仓观察"],
["国泰纳斯达克100",249.79,"核心","50元/日"],
],columns=["基金","金额","定位","动作"])

BASKETS={
"CPO/光通信":[("中际旭创","sz300308"),("新易盛","sz300502"),("天孚通信","sz300394"),("光迅科技","sz002281")],
"半导体设备":[("北方华创","sz002371"),("中微公司","sh688012"),("拓荆科技","sh688072"),("芯源微","sh688037")],
"创新药":[("恒瑞医药","sh600276"),("百济神州","sh688235"),("信达生物","hk01801")],
"机器人":[("三花智控","sz002050"),("绿的谐波","sh688017"),("拓普集团","sh601689")],
"有色/铜":[("紫金矿业","sh601899"),("洛阳钼业","sh603993"),("江西铜业","sh600362")],
"电力/电网":[("国电南瑞","sh600406"),("许继电气","sz000400"),("平高电气","sh600312")],
"消费/白酒":[("贵州茅台","sh600519"),("五粮液","sz000858"),("泸州老窖","sz000568")],
"券商":[("中信证券","sh600030"),("东方财富","sz300059"),("华泰证券","sh601688")]
}

NEWS_RULES={
"AI/算力":["nvidia","英伟达","ai data center","gpu","blackwell","rubin","capex"],
"CPO/光通信":["1.6t","800g","cpo","optical module","光模块","光通信","中际旭创","新易盛"],
"HBM/存储":["hbm","micron","sk hynix","samsung","kioxia","dram","nand","存储"],
"半导体设备":["北方华创","中微公司","拓荆科技","芯源微","半导体设备"],
"黄金/宏观":["gold","黄金","federal reserve","fed","treasury","美债","cpi","nonfarm","非农","通胀"],
"政策风险":["export control","出口管制","sanction","制裁","restriction","限制","tariff","关税","禁令"]
}
POS=["增长","超预期","上调","订单","surge","growth","beat","record","raise","expands","upgrade"]
NEG=["限制","制裁","禁令","关税","下调","restrict","sanction","ban","tariff","cut","miss","weak"]

# =========================
# 数据函数
# =========================
def get_json(url,params=None,timeout=8):
    try:
        r=requests.get(url,params=params,headers=HEADERS,timeout=timeout)
        r.raise_for_status()
        return r.json()
    except:
        return None

def yahoo(symbol):
    j=get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",{"interval":"1d","range":"5d"})
    try:
        q=j["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        q=[float(x) for x in q if x is not None]
        return q[-1],(q[-1]/q[-2]-1)*100,q
    except:
        return None,None,[]

def tencent(code):
    try:
        r=requests.get(f"https://qt.gtimg.cn/q={code}",headers=HEADERS,timeout=8)
        r.encoding="gbk"
        p=r.text.split('="',1)[1].rsplit('"',1)[0].split("~")
        cur,pre=float(p[3]),float(p[4])
        return cur,(cur/pre-1)*100
    except:
        return None,None

@st.cache_data(ttl=60)
def market_data():
    mp={
        "上证":"000001.SS","创业板":"399006.SZ","科创50":"000688.SS",
        "纳斯达克":"^IXIC","标普500":"^GSPC","SOX":"^SOX",
        "VIX":"^VIX","美债10Y":"^TNX","黄金":"GC=F"
    }
    rows=[]
    for name,symbol in mp.items():
        p,c,h=yahoo(symbol)
        rows.append([name,p,c,h])
    return pd.DataFrame(rows,columns=["市场","价格","涨跌","历史"])

@st.cache_data(ttl=180)
def sector_data():
    rows=[]
    for sec,stocks in BASKETS.items():
        vals=[];detail=[]
        for name,code in stocks:
            _,pct=tencent(code)
            if pct is not None:
                vals.append(pct)
                detail.append(f"{name} {pct:+.1f}%")
        rows.append([sec,sum(vals)/len(vals) if vals else None," ｜ ".join(detail) if detail else "数据暂不可用"])
    return pd.DataFrame(rows,columns=["板块","涨跌","成分"])

def source_grade(title):
    t=title.lower()
    if any(x in t for x in ["reuters","路透","federal reserve","公司公告","交易所"]): return "A"
    if any(x in t for x in ["bloomberg","彭博","cnbc","financial times","证券时报","财联社","第一财经"]): return "B"
    return "C"

def classify_news(title):
    t=title.lower()
    topics=[];score=50
    for topic,keys in NEWS_RULES.items():
        if any(k.lower() in t for k in keys): topics.append(topic)
    score+=sum(8 for x in POS if x.lower() in t)
    score-=sum(10 for x in NEG if x.lower() in t)
    if "政策风险" in topics: score-=8
    return "/".join(topics) or "其他",max(0,min(100,score))

@st.cache_data(ttl=900)
def news_data():
    qs=[
        "NVIDIA AI data center","1.6T optical module CPO","HBM Micron SK Hynix Samsung",
        "中国 半导体设备","gold Federal Reserve Treasury yields",
        "中国 光模块 出口管制","China A shares policy"
    ]
    rows=[];seen=set()
    for q in qs:
        try:
            f=feedparser.parse(f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans")
            for e in f.entries[:7]:
                title=e.get("title","")
                if not title or title in seen: continue
                seen.add(title)
                topic,score=classify_news(title)
                rows.append([topic,score,source_grade(title),title,e.get("published",""),e.get("link","")])
        except:
            pass
    df=pd.DataFrame(rows,columns=["主题","分数","可信度","新闻","时间","链接"])
    if not df.empty:
        df["重要度"]=df.apply(lambda r:min(5,max(1,round(abs(r["分数"]-50)/12)+2+(1 if r["可信度"]=="A" else 0))),axis=1)
        df["判断"]=df["分数"].apply(lambda x:"🟢 利好" if x>=60 else "🔴 利空" if x<=40 else "🟡 中性")
    return df

m=market_data()
sec=sector_data()
news=news_data()

def row(name):
    x=m[m["市场"]==name]
    return x.iloc[0] if len(x) else None
def pct(name):
    r=row(name)
    return float(r["涨跌"]) if r is not None and pd.notna(r["涨跌"]) else 0
def val(name,default=0):
    r=row(name)
    return float(r["价格"]) if r is not None and pd.notna(r["价格"]) else default
def topic_score(key):
    if news.empty:return 50
    x=news[news["主题"].str.contains(key,na=False)]
    return float(x["分数"].mean()) if len(x) else 50

nas=pct("纳斯达克")
vix=val("VIX",20)
tnx=val("美债10Y",4.3)
sox=pct("SOX")
cp=sec.loc[sec["板块"]=="CPO/光通信","涨跌"]
cp=float(cp.iloc[0]) if len(cp) and pd.notna(cp.iloc[0]) else 0
sp=sec.loc[sec["板块"]=="半导体设备","涨跌"]
sp=float(sp.iloc[0]) if len(sp) and pd.notna(sp.iloc[0]) else 0

manual_policy=False
if not news.empty:
    pr=news[news["主题"].str.contains("政策风险",na=False)]
    policy_bad=(len(pr)>0 and (pr["可信度"].isin(["A","B"])).any() and pr["分数"].mean()<=42)
else:
    policy_bad=False

ai_score=topic_score("AI")
cpo_score=topic_score("CPO")
semi_score=(topic_score("HBM")+topic_score("半导体"))/2

risk_score=45
risk_score+=15 if tnx>=4.6 else 8 if tnx>=4.1 else 0
risk_score+=15 if vix>=30 else 8 if vix>=22 else 0
risk_score+=10 if policy_bad else 0
risk_score+=8 if nas<=-2 else 0
risk_score=max(0,min(100,risk_score))

# V16 规则化决策
nas_buy=rules["纳指机会"] if nas<=-2.5 and ai_score>=55 and tnx<4.6 and vix<32 else rules["纳指基础"]
cpo_buy=rules["CPO机会"] if cp<=-2 and cpo_score>=55 and not policy_bad else rules["CPO基础"]
semi_buy=rules["半导体机会"] if sp<=-2 and semi_score>=55 else rules["半导体基础"]
gold_buy=rules["黄金基础"]
jx_buy=0 if policy_bad or tnx>=4.6 else rules["建信机会"] if nas<=-2 and ai_score>=55 and vix<30 else rules["建信中档"]
total=nas_buy+cpo_buy+semi_buy+gold_buy+jx_buy

if policy_bad or risk_score>=78:
    state="🔴 风险偏高"
    one="重大风险或宏观压力偏高，基础定投为主，压缩动态仓。"
elif (nas<=-2 or cp<=-2 or sp<=-2) and ai_score>=45:
    state="🔵 回撤机会"
    one="价格出现回撤，但暂未检测到核心逻辑明显破坏。"
elif tnx>=4.6:
    state="🟡 只定投不追涨"
    one="利率压力偏高，不适合扩大科技动态仓。"
else:
    state="🟢 正常执行"
    one="没有触发重大风险或明显机会，按既定计划执行。"

# =========================
# Sidebar：V17 导航 + V16 规则中心
# =========================
with st.sidebar:
    st.markdown("## 📊 阮嘤基金")
    st.caption("投资工作台 · V18 融合版")
    st.markdown("---")
    for x in [
        "🏠 市场驾驶舱","📈 市场看板","💼 我的持仓","▦ 板块分析",
        "🔥 机会追踪","🌍 全球市场","📰 新闻中心","📅 事件日历",
        "💰 资金计划","⚙️ 投资规则","🩺 组合体检","📒 投资日志"
    ]:
        st.markdown(f"**{x}**" if "市场驾驶舱" in x else x)
    st.markdown("---")
    st.caption("今日定投计划")
    st.markdown(f"<div class='kpi blue'>¥{total}</div>",unsafe_allow_html=True)
    st.caption(f"纳指 ¥{nas_buy} · 黄金 ¥{gold_buy}<br>CPO ¥{cpo_buy} · 半导体 ¥{semi_buy}<br>建信 ¥{jx_buy}",unsafe_allow_html=True)
    if st.button("🔄 刷新数据",use_container_width=True):
        st.cache_data.clear();st.rerun()
    with st.expander("⚙️ 投资规则中心"):
        edited={}
        for k,v in rules.items():
            edited[k]=st.number_input(k,min_value=0,max_value=500,value=int(v),step=10,key="rule_"+k)
        if st.button("保存规则",use_container_width=True):
            save_rules(edited);st.success("规则已保存")

# =========================
# Header
# =========================
st.markdown("# 阮嘤基金投资工作台 V18　<span class='tag tag-b'>V16 × V17 融合版</span>",unsafe_allow_html=True)
st.caption(f"● 市场状态：{state}　　更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 第一屏
A,B,C=st.columns([1.05,1.2,1.05],gap="small")
with A:
    st.markdown("### 🔥 市场情绪与风险")
    gauge=go.Figure(go.Indicator(
        mode="gauge+number",value=risk_score,title={"text":"风险温度"},
        gauge={"axis":{"range":[0,100]},"bar":{"thickness":.22},
               "steps":[{"range":[0,45]},{"range":[45,70]},{"range":[70,100]}]}
    ))
    gauge.update_layout(height=200,margin=dict(l=15,r=15,t=35,b=5))
    st.plotly_chart(gauge,use_container_width=True,config={"displayModeBar":False})
    x1,x2,x3=st.columns(3)
    x1.metric("VIX",f"{vix:.1f}")
    x2.metric("美债10Y",f"{tnx:.2f}")
    x3.metric("SOX",f"{sox:+.2f}%")
    st.info(one)

with B:
    st.markdown("### 📰 今日重大新闻")
    if news.empty:
        st.warning("新闻源暂不可用")
    else:
        major=news.sort_values(["重要度","可信度"],ascending=[False,True]).head(6)
        for _,r in major.iterrows():
            cls="tag-g" if r["分数"]>=60 else "tag-r" if r["分数"]<=40 else "tag-y"
            label="利好" if r["分数"]>=60 else "利空" if r["分数"]<=40 else "中性"
            stars="★"*int(r["重要度"])+"☆"*(5-int(r["重要度"]))
            st.markdown(
                f"<span class='tag {cls}'>{label}</span><b>{r['新闻'][:58]}</b><br>"
                f"<span class='muted'>{r['主题']} · 可信度 {r['可信度']} · {stars}</span><hr>",
                unsafe_allow_html=True
            )

with C:
    st.markdown("### 📊 板块涨跌与利好利空")
    sv=sec.copy()
    def news_face(secname):
        key="CPO" if "CPO" in secname else "半导体" if "半导体" in secname else secname
        sc=topic_score(key)
        return "🟢 利好" if sc>=60 else "🔴 利空" if sc<=40 else "🟡 中性"
    sv["新闻面"]=sv["板块"].apply(news_face)
    def judge(r):
        p=r["涨跌"]
        if pd.isna(p):return "⚪ 数据不足"
        if p<=-2 and r["新闻面"]=="🟢 利好":return "🔵 回撤机会"
        if p<=-2 and r["新闻面"]=="🔴 利空":return "🔴 谨慎抄底"
        if p>=3 and r["新闻面"]=="🟢 利好":return "🟡 强但不追"
        return "🟢 正常" if r["新闻面"]=="🟢 利好" else "🟡 观察"
    sv["综合判断"]=sv.apply(judge,axis=1)
    st.dataframe(sv[["板块","涨跌","新闻面","综合判断"]],hide_index=True,use_container_width=True,height=310)

# 今日资金卡
st.markdown("### 💰 今日执行")
cols=st.columns(5)
for col,name,amt in zip(cols,["纳指","黄金","CPO","半导体","建信"],[nas_buy,gold_buy,cpo_buy,semi_buy,jx_buy]):
    col.metric(name,f"¥{amt}")
st.success(f"今日建议总投入：¥{total}。{one}")

# 第二屏
D,E,F=st.columns([1,1.15,1.05],gap="small")
with D:
    st.markdown("### 🏆 今日机会 TOP3")
    opp=sv.copy()
    def score_op(r):
        if r["综合判断"]=="🔵 回撤机会":return 85
        if r["综合判断"]=="🟢 正常":return 68
        if r["综合判断"]=="🟡 强但不追":return 60
        if r["综合判断"]=="🟡 观察":return 50
        return 35
    opp["机会分"]=opp.apply(score_op,axis=1)
    for i,(_,r) in enumerate(opp.sort_values("机会分",ascending=False).head(3).iterrows(),1):
        pcttxt="—" if pd.isna(r["涨跌"]) else f"{r['涨跌']:+.2f}%"
        st.markdown(
            f"<div class='card'><b>{i}　{r['板块']}</b>"
            f"<span style='float:right' class='blue'>{r['机会分']}分</span><br>"
            f"<span class='muted'>今日 {pcttxt} · {r['新闻面']} · {r['综合判断']}</span></div>",
            unsafe_allow_html=True
        )

with E:
    st.markdown("### 🧠 为什么今天这么买？")
    why=pd.DataFrame([
        ["AI新闻面",f"{ai_score:.0f}分","支持加仓" if ai_score>=60 else "中性观察" if ai_score>=45 else "压缩动态仓"],
        ["SOX半导体",f"{sox:+.2f}%","判断AI硬件强弱"],
        ["美债10Y",f"{tnx:.2f}","限制科技加仓" if tnx>=4.6 else "压力可控"],
        ["VIX",f"{vix:.1f}","风险偏高" if vix>=30 else "正常"],
        ["CPO代理",f"{cp:+.2f}%","回撤关注" if cp<=-2 else "正常"],
        ["政策风险","已触发" if policy_bad else "未触发","暂停动态仓" if policy_bad else "正常执行"]
    ],columns=["关注项","当前状态","对策略影响"])
    st.dataframe(why,hide_index=True,use_container_width=True)
    st.info(f"综合结论：{state}。{one}")

with F:
    st.markdown("### 🧯 如果今天继续跌怎么办？")
    plan=pd.DataFrame([
        ["纳指","≤ -2.5%","AI逻辑正常 + VIX可控",f"{rules['纳指基础']} → {rules['纳指机会']}"],
        ["CPO","≤ -2%","无重大政策利空",f"{rules['CPO基础']} → {rules['CPO机会']}"],
        ["半导体","≤ -2%","产业逻辑正常",f"{rules['半导体基础']} → {rules['半导体机会']}"],
        ["重大风险","触发","官方/高可信利空","动态仓 0"]
    ],columns=["板块","触发条件","确认项","动作"])
    st.dataframe(plan,hide_index=True,use_container_width=True)

# 全球市场
st.markdown("### 🌍 全球市场速览")
cols=st.columns(6)
for col,name in zip(cols,["纳斯达克","标普500","SOX","黄金","VIX","美债10Y"]):
    r=row(name)
    if r is not None and pd.notna(r["价格"]):
        col.metric(name,f"{r['价格']:.2f}",f"{r['涨跌']:+.2f}%")
    else:
        col.metric(name,"暂不可用")

# 第三屏：组合
G,H,I=st.columns([1,1.1,1.05],gap="small")
with G:
    st.markdown("### 🎯 我的真实行业暴露")
    ex=pd.DataFrame([
        ["AI/半导体",29],["CPO/光通信",18],["黄金",15],
        ["海外科技",17],["其他/待迁移",19],["越南",2]
    ],columns=["行业","占比"])
    fig=px.pie(ex,names="行业",values="占比",hole=.52)
    fig.update_layout(height=270,margin=dict(l=5,r=5,t=5,b=5))
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    st.warning("科技/AI相关底层资产重复度较高，新增资金要看相关性，不只看基金名字。")

with H:
    st.markdown("### 💼 我的持仓概览")
    st.metric("估算总市值",f"¥{PORTFOLIO['金额'].sum():,.0f}")
    st.dataframe(PORTFOLIO[["基金","金额","定位"]],hide_index=True,use_container_width=True,height=255)

with I:
    st.markdown("### 🔔 持仓管理提醒")
    alerts=pd.DataFrame([
        ["华夏移动互联","🟡 接近封顶","约1000元停止新增"],
        ["嘉实全球产业升级","🟠 待迁移","逐步迁往纳指/建信"],
        ["天弘全球高端制造","🟠 待迁移","逐步迁往纳指/建信"],
        ["财通景气甄选一年持有","🔒 锁定","等待可赎回"],
        ["同泰慧盈混合C","⚪ 待评估","暂不新增"]
    ],columns=["基金","状态","动作"])
    st.dataframe(alerts,hide_index=True,use_container_width=True,height=255)

# 额外资金
st.markdown("### 💸 额外资金分配建议")
amount=st.select_slider("如果今天突然多出一笔钱",options=[0,500,1000,2000,5000],value=500)
if amount>0:
    cash=0.55 if risk_score>=70 else 0.40
    weights={"纳指":0.20,"CPO":0.15,"半导体":0.10,"其他机会":max(0,1-cash-0.45),"现金":cash}
    if jx_buy>=rules["建信机会"]:
        weights["建信"]=0.10
        weights["现金"]=max(0,weights["现金"]-0.10)
    alloc=pd.DataFrame(weights.items(),columns=["去向","比例"])
    alloc["金额"]=(alloc["比例"]*amount).round(-1).astype(int)
    x,y=st.columns([1,1])
    x.dataframe(alloc[["去向","金额"]],hide_index=True,use_container_width=True)
    y.plotly_chart(px.pie(alloc,names="去向",values="金额",hole=.45),use_container_width=True)
else:
    st.caption("无额外资金，不强行加仓。")

# 投资日志 + 周战报入口（V16）
st.markdown("### 📒 投资日志与本周战报")
with st.expander("记录今天实际买入"):
    actual={}
    for k,default in [("纳指",nas_buy),("黄金",gold_buy),("CPO",cpo_buy),("半导体",semi_buy),("建信",jx_buy)]:
        actual[k]=st.number_input(f"实际买入 · {k}",min_value=0,value=int(default),step=10,key="act_"+k)
    if st.button("保存今天记录"):
        rec={
            "日期":datetime.now().strftime("%Y-%m-%d %H:%M"),
            "状态":state,"建议总额":total,"判断":one,
            "建议_纳指":nas_buy,"建议_黄金":gold_buy,"建议_CPO":cpo_buy,"建议_半导体":semi_buy,"建议_建信":jx_buy,
            "实际_纳指":actual["纳指"],"实际_黄金":actual["黄金"],"实际_CPO":actual["CPO"],"实际_半导体":actual["半导体"],"实际_建信":actual["建信"]
        }
        pd.DataFrame([rec]).to_csv(LOG_FILE,mode="a",header=not os.path.exists(LOG_FILE),index=False,encoding="utf-8-sig")
        st.success("已保存到投资日志")
if os.path.exists(LOG_FILE):
    try:
        lg=pd.read_csv(LOG_FILE)
        st.dataframe(lg.tail(7),hide_index=True,use_container_width=True)
        st.metric("累计建议投入",f"¥{lg['建议总额'].sum():,.0f}")
    except:
        pass

# 组合体检
st.markdown("### 🩺 组合体检")
cols=st.columns(4)
for c,(name,valx) in zip(cols,[("AI集中度",82),("分散程度",62),("黄金防守",72),("流动性",68)]):
    c.metric(name,f"{valx}/100")
st.info("当前主要问题不是基金数量少，而是多只基金底层资产存在科技/AI重复暴露。")

# 未来事件入口
st.markdown("### 📅 未来7天事件日历")
st.caption("保留事件日历入口。未接入可靠日历源前不编造 CPI、非农、财报日期；重大事件优先从高可信新闻中识别。")

st.caption("V18 = V16 的决策深度 + V17 的专业终端界面。公开行情与新闻源可能延迟或限流；数据不可用时明确显示，不虚构实时值。")
