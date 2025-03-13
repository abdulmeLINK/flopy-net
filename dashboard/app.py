"""
Dashboard Web Application

This module provides a Dash web application for the FL-SDN dashboard,
visualizing different FL-SDN scenarios and their metrics.
"""

import os
import time
import json
import requests
import dash
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from urllib.parse import urlparse
import networkx as nx

# Import scenario manager for direct access (optional fallback)
try:
    from .scenarios import scenario_manager
    DIRECT_ACCESS = True
except ImportError:
    DIRECT_ACCESS = False

# API config
API_HOST = os.environ.get("API_HOST", "localhost")
API_PORT = os.environ.get("API_PORT", "8051")
API_URL = f"http://{API_HOST}:{API_PORT}"

# Create Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# Set app title
app.title = "FL-SDN Dashboard"

# App configuration
app.config.suppress_callback_exceptions = True

# Helper functions
def fetch_from_api(endpoint):
    """Fetch data from the API."""
    try:
        response = requests.get(f"{API_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching from API: {e}")
        if DIRECT_ACCESS:
            # Fallback to direct access if API is unavailable
            if endpoint == "metrics/all":
                return {"metrics": scenario_manager.get_all_metrics()}
            elif endpoint == "scenarios/list":
                scenarios = []
                for scenario_id, name in scenario_manager.scenario_names.items():
                    scenarios.append({
                        "id": scenario_id,
                        "name": name,
                        "description": scenario_manager.scenario_descriptions[scenario_id],
                        "active": scenario_id == scenario_manager.current_scenario
                    })
                return scenarios
        return None

def set_scenario(scenario_id):
    """Set the active scenario via the API."""
    try:
        response = requests.post(f"{API_URL}/scenarios/set/{scenario_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error setting scenario: {e}")
        if DIRECT_ACCESS:
            # Fallback to direct access
            result = scenario_manager.set_scenario(scenario_id)
            return {"status": "success", "message": f"Scenario set to {scenario_id}"} if result else {"status": "error", "message": "Failed to set scenario"}
        return None

