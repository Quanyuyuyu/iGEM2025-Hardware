import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from datetime import datetime
import time
import io
import streamlit_autorefresh

st.set_page_config(
    page_title="Microfluidic Test Platform Control Software",
    page_icon="🧪",
    layout="wide"
)

if 'message_display' not in st.session_state:
    st.session_state.message_display = {
        'show': False,
        'type': '',  # 'warning' or 'success'
        'content': '',
        'timestamp': 0
    }

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

def add_system_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.app_state["system_log"].append(f"[{timestamp}] {message}")
    if len(st.session_state.app_state["system_log"]) > 50:
        st.session_state.app_state["system_log"].pop(0)

def update_last_update():
    st.session_state.app_state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def parse_fcs_data(uploaded_file):
    """Parse CSV data file exported by FCS instrument"""
    try:
        df = pd.read_csv(uploaded_file)
        
        required_columns = ['protein', 'concentration', 'affinity']
        if not all(col in df.columns for col in required_columns):
            return None, f"CSV file missing necessary columns. Must include: {', '.join(required_columns)}"
        
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

def start_pump(pump_id):
    pump = st.session_state.app_state["pumps"][pump_id]
    pump["running"] = True
    add_system_log(f"Pump {pump_id} started: {pump['flow']}μL/min, {pump['time']} seconds")
    update_last_update()
    
    st.session_state.app_state[f"pump_{pump_id}_start_time"] = time.time()
    st.session_state.app_state[f"pump_{pump_id}_duration"] = pump["time"]/5
    
    st.info(f"Pump {pump_id} running...")

def check_pump_status():
    for pump_id in st.session_state.app_state["pumps"]:
        if (st.session_state.app_state["pumps"][pump_id]["running"] and 
            f"pump_{pump_id}_start_time" in st.session_state.app_state):
            elapsed = time.time() - st.session_state.app_state[f"pump_{pump_id}_start_time"]
            if elapsed >= st.session_state.app_state[f"pump_{pump_id}_duration"]:
                st.session_state.app_state["pumps"][pump_id]["running"] = False
                add_system_log(f"Pump {pump_id} stopped")
                if pump_id in [1, 2]:
                    st.session_state.app_state["pumps"][pump_id]["completed"] = True

                    completed_pumps = 0
                    for p in [1, 2]:
                        if st.session_state.app_state["pumps"][p]["completed"]:
                            completed_pumps += 1
                    
                    if completed_pumps > st.session_state.app_state["experiment"]["current_step"]:
                        st.session_state.app_state["experiment"]["current_step"] = completed_pumps
                        st.session_state.app_state["experiment"]["steps_completed"][completed_pumps] = True
                        st.session_state.app_state["experiment"]["progress"] = 20 * completed_pumps
                
                update_last_update()
                
                del st.session_state.app_state[f"pump_{pump_id}_start_time"]
                del st.session_state.app_state[f"pump_{pump_id}_duration"]

def stop_pump(pump_id):
    st.session_state.app_state["pumps"][pump_id]["running"] = False
    add_system_log(f"Pump {pump_id} manually stopped")
    update_last_update()

def run_experiment():
    add_system_log("Starting experiment procedure: Protein reaction detection")
    update_last_update()
    st.session_state.app_state["experiment"]["current_step"] = 3
    st.session_state.app_state["experiment"]["progress"] = 40
    st.session_state.app_state["experiment"]["experiment_start_time"] = time.time()
    st.session_state.app_state["experiment"]["current_step_start_time"] = time.time()
    st.session_state.app_state["experiment"]["running"] = True

def check_experiment_progress():
    if not st.session_state.app_state["experiment"].get("running", False):
        return
    
    current_step = st.session_state.app_state["experiment"]["current_step"]
    step_start_time = st.session_state.app_state["experiment"]["current_step_start_time"]
    
    step_durations = {
        3: 10,
        4: 10,
        5: 1
    }
    
    if current_step in step_durations and time.time() - step_start_time >= step_durations[current_step]:
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
        
        if current_step < 5:
            current_step += 1
            st.session_state.app_state["experiment"]["current_step"] = current_step
            st.session_state.app_state["experiment"]["current_step_start_time"] = time.time()
            
            if current_step == 4:
                add_system_log("Step 4 started: FCS data collection, waiting 5 minutes")
            elif current_step == 5:
                add_system_log("Step 5 started: Affinity data analysis")
    else:
        if current_step in step_durations:
            remaining = int(step_durations[current_step] - (time.time() - step_start_time))
            st.session_state.app_state["experiment"]["remaining_time"] = f"{remaining//60}min{remaining%60}s"

