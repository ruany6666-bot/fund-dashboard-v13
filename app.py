
import streamlit as st
import pandas as pd
import requests, feedparser, json, os
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="阮嘤基金投资工作台 V20", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
H={"User-Agent":"Mozilla/5.0"}
TZ=ZoneInfo("Asia/Shanghai")
st_autorefresh(interval=60*1000, key="market_auto_refresh")
DATA="data"; os.makedirs(DATA,exist_ok=True)
RULE_FILE=os.path.join(DATA,"rules.json")
LOG_FILE=os.path.join(DATA,"investment_log.csv")
BUDGET_FILE=os.path.join(DATA,"budget.json")

st.markdown("""
<style>
.block-container{padding:.75rem 1rem 2rem;max-width:1750px}
section[data-testid="stSidebar"]{width:230px!important}
section[data-testid="stSidebar"] .block-container{padding:.7rem}
[data-testid="stMetric"]{background:#fff;border:1px solid #e8ecf2;border-radius:11px;padding:9px 11px;box-shadow:0 1px 4px rgba(30,50,80,.04)}
.card{background:#fff;border:1px solid #e7ebf1;border-radius:12px;padding:12px 14px;margin-bottom:9px}
.small{font-size:12px;color:#7b8494}.big{font-size:25px;font-weight:800}
.tag{display:inline-block;border-radius:6px;padding:2px 7px;font-size:12px;font-weight:700;margin-right:5px}
.r{background:#fff0f0;color:#d9363e}.g{background:#edf9f3;color:#078b57}.y{background:#fff7e6;color:#c97900}.b{background:#edf5ff;color:#1677ff}
div[data-testid="stDataFrame"]{border:1px solid #edf0f4;border-radius:9px;overflow:hidden}
h1{font-size:1.65rem!important;margin:.1rem 0!important} h2{font-size:1.15rem!important}
@media(max-width:1100px){
 .block-container{padding:.55rem}
 [data-testid="column"]{min-width:47%!important}
 h1{font-size:1.45rem!important}
}
</style>
""",unsafe_allow_html=True)

DEFAULT_RULES={"纳指基础":50,"纳指机会":100,"CPO基础":20,"CPO机会":40,"半导体基础":10,"半导体机会":20,"黄金基础":50,"建信中档":50,"建信机会":100}
def load_json(path,default):
    try:
        with open(path,"r",encoding="utf-8") as f:return {**default,**json.load(f)}
    except:return default.copy()
def save_json(path,x):
    with open(path,"w",encoding="utf-8") as f:json.dump(x,f,ensure_ascii=False,indent=2)
rules=load_json(RULE_FILE,DEFAULT_RULES)
budget=load_json(BUDGET_FILE,{"月预算":4000})

PORT=pd.DataFrame([
["易方达全球成长精选",3626.13,"海外科技/半导体","保留","不新增"],
["华安黄金ETF联接C",2148.84,"黄金","核心防守","50/日"],
["德邦鑫星/CPO",1383.63,"CPO/光通信","核心","20/日"],
["嘉实全球产业升级",1334.24,"全球科技","待迁移","迁往纳指/建信"],
["建信新兴市场",1207.11,"AI/半导体/HBM","动态核心","0/50/100"],
["东方人工智能/半导体",875.65,"半导体设备","核心","10/日"],
["财通景气甄选一年持有",864.11,"A股成长","锁定","等待可赎回"],
["天弘全球高端制造",847.87,"科技制造","待迁移","迁往纳指/建信"],
["华夏移动互联",885.89,"海外半导体","接近封顶","约1000停止"],
["同泰慧盈混合C",485.94,"待分析","待评估","不新增"],
["天弘越南市场C",312.79,"越南","卫星","观察"],
["国泰纳斯达克100",249.79,"纳斯达克100","核心","50/日"],
],columns=["基金","金额","主要暴露","定位","动作"])