def create_network_graph(nodes, links):
    """Create a network graph visualization from nodes and links."""
    # Create a graph
    G = nx.Graph()
    
    # Node color map
    node_colors = {
        "server": "#FF9900",
        "gateway": "#3366CC",
        "client": "#66AA00",
    }
    
    # Node status color map
    status_colors = {
        "active": "#66AA00",
        "congested": "#FF9900",
        "suspicious": "#CC0000",
        "resource_limited": "#9900CC",
    }
    
    # Add nodes
    for node in nodes:
        G.add_node(
            node["id"],
            title=f"{node['id']} ({node['type']})",
            color=node_colors.get(node["type"], "#999999"),
            border_color=status_colors.get(node["status"], "#999999"),
            border_width=2 if node["status"] != "active" else 1,
            size=25 if node["type"] == "server" else (20 if node["type"] == "gateway" else 15),
            x=node["coordinates"][0] * 1000,
            y=node["coordinates"][1] * 1000,
        )
    
    # Add edges
    for link in links:
        G.add_edge(
            link["source"],
            link["target"],
            color="#CCCCCC" if link["status"] == "active" else 
                  "#FF9900" if link["status"] == "congested" else
                  "#CC0000" if link["status"] == "monitored" else "#999999",
            width=1 + (link["utilization"] / 30),
        )
    
    # Create edge traces
    edge_traces = []
    for u, v, data in G.edges(data=True):
        x0, y0 = G.nodes[u]["x"], G.nodes[u]["y"]
        x1, y1 = G.nodes[v]["x"], G.nodes[v]["y"]
        
        edge_trace = go.Scatter(
            x=[x0, x1], y=[y0, y1],
            line=dict(width=data.get("width", 1), color=data.get("color", "#999999")),
            hoverinfo="none",
            mode="lines",
            showlegend=False,
        )
        edge_traces.append(edge_trace)
    
    # Create node trace
    node_trace = go.Scatter(
        x=[data["x"] for _, data in G.nodes(data=True)],
        y=[data["y"] for _, data in G.nodes(data=True)],
        mode="markers",
        hoverinfo="text",
        marker=dict(
            size=[data["size"] for _, data in G.nodes(data=True)],
            color=[data["color"] for _, data in G.nodes(data=True)],
            line=dict(
                width=[data["border_width"] for _, data in G.nodes(data=True)], 
                color=[data["border_color"] for _, data in G.nodes(data=True)]
            ),
        ),
        text=[data["title"] for _, data in G.nodes(data=True)],
        showlegend=False,
    )
    
    # Create figure
    fig = go.Figure(
        data=edge_traces + [node_trace],
        layout=go.Layout(
            title="Network Topology",
            showlegend=False,
            hovermode="closest",
            margin=dict(b=0, l=0, r=0, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="rgba(240,240,240,0.8)",
        )
    )
    
    return fig

# Header component
def build_header():
    """Build the dashboard header."""
    return dbc.Row(
        [
            dbc.Col(
                html.H1("Federated Learning & SDN Integration Dashboard", className="text-primary"),
                width=8,
            ),
            dbc.Col(
                dbc.ButtonGroup(
                    [
                        dbc.Button(
                            "Refresh Data", 
                            id="refresh-button", 
                            color="primary", 
                            className="me-2"
                        ),
                        dbc.Button(
                            "Auto-Refresh ", 
                            id="auto-refresh-button", 
                            color="secondary", 
                            className="me-2",
                        ),
                        dbc.Badge(
                            "OFF", 
                            id="refresh-status-badge", 
                            color="danger", 
                            className="me-1",
                        ),
                    ],
                    className="float-end",
                ),
                width=4,
                className="d-flex justify-content-end align-items-center",
            ),
        ],
        className="mb-4 border-bottom pb-3",
    )

# Scenario selector component
def build_scenario_selector():
    """Build the scenario selector component."""
    return dbc.Card(
        [
            dbc.CardHeader("Simulation Scenarios"),
            dbc.CardBody(
                [
                    html.Div(id="scenario-loading-spinner", children=[
                        dbc.Spinner(color="primary", size="sm"),
                        html.Span(" Loading scenarios...", className="ms-2"),
                    ]),
                    html.Div(id="scenario-selector-container", style={"display": "none"}, children=[
                        dbc.RadioItems(
                            id="scenario-selector",
                            className="mb-2",
                        ),
                        html.P(id="scenario-description", className="text-muted small"),
                        dbc.Progress(id="training-progress", value=0, max=100, className="mb-2"),
                        html.Div(id="round-indicator", className="text-center small text-muted"),
                    ]),
                ]
            ),
        ],
        className="mb-4",
    )

# Create summary stats component
def build_summary_stats():
    """Build the summary statistics component."""
    return dbc.Card(
        [
            dbc.CardHeader("System Statistics"),
            dbc.CardBody(
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.H6("FL Clients", className="text-center text-muted"),
                                html.H3(id="stat-fl-clients", className="text-center"),
                                html.P(id="stat-fl-participation", className="text-center small text-muted"),
                            ],
                            width=4,
                        ),
                        dbc.Col(
                            [
                                html.H6("Network", className="text-center text-muted"),
                                html.H3(id="stat-network-health", className="text-center"),
                                html.P(id="stat-network-details", className="text-center small text-muted"),
                            ],
                            width=4,
                        ),
                        dbc.Col(
                            [
                                html.H6("Policies", className="text-center text-muted"),
                                html.H3(id="stat-active-policies", className="text-center"),
                                html.P(id="stat-policy-details", className="text-center small text-muted"),
                            ],
                            width=4,
                        ),
                    ]
                )
            ),
        ],
        className="mb-4",
    )

# FL metrics component
def build_fl_metrics():
    """Build the FL metrics component."""
    return dbc.Card(
        [
            dbc.CardHeader("Federated Learning Metrics"),
            dbc.CardBody(
                [
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                dcc.Graph(id="accuracy-graph", style={"height": "300px"}),
                                label="Accuracy",
                            ),
                            dbc.Tab(
                                dcc.Graph(id="loss-graph", style={"height": "300px"}),
                                label="Loss",
                            ),
                            dbc.Tab(
                                dcc.Graph(id="training-time-graph", style={"height": "300px"}),
                                label="Training Time",
                            ),
                        ]
                    ),
                ]
            ),
        ],
        className="mb-4",
    )

