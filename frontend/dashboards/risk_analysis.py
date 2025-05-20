import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import json

from dashboards.utils import make_map, get_api_data, get_risk_color

# Risk Analysis Dashboard Layout
risk_analysis_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Risk Analysis Dashboard", className="mt-4 mb-4"),
            
            dbc.Card([
                dbc.CardHeader("Analysis Timeframe"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select Timeframe:"),
                            dcc.Dropdown(
                                id="timeframe-dropdown",
                                options=[
                                    {"label": "Last 7 Days", "value": 7},
                                    {"label": "Last 30 Days", "value": 30},
                                    {"label": "Last 90 Days", "value": 90},
                                    {"label": "Last 365 Days", "value": 365}
                                ],
                                value=30,
                                clearable=False
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Last Updated:"),
                            html.Div(id="risk-last-update-timestamp", className="mt-2")
                        ], width=4),
                        dbc.Col([
                            html.Div([
                                dbc.Button(
                                    "Refresh Data", 
                                    id="refresh-button", 
                                    color="primary",
                                    className="mt-4"
                                )
                            ], className="d-flex justify-content-end")
                        ], width=4)
                    ])
                ])
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Risk Trends Over Time"),
                        dbc.CardBody([
                            dcc.Graph(id="risk-trends-chart")
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Risk Categories Distribution"),
                        dbc.CardBody([
                            dcc.Graph(id="risk-categories-chart")
                        ])
                    ])
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Time of Day Analysis"),
                        dbc.CardBody([
                            dcc.Graph(id="time-of-day-chart")
                        ])
                    ])
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Risk Heatmap"),
                        dbc.CardBody([
                            html.Div(id="risk-heatmap-container", style={"height": "500px"})
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Nearby Facilities Statistics"),
                        dbc.CardBody([
                            dcc.Graph(id="facilities-chart")
                        ])
                    ])
                ], width=12)
            ]),
            
            dcc.Interval(
                id='risk-interval-component',
                interval=60*1000,  # in milliseconds (60 seconds)
                n_intervals=0
            ),
            
            # Store for risk analysis data
            dcc.Store(id="risk-analysis-data")
        ], width=12)
    ])
], fluid=True)

