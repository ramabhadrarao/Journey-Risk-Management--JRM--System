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

from dashboards.utils import make_map, get_api_data

# Main Dashboard Layout
main_dashboard_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("JRM Dashboard", className="mt-4 mb-4"),
            html.Div(id="last-update-timestamp", className="text-muted mb-3"),
            dbc.Card([
                dbc.CardHeader("Dashboard Summary"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H2(id="total-routes", className="card-title text-center"),
                                    html.P("Total Routes", className="card-text text-center")
                                ])
                            ], className="mb-3")
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H2(id="total-distance", className="card-title text-center"),
                                    html.P("Total Distance (km)", className="card-text text-center")
                                ])
                            ], className="mb-3")
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H2(id="total-duration", className="card-title text-center"),
                                    html.P("Total Duration (hrs)", className="card-text text-center")
                                ])
                            ], className="mb-3")
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H2(id="total-vehicles", className="card-title text-center"),
                                    html.P("Total Vehicles", className="card-text text-center")
                                ])
                            ], className="mb-3")
                        ], width=3),
                    ]),
                ])
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Risk Distribution"),
                        dbc.CardBody([
                            dcc.Graph(id="risk-distribution-chart")
                        ])
                    ], className="mb-4")
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Risk Points by Type"),
                        dbc.CardBody([
                            dcc.Graph(id="risk-points-chart")
                        ])
                    ], className="mb-4")
                ], width=6),
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Recent Routes"),
                        dbc.CardBody([
                            html.Div(id="recent-routes-table")
                        ])
                    ], className="mb-4")
                ], width=12),
            ]),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Vehicle Locations"),
                        dbc.CardBody([
                            html.Div(id="vehicle-map-container", style={"height": "400px"}),
                        ])
                    ])
                ], width=12),
            ]),
            
            dcc.Interval(
                id='interval-component',
                interval=30*1000,  # in milliseconds (30 seconds)
                n_intervals=0
            )
        ], width=12)
    ])
], fluid=True)