# Network metrics component
def build_network_metrics():
    """Build the network metrics component."""
    return dbc.Card(
        [
            dbc.CardHeader("Network Metrics"),
            dbc.CardBody(
                [
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                dcc.Graph(id="network-topology", style={"height": "500px"}),
                                label="Topology",
                            ),
                            dbc.Tab(
                                dcc.Graph(id="latency-graph", style={"height": "500px"}),
                                label="Latency",
                            ),
                            dbc.Tab(
                                dcc.Graph(id="trust-score-graph", style={"height": "500px"}),
                                label="Trust Scores",
                            ),
                        ]
                    ),
                ]
            ),
        ],
        className="mb-4",
    )

# Policy monitoring component
def build_policy_monitor():
    """Build the policy monitoring component."""
    return dbc.Card(
        [
            dbc.CardHeader("Policy Engine"),
            dbc.CardBody(
                [
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                id="active-policies-tab",
                                label="Active Policies",
                                children=[
                                    html.Div(id="active-policies-container")
                                ],
                            ),
                            dbc.Tab(
                                id="policy-history-tab",
                                label="Policy History",
                                children=[
                                    html.Div(id="policy-history-container")
                                ],
                            ),
                        ]
                    ),
                ]
            ),
        ],
        className="mb-4",
    )

# Application-specific metrics component
def build_app_metrics():
    """Build the application-specific metrics component."""
    return dbc.Card(
        [
            dbc.CardHeader(html.Div(id="app-metrics-header", children="Application Metrics")),
            dbc.CardBody(
                [
                    html.Div(id="app-metrics-description", className="mb-3"),
                    html.Div(id="app-metrics-charts"),
                ]
            ),
        ],
        className="mb-4",
    )

# Create layout
app.layout = dbc.Container(
    [
        # Header
        build_header(),
        
        # Main content
        dbc.Row(
            [
                # Sidebar
                dbc.Col(
                    [
                        build_scenario_selector(),
                        build_summary_stats(),
                    ],
                    width=3,
                ),
                
                # Main content area
                dbc.Col(
                    [
                        dbc.Row(
                            [
                                dbc.Col(build_fl_metrics(), width=12),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(build_network_metrics(), width=12),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(build_policy_monitor(), width=6),
                                dbc.Col(build_app_metrics(), width=6),
                            ]
                        ),
                    ],
                    width=9,
                ),
            ]
        ),
        
        # Footer
        dbc.Row(
            dbc.Col(
                html.Footer(
                    [
                        html.Hr(),
                        html.P(
                            "FL-SDN Integration Dashboard - Demo Version",
                            className="text-center text-muted",
                        ),
                    ]
                ),
                width=12,
            )
        ),
        
        # Hidden div for storing the current data
        html.Div(id="current-data-store", style={"display": "none"}),
        
        # Refresh interval
        dcc.Interval(
            id="refresh-interval",
            interval=10 * 1000,  # in milliseconds (10 seconds)
            n_intervals=0,
            disabled=True,
        ),
    ],
    fluid=True,
    className="p-4",
)

# Callbacks
@callback(
    [
        Output("scenario-selector", "options"),
        Output("scenario-selector", "value"),
        Output("scenario-loading-spinner", "style"),
        Output("scenario-selector-container", "style"),
    ],
    Input("refresh-interval", "n_intervals"),
    Input("refresh-button", "n_clicks"),
)
def update_scenario_selector(n_intervals, n_clicks):
    """Update the scenario selector with available scenarios."""
    scenarios_data = fetch_from_api("scenarios/list")
    
    if not scenarios_data:
        return [], None, {"display": "block"}, {"display": "none"}
    
    options = []
    current_value = None
    
    for scenario in scenarios_data:
        option = {
            "label": scenario["name"],
            "value": scenario["id"],
        }
        options.append(option)
        
        if scenario["active"]:
            current_value = scenario["id"]
    
    return options, current_value, {"display": "none"}, {"display": "block"}

