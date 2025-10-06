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
    page_title="Microfluidic Test Platform Control Software",
    page_icon="🧪",
    layout="wide"  # 宽屏布局适合横屏观看
)

if 'message_display' not in st.session_state:
    st.session_state.message_display = {
        'show': False,
        'type': '',  # 'warning' or 'success'
        'content': '',
        'timestamp': 0
    }

# 初始化状态
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        "pumps": {
            1: { "running": False, "flow": 50, "time": 10, "name": "Protein A", "completed": False },
            2: { "running": False, "flow": 30, "time": 15, "name": "Protein B", "completed": False },
            3: { "running": False, "flow": 40, "time": 20, "name": "Buffer" }
        },
        "experiment": {
            "current_step": 0,
            "total_steps": 5,
            "progress": 0,
            "remaining_time": "--minutes",
            "steps_completed": {1: False, 2: False, 3: False, 4: False, 5: False}
        },
        "system_log": [
            "[14:28:15] System startup completed",
            "[14:28:30] Loaded experiment procedure: Protein reaction detection"
        ],
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "affinity_data": [],
        "uploaded_files": [] ,
        "emergency_status": False
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
    """Parse CSV data file exported by FCS instrument"""
    try:
        df = pd.read_csv(uploaded_file)
        
        # 检查是否存在必要列
        required_columns = ['protein', 'concentration', 'affinity']
        if not all(col in df.columns for col in required_columns):
            return None, f"CSV file missing necessary columns. Must include: {', '.join(required_columns)}"
        
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
        
        return data, "Parsing successful"
    except Exception as e:
        return None, f"Parsing failed: {str(e)}"

# 亲和力曲线拟合函数
def fit_affinity_curve(concentrations, affinities):
    """Fit concentration-affinity curve"""
    def binding_model(c, kd, bmax):
        """Typical binding model: Y = (Bmax * C) / (Kd + C)"""
        return (bmax * c) / (kd + c)
    
    try:
        params, _ = curve_fit(binding_model, concentrations, affinities, p0=[1, 100], maxfev=10000)
        return {
            "params": params,  # [Kd, Bmax]
            "model": binding_model
        }
    except Exception as e:
        st.warning(f"Curve fitting failed: {str(e)}")
        return None

# 回调函数：启动泵
def start_pump(pump_id):
    # 仅设置泵运行状态，不阻塞界面
    pump = st.session_state.app_state["pumps"][pump_id]
    pump["running"] = True
    add_system_log(f"Pump {pump_id} started: {pump['flow']}μL/min, {pump['time']} seconds")
    update_last_update()
    
    # 使用Streamlit的session_state记录开始时间
    st.session_state.app_state[f"pump_{pump_id}_start_time"] = time.time()
    st.session_state.app_state[f"pump_{pump_id}_duration"] = pump["time"]/5 # 加速模拟
    
    # 显示运行状态，不阻塞界面
    st.info(f"Pump {pump_id} running...")

# 在应用主循环中添加检查函数
def check_pump_status():
    for pump_id in st.session_state.app_state["pumps"]:
        if (st.session_state.app_state["pumps"][pump_id]["running"] and 
            f"pump_{pump_id}_start_time" in st.session_state.app_state):
            elapsed = time.time() - st.session_state.app_state[f"pump_{pump_id}_start_time"]
            if elapsed >= st.session_state.app_state[f"pump_{pump_id}_duration"]:
                # 泵运行时间到达，停止泵
                st.session_state.app_state["pumps"][pump_id]["running"] = False
                add_system_log(f"Pump {pump_id} stopped")
                # 对泵1和泵2设置完成标志
                if pump_id in [1, 2]:
                    st.session_state.app_state["pumps"][pump_id]["completed"] = True
                    
                    # 计算已完成的泵数量，而不是根据泵ID设置当前步骤
                    completed_pumps = 0
                    for p in [1, 2]:
                        if st.session_state.app_state["pumps"][p]["completed"]:
                            completed_pumps += 1
                    
                    # 仅当已完成的泵数量大于当前步骤时更新步骤和进度
                    if completed_pumps > st.session_state.app_state["experiment"]["current_step"]:
                        st.session_state.app_state["experiment"]["current_step"] = completed_pumps
                        st.session_state.app_state["experiment"]["steps_completed"][completed_pumps] = True
                        # 更新进度条
                        st.session_state.app_state["experiment"]["progress"] = 20 * completed_pumps
                
                update_last_update()
                
                # 清理临时状态
                del st.session_state.app_state[f"pump_{pump_id}_start_time"]
                del st.session_state.app_state[f"pump_{pump_id}_duration"]

