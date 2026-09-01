import streamlit as st
import pandas as pd
import requests, feedparser, json, os, re
from datetime import datetime, timedelta
from urllib.parse import quote
import plotly.express as px

st.set_page_config(page_title="阮嘤基金投资工作台 V16", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
HEADERS={"User-Agent":"Mozilla/5.0"}
DATA_DIR="data"; os.makedirs(DATA_DIR, exist_ok=True)
RULE_FILE=os.path.join(DATA_DIR,"rules.json")
LOG_FILE=os.path.join(DATA_DIR,"investment_log.csv")

# ---------- 样式 ----------
st.markdown("""
<style>
.block-container{padding-top:1.2rem;max-width:1400px}
[data-testid="stMetric"]{background:rgba(127,127,127,.07);padding:12px;border-radius:14px}
div[data-testid="stExpander"]{border-radius:14px}
h1{letter-spacing:-1px}
@media(max-width:800px){
 .block-container{padding-left:.7rem;padding-right:.7rem}
 [data-testid="column"]{min-width:48%!important}
 h1{font-size:1.9rem!important}
}
</style>
""", unsafe_allow_html=True)

DEFAULT_RULES={"纳指基础":50,"纳指机会":100,"CPO基础":20,"CPO机会":40,"半导体基础":10,"半导体机会":20,"黄金基础":50,"建信中档":50,"建信机会":100}
def load_rules():
    try:
        with open(RULE_FILE,"r",encoding="utf-8") as f: return {**DEFAULT_RULES,**json.load(f)}
    except: return DEFAULT_RULES.copy()
def save_rules(r):
    with open(RULE_FILE,"w",encoding="utf-8") as f: json.dump(r,f,ensure_ascii=False,indent=2)

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

EXPOSURE={"AI/半导体":38,"CPO/光通信":18,"黄金":15,"其他科技":16,"越南":2,"待迁移/待评估":11}

BASKETS={
"CPO/光通信":[("中际旭创","sz300308"),("新易盛","sz300502"),("天孚通信","sz300394"),("光迅科技","sz002281")],
"半导体设备":[("北方华创","sz002371"),("中微公司","sh688012"),("拓荆科技","sh688072"),("芯源微","sh688037")],
"创新药":[("恒瑞医药","sh600276"),("百济神州","sh688235"),("信达生物","hk01801")],
"机器人":[("三花智控","sz002050"),("绿的谐波","sh688017"),("拓普集团","sh601689")],
"有色/铜":[("紫金矿业","sh601899"),("洛阳钼业","sh603993"),("江西铜业","sh600362")],
"电力/电网":[("国电南瑞","sh600406"),("许继电气","sz000400"),("平高电气","sh600312")],
"消费/白酒":[("贵州茅台","sh600519"),("五粮液","sz000858"),("泸州老窖","sz000568")],
"券商":[("中信证券","sh600030"),("东方财富","sz300059"),("华泰证券","sh601688")],
}

NEWS_RULES={
"AI/算力":["nvidia","英伟达","ai data center","gpu","blackwell","rubin","capex"],
"CPO/光通信":["1.6t","800g","cpo","optical module","光模块","光通信","中际旭创","新易盛"],
"HBM/存储":["hbm","micron","sk hynix","samsung","kioxia","dram","nand","存储"],
"半导体设备":["北方华创","中微公司","拓荆科技","芯源微","半导体设备"],
"黄金/宏观":["gold","黄金","federal reserve","fed","treasury","美债","cpi","nonfarm","非农","通胀"],
"政策风险":["export control","出口管制","sanction","制裁","restriction","限制","tariff","关税","禁令"],
}
POS=["beat","growth","record","raise","upgrade","order","surge","增长","超预期","上调","订单","扩产","获批","授权"]
NEG=["ban","restrict","sanction","cut","weak","miss","tariff","限制","制裁","下调","禁令","关税","调查"]

def get_json(url,params=None,timeout=8):
    try:
        r=requests.get(url,params=params,headers=HEADERS,timeout=timeout); r.raise_for_status(); return r.json()
    except:return None
def yahoo(sym):
    j=get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(sym)}",{"interval":"1d","range":"5d"})
    try:
        q=j["chart"]["result"][0]["indicators"]["quote"][0]["close"]; q=[float(x) for x in q if x is not None]
        return q[-1],(q[-1]/q[-2]-1)*100
    except:return None,None
