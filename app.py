import streamlit as st
import pandas as pd
import requests
import feedparser
import plotly.express as px
from urllib.parse import quote

st.set_page_config(
    page_title="阮嘤基金投资工作台 V15",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

HEADERS = {"User-Agent": "Mozilla/5.0"}

# -----------------------------
# 基础持仓
# -----------------------------
PORTFOLIO = pd.DataFrame([
    ["易方达全球成长精选", 3626.13, "保留仓", "保留，不新增"],
    ["华安黄金ETF联接C", 2148.84, "核心防守", "50元/日"],
    ["德邦鑫星/CPO", 1383.63, "核心进攻", "20元/日"],
    ["嘉实全球产业升级", 1334.24, "待迁移", "逐步迁出"],
    ["建信新兴市场", 1207.11, "动态核心", "0/50/100"],
    ["东方人工智能/半导体", 875.65, "核心进攻", "10元/日"],
    ["财通景气甄选一年持有", 864.11, "锁定", "到期前不操作"],
    ["天弘全球高端制造", 847.87, "待迁移", "逐步迁出"],
    ["华夏移动互联", 885.89, "接近封顶", "约1000元停止新增"],
    ["同泰慧盈混合C", 485.94, "待评估", "暂不新增"],
    ["天弘越南市场C", 312.79, "卫星", "小仓观察"],
    ["国泰纳斯达克100", 249.79, "核心", "50元/日"],
], columns=["基金", "金额", "定位", "操作"])

FUND_EXPOSURE = {
    "建信新兴市场": {
        "NVIDIA": 9.38, "TSMC": 9.68, "SK Hynix": 8.94,
        "Samsung": 7.80, "SanDisk": 7.16, "Lumentum": 3.56
    },
    "德邦鑫星/CPO": {
        "中际旭创": 9.92, "新易盛": 9.81, "东山精密": 9.50,
        "胜宏科技": 7.95, "天孚通信": 7.93
    },
    "东方人工智能/半导体": {
        "中科飞测": 9.55, "芯源微": 9.19, "中微公司": 9.12,
        "华海清科": 9.08, "北方华创": 8.92
    },
    "易方达全球成长精选": {
        "Lam Research": 6.41, "Kioxia": 5.89, "TSMC": 5.54,
        "AMD": 4.96, "新易盛": 4.68, "中际旭创": 4.61
    },
    "华夏移动互联": {
        "Micron": 8.16, "SanDisk": 6.53, "AMD": 5.30,
        "Intel": 4.94, "Lumentum": 4.43
    }
}

TOPIC_RULES = {
    "AI/纳指": {
        "keywords": ["nvidia","英伟达","gpu","ai data center","blackwell","rubin","hyperscaler","capex"],
        "funds": ["国泰纳斯达克100","建信新兴市场","易方达全球成长精选"]
    },
    "CPO/光通信": {
        "keywords": ["1.6t","800g","cpo","optical module","co-packaged optics","光模块","光通信","中际旭创","新易盛","lumentum"],
        "funds": ["德邦鑫星/CPO","易方达全球成长精选","建信新兴市场"]
    },
    "HBM/存储": {
        "keywords": ["hbm","dram","nand","micron","sk hynix","samsung","kioxia","存储","美光","海力士"],
        "funds": ["建信新兴市场","华夏移动互联","易方达全球成长精选"]
    },
    "半导体设备": {
        "keywords": ["北方华创","中微公司","拓荆科技","芯源微","半导体设备","国产替代"],
        "funds": ["东方人工智能/半导体"]
    },
    "黄金/利率": {
        "keywords": ["gold","黄金","federal reserve","fed","treasury yield","美债","降息","加息","inflation","通胀"],
        "funds": ["华安黄金ETF联接C","国泰纳斯达克100","建信新兴市场"]
    },
    "政策风险": {
        "keywords": ["export control","出口管制","sanction","制裁","restriction","限制","tariff","关税","禁令","blacklist"],
        "funds": ["德邦鑫星/CPO","易方达全球成长精选","东方人工智能/半导体"]
    },
    "创新药": {
        "keywords": ["biotech","创新药","license-out","授权","临床","获批","fda","bd"],
        "funds": []
    }
}

POS = ["beat","beats","surge","growth","record","raise","raises","upgrade","expands","order","订单","增长","超预期","上调","扩产","中标","获批","授权"]
NEG = ["miss","misses","cut","cuts","ban","restrict","restriction","sanction","probe","weak","下调","限制","制裁","调查","不及预期","禁令","关税"]

BASKETS = {
    "CPO/光通信": [("中际旭创","sz300308"),("新易盛","sz300502"),("天孚通信","sz300394"),("光迅科技","sz002281")],
    "半导体设备": [("北方华创","sz002371"),("中微公司","sh688012"),("拓荆科技","sh688072"),("芯源微","sh688037")],
    "创新药": [("恒瑞医药","sh600276"),("百济神州","sh688235"),("信达生物HK","hk01801")],
    "机器人": [("三花智控","sz002050"),("绿的谐波","sh688017"),("拓普集团","sh601689")],
    "电力/电网": [("国电南瑞","sh600406"),("许继电气","sz000400"),("平高电气","sh600312")],
    "有色/铜": [("紫金矿业","sh601899"),("洛阳钼业","sh603993"),("江西铜业","sh600362")],
}

def get_json(url, params=None, timeout=8):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def yahoo(symbol):
    j = get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}",
                 {"interval":"1d","range":"5d"})
    try:
        r = j["chart"]["result"][0]
        closes = [x for x in r["indicators"]["quote"][0]["close"] if x is not None]
        last, prev = float(closes[-1]), float(closes[-2])
        return last, (last / prev - 1) * 100
    except Exception:
        return None, None