# 回调函数：停止泵
def stop_pump(pump_id):
    st.session_state.app_state["pumps"][pump_id]["running"] = False
    add_system_log(f"Pump {pump_id} manually stopped")
    update_last_update()

# 回调函数：运行实验流程
def run_experiment():
    add_system_log("Starting experiment procedure: Protein reaction detection")
    update_last_update()
    # 设置初始状态为步骤3
    st.session_state.app_state["experiment"]["current_step"] = 3
    st.session_state.app_state["experiment"]["progress"] = 40  # 对应步骤3的进度
    st.session_state.app_state["experiment"]["experiment_start_time"] = time.time()
    st.session_state.app_state["experiment"]["current_step_start_time"] = time.time()
    st.session_state.app_state["experiment"]["running"] = True

# 检查实验进度
def check_experiment_progress():
    if not st.session_state.app_state["experiment"].get("running", False):
        return
    
    current_step = st.session_state.app_state["experiment"]["current_step"]
    step_start_time = st.session_state.app_state["experiment"]["current_step_start_time"]
    
    # 定义每个步骤的持续时间（秒）
    step_durations = {
        3: 10,  # 混合反应（原计划5分钟，缩短为10秒）
        4: 10,  # 数据采集（原计划5分钟，缩短为10秒）
        5: 1    # 结果分析
    }
    
    # 检查当前步骤是否完成
    if current_step in step_durations and time.time() - step_start_time >= step_durations[current_step]:
        # 步骤完成，记录日志
        if current_step == 3:
            add_system_log("Step 3 completed: Mixing reaction ended")
            st.session_state.app_state["experiment"]["steps_completed"][3] = True
            st.session_state.app_state["experiment"]["progress"] = 60
        elif current_step == 4:
            add_system_log("Step 4 completed: FCS data collection ended")
            st.session_state.app_state["experiment"]["steps_completed"][4] = True
            st.session_state.app_state["experiment"]["progress"] = 80
        elif current_step == 5:
            add_system_log("Step 5 completed: Affinity data analysis ended")
            st.session_state.app_state["experiment"]["steps_completed"][5] = True
            st.session_state.app_state["experiment"]["progress"] = 100
            st.session_state.app_state["experiment"]["remaining_time"] = "0 minutes"
            add_system_log("Experiment procedure completed")
            st.session_state.app_state["experiment"]["running"] = False
            st.success("Experiment procedure completed")
        
        update_last_update()
        
        # 进入下一步（如果有）
        if current_step < 5:
            current_step += 1
            st.session_state.app_state["experiment"]["current_step"] = current_step
            st.session_state.app_state["experiment"]["current_step_start_time"] = time.time()
            
            # 记录下一步开始日志
            if current_step == 4:
                add_system_log("Step 4 started: FCS data collection, waiting 5 minutes")
            elif current_step == 5:
                add_system_log("Step 5 started: Affinity data analysis")
    else:
        # 更新剩余时间
        if current_step in step_durations:
            remaining = int(step_durations[current_step] - (time.time() - step_start_time))
            st.session_state.app_state["experiment"]["remaining_time"] = f"{remaining//60}min{remaining%60}s"

# 回调函数：紧急停止
def emergency_stop():
    for pump_id in st.session_state.app_state["pumps"]:
        if st.session_state.app_state["pumps"][pump_id]["running"]:
            st.session_state.app_state["pumps"][pump_id]["running"] = False
    st.session_state.app_state["emergency_status"] = True  # 设置紧急停止状态为True
    add_system_log("System emergency stop executed")
    update_last_update()
    st.session_state.message_display = {
        'show': True,
        'type': 'warning',
        'content': "Emergency stop executed, all devices stopped",
        'timestamp': time.time()
    }