def setup_risk_analysis_callbacks(app):
    """Setup callbacks for the risk analysis dashboard"""
    
    @app.callback(
        Output("risk-analysis-data", "data"),
        [
            Input("refresh-button", "n_clicks"),
            Input("timeframe-dropdown", "value"),
            Input("risk-interval-component", "n_intervals")
        ]
    )
    def fetch_risk_analysis_data(n_clicks, days, n_intervals):
        """Fetch risk analysis data from backend API"""
        try:
            # Get risk analysis data
            url = f"/api/dashboard/risk-analysis?days={days}"
            response = get_api_data(url, use_session=True, raw_response=True)
            
            if response and response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"Error fetching risk analysis data: {str(e)}")
            return {}
    
    @app.callback(
        [
            Output("risk-last-update-timestamp", "children"),
            Output("risk-trends-chart", "figure"),
            Output("risk-categories-chart", "figure"),
            Output("time-of-day-chart", "figure"),
            Output("risk-heatmap-container", "children"),
            Output("facilities-chart", "figure")
        ],
        [Input("risk-analysis-data", "data")]
    )
    def update_risk_analysis_dashboard(data):
        if not data:
            return (
                "No data available",
                go.Figure(),
                go.Figure(),
                go.Figure(),
                html.Div("No heatmap data available"),
                go.Figure()
            )
        
        # Create timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp_text = f"{now}"
        
        # Create Risk Trends Chart
        risk_trends = data.get("risk_trends", [])
        if risk_trends:
            # Convert to DataFrame
            trends_df = pd.DataFrame(risk_trends)
            
            # Add datetime object for better formatting
            trends_df["datetime"] = pd.to_datetime(trends_df["date"])
            trends_df = trends_df.sort_values("datetime")
            
            # Create figure
            risk_trends_fig = px.line(
                trends_df, 
                x="datetime", 
                y="risk_score",
                title="Risk Score Trends Over Time",
                labels={"datetime": "Date", "risk_score": "Risk Score"},
                hover_data=["route_name"]
            )
            
            risk_trends_fig.update_layout(
                margin=dict(l=40, r=40, t=50, b=40),
                hovermode="closest"
            )
            
            # Add reference lines for risk thresholds
            risk_trends_fig.add_shape(
                type="line",
                x0=trends_df["datetime"].min(),
                x1=trends_df["datetime"].max(),
                y0=8,
                y1=8,
                line=dict(color="red", width=2, dash="dash"),
                name="High Risk"
            )
            
            risk_trends_fig.add_shape(
                type="line",
                x0=trends_df["datetime"].min(),
                x1=trends_df["datetime"].max(),
                y0=6,
                y1=6,
                line=dict(color="orange", width=2, dash="dash"),
                name="Medium Risk"
            )
            
            # Add annotations for thresholds
            risk_trends_fig.add_annotation(
                x=trends_df["datetime"].max(),
                y=8,
                text="High Risk",
                showarrow=False,
                yshift=10,
                font=dict(color="red")
            )
            
            risk_trends_fig.add_annotation(
                x=trends_df["datetime"].max(),
                y=6,
                text="Medium Risk",
                showarrow=False,
                yshift=10,
                font=dict(color="orange")
            )
        else:
            risk_trends_fig = go.Figure()
        
        # Create Risk Categories Chart
        risk_categories = data.get("risk_categories", {})
        if risk_categories:
            # Create dataframe for stacked bar chart
            categories = list(risk_categories.keys())
            
            # Prepare data for stacked bar chart
            risk_cat_df = pd.DataFrame({
                "Category": [],
                "Risk Level": [],
                "Count": []
            })
            
            for category, risks in risk_categories.items():
                category_name = category.replace("_", " ").title()
                for level, count in risks.items():
                    risk_cat_df = pd.concat([
                        risk_cat_df,
                        pd.DataFrame({
                            "Category": [category_name],
                            "Risk Level": [level.title()],
                            "Count": [count]
                        })
                    ])
            
            # Create stacked bar chart
            risk_categories_fig = px.bar(
                risk_cat_df,
                x="Category",
                y="Count",
                color="Risk Level",
                title="Risk Categories Distribution",
                color_discrete_map={
                    "High": "#FF5252",
                    "Medium": "#FFC107",
                    "Low": "#4CAF50"
                }
            )
            
            risk_categories_fig.update_layout(
                margin=dict(l=40, r=40, t=50, b=40),
                barmode="stack",
                xaxis_tickangle=-45
            )
        else:
            risk_categories_fig = go.Figure()
        
        # Create Time of Day Analysis Chart
        time_analysis = data.get("time_analysis", {})
        if time_analysis:
            # Prepare data for grouped bar chart
            time_df = pd.DataFrame({
                "Time of Day": [],
                "Risk Level": [],
                "Count": []
            })
            
            for period, risks in time_analysis.items():
                period_name = period.title()
                for level, count in risks.items():
                    time_df = pd.concat([
                        time_df,
                        pd.DataFrame({
                            "Time of Day": [period_name],
                            "Risk Level": [level.title()],
                            "Count": [count]
                        })
                    ])
            
            # Create grouped bar chart
            time_analysis_fig = px.bar(
                time_df,
                x="Time of Day",
                y="Count",
                color="Risk Level",
                title="Risk Levels by Time of Day",
                color_discrete_map={
                    "High": "#FF5252",
                    "Medium": "#FFC107",
                    "Low": "#4CAF50"
                },
                barmode="group"
            )
            
            time_analysis_fig.update_layout(
                margin=dict(l=40, r=40, t=50, b=40)
            )
        else:
            time_analysis_fig = go.Figure()
        
        # Create Risk Heatmap
        risk_heatmap = data.get("risk_heatmap", [])
        if risk_heatmap:
            # Create heatmap layer
            heat_data = [[point['lat'], point['lng'], point['weight']] for point in risk_heatmap]
            
            heatmap_layer = dl.Heatmap(
                positions=heat_data,
                radius=20,
                blur=15,
                max=5,
                gradient={
                    0.4: 'blue',
                    0.65: 'lime',
                    0.8: 'yellow',
                    1.0: 'red'
                }
            )
            
            # Find center of heatmap
            lats = [point['lat'] for point in risk_heatmap]
            lngs = [point['lng'] for point in risk_heatmap]
            
            center = [sum(lats) / len(lats), sum(lngs) / len(lngs)] if lats and lngs else [0, 0]
            
            # Create map with heatmap layer
            risk_map = make_map([heatmap_layer], center=center, zoom=10)
        else:
            risk_map = make_map([], zoom=3)
        
        # Create Nearby Facilities Statistics Chart
        facilities_stats = data.get("facilities_stats", {})
        if facilities_stats:
            # Prepare data for grouped bar chart
            facilities_df = pd.DataFrame({
                "Facility Type": [],
                "Distance Range": [],
                "Count": []
            })
            
            for facility_type, ranges in facilities_stats.items():
                facility_name = facility_type.replace("_", " ").title()
                for range_name, count in ranges.items():
                    range_label = range_name.replace("_", " ").title()
                    
                    # Make range names more readable
                    if range_name == "under_1km":
                        range_label = "Under 1 km"
                    elif range_name == "1km_to_5km":
                        range_label = "1-5 km"
                    elif range_name == "over_5km":
                        range_label = "Over 5 km"
                    
                    facilities_df = pd.concat([
                        facilities_df,
                        pd.DataFrame({
                            "Facility Type": [facility_name],
                            "Distance Range": [range_label],
                            "Count": [count]
                        })
                    ])
            
            # Create grouped bar chart
            facilities_fig = px.bar(
                facilities_df,
                x="Facility Type",
                y="Count",
                color="Distance Range",
                title="Nearby Facilities by Distance",
                barmode="group"
            )
            
            facilities_fig.update_layout(
                margin=dict(l=40, r=40, t=50, b=80),
                xaxis_tickangle=-45
            )
        else:
            facilities_fig = go.Figure()
        
        return (
            timestamp_text,
            risk_trends_fig,
            risk_categories_fig,
            time_analysis_fig,
            risk_map,
            facilities_fig
        )