@callback(
    [
        Output("scenario-description", "children"),
        Output("current-data-store", "children"),
        Output("training-progress", "value"),
        Output("round-indicator", "children"),
    ],
    [
        Input("scenario-selector", "value"),
        Input("refresh-interval", "n_intervals"),
        Input("refresh-button", "n_clicks"),
    ],
)
def update_scenario_data(selected_scenario, n_intervals, n_clicks):
    """Update the scenario description and fetch data for the selected scenario."""
    # Set the scenario if it's changed by user selection
    if selected_scenario and dash.callback_context.triggered_id == "scenario-selector":
        set_scenario(selected_scenario)
    
    # Fetch current data
    data = fetch_from_api("metrics/all")
    
    if not data or "metrics" not in data:
        return "No data available", None, 0, "Round: 0 / 0"
    
    # Get description for the current scenario
    scenario_info = data["metrics"]["scenario"]
    description = scenario_info["description"]
    
    # Calculate progress
    current_round = scenario_info["current_round"]
    max_rounds = scenario_info["max_rounds"]
    progress = (current_round / max_rounds) * 100 if max_rounds > 0 else 0
    
    # Update round indicator
    round_text = f"Round: {current_round} / {max_rounds}"
    
    # Store the data
    return description, json.dumps(data["metrics"]), progress, round_text

@callback(
    [
        Output("accuracy-graph", "figure"),
        Output("loss-graph", "figure"),
        Output("training-time-graph", "figure"),
    ],
    Input("current-data-store", "children"),
)
def update_fl_metrics(json_data):
    """Update the FL metrics visualizations."""
    if not json_data:
        # Return empty figures
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No data available")
        return empty_fig, empty_fig, empty_fig
    
    # Parse the data
    data = json.loads(json_data)
    fl_data = data["fl"]
    
    # Create accuracy chart
    accuracy_fig = px.line(
        x=fl_data["rounds"],
        y=fl_data["accuracy"],
        labels={"x": "Round", "y": "Accuracy"},
        title="Model Accuracy",
    )
    accuracy_fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    
    # Create loss chart
    loss_fig = px.line(
        x=fl_data["rounds"],
        y=fl_data["loss"],
        labels={"x": "Round", "y": "Loss"},
        title="Model Loss",
    )
    loss_fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    
    # Create training time chart
    training_time_fig = px.line(
        x=fl_data["rounds"],
        y=fl_data["training_time"],
        labels={"x": "Round", "y": "Time (s)"},
        title="Training Time per Round",
    )
    training_time_fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    
    return accuracy_fig, loss_fig, training_time_fig

@callback(
    [
        Output("network-topology", "figure"),
        Output("latency-graph", "figure"),
        Output("trust-score-graph", "figure"),
    ],
    Input("current-data-store", "children"),
)
def update_network_metrics(json_data):
    """Update the network metrics visualizations."""
    if not json_data:
        # Return empty figures
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No data available")
        return empty_fig, empty_fig, empty_fig
    
    # Parse the data
    data = json.loads(json_data)
    network_data = data["network"]
    
    # Create network topology visualization
    topology = network_data["topology"]
    topology_fig = create_network_graph(topology["nodes"], topology["links"])
    
    # Create node latency chart
    # Group nodes by type
    node_types = {}
    for node in topology["nodes"]:
        node_type = node["type"]
        if node_type not in node_types:
            node_types[node_type] = []
        node_types[node_type].append(node)
    
    # Create link latency dataframe
    links_df = pd.DataFrame([
        {
            "link": link["id"],
            "source": link["source"],
            "target": link["target"],
            "latency": link["latency"],
            "status": link["status"]
        }
        for link in topology["links"]
    ])
    
    latency_fig = px.bar(
        links_df,
        x="link",
        y="latency",
        color="status",
        title="Link Latency (ms)",
        color_discrete_map={
            "active": "#66AA00",
            "congested": "#FF9900",
            "monitored": "#CC0000",
        }
    )
    latency_fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    
    # Create trust score chart
    trust_df = pd.DataFrame([
        {
            "node": node["id"],
            "trust_score": node["trust_score"],
            "type": node["type"],
            "status": node["status"]
        }
        for node in topology["nodes"]
        if "trust_score" in node
    ])
    
    trust_fig = px.bar(
        trust_df,
        x="node",
        y="trust_score",
        color="status",
        title="Node Trust Scores",
        color_discrete_map={
            "active": "#66AA00",
            "congested": "#FF9900",
            "suspicious": "#CC0000",
            "resource_limited": "#9900CC",
        }
    )
    trust_fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    
    return topology_fig, latency_fig, trust_fig

