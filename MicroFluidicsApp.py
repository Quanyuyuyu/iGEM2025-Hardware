import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import numpy as np

# 页面配置
st.set_page_config(
    page_title="微流控测试平台控制软件",
    page_icon="🧪",
    layout="wide"
)

# 初始化状态
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        "pumps": {
            1: { "running": False, "flow": 50, "time": 10, "name": "蛋白液" },
            2: { "running": False, "flow": 30, "time": 15, "name": "缓冲液A" },
            3: { "running": False, "flow": 40, "time": 20, "name": "缓冲液B" }
        },
        "valves": {
            1: { "state": "open", "description": "通向芯片入口A" },
            2: { "state": "close", "description": "通向芯片入口B" },
            3: { "state": "close", "description": "通向废液槽" },
            4: { "state": "open", "description": "检测通道" },
            5: { "state": "close", "description": "清洗通道" },
            6: { "state": "close", "description": "缓冲液B通道" }
        },
        "experiment": {
            "current_step": 2,
            "total_steps": 5,
            "progress": 35,
            "remaining_time": "9分钟"
        },
        "spectra_params": {
            "start": 400,
            "end": 700,
            "mode": "absorbance",
            "interval": 5
        },
        "camera_params": {
            "exposure": 50,
            "magnification": "20x",
            "image_captured": False,
            "image_url": ""
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
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# 辅助函数：添加系统日志
def add_system_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.app_state["system_log"].append(f"[{timestamp}] {message}")
    # 限制日志长度
    if len(st.session_state.app_state["system_log"]) > 50:
        st.session_state.app_state["system_log"].pop(0)

# 辅助函数：更新最后更新时间
def update_last_update():
    st.session_state.app_state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 回调函数：启动泵
def start_pump(pump_id):
    pump = st.session_state.app_state["pumps"][pump_id]
    pump["running"] = True
    add_system_log(f"泵{pump_id}启动: {pump['flow']}μL/min, {pump['time']}秒")
    update_last_update()
    
    # 模拟泵自动停止
    with st.spinner(f"泵{pump_id}运行中..."):
        time.sleep(pump["time"] / 10)  # 加速模拟，实际应使用pump["time"]秒
    pump["running"] = False
    add_system_log(f"泵{pump_id}已停止")
    update_last_update()

# 回调函数：停止泵
def stop_pump(pump_id):
    st.session_state.app_state["pumps"][pump_id]["running"] = False
    add_system_log(f"泵{pump_id}已手动停止")
    update_last_update()

# 回调函数：切换阀门状态
def toggle_valve(valve_id):
    valve = st.session_state.app_state["valves"][valve_id]
    new_state = "open" if valve["state"] == "close" else "close"
    valve["state"] = new_state
    add_system_log(f"阀门{valve_id}已{new_state}")
    update_last_update()

# 回调函数：开始光谱检测
def start_spectra_detection():
    params = st.session_state.app_state["spectra_params"]
    add_system_log(f"开始光谱检测: {params['start']}-{params['end']}nm, {params['mode']}模式")
    update_last_update()
    
    with st.spinner("正在进行光谱检测..."):
        time.sleep(2)  # 模拟检测时间
    add_system_log("光谱检测完成")
    update_last_update()
    st.success("光谱检测已完成")

# 回调函数：捕获图像
def capture_image():
    params = st.session_state.app_state["camera_params"]
    add_system_log(f"开始成像检测: {params['magnification']}, {params['exposure']}ms曝光")
    update_last_update()
    
    with st.spinner("正在捕获图像..."):
        time.sleep(1.5)  # 模拟捕获时间
        # 生成随机图像
        st.session_state.app_state["camera_params"]["image_url"] = f"https://picsum.photos/seed/{np.random.randint(1000)}/600/400"
        st.session_state.app_state["camera_params"]["image_captured"] = True
    
    add_system_log("成像检测完成，已捕获反应区域图像")
    update_last_update()
    st.success("图像捕获成功")

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
    # 停止所有泵
    for pump_id in st.session_state.app_state["pumps"]:
        if st.session_state.app_state["pumps"][pump_id]["running"]:
            st.session_state.app_state["pumps"][pump_id]["running"] = False
    
    add_system_log("系统紧急停止已执行")
    update_last_update()
    st.warning("紧急停止已执行，所有设备已停止运行")

# 生成实时数据图表
def generate_realtime_chart():
    x = list(range(20))
    # 生成有趋势的随机数据
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

# 生成光谱结果图表
def generate_spectra_chart():
    wavelengths = np.arange(400, 710, 10)
    # 生成模拟光谱数据
    peak = 527
    data = 0.5 * np.exp(-0.5 * ((wavelengths - peak) / 100) ** 2) + 0.1
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=wavelengths, y=data, mode='lines', name='吸光度',
                            line=dict(color='#36CFC9'),
                            fill='tozeroy', fillcolor='rgba(54, 207, 201, 0.1)'))
    
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title='波长 (nm)',
        yaxis_title='吸光度',
        showlegend=False
    )
    return fig