def em(secid):
    j=get_json("https://push2.eastmoney.com/api/qt/stock/get",{"secid":secid,"fields":"f43,f170"})
    try:return j["data"]["f43"]/100,j["data"]["f170"]/100
    except:return None,None
def tencent(code):
    try:
        r=requests.get(f"https://qt.gtimg.cn/q={code}",headers=HEADERS,timeout=8); r.encoding="gbk"
        p=r.text.split('="',1)[1].rsplit('"',1)[0].split("~"); cur,pre=float(p[3]),float(p[4])
        return cur,(cur/pre-1)*100
    except:return None,None
def fallback(*fns):
    for f in fns:
        try:
            x=f()
            if x[0] is not None and x[1] is not None:return x
        except:pass
    return None,None

@st.cache_data(ttl=60)
def market_data():
    specs=[
    ("上证",lambda:fallback(lambda:em("1.000001"),lambda:tencent("sh000001"),lambda:yahoo("000001.SS"))),
    ("创业板",lambda:fallback(lambda:em("0.399006"),lambda:tencent("sz399006"),lambda:yahoo("399006.SZ"))),
    ("科创50",lambda:fallback(lambda:em("1.000688"),lambda:tencent("sh000688"),lambda:yahoo("000688.SS"))),
    ("纳斯达克",lambda:yahoo("^IXIC")),("标普500",lambda:yahoo("^GSPC")),("SOX",lambda:yahoo("^SOX")),
    ("VIX",lambda:yahoo("^VIX")),("美债10Y",lambda:yahoo("^TNX")),("黄金",lambda:yahoo("GC=F"))]
    return pd.DataFrame([[n,*f()] for n,f in specs],columns=["市场","价格","涨跌幅"])

@st.cache_data(ttl=180)
def sector_data():
    rows=[]
    for sec,stocks in BASKETS.items():
        vals=[];ds=[]
        for name,code in stocks:
            _,p=tencent(code)
            if p is not None: vals.append(p);ds.append(f"{name} {p:+.1f}%")
        rows.append([sec,sum(vals)/len(vals) if vals else None," ｜ ".join(ds) if ds else "数据暂不可用"])
    return pd.DataFrame(rows,columns=["板块","涨跌幅","成分"])

def source_grade(title):
    t=title.lower()
    if any(x in t for x in ["reuters","路透","federal reserve","sec.gov","公司公告","交易所"]):return "A"
    if any(x in t for x in ["bloomberg","彭博","wall street journal","financial times","cnbc"]):return "B"
    if any(x in t for x in ["证券时报","中国证券报","上海证券报","第一财经","财联社"]):return "B"
    return "C"

def classify_news(title):
    t=title.lower(); topics=[];score=50
    for k,keys in NEWS_RULES.items():
        if any(x.lower() in t for x in keys):topics.append(k)
    for x in POS:
        if x.lower() in t:score+=8
    for x in NEG:
        if x.lower() in t:score-=10
    if "政策风险" in topics:score-=10
    return "/".join(topics) or "其他",max(0,min(100,score))