def emergency_stop():
    for pump_id in st.session_state.app_state["pumps"]:
        if st.session_state.app_state["pumps"][pump_id]["running"]:
            st.session_state.app_state["pumps"][pump_id]["running"] = False
    st.session_state.app_state["emergency_status"] = True
    add_system_log("System emergency stop executed")
    update_last_update()
    st.session_state.message_display = {
        'show': True,
        'type': 'warning',
        'content': "Emergency stop executed, all devices stopped",
        'timestamp': time.time()
    }

def reset_after_emergency():
    st.session_state.app_state["emergency_status"] = False
    st.session_state.app_state["experiment"] = {
        "current_step": 0,
        "total_steps": 5,
        "progress": 0,
        "remaining_time": "--minutes",
        "steps_completed": {1: False, 2: False, 3: False, 4: False, 5: False}
    }
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

def generate_affinity_chart():
    affinity_data = st.session_state.app_state["affinity_data"]
    if not affinity_data:
        return None
    
    proteins = list(set(item["protein"] for item in affinity_data))
    
    fig = go.Figure()
    
    for protein in proteins:
        protein_data = [item for item in affinity_data if item["protein"] == protein]
        concentrations = [item["concentration"] for item in protein_data]
        affinities = [item["affinity"] for item in protein_data]
        
        fig.add_trace(go.Scatter(
            x=concentrations,
            y=affinities,
            mode='markers',
            name=protein,
            marker=dict(size=8)
        ))
        
        if len(concentrations) >= 3:
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
    
    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title='Concentration (μM)',
        yaxis_title='Affinity (μM⁻¹)',
        title='FCS Measured Affinity vs Concentration Curve',
        showlegend=True
    )
    
    return fig

def generate_affinity_ranking():
    affinity_data = st.session_state.app_state["affinity_data"]
    if not affinity_data:
        return None, None
    
    protein_avg = {}
    for item in affinity_data:
        if item["protein"] not in protein_avg:
            protein_avg[item["protein"]] = []
        protein_avg[item["protein"]].append(item["affinity"])
    
    protein_stats = []
    for protein, values in protein_avg.items():
        protein_stats.append({
            "protein": protein,
            "avg_affinity": np.mean(values),
            "std_affinity": np.std(values),
            "count": len(values)
        })
    
    protein_stats.sort(key=lambda x: x["avg_affinity"], reverse=True)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[item["protein"] for item in protein_stats],
        y=[item["avg_affinity"] for item in protein_stats],
        error_y=dict(
            type='data',
            array=[item["std_affinity"] for item in protein_stats],
            visible=True
        ),
        marker_color=np.linspace(0, 1, len(protein_stats))
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

check_experiment_progress()

check_pump_status()

st.title("🧪 Microfluidic Test Platform Control Software")
st.caption(f"Last update: {st.session_state.app_state['last_update']}")

if st.session_state.message_display['show']:
    elapsed = time.time() - st.session_state.message_display['timestamp']
    if elapsed < 5:
        if st.session_state.message_display['type'] == 'warning':
            st.warning(st.session_state.message_display['content'])
        else:
            st.success(st.session_state.message_display['content'])
    else:
        st.session_state.message_display['show'] = False

top_row = st.columns([1, 4])
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

workspace = st.columns([6, 7])