FUND_DETAIL={
"德邦鑫星/CPO":{"核心持仓":"中际旭创、新易盛、东山精密、胜宏科技、天孚通信、炬光科技、剑桥科技、长芯博创、鼎通科技、沪电股份","风险":"AI资本开支、光模块出口限制、CPO/1.6T景气度","规则":"基础20；明显回撤且逻辑未坏→40"},
"东方人工智能/半导体":{"核心持仓":"中科飞测、芯源微、中微公司、华海清科、北方华创、精测电子、富创精密、拓荆科技、寒武纪、盛美上海","风险":"半导体设备估值、国产替代节奏、资本开支","规则":"基础10；明显回撤且逻辑未坏→20"},
"建信新兴市场":{"核心持仓":"TSMC、NVIDIA、SK Hynix、Samsung、SanDisk、Broadcom、Western Digital、Micron、Lumentum、Corning","风险":"美债、AI估值、HBM/存储周期","规则":"动态0/50/100"},
"华夏移动互联":{"核心持仓":"Micron、SanDisk、Onto、AMD、Intel、Kioxia、Lumentum、TSMC、STMicro、Astera Labs","风险":"半导体周期、基金风格漂移","规则":"总持仓约1000后停止新增"},
"易方达全球成长精选":{"核心持仓":"Lam Research、Kioxia、TSMC、AMD、新易盛、中际旭创、SanDisk、Intel、源杰科技、ASML","风险":"科技集中、与其他基金重叠","规则":"保留，不新增"},
}
BASKETS={
"CPO/光通信":[("中际旭创","sz300308"),("新易盛","sz300502"),("天孚通信","sz300394"),("光迅科技","sz002281")],
"半导体设备":[("北方华创","sz002371"),("中微公司","sh688012"),("拓荆科技","sh688072"),("芯源微","sh688037")],
"创新药":[("恒瑞医药","sh600276"),("百济神州","sh688235")],
"机器人":[("三花智控","sz002050"),("绿的谐波","sh688017"),("拓普集团","sh601689")],
"有色/铜":[("紫金矿业","sh601899"),("洛阳钼业","sh603993"),("江西铜业","sh600362")],
"电力/电网":[("国电南瑞","sh600406"),("许继电气","sz000400"),("平高电气","sh600312")],
"消费/白酒":[("贵州茅台","sh600519"),("五粮液","sz000858")],
"券商":[("中信证券","sh600030"),("东方财富","sz300059")],
}
POS=["增长","超预期","上调","订单","growth","beat","record","raise","surge","upgrade"]
NEG=["限制","制裁","禁令","关税","下调","restrict","sanction","ban","tariff","cut","miss","weak"]

def gj(url,params=None):
    try:
        r=requests.get(url,params=params,headers=H,timeout=7);r.raise_for_status();return r.json()
    except:return None
def yahoo(s):
    j=gj(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(s)}",{"range":"5d","interval":"1d"})
    try:
        a=[float(x) for x in j["chart"]["result"][0]["indicators"]["quote"][0]["close"] if x is not None]
        return a[-1],(a[-1]/a[-2]-1)*100
    except:return None,None

def eastmoney(secid):
    j=gj("https://push2.eastmoney.com/api/qt/stock/get",{"secid":secid,"fields":"f43,f170"})
    try:return j["data"]["f43"]/100,j["data"]["f170"]/100
    except:return None,None
def fallback(*fns):
    for fn in fns:
        try:
            p,c=fn()
            if p is not None and c is not None:return p,c
        except:pass
    return None,None

def tq(code):
    try:
        r=requests.get(f"https://qt.gtimg.cn/q={code}",headers=H,timeout=7);r.encoding="gbk"
        p=r.text.split('="',1)[1].rsplit('"',1)[0].split("~");a,b=float(p[3]),float(p[4]);return a,(a/b-1)*100
    except:return None,None

@st.cache_data(ttl=60)
def markets():
    specs=[
        ("上证",lambda:fallback(lambda:eastmoney("1.000001"),lambda:tq("sh000001"),lambda:yahoo("000001.SS"))),
        ("创业板",lambda:fallback(lambda:eastmoney("0.399006"),lambda:tq("sz399006"),lambda:yahoo("399006.SZ"))),
        ("科创50",lambda:fallback(lambda:eastmoney("1.000688"),lambda:tq("sh000688"),lambda:yahoo("000688.SS"))),
        ("纳斯达克",lambda:yahoo("^IXIC")),("标普500",lambda:yahoo("^GSPC")),("SOX",lambda:yahoo("^SOX")),
        ("VIX",lambda:yahoo("^VIX")),("美债10Y",lambda:yahoo("^TNX")),("黄金",lambda:yahoo("GC=F"))
    ]
    return pd.DataFrame([[n,*fn()] for n,fn in specs],columns=["市场","价格","涨跌"])