# 回调函数：紧急停止后重置系统
def reset_after_emergency():
    st.session_state.app_state["emergency_status"] = False  # 重置紧急停止状态
    # 重置实验相关状态，步骤归零
    st.session_state.app_state["experiment"] = {
        "current_step": 0,
        "total_steps": 5,
        "progress": 0,
        "remaining_time": "--minutes",
        "steps_completed": {1: False, 2: False, 3: False, 4: False, 5: False}
    }
    # 重置泵完成状态
    for pump_id in [1, 2]:
        if "completed" in st.session_state.app_state["pumps"][pump_id]:
            st.session_state.app_state["pumps"][pump_id]["completed"] = False
    
    add_system_log("Emergency situation resolved, system returned to normal state")
    update_last_update()
    st.session_state.message_display = {
        'show': True,
        'type': 'success',
        'content': "System returned to normal, experiment can be restarted",
        'timestamp': time.time()
    }

# 生成实时数据图表
def generate_realtime_chart():
    x = list(range(20))
    base = np.linspace(0.1, 0.6, 20)
    noise = np.random.normal(0, 0.02, 20)
    y = base + noise
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name='Absorbance (527nm)',
                            line=dict(color='#165DFF'),
                            fill='tozeroy', fillcolor='rgba(22, 93, 255, 0.1)'))
    
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title='Time points',
        yaxis_title='Absorbance',
        showlegend=False
    )
    return fig

# 生成亲和力曲线图表
def generate_affinity_chart():
    affinity_data = st.session_state.app_state["affinity_data"]
    if not affinity_data:
        return None
    
    # 获取唯一蛋白列表
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
        if len(concentrations) >= 3:  # 至少需要3个点才能拟合
            fit_result = fit_affinity_curve(concentrations, affinities)
            if fit_result:
                x_fit = np.linspace(min(concentrations), max(concentrations), 100)
                y_fit = fit_result["model"](x_fit, *fit_result["params"])
                fig.add_trace(go.Scatter(
                    x=x_fit,
                    y=y_fit,
                    mode='lines',
                    name=f'{protein} Fitted Curve',
                    line=dict(dash='dash')
                ))
    
    # 更新图表布局
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title='Concentration (μM)',
        yaxis_title='Affinity (μM⁻¹)',
        title='FCS Measured Affinity vs Concentration Curve',
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
        xaxis_title='Protein Name',
        yaxis_title='Average Affinity (μM⁻¹)',
        title='Affinity Ranking of Different Proteins',
        showlegend=False
    )
    
    return fig, protein_stats

# 在页面布局前添加此行
check_experiment_progress()

# -------------------------- 页面布局开始 --------------------------
check_pump_status()

# 页面标题和紧急控制区
st.title("🧪 Microfluidic Test Platform Control Software")
st.caption(f"Last update: {st.session_state.app_state['last_update']}")

if st.session_state.message_display['show']:
    elapsed = time.time() - st.session_state.message_display['timestamp']
    if elapsed < 5:  # 显示5秒消息
        if st.session_state.message_display['type'] == 'warning':
            st.warning(st.session_state.message_display['content'])
        else:
            st.success(st.session_state.message_display['content'])
    else:
        st.session_state.message_display['show'] = False

# 顶部状态栏（紧急控制 + 系统状态）
top_row = st.columns([1, 4])  # 扩大右侧状态区域
with top_row[0]:
    st.button("⚠️ Emergency Stop", on_click=emergency_stop, type="primary", use_container_width=True, key="emergency_stop_btn")
    if st.session_state.app_state["emergency_status"]:
        st.button("✅ Issue Resolved, Restart Experiment", on_click=reset_after_emergency, type="secondary", use_container_width=True, key="reset_emergency_btn")