@callback(
    [
        Output("active-policies-container", "children"),
        Output("policy-history-container", "children"),
    ],
    Input("current-data-store", "children"),
)
def update_policy_data(json_data):
    """Update the policy data visualizations."""
    if not json_data:
        return "No policy data available", "No policy history available"
    
    # Parse the data
    data = json.loads(json_data)
    policy_data = data["policy"]
    
    # Create active policies table
    active_policies = policy_data["active_policies"]
    if not active_policies:
        active_policies_component = html.P("No active policies")
    else:
        rows = []
        for policy in active_policies:
            # Create conditions and actions text
            conditions = ", ".join([f"{c['metric']} {c['operator']} {c['value']}" for c in policy["conditions"]])
            actions = ", ".join([a["action"] for a in policy["actions"]])
            
            rows.append(
                html.Tr([
                    html.Td(policy["name"]),
                    html.Td(policy["type"]),
                    html.Td(conditions),
                    html.Td(actions),
                ])
            )
        
        active_policies_component = dbc.Table(
            [
                html.Thead(
                    html.Tr([
                        html.Th("Name"),
                        html.Th("Type"),
                        html.Th("Conditions"),
                        html.Th("Actions"),
                    ])
                ),
                html.Tbody(rows),
            ],
            bordered=True,
            hover=True,
            responsive=True,
            size="sm",
        )
    
    # Create policy history table
    history = policy_data["policy_history"]
    if not history:
        history_component = html.P("No policy history available")
    else:
        # Only show the latest 10 entries
        history = history[-10:]
        
        history_rows = []
        for entry in history:
            history_rows.append(
                html.Tr([
                    html.Td(entry["name"]),
                    html.Td(entry["timestamp"]),
                    html.Td(entry["scenario"]),
                    html.Td(
                        html.Span(
                            entry["result"],
                            className=f"badge bg-{'success' if entry['result'] == 'Applied' else 'danger'}"
                        )
                    ),
                ])
            )
        
        history_component = dbc.Table(
            [
                html.Thead(
                    html.Tr([
                        html.Th("Policy"),
                        html.Th("Timestamp"),
                        html.Th("Scenario"),
                        html.Th("Result"),
                    ])
                ),
                html.Tbody(history_rows),
            ],
            bordered=True,
            hover=True,
            responsive=True,
            size="sm",
        )
    
    return active_policies_component, history_component