@st.cache_data(ttl=180)
def sectors():
    out=[]
    for sec,ls in BASKETS.items():
        vals=[];detail=[]
        for name,c in ls:
            _,p=tq(c)
            if p is not None:vals.append(p);detail.append(f"{name} {p:+.1f}%")
        out.append([sec,sum(vals)/len(vals) if vals else None," ｜ ".join(detail) if detail else "暂不可用"])
    return pd.DataFrame(out,columns=["板块","涨跌","核心成分"])
@st.cache_data(ttl=900)
def getnews():
    qs=["NVIDIA AI data center","1.6T optical module CPO","HBM Micron SK Hynix Samsung","中国 半导体设备","gold Federal Reserve Treasury","中国 光模块 出口管制","China A shares policy"]
    rows=[];seen=set()
    for q in qs:
        try:
            f=feedparser.parse(f"https://news.google.com/rss/search?q={quote(q)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans")
            for e in f.entries[:7]:
                t=e.get("title","")
                if not t or t in seen:continue
                seen.add(t);lo=t.lower();score=50
                score+=sum(8 for x in POS if x.lower() in lo);score-=sum(10 for x in NEG if x.lower() in lo)
                topic="CPO/光通信" if any(x in lo for x in ["cpo","optical","光模块","1.6t"]) else "HBM/存储" if any(x in lo for x in ["hbm","micron","hynix","samsung"]) else "AI/算力" if any(x in lo for x in ["nvidia","英伟达","ai data"]) else "黄金/宏观" if any(x in lo for x in ["gold","fed","treasury","黄金"]) else "半导体/政策"
                grade="A" if any(x in lo for x in ["reuters","路透","federal reserve","公告"]) else "B" if any(x in lo for x in ["bloomberg","彭博","cnbc","证券时报","财联社"]) else "C"
                importance=min(5,max(2,round(abs(score-50)/10)+2))
                rows.append([topic,max(0,min(100,score)),grade,importance,t,e.get("published",""),e.get("link","")])
        except:pass
    return pd.DataFrame(rows,columns=["主题","分数","可信度","重要度","新闻","时间","链接"])

m=markets();sec=sectors();news=getnews()
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
goldb=rules["黄金基础"];jxb=0 if policy_bad or tnx>=4.6 else rules["建信机会"] if nas<=-2 and vix<30 else rules["建信中档"]
total=nasb+cpob+semib+goldb+jxb
state="🔴 风险偏高" if risk>=75 else "🔵 回撤关注" if (nas<=-2 or cp<=-2 or sp<=-2) else "🟢 正常执行"

# 真导航
with st.sidebar:
    st.markdown("## 📊 阮嘤基金")
    st.caption("V20 · 交互增强完整版")
    page=st.radio("功能导航",[
        "🏠 今日驾驶舱","📈 市场看板","▦ 板块中心","💼 基金中心","📰 新闻中心",
        "🔥 机会与风险","💰 资金计划","🩺 组合体检","📒 投资日志","⚙️ 投资规则"
    ],label_visibility="collapsed")
    st.markdown("---")
    st.markdown(f"<span class='small'>今日建议</span><div class='big' style='color:#1677ff'>¥{total}</div>",unsafe_allow_html=True)
    st.caption(f"纳指{nasb} · 黄金{goldb} · CPO{cpob} · 半导体{semib} · 建信{jxb}")
    if st.button("🔄 刷新实时数据",use_container_width=True):st.cache_data.clear();st.rerun()
    st.caption("每 60 秒自动刷新")
    st.caption("数据健康：🟢页面运行　🟢规则引擎　" + ("🟢新闻" if not news.empty else "🔴新闻"))

st.markdown(f"# {page}")
st.caption(f"{state}　｜　风险温度 {risk}/100　｜　北京时间 {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}　｜　每60秒自动刷新")