with top_row[1]:
    status_cols = st.columns(3)
    with status_cols[0]:
        st.info("""
        **Fluid Transfer System**  
        Pumps × 3  
        🟢 Operating normally
        """, icon="💧")
    with status_cols[1]:
        st.info("""
        **Data Analysis System**  
        FCS data processing  
        🟢 Operating normally
        """, icon="📊")
    with status_cols[2]:
        st.info("""
        **Current Task**  
        Experiment ID: EXP-20230515-002  
        🔄 In progress
        """, icon="🔬")

st.divider()

# 主要工作区（左侧：实验控制 | 右侧：数据分析）
workspace = st.columns([6, 7])  # 加宽整体比例，更适合横屏

# -------------------------- 左侧：实验控制区 --------------------------
with workspace[0]:
    st.subheader("🔧 Experiment Control Center")
    
    # 1. 泵控制（核心操作，放在顶部）
    with st.container(border=True):
        st.markdown("### 💧 Pump Control")
        # 泵控制横向排列，节省垂直空间
        pump_cols = st.columns(3)
        for idx, pump_id in enumerate([1, 2, 3]):
            with pump_cols[idx]:
                pump = st.session_state.app_state["pumps"][pump_id]
                st.markdown(f"**Pump {pump_id}**<br>{pump['name']}", unsafe_allow_html=True)
                
                flow = st.number_input(
                    "Flow rate (μL/min)", 
                    min_value=0, 
                    max_value=1000, 
                    value=pump["flow"],
                    key=f"flow_{pump_id}"
                )
                st.session_state.app_state["pumps"][pump_id]["flow"] = flow
                
                time_val = st.number_input(
                    "Time (s)", 
                    min_value=1, 
                    max_value=3600, 
                    value=pump["time"],
                    key=f"time_{pump_id}"
                )
                st.session_state.app_state["pumps"][pump_id]["time"] = time_val
                
                run_col1, run_col2 = st.columns(2)
                with run_col1:
                    st.button(
                        "Start", 
                        on_click=start_pump, 
                        args=(pump_id,),
                        disabled=pump["running"] or st.session_state.app_state["emergency_status"],
                        key=f"start_pump_{pump_id}",
                        type="primary",
                        use_container_width=True
                    )
                
                with run_col2:
                    st.button(
                        "Stop", 
                        on_click=stop_pump, 
                        args=(pump_id,),
                        disabled=not pump["running"],
                        key=f"stop_pump_{pump_id}",
                        use_container_width=True
                    )
                
                status = "Running ⚠️" if pump["running"] else "Ready ✅"
                st.caption(f"Status: {status}")
    
    # 2. 实验流程（次要重要，放在泵控制下方）
    with st.container(border=True):
        st.markdown("### 📋 Experiment Procedure Design")
        with st.expander("Current procedure: Protein reaction detection", expanded=True):
            st.markdown("Contains 5 steps | Estimated duration: 15 minutes")
            
            # 流程步骤
            for step in range(1, 6):
                # 根据步骤是否完成设置颜色
                if step == 1:
                    bg_color = "#e6f7ff" if st.session_state.app_state["pumps"][1]["completed"] else "#f5f5f5"
                    step_num_color = "#1890ff" if st.session_state.app_state["pumps"][1]["completed"] else "#8c8c8c"
                elif step == 2:
                    bg_color = "#e6f7ff" if st.session_state.app_state["pumps"][2]["completed"] else "#f5f5f5"
                    step_num_color = "#1890ff" if st.session_state.app_state["pumps"][2]["completed"] else "#8c8c8c"
                else:
                    # 步骤3-5根据steps_completed状态设置颜色
                    bg_color = "#e6f7ff" if st.session_state.app_state["experiment"]["steps_completed"].get(step, False) else "#f5f5f5"
                    step_num_color = "#1890ff" if st.session_state.app_state["experiment"]["steps_completed"].get(step, False) else "#8c8c8c"
                
                # 根据步骤和泵完成状态生成显示文本
                if step == 1:
                    if st.session_state.app_state["pumps"][1]["completed"]:
                        step_detail = f"Pump 1 | {st.session_state.app_state['pumps'][1]['flow']}μL/min | {st.session_state.app_state['pumps'][1]['time']}s"
                    else:
                        step_detail = "Pump 1 | --μL/min | --s"
                elif step == 2:
                    if st.session_state.app_state["pumps"][2]["completed"]:
                        step_detail = f"Pump 2 | {st.session_state.app_state['pumps'][2]['flow']}μL/min | {st.session_state.app_state['pumps'][2]['time']}s"
                    else:
                        step_detail = "Pump 2 | --μL/min | --s"
                else:
                    step_detail = ["Incubation | 5min", "FCS detection", "Affinity analysis"][step-3]             
                
                st.markdown(f"""
                <div style="background-color: {bg_color}; padding: 10px; border-radius: 5px; margin: 5px 0;">
                    <div style="display: flex; align-items: center;">
                        <div style="background-color: {step_num_color}; color: white; width: 20px; height: 20px; border-radius: 50%; 
                                    display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                            {step}
                        </div>
                        <div style="flex-grow: 1;">
                            {
                                ["Inject protein A", "Inject protein B", "Inject buffer", "Data collection", "Result analysis"][step-1]
                            }
                            <div style="font-size: 12px; color: #666;">
                                {step_detail}
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
                st.button("➕ Add Step", key="add_step_btn", use_container_width=True)
            with col_btn2:
                # 只有泵1和泵2都完成才能点击运行流程按钮
                can_run = st.session_state.app_state["pumps"][1]["completed"] and st.session_state.app_state["pumps"][2]["completed"]
                st.button("▶️ Run Procedure", on_click=run_experiment, key="run_process_btn", 
                         type="primary", use_container_width=True, disabled=not can_run)
    
    # 3. 实时监控（辅助功能，放在底部）
    with st.container(border=True):
        st.markdown("### 🔍 Real-time Monitoring")
        progress_cols = st.columns([1, 2])
        with progress_cols[0]:
            st.markdown("#### Reaction Progress")
            progress = st.session_state.app_state["experiment"]["progress"]
            st.progress(progress)
            
            # 显示当前步骤和总步骤
            current_step = st.session_state.app_state["experiment"]["current_step"]
            total_steps = st.session_state.app_state["experiment"]["total_steps"]
            st.markdown(f"Step {current_step}/{total_steps}")
            
            # 根据当前步骤显示状态信息
            if current_step == 0:
                st.markdown("Ready, waiting to start")
            elif current_step in [1, 2]:
                # 显示哪个泵正在运行或已完成
                if st.session_state.app_state["pumps"][1]["running"]:
                    st.markdown("Executing: Pump 1 injection")
                elif st.session_state.app_state["pumps"][2]["running"]:
                    st.markdown("Executing: Pump 2 injection")
                else:
                    completed_pumps = sum(1 for p in [1, 2] if st.session_state.app_state["pumps"][p]["completed"])
                    st.markdown(f"Completed: {completed_pumps} pump injections")
            
            st.markdown(f"Remaining time: {st.session_state.app_state['experiment']['remaining_time']}")
        
        with progress_cols[1]:
            st.markdown("#### Real-time Data")
            st.plotly_chart(generate_realtime_chart(), use_container_width=True)

# -------------------------- 右侧：数据分析区 --------------------------
with workspace[1]:
    st.subheader("📈 FCS Affinity Data Analysis")
    
    # 1. 数据上传（数据分析入口，放在顶部）
    with st.container(border=True):
        st.markdown("### 📂 Data Upload")
        # 数据上传区使用更宽的布局
        upload_row = st.columns([3, 1])
        with upload_row[0]:
            uploaded_file = st.file_uploader("Upload CSV data file from FCS instrument", type=["csv"], 
                                            label_visibility="collapsed", key="fcs_file_uploader")
        
        with upload_row[1]:
            # 数据管理按钮垂直排列
            view_data = st.button("👀 View Current Data", type="secondary", use_container_width=True, key="view_data_btn")
            clear_data = st.button("🗑️ Clear All Data", type="secondary", use_container_width=True, key="clear_data_btn")
        
        # 数据格式说明（使用折叠面板节省空间）
        with st.expander("📋 Data Format Requirements", expanded=False):
            st.markdown("""
            CSV file must contain the following columns:
            - protein: Protein name (string)
            - concentration: Concentration value (numeric, unit μM)
            - affinity: Affinity value (numeric, unit μM⁻¹)
            
            Example data:
            ```
            protein,concentration,affinity
            ProteinA,0.1,2.3
            ProteinA,0.2,3.8
            ProteinB,0.1,1.9
            ProteinB,0.3,4.2
            ```
            """)
        
        # Process uploaded file
        if uploaded_file is not None and uploaded_file.name not in st.session_state.app_state["uploaded_files"]:
            data, message = parse_fcs_data(uploaded_file)
            
            if data:
                # Save data
                st.session_state.app_state["affinity_data"].extend(data)
                st.session_state.app_state["uploaded_files"].append(uploaded_file.name)
                add_system_log(f"Uploaded FCS data file: {uploaded_file.name}, containing {len(data)} records")
                update_last_update()
                st.success(f"File uploaded successfully! {message}, added {len(data)} new records")
            else:
                st.error(f"File upload failed: {message}")
        
        # Data management buttons (添加了唯一key)
        col_data1, col_data2 = st.columns(2)
        with col_data1:
            if st.button("👀 View Current Data", type="secondary", use_container_width=True, key="view_current_data_btn"):
                if st.session_state.app_state["affinity_data"]:
                    df = pd.DataFrame(st.session_state.app_state["affinity_data"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No data available")
        
        with col_data2:
            if st.button("🗑️ Clear All Data", type="secondary", use_container_width=True, key="clear_all_data_btn"):
                st.session_state.app_state["affinity_data"] = []
                st.session_state.app_state["uploaded_files"] = []
                add_system_log("All affinity data cleared")
                st.success("All data has been cleared")
    
    # 2. Affinity curve (core analysis result, placed in the middle)
    with st.container(border=True):
        st.markdown("### 📉 Affinity Curve")
        affin_fig = generate_affinity_chart()
        if affin_fig:
            st.plotly_chart(affin_fig, use_container_width=True)
            
            # Chart notes
            st.markdown("""
            **Chart Notes**:  
            - Different colors represent affinity data for different proteins  
            - Solid points indicate actual measured values  
            - Dashed lines represent fitted curves based on binding models  
            - Higher affinity values indicate stronger protein binding ability
            """)
        else:
            st.info("No affinity data uploaded yet. Please upload an FCS data file first")
    
    # 3. Affinity ranking (analysis conclusion, placed at the bottom)
    with st.container(border=True):
        st.markdown("### 🏆 Protein Affinity Ranking")
        ranking_fig, protein_stats = generate_affinity_ranking()
        if ranking_fig and protein_stats:
            st.plotly_chart(ranking_fig, use_container_width=True)
            
            # Display detailed statistical data
            st.markdown("#### Detailed Statistical Results")
            sorted_proteins = sorted(protein_stats, key=lambda x: x["avg_affinity"], reverse=True)
            for i, item in enumerate(sorted_proteins, 1):
                st.markdown(f"{i}. **{item['protein']}**: Average affinity = {item['avg_affinity']:.3f} ± {item['std_affinity']:.3f} (n={item['count']})")
            
            # Display highest affinity protein
            top_protein = sorted_proteins[0]
            st.success(f"Highest affinity protein: {top_protein['protein']} (Average: {top_protein['avg_affinity']:.3f})")
        else:
            st.info("Insufficient data for ranking analysis")

# Bottom system log (full-width display for easy viewing of complete records)
st.divider()
with st.container(border=True):
    st.subheader("📝 System Log")
    log_text = "\n".join(reversed(st.session_state.app_state["system_log"]))
    # Remove unsupported use_container_width parameter
    st.text_area("System operation records", log_text, height=150, disabled=True)

# -------------------------- End of page layout --------------------------

# Add auto-refresh with 5000ms (5 seconds) interval
streamlit_autorefresh.st_autorefresh(interval=5000, key="auto_refresh")