import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from datetime import datetime
import time
import io
import streamlit_autorefresh
# 页面配置
st.set_page_config(
    page_title="微流控测试平台控制软件",
    page_icon="🧪",
    layout="centered"
)
if 'message_display' not in st.session_state:
    st.session_state.message_display = {
        'show': False,
        'type': '',  # 'warning' 或 'success'
        'content': '',
        'timestamp': 0
    }
# 初始化状态
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        "pumps": {
            1: { "running": False, "flow": 50, "time": 10, "name": "蛋白液" },
            2: { "running": False, "flow": 30, "time": 15, "name": "缓冲液A" },
            3: { "running": False, "flow": 40, "time": 20, "name": "缓冲液B" }
        },
        "experiment": {
            "current_step": 2,
            "total_steps": 5,
            "progress": 35,
            "remaining_time": "9分钟"
        },
        "system_log": [
            "[14:28:15] 系统启动完成",
            "[14:28:30] 加载实验流程: 蛋白反应检测",
            "[14:29:05] 泵1启动: 50μL/min, 10秒",
            "[14:29:15] 泵1已停止",
            "[14:29:20] 泵2启动: 30μL/min, 15秒",
            "[14:29:35] 泵2已停止",
            "[14:29:36] 开始混合反应，等待5分钟"
        ],
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "affinity_data": [],  # 存储格式: {"protein": "蛋白A", "concentration": 0.1, "affinity": 1.2, ...}
        "uploaded_files": [] , # 存储已上传的文件名
        "emergency_status": False  # 添加紧急停止状态标志
    }

# 辅助函数：添加系统日志
def add_system_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.app_state["system_log"].append(f"[{timestamp}] {message}")
    if len(st.session_state.app_state["system_log"]) > 50:
        st.session_state.app_state["system_log"].pop(0)

# 辅助函数：更新最后更新时间
def update_last_update():
    st.session_state.app_state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 解析FCS数据文件