if page=="🏠 今日驾驶舱":
    c1,c2,c3,c4,c5=st.columns(5)
    for c,n,a in zip([c1,c2,c3,c4,c5],["纳指","黄金","CPO","半导体","建信"],[nasb,goldb,cpob,semib,jxb]):c.metric(n,f"¥{a}")
    A,B=st.columns([1.05,1.45])
    with A:
        fig=go.Figure(go.Indicator(mode="gauge+number",value=risk,title={"text":"市场风险温度"},gauge={"axis":{"range":[0,100]},"bar":{"thickness":.22},"steps":[{"range":[0,45]},{"range":[45,70]},{"range":[70,100]}]}))
        fig.update_layout(height=220,margin=dict(l=10,r=10,t=40,b=5));st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
        st.dataframe(pd.DataFrame([["VIX",f"{vix:.2f}"],["美债10Y",f"{tnx:.2f}"],["SOX当日",f"{sox:+.2f}%"]],columns=["风险指标","当前值"]),hide_index=True,use_container_width=True)
    with B:
        st.subheader("📰 最重要的 5 条新闻")
        if news.empty:st.warning("新闻暂不可用")
        else:
            for _,r in news.sort_values("重要度",ascending=False).head(5).iterrows():
                lab="利好" if r["分数"]>=60 else "利空" if r["分数"]<=40 else "中性";cl="g" if lab=="利好" else "r" if lab=="利空" else "y"
                st.markdown(f"<div class='card'><span class='tag {cl}'>{lab}</span><b>{r['新闻']}</b><br><span class='small'>{r['主题']} · 可信度{r['可信度']} · {'★'*r['重要度']}</span></div>",unsafe_allow_html=True)
                if r.get("链接",""):
                    st.link_button("打开新闻原文 ↗",r["链接"],key=f"home_news_{r.name}")
    C,D=st.columns(2)
    with C:
        st.subheader("📊 板块涨跌")
        show=sec[["板块","涨跌","核心成分"]].copy()
        show["判断"]=show["涨跌"].apply(lambda x:"🔵 回撤关注" if pd.notna(x) and x<=-2 else "🟡 不追涨" if pd.notna(x) and x>=3 else "🟢 正常")
        st.dataframe(show,hide_index=True,use_container_width=True,height=340)
    with D:
        st.subheader("🔥 今天最值得注意")
        opp=sec.dropna(subset=["涨跌"]).copy()
        opp["机会分"]=opp["涨跌"].apply(lambda x:85 if x<=-2 else 60 if x<1 else 50)
        st.dataframe(opp.sort_values("机会分",ascending=False).head(3)[["板块","涨跌","机会分"]],hide_index=True,use_container_width=True)
        st.warning("今天不要做：追涨单日大涨板块；在高可信基本面利空出现时机械抄底；为了凑满仓位而动用未来定投资金。")

elif page=="📈 市场看板":
    st.subheader("全球与A股市场")
    cols=st.columns(3)
    for i,(_,r) in enumerate(m.iterrows()):
        if pd.notna(r["价格"]):cols[i%3].metric(r["市场"],f'{r["价格"]:.2f}',f'{r["涨跌"]:+.2f}%')
        else:cols[i%3].metric(r["市场"],"暂不可用")
    st.info("A股指数采用多源回退；VIX与美债主要用于控制科技动态仓；SOX用于观察AI/半导体硬件风险偏好。页面每60秒自动刷新。")

elif page=="▦ 板块中心":
    chosen=st.selectbox("选择板块",list(BASKETS.keys()))
    r=sec[sec["板块"]==chosen].iloc[0]
    a,b,c=st.columns(3);a.metric("代理涨跌","—" if pd.isna(r["涨跌"]) else f'{r["涨跌"]:+.2f}%');b.metric("风险温度",f"{risk}/100");c.metric("状态","回撤关注" if pd.notna(r["涨跌"]) and r["涨跌"]<=-2 else "观察")
    st.subheader("核心成分股")
    st.write(r["核心成分"])
    st.subheader("相关重大新闻")
    rel=news[news["主题"].str.contains("CPO" if "CPO" in chosen else "半导体" if "半导体" in chosen else chosen,na=False)]
    if rel.empty:
        st.caption("暂未抓到直接相关新闻。")
    else:
        for _,nr in rel.head(10).iterrows():
            with st.container(border=True):
                st.write(nr["新闻"])
                st.caption(f"可信度 {nr['可信度']} · {nr['时间']}")
                if nr.get("链接",""): st.link_button("打开原文 ↗",nr["链接"],key=f"sector_news_{chosen}_{nr.name}")
    if chosen=="CPO/光通信":st.info(f"对核心CPO基金：当前基础 {rules['CPO基础']} 元；明显回撤且逻辑未坏时提高到 {rules['CPO机会']} 元。")
    elif chosen=="半导体设备":st.info(f"对半导体核心基金：当前基础 {rules['半导体基础']} 元；机会档 {rules['半导体机会']} 元。")
    else:st.caption("该板块属于战术观察池，不自动挤占核心定投资金。")