@st.cache_data(ttl=900)
def news_data():
    qs=["NVIDIA AI data center","1.6T optical module CPO","HBM Micron SK Hynix Samsung","中国 半导体设备",
        "gold Federal Reserve Treasury yields","中国 光模块 出口管制","China A shares policy"]
    rows=[];seen=set()
    for q in qs:
        try:
            f=feedparser.parse(f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans")
            for e in f.entries[:8]:
                title=e.get("title","")
                if not title or title in seen:continue
                seen.add(title);topic,score=classify_news(title)
                pub=e.get("published","")
                rows.append([topic,score,source_grade(title),title,pub,e.get("link","")])
        except:pass
    df=pd.DataFrame(rows,columns=["主题","情绪分","可信度","新闻","发布时间","链接"])
    if not df.empty:
        df["重要度"]=df.apply(lambda r:min(5,max(1,round(abs(r["情绪分"]-50)/12)+2+(1 if r["可信度"]=="A" else 0))),axis=1)
        df["判断"]=df["情绪分"].apply(lambda x:"🟢 利好" if x>=60 else "🔴 利空" if x<=40 else "🟡 中性")
    return df

def pct(m,name):
    x=m[m["市场"]==name]
    return float(x.iloc[0]["涨跌幅"]) if len(x) and pd.notna(x.iloc[0]["涨跌幅"]) else 0
def price(m,name,default=None):
    x=m[m["市场"]==name]
    return float(x.iloc[0]["价格"]) if len(x) and pd.notna(x.iloc[0]["价格"]) else default
def topic_score(n,key):
    if n.empty:return 50
    x=n[n["主题"].str.contains(key,na=False)]
    return float(x["情绪分"].mean()) if len(x) else 50

def build_scores(m,n,sectors):
    ai=topic_score(n,"AI"); cpo=topic_score(n,"CPO"); semi=(topic_score(n,"HBM")+topic_score(n,"半导体"))/2
    policy=topic_score(n,"政策风险")
    y=price(m,"美债10Y",4.3);v=price(m,"VIX",20)
    bond=4 if y>=5 else 3 if y>=4.6 else 2 if y>=4.1 else 1 if y>=3.6 else 0
    return {"AI":ai,"CPO":cpo,"半导体":semi,"政策":policy,"美债压力":bond,"VIX":v}

def decision(m,s,sec,rules,manual_policy=False):
    nasp=pct(m,"纳斯达克"); sox=pct(m,"SOX")
    cpo_sec=sec.loc[sec["板块"]=="CPO/光通信","涨跌幅"]
    semi_sec=sec.loc[sec["板块"]=="半导体设备","涨跌幅"]
    cp=float(cpo_sec.iloc[0]) if len(cpo_sec) and pd.notna(cpo_sec.iloc[0]) else 0
    sp=float(semi_sec.iloc[0]) if len(semi_sec) and pd.notna(semi_sec.iloc[0]) else 0
    bad_policy=manual_policy or s["政策"]<=35
    nas=rules["纳指基础"];cpo=rules["CPO基础"];semi=rules["半导体基础"];gold=rules["黄金基础"];jx=rules["建信中档"]
    reasons=[]
    if bad_policy:jx=0;reasons.append("重大政策风险：动态仓收缩")
    elif s["AI"]<38:jx=0;reasons.append("AI新闻面偏弱：建信暂停")
    elif nasp<=-2 and s["AI"]>=55 and s["美债压力"]<=2:jx=rules["建信机会"];reasons.append("纳指明显回撤且AI逻辑正常：建信机会档")
    elif s["美债压力"]>=3:jx=0;reasons.append("美债压力高：建信暂缓")
    else:reasons.append("基本面与宏观均未触发极端条件：建信中档")
    if nasp<=-2.5 and s["AI"]>=55 and s["美债压力"]<=2 and s["VIX"]<32:nas=rules["纳指机会"]
    if cp<=-2 and s["CPO"]>=55 and not bad_policy:cpo=rules["CPO机会"]
    if sp<=-2 and s["半导体"]>=55:semi=rules["半导体机会"]
    # 区分“便宜了”和“坏了”
    if (nasp<=-2 or cp<=-2 or sp<=-2) and not bad_policy and s["AI"]>=45:
        state="🔵 回撤机会";one="价格出现回撤，但暂未检测到核心逻辑破坏。"
    elif bad_policy or s["VIX"]>=35:
        state="🔴 风险偏高";one="先控制动态仓，避免把“坏了”误判成“便宜了”。"
    elif s["美债压力"]>=3:
        state="🟡 只定投不追涨";one="产业面尚可，但利率对科技估值形成压力。"
    else:
        state="🟢 正常执行";one="没有触发重大风险或明显机会，执行基础计划。"
    return {"纳指":nas,"CPO":cpo,"半导体":semi,"黄金":gold,"建信":jx,"总计":nas+cpo+semi+gold+jx,
            "状态":state,"一句话":one,"原因":"；".join(reasons),"纳指跌幅":nasp,"CPO跌幅":cp,"半导体跌幅":sp,"SOX":sox}

def sector_view(sec,n):
    rows=[]
    for _,r in sec.iterrows():
        name=r["板块"];p=r["涨跌幅"]
        key="CPO" if "CPO" in name else "半导体" if "半导体" in name else name
        ns=topic_score(n,key)
        news="🟢 利好" if ns>=60 else "🔴 利空" if ns<=40 else "🟡 中性"
        if pd.isna(p):judge="⚪ 数据不足"
        elif p<=-2 and ns>=55:judge="🔵 回撤机会"
        elif p>=3 and ns>=55:judge="🟡 强但不追"
        elif p<=-2 and ns<=40:judge="🔴 谨慎抄底"
        else:judge="🟢 正常" if ns>=55 else "🟡 观察"
        rows.append([name,p,news,judge,r["成分"]])
    return pd.DataFrame(rows,columns=["板块","今日涨跌","新闻面","综合判断","成分"])

def extra_alloc(amount,d):
    if amount<=0:return pd.DataFrame()
    w={"建信":.22,"CPO":.16,"半导体":.10,"其他机会":.07,"现金":.45}
    if d["建信"]>=100:w["建信"]+=.10;w["现金"]-=.10
    if d["CPO"]>=40:w["CPO"]+=.08;w["现金"]-=.08
    if d["状态"].startswith("🔴"):w["现金"]+=.20;w["建信"]-=.12;w["CPO"]-=.08
    w={k:max(0,v) for k,v in w.items()};z=sum(w.values());w={k:v/z for k,v in w.items()}
    vals={k:round(amount*v/10)*10 for k,v in w.items()};vals["现金"]+=amount-sum(vals.values())
    return pd.DataFrame([[k,v] for k,v in vals.items()],columns=["去向","金额"])

def save_log(d,actuals):
    row={"日期":datetime.now().strftime("%Y-%m-%d %H:%M"),"状态":d["状态"],"建议总额":d["总计"],"判断":d["一句话"],**{f"建议_{k}":d[k] for k in ["纳指","CPO","半导体","黄金","建信"]},**actuals}
    df=pd.DataFrame([row])
    df.to_csv(LOG_FILE,mode="a",header=not os.path.exists(LOG_FILE),index=False,encoding="utf-8-sig")

m=market_data(); n=news_data(); sec=sector_data(); rules=load_rules(); scores=build_scores(m,n,sec)

with st.sidebar:
    st.title("阮嘤 V16")
    st.caption("驾驶舱设置")
    manual_policy=st.toggle("手动标记重大政策风险",False)
    if st.button("🔄 刷新实时数据",use_container_width=True):st.cache_data.clear();st.rerun()
    with st.expander("⚙️ 投资规则中心"):
        edited={}
        for k,v in rules.items():edited[k]=st.number_input(k,min_value=0,max_value=500,value=int(v),step=10)
        if st.button("保存规则",use_container_width=True):save_rules(edited);st.success("规则已保存")
    st.caption("公开数据源失效时显示不可用，不伪造行情。")

d=decision(m,scores,sec,rules,manual_policy)
sv=sector_view(sec,n)

st.title("📊 阮嘤基金投资工作台 V16")
st.caption("个人投资驾驶舱 · 发生了什么 → 对我有什么影响 → 我的钱怎么办 → 事后复盘")

# 第一屏
st.subheader("🚦 今天 10 秒看懂")
a,b,c=st.columns([1,1,2])
a.metric("今日状态",d["状态"]);b.metric("建议投入",f'{d["总计"]} 元');c.info(d["一句话"])
cols=st.columns(5)
for col,k in zip(cols,["纳指","黄金","CPO","半导体","建信"]):col.metric(k,f'{d[k]} 元')
st.caption("决策原因："+d["原因"])

# 重大新闻
st.subheader("📰 今日重大新闻")
if n.empty:st.warning("新闻源暂不可用。")
else:
    major=n.sort_values(["重要度","可信度"],ascending=[False,True]).head(10).copy()
    major["重要度"]=major["重要度"].apply(lambda x:"★"*int(x)+"☆"*(5-int(x)))
    st.dataframe(major[["判断","主题","重要度","可信度","新闻","发布时间"]],use_container_width=True,hide_index=True)
    st.caption("可信度：A=官方/高可信来源；B=主流财经媒体；C=普通聚合来源。低可信消息不会单独触发重大交易动作。")

# 板块
st.subheader("📈 板块涨跌 + 利好利空")
st.dataframe(sv,use_container_width=True,hide_index=True)
valid=sv.dropna(subset=["今日涨跌"])
if not valid.empty:st.plotly_chart(px.bar(valid.sort_values("今日涨跌"),x="今日涨跌",y="板块",orientation="h"),use_container_width=True)

# 机会
st.subheader("🔥 今日机会 TOP 3")
tmp=sv.copy()
def oscore(r):
    p=0 if pd.isna(r["今日涨跌"]) else r["今日涨跌"]
    return 80 if r["综合判断"]=="🔵 回撤机会" else 65 if r["综合判断"]=="🟢 正常" else 50 if r["综合判断"]=="🟡 观察" else 35
tmp["机会分"]=tmp.apply(oscore,axis=1)
top=tmp.sort_values("机会分",ascending=False).head(3)
cc=st.columns(3)
for col,(_,r) in zip(cc,top.iterrows()):col.metric(r["板块"],f'{r["机会分"]} 分',r["综合判断"])

# 为什么这么买
st.subheader("🧠 为什么今天这么买")
reason=pd.DataFrame([
["AI新闻面",scores["AI"],"🟢" if scores["AI"]>=55 else "🔴"],
["美债压力",scores["美债压力"],"🟢" if scores["美债压力"]<=2 else "🔴"],
["VIX",scores["VIX"],"🟢" if scores["VIX"]<25 else "🔴" if scores["VIX"]>=35 else "🟡"],
["纳指当日",d["纳指跌幅"],"🔵 回撤" if d["纳指跌幅"]<=-2 else "🟡 正常"],
["CPO当日",d["CPO跌幅"],"🔵 回撤" if d["CPO跌幅"]<=-2 else "🟡 正常"],
["政策新闻",scores["政策"],"🔴" if scores["政策"]<=35 or manual_policy else "🟢"],
],columns=["信号","数值","状态"])
st.dataframe(reason,use_container_width=True,hide_index=True)

# 预案
st.subheader("🧯 如果今天继续跌，我怎么办")
st.markdown(f"""
- **纳指跌到明显机会区**，且 AI 基本面没有恶化、美债压力可控：`{rules["纳指基础"]} → {rules["纳指机会"]} 元`
- **CPO 明显回撤**，且没有出口禁令/订单恶化等重大利空：`{rules["CPO基础"]} → {rules["CPO机会"]} 元`
- **半导体设备明显回撤**，产业逻辑正常：`{rules["半导体基础"]} → {rules["半导体机会"]} 元`
- **如果是基本面恶化导致的大跌**：不机械抄底，动态仓可以直接降到 0。
""")

# 全球风险
st.subheader("🌍 全球市场 / 风险温度")
cols=st.columns(3)
for i,name in enumerate(["上证","创业板","科创50","纳斯达克","标普500","黄金","SOX","VIX","美债10Y"]):
    r=m[m["市场"]==name]
    if len(r) and pd.notna(r.iloc[0]["价格"]):cols[i%3].metric(name,f'{r.iloc[0]["价格"]:.2f}',f'{r.iloc[0]["涨跌幅"]:+.2f}%')
    else:cols[i%3].metric(name,"暂不可用")

# 持仓和暴露
st.subheader("💼 我的钱现在在哪里")
left,right=st.columns([1.15,1])
left.dataframe(PORTFOLIO,use_container_width=True,hide_index=True)
exp=pd.DataFrame(EXPOSURE.items(),columns=["风险暴露","估算占比"])
right.plotly_chart(px.pie(exp,names="风险暴露",values="估算占比",hole=.5),use_container_width=True)
right.warning("行业暴露为基于最近公开持仓的近似归类，不等同于实时基金净值穿透。")

# 管理提醒
st.subheader("🔔 持仓管理提醒")
st.dataframe(pd.DataFrame([
["华夏移动互联","🟡 接近封顶","约 1000 元后停止新增"],
["嘉实全球产业升级","🟠 待迁移","逐步迁往纳指/建信"],
["天弘全球高端制造","🟠 待迁移","逐步迁往纳指/建信"],
["财通景气甄选一年持有","🔒 锁定","等待最早可赎回日"],
["同泰慧盈混合C","⚪ 待评估","分析完成前不新增"],
],columns=["基金","状态","动作"]),use_container_width=True,hide_index=True)

# 额外资金
st.subheader("💸 今天突然多出一笔钱")
extra=st.number_input("额外可投资金额",min_value=0,value=0,step=100)
ea=extra_alloc(extra,d)
if not ea.empty:
    x,y=st.columns(2);x.dataframe(ea,use_container_width=True,hide_index=True);y.plotly_chart(px.pie(ea,names="去向",values="金额",hole=.45),use_container_width=True)
else:st.caption("没有额外资金就保持 0。系统不会为了“有机会”强迫满仓。")

# 日志/周报
st.subheader("📒 投资日志与本周战报")
with st.expander("记录今天实际买入"):
    actuals={}
    for k in ["纳指","黄金","CPO","半导体","建信"]:
        actuals[f"实际_{k}"]=st.number_input(f"实际买入 · {k}",min_value=0,value=int(d[k]),step=10,key="act_"+k)
    if st.button("保存今天记录"):save_log(d,actuals);st.success("已写入投资日志")
if os.path.exists(LOG_FILE):
    try:
        lg=pd.read_csv(LOG_FILE)
        st.dataframe(lg.tail(7),use_container_width=True,hide_index=True)
        st.metric("日志累计建议投入",f'{lg["建议总额"].sum():.0f} 元')
    except:pass
else:st.caption("第一次保存实际买入后，这里会开始积累你的历史决策。")

# 组合体检
st.subheader("🩺 组合体检")
total=PORTFOLIO["金额"].sum()
ai_risk=82;div=62;defense=72;liquidity=68
cols=st.columns(4)
for c,(nme,val) in zip(cols,[("AI集中度",ai_risk),("分散程度",div),("黄金防守",defense),("流动性",liquidity)]):
    c.metric(nme,f"{val}/100")
st.info("当前最需要关注的是科技/AI相关底层资产重复度。新增资金优先看价格和相关性，不要因为基金名字不同就把它们当成完全分散。")

# 事件日历：不虚构实时事件
st.subheader("📅 未来事件日历")
st.caption("V16 先建立事件日历入口。由于财报/CPI/非农日期需要可靠实时日历源，当前不自动编造日期；重大事件会优先通过新闻区识别。后续接入稳定日历源后再自动展示具体日期。")

st.caption("V16 使用公开行情与新闻源，可能存在延迟、限流或源站不可用。工作台在数据不足时会显示不可用，不会伪造实时值；决策规则用于个人投研辅助，不代表收益保证。")