# 页面标题
st.title("🧪 微流控测试平台控制软件")

# 顶部状态栏
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"**系统状态**: 正常运行中")
with col2:
    st.button("⚠️ 紧急停止", on_click=emergency_stop, type="primary")

st.markdown(f"最后更新: {st.session_state.app_state['last_update']}")
st.divider()

# 系统状态概览
st.subheader("系统状态")
status_cols = st.columns(3)

with status_cols[0]:
    st.info("""
    **液体传输系统**  
    泵 × 3 | 阀门 × 8  
    🟢 正常运行
    """)

with status_cols[1]:
    st.info("""
    **检测系统**  
    光谱仪 × 1 | 成像模块 × 1  
    🟢 正常运行
    """)

with status_cols[2]:
    st.info("""
    **当前任务**  
    实验ID: EXP-20230515-002  
    🔄 进行中
    """)

st.divider()

# 主要内容区 - 两列布局
main_col1, main_col2 = st.columns([2, 1])

with main_col1:
    # 液体传输控制
    st.subheader("液体传输控制")
    pump_col, valve_col = st.columns(2)
    
    # 泵控制
    with pump_col:
        st.markdown("### 💧 泵控制")
        for pump_id in [1, 2, 3]:
            pump = st.session_state.app_state["pumps"][pump_id]
            with st.expander(f"泵{pump_id} ({pump['name']})", expanded=True):
                # 使用HTML布局替代嵌套列，避免Streamlit嵌套限制
                st.markdown("<div style='display: flex; gap: 15px; margin-bottom: 10px;'>", unsafe_allow_html=True)
                
                # 左侧 - 流量输入
                st.markdown("<div style='flex: 1;'>", unsafe_allow_html=True)
                flow = st.number_input(
                    "流量 (μL/min)", 
                    min_value=0, 
                    max_value=1000, 
                    value=pump["flow"],
                    key=f"flow_{pump_id}"
                )
                st.session_state.app_state["pumps"][pump_id]["flow"] = flow
                st.markdown("</div>", unsafe_allow_html=True)
                
                # 右侧 - 时间输入
                st.markdown("<div style='flex: 1;'>", unsafe_allow_html=True)
                time_val = st.number_input(
                    "时间 (s)", 
                    min_value=1, 
                    max_value=3600, 
                    value=pump["time"],
                    key=f"time_{pump_id}"
                )
                st.session_state.app_state["pumps"][pump_id]["time"] = time_val
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
                # 按钮布局
                st.markdown("<div style='display: flex; gap: 15px;'>", unsafe_allow_html=True)
                st.markdown("<div style='flex: 1;'>", unsafe_allow_html=True)
                if st.button(
                    "启动", 
                    on_click=start_pump, 
                    args=(pump_id,),
                    disabled=pump["running"],
                    key=f"start_{pump_id}",
                    type="primary"
                ):
                    pass
                st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<div style='flex: 1;'>", unsafe_allow_html=True)
                if st.button(
                    "停止", 
                    on_click=stop_pump, 
                    args=(pump_id,),
                    disabled=not pump["running"],
                    key=f"stop_{pump_id}"
                ):
                    pass
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                
                status = "运行中 ⚠️" if pump["running"] else "就绪 ✅"
                st.caption(f"状态: {status}")
    
    # 阀门控制 - 使用HTML布局替代嵌套列
    with valve_col:
        st.markdown("### 🔄 阀门控制")
        
        # 使用HTML flexbox布局实现阀门网格，避免嵌套列
        st.markdown("<div style='display: flex; flex-wrap: wrap; gap: 15px;'>", unsafe_allow_html=True)
        
        # 为所有6个阀门创建统一的布局
        for valve_id in range(1, 7):
            valve = st.session_state.app_state["valves"][valve_id]
            # 每个阀门占用大约50%宽度，留出间隙
            st.markdown("<div style='flex: 1 1 calc(50% - 10px); min-width: 200px;'>", unsafe_allow_html=True)
            
            st.markdown(f"**阀门{valve_id}**")
            state = valve["state"]
            is_open = state == "open"
            
            if st.button(
                "开" if not is_open else "已开 ✅", 
                on_click=toggle_valve, 
                args=(valve_id,),
                disabled=is_open,
                key=f"open_{valve_id}"
            ):
                pass
            
            if st.button(
                "关" if is_open else "已关 ❌", 
                on_click=toggle_valve, 
                args=(valve_id,),
                disabled=not is_open,
                key=f"close_{valve_id}"
            ):
                pass
            
            st.caption(valve["description"])
            st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 继续处理其他代码
        st.button("预设通路模式", key="preset_valves")
        
        # 检测控制
        st.subheader("检测控制")
        # 使用HTML布局替代嵌套列
        st.markdown("<div style='display: flex; flex-wrap: wrap; gap: 15px;'>", unsafe_allow_html=True)
        
        # 光谱检测部分
        st.markdown("<div style='flex: 1 1 100%; min-width: 300px;'>", unsafe_allow_html=True)
        st.markdown("### 📈 光谱检测")
        with st.expander("光谱参数设置", expanded=True):
            # 使用HTML布局替代嵌套列
            st.markdown("<div style='display: flex; gap: 15px; margin-bottom: 10px;'>", unsafe_allow_html=True)
            
            # 左侧 - 起始波长
            st.markdown("<div style='flex: 1;'>", unsafe_allow_html=True)
            start = st.number_input(
                "起始波长 (nm)", 
                min_value=300, 
                max_value=1000, 
                value=st.session_state.app_state["spectra_params"]["start"],
                key="spectra_start"
            )
            st.session_state.app_state["spectra_params"]["start"] = start
            st.markdown("</div>", unsafe_allow_html=True)
            
            # 右侧 - 结束波长
            st.markdown("<div style='flex: 1;'>", unsafe_allow_html=True)
            end = st.number_input(
                "结束波长 (nm)", 
                min_value=300, 
                max_value=1000, 
                value=st.session_state.app_state["spectra_params"]["end"],
                key="spectra_end"
            )
            st.session_state.app_state["spectra_params"]["end"] = end
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            mode = st.selectbox(
                "检测模式",
                ["absorbance", "fluorescence", "transmittance"],
                index=0,
                key="spectra_mode"
            )
            st.session_state.app_state["spectra_params"]["mode"] = mode
            
            interval = st.number_input(
                "检测间隔 (s)",
                min_value=1,
                max_value=300,
                value=st.session_state.app_state["spectra_params"]["interval"],
                key="spectra_interval"
            )
            st.session_state.app_state["spectra_params"]["interval"] = interval
            
            st.button(
                "开始光谱检测",
                on_click=start_spectra_detection,
                key="start_spectra",
                type="primary"
            )
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 成像检测部分
        st.markdown("<div style='flex: 1 1 100%; min-width: 300px;'>", unsafe_allow_html=True)
        st.markdown("### 📷 成像检测")
        with st.expander("成像参数设置", expanded=True):
            # 使用HTML布局替代嵌套列
            st.markdown("<div style='display: flex; gap: 15px; margin-bottom: 10px;'>", unsafe_allow_html=True)
            
            # 左侧 - 曝光时间
            st.markdown("<div style='flex: 1;'>", unsafe_allow_html=True)
            exposure = st.number_input(
                "曝光时间 (ms)",
                min_value=1,
                max_value=1000,
                value=st.session_state.app_state["camera_params"]["exposure"],
                key="camera_exposure"
            )
            st.session_state.app_state["camera_params"]["exposure"] = exposure
            st.markdown("</div>", unsafe_allow_html=True)
            
            # 右侧 - 放大倍数
            st.markdown("<div style='flex: 1;'>", unsafe_allow_html=True)
            magnification = st.selectbox(
                "放大倍数",
                ["10x", "20x", "40x"],
                index=1,
                key="camera_magnification"
            )
            st.session_state.app_state["camera_params"]["magnification"] = magnification
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # 图像预览区域
            st.markdown("**图像预览**")
            preview_placeholder = st.empty()
            if st.session_state.app_state["camera_params"]["image_captured"]:
                preview_placeholder.image(
                    st.session_state.app_state["camera_params"]["image_url"],
                    caption="捕获的图像",
                    use_column_width=True
                )
            else:
                preview_placeholder.info("实时图像预览区域")
            
            st.button(
                "捕获图像",
                on_click=capture_image,
                key="capture_image",
                type="primary"
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.divider()
        
        # 实验流程设计
        st.subheader("实验流程设计")
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
                            {[
                                "注入蛋白液", "注入缓冲液A", "混合反应", "光谱检测", "成像检测"][step-1]}
                            <div style="font-size: 12px; color: #666;">
                                {[
                                    "泵1 | 50μL/min | 10秒", "泵2 | 30μL/min | 15秒", 
                                    "静置 | 5分钟", "400-700nm | 吸光度", "20x | 50ms曝光"][step-1]}
                            </div>
                        </div>
                        <div>
                            <button style="background: none; border: none; color: #1890ff; cursor: pointer;">✏️</button>
                            <button style="background: none; border: none; color: #ff4d4d; cursor: pointer;">🗑️</button>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # 使用HTML布局替代嵌套列
            st.markdown("<div style='display: flex; gap: 15px;'>", unsafe_allow_html=True)
            st.markdown("<div style='flex: 1;'>", unsafe_allow_html=True)
            st.button("➕ 添加步骤", key="add_step")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div style='flex: 1;'>", unsafe_allow_html=True)
            st.button("▶️ 运行流程", on_click=run_experiment, key="run_process", type="primary")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    
with main_col2:
    # 实时监测
    st.subheader("实时监测")
    with st.expander("反应进度", expanded=True):
        progress = st.session_state.app_state["experiment"]["progress"]
        st.progress(progress)
        st.markdown(f"步骤 {st.session_state.app_state['experiment']['current_step']}/5 | 预计剩余: {st.session_state.app_state['experiment']['remaining_time']}")
    
    with st.expander("实时数据", expanded=True):
        st.plotly_chart(generate_realtime_chart(), use_container_width=True)
    
    with st.expander("系统日志", expanded=True):
        log_text = "\n".join(st.session_state.app_state["system_log"][-10:])  # 显示最后10条日志
        st.text_area("系统日志", log_text, height=200, disabled=True)
    
    st.divider()
    
    # 检测结果
    st.subheader("检测结果")
    with st.expander("最新光谱数据", expanded=True):
        st.plotly_chart(generate_spectra_chart(), use_container_width=True)
        st.button("查看历史", key="view_history")
    
    with st.expander("分析结果", expanded=True):
        st.markdown("""
        | 指标 | 结果 |
        |------|------|
        | 反应程度 | 35% |
        | 峰值波长 | 527 nm |
        | 浓度估算 | 0.32 mg/mL |
        
        **结果判定**: 反应正常进行中，建议继续监测。预计还需10分钟达到稳定状态。
        """)
        st.button("生成详细报告", key="generate_report")
# -------------------- KD值计算功能 (新增内容) --------------------
st.divider()
st.subheader("KD值计算工具")

with st.expander("Excel数据导入与KD值计算", expanded=True):
    # 文件上传组件
    kd_file = st.file_uploader("上传Excel数据文件", type=["xlsx", "xls"], key="kd_calculator_uploader")
    
    if kd_file is not None:
        try:
            # 动态导入pandas以避免影响原有功能
            import pandas as pd
            
            # 读取Excel文件第一张工作表
            df = pd.read_excel(kd_file, sheet_name=0)
            
            # 显示数据预览
            st.markdown("### 数据预览")
            st.dataframe(df.head(5))
            
            # 提取指定单元格数据 (第二行第三、四、五列)
            # 注意：pandas使用0-based索引
            row_index = 1  # 第二行
            col_indices = [2, 3, 4]  # 第三、四、五列
            
            # 检查数据是否存在
            if len(df) > row_index and len(df.columns) > max(col_indices):
                m1_plus_m1m2 = df.iloc[row_index, col_indices[0]]
                m2_plus_m1m2 = df.iloc[row_index, col_indices[1]]
                m1m2 = df.iloc[row_index, col_indices[2]]
                
                # 显示提取的数据
                st.markdown("### 提取的参数值")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("m1+m1m2", f"{m1_plus_m1m2:.4f}")
                with col2:
                    st.metric("m2+m1m2", f"{m2_plus_m1m2:.4f}")
                with col3:
                    st.metric("m1m2", f"{m1m2:.4f}")
                
                # 计算KD值
                m1 = m1_plus_m1m2 - m1m2
                m2 = m2_plus_m1m2 - m1m2
                
                if m1m2 != 0:
                    kd_value = (m1 * m2) / m1m2
                    
                    # 显示计算结果
                    st.markdown("### KD值计算结果")
                    st.latex(r"KD = \frac{m1 \times m2}{m1m2}")
                    st.success(f"KD = {kd_value:.6f}")
                    
                    # 添加到系统日志
                    add_system_log(f"KD值计算完成: {kd_value:.6f}")
                else:
                    st.error("无法计算KD值: m1m2的值不能为零")
            else:
                st.error("Excel文件格式不正确，无法找到指定单元格数据")
        except Exception as e:
            st.error(f"数据处理错误: {str(e)}")
            add_system_log(f"KD值计算失败: {str(e)}")
    else:
        st.info("请上传包含实验数据的Excel文件")