def eastmoney_index(secid):
    j = get_json("https://push2.eastmoney.com/api/qt/stock/get",
                 {"secid":secid,"fields":"f43,f170"})
    try:
        return j["data"]["f43"]/100, j["data"]["f170"]/100
    except Exception:
        return None, None

def tencent_quote(code):
    try:
        r = requests.get(f"https://qt.gtimg.cn/q={code}", headers=HEADERS, timeout=8)
        r.encoding = "gbk"
        body = r.text.split('="',1)[1].rsplit('"',1)[0]
        p = body.split("~")
        price, prev = float(p[3]), float(p[4])
        pct = (price/prev - 1)*100 if prev else None
        return price, pct
    except Exception:
        return None, None

def first_valid(*providers):
    for fn in providers:
        try:
            price, pct = fn()
            if price is not None and pct is not None:
                return price, pct
        except Exception:
            pass
    return None, None

@st.cache_data(ttl=60)
def markets():
    specs = [
        ("上证", lambda: first_valid(lambda:eastmoney_index("1.000001"), lambda:tencent_quote("sh000001"), lambda:yahoo("000001.SS"))),
        ("创业板", lambda: first_valid(lambda:eastmoney_index("0.399006"), lambda:tencent_quote("sz399006"), lambda:yahoo("399006.SZ"))),
        ("科创50", lambda: first_valid(lambda:eastmoney_index("1.000688"), lambda:tencent_quote("sh000688"), lambda:yahoo("000688.SS"))),
        ("纳斯达克", lambda:yahoo("^IXIC")),
        ("标普500", lambda:yahoo("^GSPC")),
        ("SOX半导体", lambda:yahoo("^SOX")),
        ("VIX", lambda:yahoo("^VIX")),
        ("美债10Y", lambda:yahoo("^TNX")),
        ("黄金", lambda:yahoo("GC=F")),
    ]
    rows=[]
    for name, fn in specs:
        p, pct = fn()
        rows.append([name,p,pct])
    return pd.DataFrame(rows, columns=["市场","价格","涨跌幅"])

