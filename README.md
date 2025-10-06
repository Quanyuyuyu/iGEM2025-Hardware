# iGEM2025-Hardware
Microfluidic test platform control software for iGEM 2025 project

## Overview
This repository contains the control software for a microfluidic test platform, designed to automate protein reaction detection experiments. The software provides pump control, experiment progress tracking, data analysis, and system logging functionalities.

## Features
- Real-time pump control (flow rate and duration settings)
- Experiment procedure automation with progress tracking
- FCS data parsing and affinity curve fitting
- System logging and status monitoring
- Emergency stop functionality

## Installation & Setup
1. **Clone this repository**:
    ```bash
    git clone https://github.com/your-username/iGEM2025-Hardware.git
    cd iGEM2025-Hardware
2. Create and activate a virtual environment (recommended):
    ```bash
    python -m venv Streamlit
    
    # Windows (Command Prompt)
    Streamlit\Scripts\activate
    # Windows (PowerShell)
    .\Streamlit\Scripts\Activate.ps1
    # macOS/Linux
    source Streamlit/bin/activate
3. **Install dependencies**
    ```bash
    pip install -r requirements.txt
4. **Run the Streamlit application**
    ```bash
    streamlit run .\MicroFluidicsApp.py