def parse_fcs_data(uploaded_file):
    """解析FCS仪器导出的CSV数据文件"""
    try:
        df = pd.read_csv(uploaded_file)
        
        # 检查必要的列是否存在
        required_columns = ['protein', 'concentration', 'affinity']
        if not all(col in df.columns for col in required_columns):
            return None, f"CSV文件缺少必要列。需要包含: {', '.join(required_columns)}"
        
        # 转换数据格式
        data = []
        for _, row in df.iterrows():
            data.append({
                "protein": str(row['protein']),
                "concentration": float(row['concentration']),
                "affinity": float(row['affinity']),
                "experiment_id": f"EXP{datetime.now().strftime('%y%m%d')}{len(st.session_state.app_state['affinity_data']) + 1}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return data, "解析成功"
    except Exception as e:
        return None, f"解析失败: {str(e)}"

# 拟合亲和力曲线函数
def fit_affinity_curve(concentrations, affinities):
    """拟合浓度-亲和力曲线"""
    def binding_model(c, kd, bmax):
        """典型的结合模型：Y = (Bmax * C) / (Kd + C)"""
        return (bmax * c) / (kd + c)
    
    try:
        params, _ = curve_fit(binding_model, concentrations, affinities, p0=[1, 100], maxfev=10000)
        return {
            "params": params,  # [Kd, Bmax]
            "model": binding_model
        }
    except Exception as e:
        st.warning(f"曲线拟合失败: {str(e)}")
        return None

# 回调函数：启动泵
def start_pump(pump_id):
    # 只设置泵的运行状态，不阻塞界面
    pump = st.session_state.app_state["pumps"][pump_id]
    pump["running"] = True
    add_system_log(f"泵{pump_id}启动: {pump['flow']}μL/min, {pump['time']}秒")
    update_last_update()
    
    # 使用Streamlit的session_state记录启动时间
    st.session_state.app_state[f"pump_{pump_id}_start_time"] = time.time()
    st.session_state.app_state[f"pump_{pump_id}_duration"] = pump["time"]*5 #加速
    
    # 显示运行中状态，但不阻塞界面
    st.info(f"泵{pump_id}运行中...")

# 在应用主循环中添加一个检查函数
def check_pump_status():
    for pump_id in st.session_state.app_state["pumps"]:
        if (st.session_state.app_state["pumps"][pump_id]["running"] and 
            f"pump_{pump_id}_start_time" in st.session_state.app_state):
            elapsed = time.time() - st.session_state.app_state[f"pump_{pump_id}_start_time"]
            if elapsed >= st.session_state.app_state[f"pump_{pump_id}_duration"]:
                # 泵运行时间已到，停止泵
                st.session_state.app_state["pumps"][pump_id]["running"] = False
                add_system_log(f"泵{pump_id}已停止")
                update_last_update()
                # 清理临时状态
                del st.session_state.app_state[f"pump_{pump_id}_start_time"]
                del st.session_state.app_state[f"pump_{pump_id}_duration"]
# 回调函数：停止泵
def stop_pump(pump_id):
    st.session_state.app_state["pumps"][pump_id]["running"] = False
    add_system_log(f"泵{pump_id}已手动停止")
    update_last_update()

# 回调函数：运行实验流程
def run_experiment():
    add_system_log("开始执行实验流程: 蛋白反应检测")
    update_last_update()
    
    progress_bar = st.progress(35)
    status_text = st.empty()
    
    for progress in range(36, 101):
        st.session_state.app_state["experiment"]["progress"] = progress
        
        if progress >= 60:
            st.session_state.app_state["experiment"]["current_step"] = 3
        if progress >= 80:
            st.session_state.app_state["experiment"]["current_step"] = 4
        if progress == 100:
            st.session_state.app_state["experiment"]["current_step"] = 5
        
        remaining = 9 - (progress - 35) // 7
        st.session_state.app_state["experiment"]["remaining_time"] = f"{remaining}分钟"
        
        progress_bar.progress(progress)
        status_text.text(f"进度: {progress}% | 步骤 {st.session_state.app_state['experiment']['current_step']}/5 | 剩余: {remaining}分钟")
        time.sleep(0.1)  # 加速模拟
    
    add_system_log("实验流程执行完成")
    update_last_update()
    st.success("实验流程已完成")

# 回调函数：紧急停止
def emergency_stop():
    for pump_id in st.session_state.app_state["pumps"]:
        if st.session_state.app_state["pumps"][pump_id]["running"]:
            st.session_state.app_state["pumps"][pump_id]["running"] = False
    st.session_state.app_state["emergency_status"] = True  # 设置紧急停止状态为True
    add_system_log("系统紧急停止已执行")
    update_last_update()
    # st.warning("紧急停止已执行，所有设备已停止运行")
    st.session_state.message_display = {
        'show': True,
        'type': 'warning',
        'content': "紧急停止已执行，所有设备已停止运行",
        'timestamp': time.time()
    }
# 回调函数：紧急停止后重置系统
def reset_after_emergency():
    st.session_state.app_state["emergency_status"] = False  # 重置紧急停止状态
    add_system_log("紧急情况已排查完毕，系统恢复正常状态")
    update_last_update()
    # st.success("系统已恢复正常，可以重新开始实验")
    st.session_state.message_display = {
        'show': True,
        'type': 'success',
        'content': "系统已恢复正常，可以重新开始实验",
        'timestamp': time.time()
    }
# 生成实时数据图表
def generate_realtime_chart():
    x = list(range(20))
    base = np.linspace(0.1, 0.6, 20)
    noise = np.random.normal(0, 0.02, 20)
    y = base + noise
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name='吸光度 (527nm)',
                            line=dict(color='#165DFF'),
                            fill='tozeroy', fillcolor='rgba(22, 93, 255, 0.1)'))
    
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title='时间点',
        yaxis_title='吸光度',
        showlegend=False
    )
    return fig