@callback(
    [
        Output("app-metrics-header", "children"),
        Output("app-metrics-description", "children"),
        Output("app-metrics-charts", "children"),
    ],
    Input("current-data-store", "children"),
)
def update_app_metrics(json_data):
    """Update the application-specific metrics visualizations."""
    if not json_data:
        return "Application Metrics", "No data available", []
    
    # Parse the data
    data = json.loads(json_data)
    app_data = data["app"]
    scenario = app_data["scenario"]
    
    # Set header with scenario name
    header = f"Application Metrics: {app_data['name']}"
    
    # Set description
    description = app_data["description"]
    
    # Create charts based on the scenario
    charts = []
    
    if scenario == "normal":  # Smart City Traffic
        metrics = app_data["metrics"]
        
        # Traffic flow improvement
        if "traffic_flow_improvement" in metrics and metrics["traffic_flow_improvement"]:
            traffic_fig = px.line(
                x=list(range(len(metrics["traffic_flow_improvement"]))),
                y=metrics["traffic_flow_improvement"],
                labels={"x": "Time", "y": "Improvement (%)"},
                title="Traffic Flow Improvement",
            )
            charts.append(dcc.Graph(figure=traffic_fig, style={"height": "250px"}))
        
        # Prediction accuracy
        if "prediction_accuracy" in metrics and metrics["prediction_accuracy"]:
            pred_fig = px.line(
                x=list(range(len(metrics["prediction_accuracy"]))),
                y=metrics["prediction_accuracy"],
                labels={"x": "Time", "y": "Accuracy"},
                title="Traffic Prediction Accuracy",
            )
            charts.append(dcc.Graph(figure=pred_fig, style={"height": "250px"}))
        
        # Signal timing efficiency
        if "signal_timing_efficiency" in metrics and metrics["signal_timing_efficiency"]:
            signal_fig = px.line(
                x=list(range(len(metrics["signal_timing_efficiency"]))),
                y=metrics["signal_timing_efficiency"],
                labels={"x": "Time", "y": "Efficiency (%)"},
                title="Signal Timing Efficiency",
            )
            charts.append(dcc.Graph(figure=signal_fig, style={"height": "250px"}))
    
    elif scenario == "congestion":  # Healthcare Monitoring
        metrics = app_data["metrics"]
        
        # Alert latency
        if "alert_latency" in metrics and metrics["alert_latency"]:
            alert_fig = px.line(
                x=list(range(len(metrics["alert_latency"]))),
                y=metrics["alert_latency"],
                labels={"x": "Time", "y": "Latency (s)"},
                title="Critical Alert Latency",
            )
            charts.append(dcc.Graph(figure=alert_fig, style={"height": "250px"}))
        
        # Anomaly detection rate
        if "anomaly_detection_rate" in metrics and metrics["anomaly_detection_rate"]:
            anomaly_fig = px.line(
                x=list(range(len(metrics["anomaly_detection_rate"]))),
                y=metrics["anomaly_detection_rate"],
                labels={"x": "Time", "y": "Detection Rate (%)"},
                title="Anomaly Detection Rate",
            )
            charts.append(dcc.Graph(figure=anomaly_fig, style={"height": "250px"}))
        
        # False alarm rate
        if "false_alarm_rate" in metrics and metrics["false_alarm_rate"]:
            alarm_fig = px.line(
                x=list(range(len(metrics["false_alarm_rate"]))),
                y=metrics["false_alarm_rate"],
                labels={"x": "Time", "y": "False Alarm Rate (%)"},
                title="False Alarm Rate",
            )
            charts.append(dcc.Graph(figure=alarm_fig, style={"height": "250px"}))
    
    elif scenario == "security":  # Financial Fraud
        metrics = app_data["metrics"]
        
        # Fraud detection rate
        if "fraud_detection_rate" in metrics and metrics["fraud_detection_rate"]:
            fraud_fig = px.line(
                x=list(range(len(metrics["fraud_detection_rate"]))),
                y=metrics["fraud_detection_rate"],
                labels={"x": "Time", "y": "Detection Rate (%)"},
                title="Fraud Detection Rate",
            )
            charts.append(dcc.Graph(figure=fraud_fig, style={"height": "250px"}))
        
        # False positive rate
        if "false_positive_rate" in metrics and metrics["false_positive_rate"]:
            fp_fig = px.line(
                x=list(range(len(metrics["false_positive_rate"]))),
                y=metrics["false_positive_rate"],
                labels={"x": "Time", "y": "False Positive Rate (%)"},
                title="False Positive Rate",
            )
            charts.append(dcc.Graph(figure=fp_fig, style={"height": "250px"}))
        
        # Model robustness
        if "model_robustness" in metrics and metrics["model_robustness"]:
            robust_fig = px.line(
                x=list(range(len(metrics["model_robustness"]))),
                y=metrics["model_robustness"],
                labels={"x": "Time", "y": "Robustness Score"},
                title="Model Robustness",
            )
            charts.append(dcc.Graph(figure=robust_fig, style={"height": "250px"}))
    
    elif scenario == "resource":  # Mobile Keyboard
        metrics = app_data["metrics"]
        
        # Word prediction accuracy
        if "word_prediction_accuracy" in metrics and metrics["word_prediction_accuracy"]:
            word_fig = px.line(
                x=list(range(len(metrics["word_prediction_accuracy"]))),
                y=metrics["word_prediction_accuracy"],
                labels={"x": "Time", "y": "Accuracy"},
                title="Word Prediction Accuracy",
            )
            charts.append(dcc.Graph(figure=word_fig, style={"height": "250px"}))
        
        # Battery consumption
        if "battery_consumption" in metrics and metrics["battery_consumption"]:
            battery_fig = px.line(
                x=list(range(len(metrics["battery_consumption"]))),
                y=metrics["battery_consumption"],
                labels={"x": "Time", "y": "Battery Usage (%)"},
                title="Battery Consumption per Prediction",
            )
            charts.append(dcc.Graph(figure=battery_fig, style={"height": "250px"}))
        
        # Model size
        if "model_size" in metrics and metrics["model_size"]:
            size_fig = px.line(
                x=list(range(len(metrics["model_size"]))),
                y=metrics["model_size"],
                labels={"x": "Time", "y": "Size (MB)"},
                title="Model Size",
            )
            charts.append(dcc.Graph(figure=size_fig, style={"height": "250px"}))
    
    if not charts:
        charts = [html.P("No application-specific metrics available for this scenario")]
    
    return header, description, charts

