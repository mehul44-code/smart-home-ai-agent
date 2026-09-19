# System Architecture

## Overview
The Autonomous Smart Home Energy Optimization and Comfort Management platform consists of three main tiers:
1. **Simulation & Hardware Emulation Layer**: Simulates real-time thermodynamic thermal dynamics, human occupancy schedules, solar PV generation, and appliance electrical load profiles.
2. **AI Decision Brain**: Orchestrates perception, ML inference, multi-objective optimization, action dispatch, and explanation generation.
3. **Control & Monitoring Dashboard**: A modern React + Vite frontend communicating over low-latency WebSockets and REST APIs for real-time visualization and user supervision.

```mermaid
graph TB
    subgraph Frontend ["React + Vite Dashboard"]
        UI["Live Monitoring UI"]
        Charts["Recharts (Power & Temp)"]
        Expl["7-Step Explainability Feed"]
        WS_Client["WebSocket Client"]
    end

    subgraph Backend ["FastAPI Application"]
        Router["REST API Endpoints"]
        WS_Server["WebSocket Manager"]
        Config["Pydantic Settings"]
        DB[(SQLite Database)]
    end

    subgraph AgentBrain ["Autonomous AI Agent"]
        Perception["1. Perception Engine"]
        Prediction["2. ML Predictor (Thermal/Load)"]
        Reasoning["3. Multi-Objective Reasoning"]
        Decision["4. Decision Optimizer"]
        Action["5. Action Dispatcher"]
        Feedback["6. Feedback & Calibration"]
        Explanation["7. Natural Language Explainer"]
    end

    subgraph Simulator ["Smart Home Simulator"]
        Thermal["Thermodynamic Model (RC)"]
        Tariff["TOU Tariff Engine"]
        Appliances["Virtual Appliances (AC, EV, etc.)"]
        Occupancy["Stochastic Occupancy Model"]
    end

    UI --> Router
    WS_Client <--> WS_Server
    WS_Server --> UI
    WS_Server --> Charts
    WS_Server --> Expl

    Router --> DB
    Router --> AgentBrain
    
    Simulator --> Perception
    Perception --> Prediction
    Prediction --> Reasoning
    Reasoning --> Decision
    Decision --> Action
    Action --> Appliances
    Appliances --> Thermal
    Thermal --> Feedback
    Feedback --> Explanation
    Explanation --> WS_Server
    Action --> DB
```