# 生成亲和力曲线图表
def generate_affinity_chart():
    affinity_data = st.session_state.app_state["affinity_data"]
    if not affinity_data:
        return None
    
    # 获取唯一的蛋白列表
    proteins = list(set(item["protein"] for item in affinity_data))
    
    # 创建图表
    fig = go.Figure()
    
    # 为每种蛋白添加数据点和曲线
    for protein in proteins:
        # 筛选该蛋白的数据
        protein_data = [item for item in affinity_data if item["protein"] == protein]
        concentrations = [item["concentration"] for item in protein_data]
        affinities = [item["affinity"] for item in protein_data]
        
        # 添加数据点
        fig.add_trace(go.Scatter(
            x=concentrations,
            y=affinities,
            mode='markers',
            name=protein,
            marker=dict(size=8)
        ))
        
        # 拟合曲线
        if len(concentrations) >= 3:  # 需要至少3个点才能拟合
            fit_result = fit_affinity_curve(concentrations, affinities)
            if fit_result:
                x_fit = np.linspace(min(concentrations), max(concentrations), 100)
                y_fit = fit_result["model"](x_fit, *fit_result["params"])
                fig.add_trace(go.Scatter(
                    x=x_fit,
                    y=y_fit,
                    mode='lines',
                    name=f'{protein} 拟合曲线',
                    line=dict(dash='dash')
                ))
    
    # 更新图表布局
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title='浓度 (μM)',
        yaxis_title='亲和力 (μM⁻¹)',
        title='FCS测得亲和力与浓度关系曲线',
        showlegend=True
    )
    
    return fig

# 生成亲和力排序图表
def generate_affinity_ranking():
    affinity_data = st.session_state.app_state["affinity_data"]
    if not affinity_data:
        return None, None
    
    # 按蛋白分组计算平均亲和力
    protein_avg = {}
    for item in affinity_data:
        if item["protein"] not in protein_avg:
            protein_avg[item["protein"]] = []
        protein_avg[item["protein"]].append(item["affinity"])
    
    # 计算平均值
    protein_stats = []
    for protein, values in protein_avg.items():
        protein_stats.append({
            "protein": protein,
            "avg_affinity": np.mean(values),
            "std_affinity": np.std(values),
            "count": len(values)
        })
    
    # 排序
    protein_stats.sort(key=lambda x: x["avg_affinity"], reverse=True)
    
    # 创建排序图表
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[item["protein"] for item in protein_stats],
        y=[item["avg_affinity"] for item in protein_stats],
        error_y=dict(
            type='data',
            array=[item["std_affinity"] for item in protein_stats],
            visible=True
        ),
        marker_color=np.linspace(0, 1, len(protein_stats))  # 颜色渐变
    ))
    
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title='蛋白名称',
        yaxis_title='平均亲和力 (μM⁻¹)',
        title='不同蛋白亲和力排序',
        showlegend=False
    )
    
    return fig, protein_stats

# -------------------------- 页面布局开始 --------------------------
check_pump_status()
# 页面标题和紧急控制区
st.title("🧪 微流控测试平台控制软件")
st.caption(f"最后更新: {st.session_state.app_state['last_update']}")
if st.session_state.message_display['show']:
    elapsed = time.time() - st.session_state.message_display['timestamp']
    if elapsed < 5:  # 消息显示5秒
        if st.session_state.message_display['type'] == 'warning':
            st.warning(st.session_state.message_display['content'])
        else:
            st.success(st.session_state.message_display['content'])
    else:
        st.session_state.message_display['show'] = False
# 顶部状态栏（紧急控制 + 系统状态）
top_row = st.columns([1, 3])
with top_row[0]:
    st.button("⚠️ 紧急停止", on_click=emergency_stop, type="primary", use_container_width=True)
    if st.session_state.app_state["emergency_status"]:
        st.button("✅ 已排查完毕，重新实验", on_click=reset_after_emergency, type="secondary", use_container_width=True)
with top_row[1]:
    status_cols = st.columns(3)
    with status_cols[0]:
        st.info("""
        **液体传输系统**  
        泵 × 3  
        🟢 正常运行
        """, icon="💧")
    with status_cols[1]:
        st.info("""
        **数据分析系统**  
        FCS数据处理  
        🟢 正常运行
        """, icon="📊")
    with status_cols[2]:
        st.info("""
        **当前任务**  
        实验ID: EXP-20230515-002  
        🔄 进行中
        """, icon="🔬")

st.divider()

# 主要工作区（左侧：实验控制 | 右侧：数据分析）
workspace = st.columns([5, 6])  # 微调比例，数据分析区域略宽以更好展示图表