@callback(
    [
        Output("stat-fl-clients", "children"),
        Output("stat-fl-participation", "className"),
        Output("stat-fl-participation", "children"),
        Output("stat-network-health", "children"),
        Output("stat-network-details", "className"),
        Output("stat-network-details", "children"),
        Output("stat-active-policies", "children"),
        Output("stat-policy-details", "className"),
        Output("stat-policy-details", "children"),
    ],
    Input("current-data-store", "children"),
)
def update_summary_stats(json_data):
    """Update the summary statistics."""
    if not json_data:
        return (
            "N/A", "text-center small text-muted", "No data available",
            "N/A", "text-center small text-muted", "No data available",
            "N/A", "text-center small text-muted", "No data available",
        )
    
    # Parse the data
    data = json.loads(json_data)
    
    # FL client stats
    fl_clients = data["network"]["nodes"]["total"] - 1  # Excluding server
    participation = data["fl"]["participation_rate"][-1] if data["fl"]["participation_rate"] else 0
    participation_text = f"{int(participation * 100)}% participation"
    participation_class = f"text-center small {'text-success' if participation >= 0.8 else 'text-warning' if participation >= 0.6 else 'text-danger'}"
    
    # Network health
    healthy_links = data["network"]["links"]["active"]
    total_links = data["network"]["links"]["total"]
    health_percentage = (healthy_links / total_links) * 100 if total_links > 0 else 0
    network_health = f"{int(health_percentage)}%"
    
    avg_latency = data["network"]["performance"]["avg_latency"]
    network_details = f"Avg latency: {avg_latency:.1f}ms, {data['network']['links']['congested']} congested links"
    network_class = f"text-center small {'text-success' if health_percentage >= 90 else 'text-warning' if health_percentage >= 70 else 'text-danger'}"
    
    # Policy stats
    active_policies = data["policy"]["active_count"]
    total_policies = data["policy"]["total_policies"]
    policy_details = f"{active_policies} of {total_policies} policies active"
    policy_class = "text-center small text-info"
    
    return (
        fl_clients, participation_class, participation_text,
        network_health, network_class, network_details,
        active_policies, policy_class, policy_details,
    )

@callback(
    [
        Output("refresh-interval", "disabled"),
        Output("refresh-status-badge", "children"),
        Output("refresh-status-badge", "color"),
    ],
    Input("auto-refresh-button", "n_clicks"),
    State("refresh-interval", "disabled"),
)
def toggle_auto_refresh(n_clicks, currently_disabled):
    """Toggle the auto-refresh functionality."""
    if n_clicks is None:
        return True, "OFF", "danger"
    
    # Toggle the state
    new_disabled = not currently_disabled
    
    # Update the badge
    badge_text = "OFF" if new_disabled else "ON"
    badge_color = "danger" if new_disabled else "success"
    
    return new_disabled, badge_text, badge_color

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050) 