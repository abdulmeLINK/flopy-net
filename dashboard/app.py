"""
Dashboard Web Application

This module provides a Dash web application for the dashboard.
"""

import os
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np

# Create Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

# Set app title
app.title = "FL-SDN Dashboard"

# Generate some sample data
def generate_sample_data():
    """Generate sample data for demonstration."""
    # FL metrics
    rounds = list(range(1, 11))
    accuracy = [0.5 + (i / 20) for i in rounds]
    loss = [1.0 - (i / 15) for i in rounds]
    
    # Network metrics
    network_df = pd.DataFrame({
        "node": [f"Node {i}" for i in range(1, 11)],
        "latency": np.random.uniform(10, 100, 10),
        "bandwidth": np.random.uniform(50, 200, 10),
        "trust_score": np.random.uniform(0.5, 1.0, 10),
    })
    
    return {
        "rounds": rounds,
        "accuracy": accuracy,
        "loss": loss,
        "network_df": network_df,
    }

# Get sample data
sample_data = generate_sample_data()

# Create layout
app.layout = dbc.Container(
    [
        # Header
        dbc.Row(
            dbc.Col(
                html.H1("Federated Learning & SDN Integration Dashboard", className="text-center my-4"),
                width=12,
            )
        ),
        
        # FL Metrics Section
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Training Progress"),
                            dbc.CardBody(
                                dcc.Graph(
                                    figure=px.line(
                                        x=sample_data["rounds"],
                                        y=sample_data["accuracy"],
                                        labels={"x": "Round", "y": "Accuracy"},
                                        title="Model Accuracy",
                                    )
                                )
                            ),
                        ],
                        className="mb-4",
                    ),
                    md=6,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Loss Curve"),
                            dbc.CardBody(
                                dcc.Graph(
                                    figure=px.line(
                                        x=sample_data["rounds"],
                                        y=sample_data["loss"],
                                        labels={"x": "Round", "y": "Loss"},
                                        title="Model Loss",
                                    )
                                )
                            ),
                        ],
                        className="mb-4",
                    ),
                    md=6,
                ),
            ]
        ),
        
        # Network Metrics Section
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Network Latency"),
                            dbc.CardBody(
                                dcc.Graph(
                                    figure=px.bar(
                                        sample_data["network_df"],
                                        x="node",
                                        y="latency",
                                        title="Node Latency (ms)",
                                    )
                                )
                            ),
                        ],
                        className="mb-4",
                    ),
                    md=6,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader("Trust Scores"),
                            dbc.CardBody(
                                dcc.Graph(
                                    figure=px.bar(
                                        sample_data["network_df"],
                                        x="node",
                                        y="trust_score",
                                        title="Node Trust Scores",
                                        color="trust_score",
                                        color_continuous_scale="RdYlGn",
                                    )
                                )
                            ),
                        ],
                        className="mb-4",
                    ),
                    md=6,
                ),
            ]
        ),
        
        # Footer
        dbc.Row(
            dbc.Col(
                html.P(
                    "FL-SDN Integration Dashboard - Demo Version",
                    className="text-center text-muted",
                ),
                width=12,
            )
        ),
        
        # Refresh interval
        dcc.Interval(
            id="interval-component",
            interval=10 * 1000,  # in milliseconds (10 seconds)
            n_intervals=0,
        ),
    ],
    fluid=True,
    className="p-4",
)

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050) 