with workspace[0]:
    st.subheader("🔧 Experiment Control Center")
    
    with st.container(border=True):
        st.markdown("### 💧 Pump Control")
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
    
    with st.container(border=True):
        st.markdown("### 📋 Experiment Procedure Design")
        with st.expander("Current procedure: Protein reaction detection", expanded=True):
            st.markdown("Contains 5 steps | Estimated duration: 15 minutes")
            
            for step in range(1, 6):
                if step == 1:
                    bg_color = "#e6f7ff" if st.session_state.app_state["pumps"][1]["completed"] else "#f5f5f5"
                    step_num_color = "#1890ff" if st.session_state.app_state["pumps"][1]["completed"] else "#8c8c8c"
                elif step == 2:
                    bg_color = "#e6f7ff" if st.session_state.app_state["pumps"][2]["completed"] else "#f5f5f5"
                    step_num_color = "#1890ff" if st.session_state.app_state["pumps"][2]["completed"] else "#8c8c8c"
                else:
                    bg_color = "#e6f7ff" if st.session_state.app_state["experiment"]["steps_completed"].get(step, False) else "#f5f5f5"
                    step_num_color = "#1890ff" if st.session_state.app_state["experiment"]["steps_completed"].get(step, False) else "#8c8c8c"
                
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
                can_run = st.session_state.app_state["pumps"][1]["completed"] and st.session_state.app_state["pumps"][2]["completed"]
                st.button("▶️ Run Procedure", on_click=run_experiment, key="run_process_btn", 
                         type="primary", use_container_width=True, disabled=not can_run)
    
    with st.container(border=True):
        st.markdown("### 🔍 Real-time Monitoring")
        progress_cols = st.columns([1, 2])
        with progress_cols[0]:
            st.markdown("#### Reaction Progress")
            progress = st.session_state.app_state["experiment"]["progress"]
            st.progress(progress)
            
            current_step = st.session_state.app_state["experiment"]["current_step"]
            total_steps = st.session_state.app_state["experiment"]["total_steps"]
            st.markdown(f"Step {current_step}/{total_steps}")
            
            if current_step == 0:
                st.markdown("Ready, waiting to start")
            elif current_step in [1, 2]:
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

with workspace[1]:
    st.subheader("📈 FCS Affinity Data Analysis")
    
    with st.container(border=True):
        st.markdown("### 📂 Data Upload")
        upload_row = st.columns([3, 1])
        with upload_row[0]:
            uploaded_file = st.file_uploader("Upload CSV data file from FCS instrument", type=["csv"], 
                                            label_visibility="collapsed", key="fcs_file_uploader")
        
        with upload_row[1]:
            view_data = st.button("👀 View Current Data", type="secondary", use_container_width=True, key="view_data_btn")
            clear_data = st.button("🗑️ Clear All Data", type="secondary", use_container_width=True, key="clear_data_btn")
        
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
        
        if uploaded_file is not None and uploaded_file.name not in st.session_state.app_state["uploaded_files"]:
            data, message = parse_fcs_data(uploaded_file)
            
            if data:
                st.session_state.app_state["affinity_data"].extend(data)
                st.session_state.app_state["uploaded_files"].append(uploaded_file.name)
                add_system_log(f"Uploaded FCS data file: {uploaded_file.name}, containing {len(data)} records")
                update_last_update()
                st.success(f"File uploaded successfully! {message}, added {len(data)} new records")
            else:
                st.error(f"File upload failed: {message}")
        
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
    
    with st.container(border=True):
        st.markdown("### 📉 Affinity Curve")
        affin_fig = generate_affinity_chart()
        if affin_fig:
            st.plotly_chart(affin_fig, use_container_width=True)
            
            st.markdown("""
            **Chart Notes**:  
            - Different colors represent affinity data for different proteins  
            - Solid points indicate actual measured values  
            - Dashed lines represent fitted curves based on binding models  
            - Higher affinity values indicate stronger protein binding ability
            """)
        else:
            st.info("No affinity data uploaded yet. Please upload an FCS data file first")
    
    with st.container(border=True):
        st.markdown("### 🏆 Protein Affinity Ranking")
        ranking_fig, protein_stats = generate_affinity_ranking()
        if ranking_fig and protein_stats:
            st.plotly_chart(ranking_fig, use_container_width=True)
            
            st.markdown("#### Detailed Statistical Results")
            sorted_proteins = sorted(protein_stats, key=lambda x: x["avg_affinity"], reverse=True)
            for i, item in enumerate(sorted_proteins, 1):
                st.markdown(f"{i}. **{item['protein']}**: Average affinity = {item['avg_affinity']:.3f} ± {item['std_affinity']:.3f} (n={item['count']})")
            
            top_protein = sorted_proteins[0]
            st.success(f"Highest affinity protein: {top_protein['protein']} (Average: {top_protein['avg_affinity']:.3f})")
        else:
            st.info("Insufficient data for ranking analysis")

st.divider()
with st.container(border=True):
    st.subheader("📝 System Log")
    log_text = "\n".join(reversed(st.session_state.app_state["system_log"]))
    st.text_area("System operation records", log_text, height=150, disabled=True)

streamlit_autorefresh.st_autorefresh(interval=5000, key="auto_refresh")