def setup_main_dashboard_callbacks(app):
    """Setup callbacks for the main dashboard"""
    
    @app.callback(
        [
            Output("last-update-timestamp", "children"),
            Output("total-routes", "children"),
            Output("total-distance", "children"),
            Output("total-duration", "children"),
            Output("total-vehicles", "children"),
            Output("risk-distribution-chart", "figure"),
            Output("risk-points-chart", "figure"),
            Output("recent-routes-table", "children"),
            Output("vehicle-map-container", "children")
        ],
        [Input("interval-component", "n_intervals")]
    )
    def update_dashboard(n_intervals):
        # Get dashboard data from backend API
        dashboard_data = get_api_data("/dashboard/api/dashboard-data")
        real_time_data = get_api_data("/dashboard/api/real-time-updates")
        
        if not dashboard_data:
            return (
                "Failed to load data",
                "0", "0", "0", "0",
                go.Figure(), go.Figure(),
                html.Div("No data available"),
                html.Div("No map data available")
            )
        
        # Extract summary data
        summary = dashboard_data.get("summary", {})
        
        # Create timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp_text = f"Last updated: {now}"
        
        # Format numbers
        total_routes = summary.get("total_routes", 0)
        total_distance = summary.get("total_distance", 0)
        total_duration = summary.get("total_duration", 0)
        total_vehicles = summary.get("total_vehicles", 0)
        
        # Create Risk Distribution Chart
        risk_distribution = summary.get("risk_distribution", {})
        if risk_distribution:
            risk_df = pd.DataFrame({
                "Risk Level": ["High", "Medium", "Low", "Unknown"],
                "Count": [
                    risk_distribution.get("high", 0),
                    risk_distribution.get("medium", 0),
                    risk_distribution.get("low", 0),
                    risk_distribution.get("unknown", 0)
                ]
            })
            
            # Map risk levels to colors
            colors = {
                "High": "#FF5252",
                "Medium": "#FFC107",
                "Low": "#4CAF50",
                "Unknown": "#9E9E9E"
            }
            
            risk_fig = px.pie(
                risk_df, values="Count", names="Risk Level",
                title="Route Risk Distribution",
                color="Risk Level",
                color_discrete_map=colors
            )
            
            risk_fig.update_traces(textposition='inside', textinfo='percent+label')
            risk_fig.update_layout(margin=dict(l=30, r=30, t=50, b=30))
        else:
            risk_fig = go.Figure()
        
        # Create Risk Points Chart
        risk_points = summary.get("risk_points_by_type", {})
        if risk_points:
            risk_points_df = pd.DataFrame({
                "Risk Type": [k.replace("_", " ").title() for k in risk_points.keys()],
                "Count": list(risk_points.values())
            })
            
            risk_points_fig = px.bar(
                risk_points_df, x="Risk Type", y="Count",
                title="Risk Points by Type"
            )
            
            risk_points_fig.update_layout(
                margin=dict(l=30, r=30, t=50, b=80),
                xaxis_tickangle=-45
            )
        else:
            risk_points_fig = go.Figure()
        
        # Create Recent Routes Table
        recent_routes = dashboard_data.get("recent_routes", [])
        if recent_routes:
            routes_table = dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Route Name"),
                        html.Th("Origin"),
                        html.Th("Destination"),
                        html.Th("Distance"),
                        html.Th("Duration"),
                        html.Th("Risk Level"),
                        html.Th("Actions")
                    ])
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td(route.get("name", f"Route {route.get('route_id', '')[:8]}")),
                        html.Td(route.get("origin", {}).get("address", "N/A")),
                        html.Td(route.get("destination", {}).get("address", "N/A")),
                        html.Td(route.get("distance", "N/A")),
                        html.Td(route.get("duration", "N/A")),
                        html.Td(
                            html.Span(
                                route.get("risk_level", "Unknown").title(),
                                className=f"badge rounded-pill bg-{get_risk_badge_color(route.get('risk_level', 'unknown'))}"
                            )
                        ),
                        html.Td(
                            html.A(
                                "View",
                                href=f"/routes/{route.get('route_id', '')}",
                                className="btn btn-sm btn-primary"
                            )
                        )
                    ]) for route in recent_routes
                ])
            ], bordered=True, hover=True, responsive=True, striped=True)
        else:
            routes_table = html.Div("No recent routes available")
        
        # Create Vehicle Map
        vehicles = dashboard_data.get("vehicles", [])
        latest_telemetry = dashboard_data.get("latest_telemetry", {})
        
        if vehicles and latest_telemetry:
            # Create map with vehicle markers
            vehicle_markers = []
            
            for vehicle in vehicles:
                vehicle_id = str(vehicle.get("_id", ""))
                telemetry = latest_telemetry.get(vehicle_id, {})
                
                if telemetry and "location" in telemetry:
                    location = telemetry["location"]
                    
                    # Create popup content
                    popup_content = f"""
                    <strong>{vehicle.get('name', 'Vehicle')}</strong><br>
                    Make: {vehicle.get('make', 'N/A')}<br>
                    Model: {vehicle.get('model', 'N/A')}<br>
                    Fuel: {telemetry.get('fuel_level', 'N/A')}%<br>
                    Speed: {telemetry.get('speed', 'N/A')} km/h<br>
                    Engine Temp: {telemetry.get('engine_temp', 'N/A')}°C
                    """
                    
                    marker = dl.Marker(
                        position=[location.get("lat", 0), location.get("lng", 0)],
                        children=[
                            dl.Tooltip(vehicle.get('name', 'Vehicle')),
                            dl.Popup(html.Div([
                                html.P(html.Span([
                                    dcc.Markdown(popup_content)
                                ]))
                            ]))
                        ]
                    )
                    
                    vehicle_markers.append(marker)
            
            # If we have real-time data with active routes, add route polylines
            if real_time_data and "active_routes" in real_time_data:
                for route in real_time_data["active_routes"]:
                    if route.get("polyline"):
                        try:
                            # Use polyline library to decode
                            import polyline
                            points = polyline.decode(route["polyline"])
                            
                            # Create polyline
                            vehicle_markers.append(
                                dl.Polyline(
                                    positions=[(p[0], p[1]) for p in points],
                                    color="blue",
                                    weight=4,
                                    opacity=0.7,
                                    children=[
                                        dl.Tooltip(f"Active Route: {route.get('name', 'Route')}")
                                    ]
                                )
                            )
                        except Exception as e:
                            print(f"Error decoding polyline: {str(e)}")
            
            vehicle_map = make_map(vehicle_markers, zoom=10)
        else:
            vehicle_map = make_map([], zoom=3)
        
        return (
            timestamp_text,
            str(total_routes),
            str(total_distance),
            str(total_duration),
            str(total_vehicles),
            risk_fig,
            risk_points_fig,
            routes_table,
            vehicle_map
        )

def get_risk_badge_color(risk_level):
    """Get appropriate badge color for risk level"""
    risk_level = risk_level.lower() if risk_level else "unknown"
    
    if risk_level == "high":
        return "danger"
    elif risk_level == "medium":
        return "warning"
    elif risk_level == "low":
        return "success"
    else:
        return "secondary"