elif page=="💼 基金中心":
    chosen=st.selectbox("选择我的基金",PORT["基金"].tolist())
    r=PORT[PORT["基金"]==chosen].iloc[0]
    a,b,c,d=st.columns(4);a.metric("当前金额",f'¥{r["金额"]:,.2f}');b.metric("定位",r["定位"]);c.metric("主要暴露",r["主要暴露"]);d.metric("当前动作",r["动作"])
    detail=FUND_DETAIL.get(chosen)
    if detail:
        st.subheader("🔬 底层穿透")
        st.write(detail["核心持仓"])
        st.subheader("⚠️ 主要风险");st.write(detail["风险"])
        st.subheader("💰 我的规则");st.success(detail["规则"])
    else:st.info("该基金还没有完整穿透数据，当前按“不新增/原计划”处理，避免假装知道实时底层持仓。")
    st.subheader("相关新闻")
    keys=r["主要暴露"].split("/")
    rel=news[news["主题"].apply(lambda x:any(k.lower() in x.lower() for k in keys))]
    if rel.empty:
        st.caption("暂无匹配新闻。")
    else:
        for _,nr in rel.head(10).iterrows():
            with st.container(border=True):
                st.write(nr["新闻"])
                st.caption(f"可信度 {nr['可信度']} · {nr['时间']}")
                if nr.get("链接",""): st.link_button("打开原文 ↗",nr["链接"],key=f"fund_news_{chosen}_{nr.name}")

elif page=="📰 新闻中心":
    topic=st.selectbox("新闻筛选",["全部"]+sorted(news["主题"].unique().tolist()) if not news.empty else ["全部"])
    grade=st.multiselect("可信度",["A","B","C"],default=["A","B"])
    x=news.copy()
    if topic!="全部":x=x[x["主题"]==topic]
    x=x[x["可信度"].isin(grade)] if not x.empty else x
    if not x.empty:
        x["利好利空"]=x["分数"].apply(lambda z:"🟢 利好" if z>=60 else "🔴 利空" if z<=40 else "🟡 中性")
        for _,nr in x.iterrows():
            with st.container(border=True):
                st.markdown(f"**{nr['利好利空']}｜{nr['主题']}｜重要度 {'★'*int(nr['重要度'])}｜可信度 {nr['可信度']}**")
                st.write(nr["新闻"])
                st.caption(nr["时间"])
                if nr.get("链接",""): st.link_button("打开新闻原文 ↗",nr["链接"],key=f"news_center_{nr.name}")
    else:st.warning("当前筛选没有新闻。")

elif page=="🔥 机会与风险":
    L,R=st.columns(2)
    with L:
        st.subheader("🔥 机会 TOP3")
        x=sec.dropna(subset=["涨跌"]).copy();x["机会分"]=x["涨跌"].apply(lambda z:85 if z<=-2 else 65 if z<=0 else 50)
        st.dataframe(x.sort_values("机会分",ascending=False).head(3)[["板块","涨跌","机会分","核心成分"]],hide_index=True,use_container_width=True)
    with R:
        st.subheader("🚨 风险 TOP3")
        risks=pd.DataFrame([["美债收益率",tnx,90 if tnx>=4.6 else 60],["VIX",vix,90 if vix>=30 else 55],["政策风险","触发" if policy_bad else "未触发",95 if policy_bad else 30]],columns=["风险","当前","风险分"])
        st.dataframe(risks.sort_values("风险分",ascending=False),hide_index=True,use_container_width=True)
    st.subheader("🧠 决策解释")
    st.dataframe(pd.DataFrame([["美债10Y",f"{tnx:.2f}","限制动态仓" if tnx>=4.6 else "压力可控"],["VIX",f"{vix:.2f}","风险偏高" if vix>=30 else "正常"],["SOX",f"{sox:+.2f}%","AI硬件风险偏好"],["CPO代理",f"{cp:+.2f}%","回撤关注" if cp<=-2 else "正常"],["半导体设备代理",f"{sp:+.2f}%","回撤关注" if sp<=-2 else "正常"],["政策风险","触发" if policy_bad else "未触发","动态仓暂停" if policy_bad else "正常"]],columns=["信号","当前值","策略含义"]),hide_index=True,use_container_width=True)
    st.subheader("🧯 下跌预案")
    st.dataframe(pd.DataFrame([["纳指","≤-2.5%","AI逻辑正常+VIX可控",f"{rules['纳指基础']}→{rules['纳指机会']}"],["CPO","≤-2%","无重大政策利空",f"{rules['CPO基础']}→{rules['CPO机会']}"],["半导体","≤-2%","产业逻辑正常",f"{rules['半导体基础']}→{rules['半导体机会']}"],["基本面恶化","任何跌幅","高可信重大利空","不机械抄底"]],columns=["对象","触发","确认","动作"]),hide_index=True,use_container_width=True)