@st.cache_data(ttl=180)
def basket_radar():
    rows=[]
    for sector, stocks in BASKETS.items():
        vals=[]; detail=[]
        for name, code in stocks:
            _, pct = tencent_quote(code)
            if pct is not None:
                vals.append(pct)
                detail.append(f"{name}{pct:+.1f}%")
        avg = sum(vals)/len(vals) if vals else None
        rows.append([sector, avg, " / ".join(detail) if detail else "数据暂不可用"])
    return pd.DataFrame(rows, columns=["板块","平均涨跌幅","成分表现"])

def classify(title):
    text=title.lower()
    topics=[]; funds=[]; score=50
    for topic, rule in TOPIC_RULES.items():
        if any(k.lower() in text for k in rule["keywords"]):
            topics.append(topic)
            funds += rule["funds"]
    for k in POS:
        if k.lower() in text:
            score += 6
    for k in NEG:
        if k.lower() in text:
            score -= 8
    if "政策风险" in topics:
        score -= 8
    score=max(0,min(100,score))
    return " / ".join(topics) if topics else "其他", score, "、".join(sorted(set(funds)))

@st.cache_data(ttl=900)
def news():
    queries=[
        "NVIDIA AI data center",
        "1.6T optical module CPO",
        "HBM Micron SK Hynix Samsung",
        "中国 半导体设备",
        "gold Federal Reserve Treasury yields",
        "中国 光模块 出口管制",
        "创新药 BD 授权"
    ]
    rows=[]; seen=set()
    for q in queries:
        try:
            f=feedparser.parse(f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans")
            for e in f.entries[:8]:
                title=e.get("title","")
                if not title or title in seen:
                    continue
                seen.add(title)
                topic, score, funds = classify(title)
                rows.append([topic,score,funds,title,e.get("link","")])
        except Exception:
            pass
    return pd.DataFrame(rows, columns=["主题","评分","影响基金","新闻","链接"])

def topic_score(ndf, key):
    if ndf.empty:
        return 50
    x=ndf[ndf["主题"].str.contains(key, na=False)]
    return round(x["评分"].mean(),1) if len(x) else 50

def auto_bond_pressure(m):
    r=m[m["市场"]=="美债10Y"]
    if len(r)==0 or pd.isna(r.iloc[0]["价格"]):
        return 2
    y=float(r.iloc[0]["价格"])
    if y>=5.0: return 4
    if y>=4.6: return 3
    if y>=4.1: return 2
    if y>=3.6: return 1
    return 0

def auto_ai_strength(m, scores):
    sox=m[m["市场"]=="SOX半导体"]
    nas=m[m["市场"]=="纳斯达克"]
    sox_pct=float(sox.iloc[0]["涨跌幅"]) if len(sox) and pd.notna(sox.iloc[0]["涨跌幅"]) else 0
    nas_pct=float(nas.iloc[0]["涨跌幅"]) if len(nas) and pd.notna(nas.iloc[0]["涨跌幅"]) else 0
    x=2
    if scores["AI"]>=65: x+=1
    if sox_pct>=1: x+=1
    if scores["AI"]<40: x-=1
    if sox_pct<=-2: x-=1
    if nas_pct<=-2: x-=1
    return max(0,min(4,x))

def auto_cn_pullback(radar):
    if radar.empty:
        return 2
    r=radar[radar["板块"].isin(["CPO/光通信","半导体设备"])]
    vals=[x for x in r["平均涨跌幅"].tolist() if pd.notna(x)]
    if not vals:
        return 2
    avg=sum(vals)/len(vals)
    if avg<=-4: return 4
    if avg<=-2: return 3
    if avg<0: return 2
    if avg<2: return 1
    return 0

def get_market_pct(m, name, default=0):
    r=m[m["市场"]==name]
    if len(r) and pd.notna(r.iloc[0]["涨跌幅"]):
        return float(r.iloc[0]["涨跌幅"])
    return default

def decision(m, bond, ai, cn, policy, scores):
    nas_pct=get_market_pct(m,"纳斯达克",0)
    vix_row=m[m["市场"]=="VIX"]
    vix=float(vix_row.iloc[0]["价格"]) if len(vix_row) and pd.notna(vix_row.iloc[0]["价格"]) else 20

    nas,cpo,semi,gold,jx = 50,20,10,50,50
    notes=[]

    if policy or scores["政策风险"]<38:
        jx=0; notes.append("政策风险偏高，建信暂停")
    elif ai<=1 or scores["AI"]<35:
        jx=0; notes.append("AI信号偏弱，建信暂停")
    elif bond>=3 and nas_pct>-1 and scores["AI"]<65:
        jx=0; notes.append("利率压力高且没有明显回撤，建信暂停")
    elif nas_pct<=-2 and ai>=3 and bond<=2 and scores["AI"]>=55:
        jx=100; notes.append("纳指回撤但AI逻辑未坏，建信100")
    else:
        notes.append("建信50")

    if scores["AI"]<30 and bond>=3:
        nas=30
    elif nas_pct<=-2.5 and scores["AI"]>=60 and bond<=2 and vix<32:
        nas=100

    if policy or scores["CPO"]<30:
        cpo=10
    elif cn>=3 and ai>=2 and scores["CPO"]>=60:
        cpo=40

    if scores["半导体"]<30:
        semi=0
    elif cn>=3 and scores["半导体"]>=60:
        semi=20

    # 黄金保持固定定投为主
    gold=50

    total=nas+cpo+semi+gold+jx

    # 今天属于什么状态
    if policy or vix>=35:
        state="🔴 风险偏高"
        action="以基础定投为主，不启动额外机会仓。"
    elif nas_pct<=-2 or cn>=3:
        state="🔵 出现回撤机会"
        action="可以按规则小幅提高动态仓，但不要一次性满仓。"
    elif bond>=3:
        state="🟡 只定投，不追涨"
        action="利率压力偏高，维持基本盘，等待更好的价格。"
    else:
        state="🟢 正常执行"
        action="按计划定投，动态仓保持克制。"

    return {
        "纳指":nas,"CPO":cpo,"半导体":semi,"黄金":gold,"建信":jx,
        "总投入":total,"说明":"；".join(notes),
        "状态":state,"行动":action
    }

def opportunity_scores(radar, scores, m, policy):
    data=[]
    radar_map={r["板块"]:r["平均涨跌幅"] for _,r in radar.iterrows()} if not radar.empty else {}
    sox=get_market_pct(m,"SOX半导体",0)

    candidates={
        "CPO/光通信": 50 + (scores["CPO"]-50)*0.6,
        "半导体设备": 50 + (scores["半导体"]-50)*0.6 + max(-10,min(10,sox*2)),
        "创新药": 50 + (scores["创新药"]-50)*0.7,
        "机器人": 50,
        "电力/电网": 50,
        "有色/铜": 50,
    }
    for sector in list(candidates):
        pct=radar_map.get(sector)
        if pct is not None and pd.notna(pct):
            # 下跌但不是暴跌时，提高“观察机会分”
            if -4 <= pct <= -1:
                candidates[sector]+=8
            elif pct>3:
                candidates[sector]-=5
        if policy and sector=="CPO/光通信":
            candidates[sector]-=15

    for sector,score in candidates.items():
        score=max(0,min(100,round(score,1)))
        stars="★"*max(1,min(5,round(score/20)))+"☆"*(5-max(1,min(5,round(score/20))))
        data.append([sector,score,stars])
    return pd.DataFrame(data,columns=["机会","评分","星级"]).sort_values("评分",ascending=False)

def allocate_extra(extra, decision_obj, opp_df, policy, bond):
    if extra<=0:
        return pd.DataFrame(columns=["去向","金额","理由"])
    weights={"建信":0.25,"CPO":0.18,"半导体":0.10,"A股其他机会":0.07,"现金":0.40}

    if decision_obj["建信"]==100:
        weights["建信"]+=0.10; weights["现金"]-=0.10
    elif decision_obj["建信"]==0:
        weights["建信"]-=0.15; weights["现金"]+=0.15

    if decision_obj["CPO"]>=40 and not policy:
        weights["CPO"]+=0.08; weights["现金"]-=0.08
    if decision_obj["半导体"]>=20:
        weights["半导体"]+=0.05; weights["现金"]-=0.05
    if bond>=3:
        weights["现金"]+=0.08; weights["建信"]-=0.05; weights["CPO"]-=0.03

    weights={k:max(0,v) for k,v in weights.items()}
    s=sum(weights.values())
    weights={k:v/s for k,v in weights.items()}

    alloc={k:round(extra*v/10)*10 for k,v in weights.items()}
    alloc["现金"] += extra-sum(alloc.values())

    reason_map={
        "建信":"海外AI动态仓",
        "CPO":"国内光通信核心",
        "半导体":"国产设备核心",
        "A股其他机会":"只给当前Top机会少量资金",
        "现金":"保留等待更好价格"
    }
    return pd.DataFrame([[k,v,reason_map[k]] for k,v in alloc.items()],columns=["去向","金额","理由"])

# -----------------------------
# 页面数据
# -----------------------------
m=markets()
n=news()
radar=basket_radar()

scores={
    "AI":topic_score(n,"AI"),
    "CPO":topic_score(n,"CPO"),
    "半导体":topic_score(n,"半导体"),
    "黄金":topic_score(n,"黄金"),
    "政策风险":topic_score(n,"政策风险"),
    "创新药":topic_score(n,"创新药")
}

auto_bond=auto_bond_pressure(m)
auto_ai=auto_ai_strength(m,scores)
auto_cn=auto_cn_pullback(radar)

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.title("阮嘤基金投资工作台")
    st.caption("V15 · 正式日用版")
    st.divider()

    auto_mode=st.toggle("自动校准",True)
    if auto_mode:
        bond, ai, cn = auto_bond, auto_ai, auto_cn
        st.metric("美债压力",bond)
        st.metric("AI基本面",ai)
        st.metric("A股科技回撤",cn)
    else:
        bond=st.slider("美债压力",0,4,auto_bond)
        ai=st.slider("AI基本面",0,4,auto_ai)
        cn=st.slider("A股科技回撤",0,4,auto_cn)

    policy=st.toggle("重大政策风险",False)

    if st.button("🔄 立即刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("固定基本盘：纳指50 + CPO20 + 半导体10 + 黄金50")

# -----------------------------
# Header
# -----------------------------
st.title("📊 阮嘤基金投资工作台 V15")
st.caption("个人动态投资决策中心 · 自动行情 + 新闻影响 + 基金穿透 + 机会雷达 + 今日执行")

d=decision(m,bond,ai,cn,policy,scores)

# 顶部10秒看懂
st.subheader("🚦 今天先看这里")
c1,c2,c3=st.columns([1,1,2])
c1.metric("市场状态",d["状态"])
c2.metric("今日建议总投入",f'{d["总投入"]}元')
c3.info(d["行动"])

# 今日金额
st.subheader("🎯 今天怎么买")
cols=st.columns(5)
for col,k in zip(cols,["纳指","CPO","半导体","黄金","建信"]):
    col.metric(k,f'{d[k]}元')
st.success(d["说明"])

# 全球市场
st.subheader("🌍 全球市场与风险温度")
names=["上证","创业板","科创50","纳斯达克","标普500","黄金"]
cols=st.columns(3)
for i,name in enumerate(names):
    r=m[m["市场"]==name]
    if len(r) and pd.notna(r.iloc[0]["价格"]):
        cols[i%3].metric(name,f'{r.iloc[0]["价格"]:.2f}',f'{r.iloc[0]["涨跌幅"]:+.2f}%')
    else:
        cols[i%3].metric(name,"暂不可用")

rcols=st.columns(3)
for c,name in zip(rcols,["美债10Y","VIX","SOX半导体"]):
    r=m[m["市场"]==name]
    if len(r) and pd.notna(r.iloc[0]["价格"]):
        c.metric(name,f'{r.iloc[0]["价格"]:.2f}',f'{r.iloc[0]["涨跌幅"]:+.2f}%')
    else:
        c.metric(name,"暂不可用")

# 新闻决策分
st.subheader("🧠 新闻决策分")
cs=st.columns(6)
for c,(k,v) in zip(cs,scores.items()):
    c.metric(k,f"{v:.0f}分","偏利好" if v>=65 else "偏利空" if v<40 else "中性")

# 机会Top3
opp=opportunity_scores(radar,scores,m,policy)
st.subheader("⭐ 今日机会 TOP 3")
top3=opp.head(3)
cols=st.columns(3)
for col,(_,r) in zip(cols,top3.iterrows()):
    col.metric(r["机会"],f'{r["评分"]:.0f}分',r["星级"])

with st.expander("查看全部A股机会雷达"):
    st.dataframe(opp,use_container_width=True,hide_index=True)
    st.dataframe(radar,use_container_width=True,hide_index=True)

# 额外资金
st.subheader("💸 今天如果有额外资金")
extra=st.number_input("额外可用资金（元）",min_value=0,value=0,step=50)
alloc=allocate_extra(extra,d,opp,policy,bond)
if extra>0 and not alloc.empty:
    a,b=st.columns([1,1])
    a.dataframe(alloc,use_container_width=True,hide_index=True)
    b.plotly_chart(px.pie(alloc,names="去向",values="金额",hole=.45),use_container_width=True)
else:
    st.caption("没有额外资金时保持0即可，不需要为了“有机会”强行加仓。")

# 持仓管理
st.subheader("💼 持仓管理提醒")
alerts=[
    ["华夏移动互联","🟡 接近约1000元封顶","达到目标后停止新增"],
    ["嘉实全球产业升级","🟠 待迁移","后续逐步迁往纳指/建信"],
    ["天弘全球高端制造","🟠 待迁移","后续逐步迁往纳指/建信"],
    ["财通景气甄选一年持有","🔒 锁定","到最早可赎回日前不操作"],
    ["同泰慧盈混合C","⚪ 待评估","没有完成持仓分析前不新增"],
    ["易方达全球成长精选","🟢 保留","申购暂停时保留现有仓即可"],
]
st.dataframe(pd.DataFrame(alerts,columns=["基金","状态","当前动作"]),use_container_width=True,hide_index=True)

# 基金穿透
st.subheader("🔎 核心基金穿透")
fund_name=st.selectbox("选择基金",list(FUND_EXPOSURE.keys()))
exp=pd.DataFrame(
    [[k,v] for k,v in FUND_EXPOSURE[fund_name].items()],
    columns=["底层资产","权重%"]
).sort_values("权重%",ascending=False)
a,b=st.columns([1,1])
a.dataframe(exp,use_container_width=True,hide_index=True)
b.plotly_chart(px.bar(exp.sort_values("权重%"),x="权重%",y="底层资产",orientation="h"),use_container_width=True)

# 新闻
st.subheader("📰 与持仓有关的新闻")
if not n.empty:
    st.dataframe(n[["主题","评分","影响基金","新闻"]].head(30),use_container_width=True,hide_index=True)
else:
    st.warning("新闻源暂不可用。")

# 总持仓
with st.expander("查看全部基金持仓"):
    a,b=st.columns([1,1])
    a.dataframe(PORTFOLIO,use_container_width=True,hide_index=True)
    b.plotly_chart(px.pie(PORTFOLIO,names="基金",values="金额",hole=.45),use_container_width=True)

st.caption("V15 为个人投研辅助工具。公开行情/新闻接口可能延迟或限流；页面会明确显示数据不可用，不会虚构实时数据。建议金额是规则化辅助，不构成收益保证。")