# -------------------------- 左侧：实验控制区 --------------------------
with workspace[0]:
    st.subheader("🔧 实验控制中心")
    
    # 1. 泵控制（核心操作，放在最上方）
    with st.container(border=True):
        st.markdown("### 💧 泵控制")
        for pump_id in [1, 2, 3]:
            pump = st.session_state.app_state["pumps"][pump_id]
            with st.expander(f"泵{pump_id} ({pump['name']})", expanded=True):
                col_flow, col_time = st.columns(2)
                with col_flow:
                    flow = st.number_input(
                        "流量 (μL/min)", 
                        min_value=0, 
                        max_value=1000, 
                        value=pump["flow"],
                        key=f"flow_{pump_id}"
                    )
                    st.session_state.app_state["pumps"][pump_id]["flow"] = flow
                
                with col_time:
                    time_val = st.number_input(
                        "时间 (s)", 
                        min_value=1, 
                        max_value=3600, 
                        value=pump["time"],
                        key=f"time_{pump_id}"
                    )
                    st.session_state.app_state["pumps"][pump_id]["time"] = time_val
                
                run_col1, run_col2 = st.columns(2)
                with run_col1:
                    st.button(
                        "启动", 
                        on_click=start_pump, 
                        args=(pump_id,),
                        disabled=pump["running"] or st.session_state.app_state["emergency_status"],  # 添加紧急停止状态检查
                        key=f"start_{pump_id}",
                        type="primary",
                        use_container_width=True
                    )
                
                with run_col2:
                    st.button(
                        "停止", 
                        on_click=stop_pump, 
                        args=(pump_id,),
                        disabled=not pump["running"],
                        key=f"stop_{pump_id}",
                        use_container_width=True
                    )
                
                status = "运行中 ⚠️" if pump["running"] else "就绪 ✅"
                st.caption(f"状态: {status}")
    
    # 2. 实验流程（次重要，放在泵控制下方）
    with st.container(border=True):
        st.markdown("### 📋 实验流程设计")
        with st.expander("当前流程: 蛋白反应检测", expanded=True):
            st.markdown("包含 5 个步骤 | 预计时长: 15分钟")
            
            # 流程步骤
            for step in range(1, 6):
                bg_color = "#e6f7ff" if step <= 2 else "#f5f5f5"
                step_num_color = "#1890ff" if step <= 2 else "#8c8c8c"
                
                st.markdown(f"""
                <div style="background-color: {bg_color}; padding: 10px; border-radius: 5px; margin: 5px 0;">
                    <div style="display: flex; align-items: center;">
                        <div style="background-color: {step_num_color}; color: white; width: 20px; height: 20px; border-radius: 50%; 
                                    display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                            {step}
                        </div>
                        <div style="flex-grow: 1;">
                            {
                                ["注入蛋白液", "注入缓冲液A", "混合反应", "数据采集", "结果分析"][step-1]
                            }
                            <div style="font-size: 12px; color: #666;">
                                {
                                    ["泵1 | 50μL/min | 10秒", "泵2 | 30μL/min | 15秒", 
                                     "静置 | 5分钟", "FCS检测", "亲和力分析"][step-1]
                                }
                            </div>
                        </div>
                        <div>
                            <button style="background: none; border: none; color: #1890ff; cursor: pointer;">✏️</button>
                            <button style="background: none; border: none; color: #ff4d4d; cursor: pointer;">🗑️</button>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                st.button("➕ 添加步骤", key="add_step", use_container_width=True)
            with col_btn2:
                st.button("▶️ 运行流程", on_click=run_experiment, key="run_process", 
                         type="primary", use_container_width=True)
    
    # 3. 实时监测（辅助功能，放在最下方）
    with st.container(border=True):
        st.markdown("### 🔍 实时监测")
        progress_cols = st.columns([1, 2])
        with progress_cols[0]:
            st.markdown("#### 反应进度")
            progress = st.session_state.app_state["experiment"]["progress"]
            st.progress(progress)
            st.markdown(f"步骤 {st.session_state.app_state['experiment']['current_step']}/5")
            st.markdown(f"剩余时间: {st.session_state.app_state['experiment']['remaining_time']}")
        
        with progress_cols[1]:
            st.markdown("#### 实时数据")
            st.plotly_chart(generate_realtime_chart(), use_container_width=True)

# -------------------------- 右侧：数据分析区 --------------------------
with workspace[1]:
    st.subheader("📈 FCS亲和力数据分析")
    
    # 1. 数据上传（数据分析入口，放在最上方）
    with st.container(border=True):
        st.markdown("### 📂 数据上传")
        uploaded_file = st.file_uploader("上传FCS仪器测得的CSV数据文件", type=["csv"], 
                                        label_visibility="collapsed")
        
        # 数据格式说明（使用折叠面板节省空间）
        with st.expander("📋 数据格式要求", expanded=False):
            st.markdown("""
            CSV文件需包含以下列：
            - protein: 蛋白名称（字符串）
            - concentration: 浓度值（数值，单位μM）
            - affinity: 亲和力值（数值，单位μM⁻¹）
            
            示例数据：
            ```
            protein,concentration,affinity
            蛋白A,0.1,2.3
            蛋白A,0.2,3.8
            蛋白B,0.1,1.9
            蛋白B,0.3,4.2
            ```
            """)
        
        # 处理上传文件
        if uploaded_file is not None and uploaded_file.name not in st.session_state.app_state["uploaded_files"]:
            data, message = parse_fcs_data(uploaded_file)
            
            if data:
                # 保存数据
                st.session_state.app_state["affinity_data"].extend(data)
                st.session_state.app_state["uploaded_files"].append(uploaded_file.name)
                add_system_log(f"已上传FCS数据文件: {uploaded_file.name}，包含{len(data)}条记录")
                update_last_update()
                st.success(f"文件上传成功！{message}，新增{len(data)}条数据")
            else:
                st.error(f"文件上传失败: {message}")
        
        # 数据管理按钮
        col_data1, col_data2 = st.columns(2)
        with col_data1:
            if st.button("👀 查看当前数据", type="secondary", use_container_width=True):
                if st.session_state.app_state["affinity_data"]:
                    df = pd.DataFrame(st.session_state.app_state["affinity_data"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("暂无数据")
        
        with col_data2:
            if st.button("🗑️ 清除所有数据", type="secondary", use_container_width=True):
                st.session_state.app_state["affinity_data"] = []
                st.session_state.app_state["uploaded_files"] = []
                add_system_log("已清除所有亲和力数据")
                st.success("所有数据已清除")
    
    # 2. 亲和力曲线（核心分析结果，放在中间）
    with st.container(border=True):
        st.markdown("### 📉 亲和力曲线")
        affin_fig = generate_affinity_chart()
        if affin_fig:
            st.plotly_chart(affin_fig, use_container_width=True)
            
            # 图表注释
            st.markdown("""
            **图表注释**:  
            - 不同颜色代表不同蛋白的亲和力数据  
            - 实线点表示实际测量值  
            - 虚线表示基于结合模型的拟合曲线  
            - 亲和力值越高，表示蛋白结合能力越强
            """)
        else:
            st.info("尚未上传亲和力数据，请先上传FCS数据文件")
    
    # 3. 亲和力排序（分析结论，放在最下方）
    with st.container(border=True):
        st.markdown("### 🏆 蛋白亲和力排序")
        ranking_fig, protein_stats = generate_affinity_ranking()
        if ranking_fig and protein_stats:
            st.plotly_chart(ranking_fig, use_container_width=True)
            
            # 显示详细统计数据
            st.markdown("#### 详细统计结果")
            sorted_proteins = sorted(protein_stats, key=lambda x: x["avg_affinity"], reverse=True)
            for i, item in enumerate(sorted_proteins, 1):
                st.markdown(f"{i}. **{item['protein']}**: 平均亲和力 = {item['avg_affinity']:.3f} ± {item['std_affinity']:.3f} (n={item['count']})")
            
            # 显示最高亲和力蛋白
            top_protein = sorted_proteins[0]
            st.success(f"最高亲和力蛋白: {top_protein['protein']} (平均值: {top_protein['avg_affinity']:.3f})")
        else:
            st.info("暂无足够数据进行排序分析")

# 底部系统日志（全宽显示，方便查看完整记录）
st.divider()
with st.container(border=True):
    st.subheader("📝 系统日志")
    log_text = "\n".join(reversed(st.session_state.app_state["system_log"]))
    # 移除不支持的use_container_width参数
    st.text_area("系统操作记录", log_text, height=150, disabled=True)

# -------------------------- 页面布局结束 --------------------------

# 添加自动刷新，间隔1000毫秒（2秒）
streamlit_autorefresh.st_autorefresh(interval=2000, key="auto_refresh")