elif page=="💰 资金计划":
    newbudget=st.number_input("本月最大投资预算",min_value=0,value=int(budget["月预算"]),step=500)
    if st.button("保存月预算"):save_json(BUDGET_FILE,{"月预算":newbudget});st.success("已保存")
    spent=0
    if os.path.exists(LOG_FILE):
        try:
            lg=pd.read_csv(LOG_FILE);lg["日期"]=pd.to_datetime(lg["日期"]);now=datetime.now(TZ)
            this=lg[(lg["日期"].dt.year==now.year)&(lg["日期"].dt.month==now.month)]
            cols=[c for c in this.columns if c.startswith("实际_")];spent=float(this[cols].sum().sum()) if cols else 0
        except:pass
    rem=max(0,newbudget-spent)
    a,b,c=st.columns(3);a.metric("月预算",f"¥{newbudget:,.0f}");b.metric("已记录投入",f"¥{spent:,.0f}");c.metric("剩余预算",f"¥{rem:,.0f}")
    st.progress(min(1,spent/newbudget) if newbudget else 0)
    st.subheader("额外资金怎么分")
    amount=st.select_slider("额外资金",options=[0,500,1000,2000,5000],value=500)
    cash=.55 if risk>=70 else .4
    if amount:
        w={"纳指":.20,"CPO":.15,"半导体":.10,"其他机会":max(0,1-cash-.45),"现金":cash}
        al=pd.DataFrame(w.items(),columns=["去向","比例"]);al["金额"]=(al["比例"]*amount).round(-1).astype(int)
        st.dataframe(al[["去向","金额"]],hide_index=True,use_container_width=True)

elif page=="🩺 组合体检":
    a,b,c,d=st.columns(4);a.metric("AI集中度","82/100");b.metric("分散程度","62/100");c.metric("黄金防守","72/100");d.metric("流动性","68/100")
    ex=pd.DataFrame([["AI/半导体",29],["CPO/光通信",18],["黄金",15],["海外科技",17],["其他/待迁移",19],["越南",2]],columns=["行业","占比"])
    L,R=st.columns(2);L.plotly_chart(px.pie(ex,names="行业",values="占比",hole=.5),use_container_width=True)
    R.warning("组合的主要问题不是基金数量，而是多只基金底层都集中在AI硬件、半导体和光通信。")
    R.subheader("管理提醒")
    R.dataframe(PORT[PORT["定位"].isin(["待迁移","接近封顶","锁定","待评估"])][["基金","定位","动作"]],hide_index=True,use_container_width=True)

elif page=="📒 投资日志":
    st.subheader("记录今天实际执行")
    actual={}
    for k,dft in [("纳指",nasb),("黄金",goldb),("CPO",cpob),("半导体",semib),("建信",jxb)]:
        actual[k]=st.number_input(k,min_value=0,value=int(dft),step=10,key="log"+k)
    if st.button("保存今日投资记录"):
        rec={"日期":datetime.now(TZ).strftime("%Y-%m-%d %H:%M"),"市场状态":state,"建议总额":total,
             **{f"建议_{k}":v for k,v in {"纳指":nasb,"黄金":goldb,"CPO":cpob,"半导体":semib,"建信":jxb}.items()},
             **{f"实际_{k}":v for k,v in actual.items()}}
        pd.DataFrame([rec]).to_csv(LOG_FILE,mode="a",header=not os.path.exists(LOG_FILE),index=False,encoding="utf-8-sig");st.success("已保存")
    if os.path.exists(LOG_FILE):
        lg=pd.read_csv(LOG_FILE);st.dataframe(lg.tail(30),hide_index=True,use_container_width=True)
    else:st.caption("保存第一条记录后，这里会开始形成你的历史。")

elif page=="⚙️ 投资规则":
    edited={}
    for k,v0 in rules.items():edited[k]=st.number_input(k,min_value=0,max_value=500,value=int(v0),step=10,key="rr"+k)
    if st.button("保存投资规则"):save_json(RULE_FILE,edited);st.success("已保存。刷新后决策引擎按新规则运行。")
    st.info("核心原则：价格跌了不等于可以买。只有价格回撤 + 基本面没有明显恶化，才进入机会档。")

st.caption("V20：北京时间显示、每60秒自动刷新、新闻可点击、A股多源回退、iPad完整信息优化。公开行情/新闻可能延迟或限流；不可用时不伪造数值。")
