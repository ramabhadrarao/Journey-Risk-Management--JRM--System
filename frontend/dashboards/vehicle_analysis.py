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

from frontend.dashboards.utils import make_map, get_api_data, get_risk_color

# Vehicle Analysis Dashboard Layout
vehicle_analysis_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Vehicle Analysis Dashboard", className="mt-4 mb-4"),
            
            dbc.Card([
                dbc.CardHeader("Vehicle Selection"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select Vehicle:"),
                            dcc.Dropdown(
                                id="vehicle-dropdown",
                                options=[],  # Will be populated in callback
                                value=None,
                                placeholder="Select a vehicle"
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label("Last Updated:"),
                            html.Div(id="vehicle-last-update-timestamp", className="mt-2")
                        ], width=4),
                        dbc.Col([
                            html.Div([
                                dbc.Button(
                                    "Refresh Data", 
                                    id="vehicle-refresh-button", 
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
                        dbc.CardHeader("Vehicle Stats"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H2(id="total-routes-vehicle", className="card-title text-center"),
                                            html.P("Total Routes", className="card-text text-center")
                                        ])
                                    ])
                                ], width=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H2(id="total-distance-vehicle", className="card-title text-center"),
                                            html.P("Total Distance (km)", className="card-text text-center")
                                        ])
                                    ])
                                ], width=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H2(id="total-duration-vehicle", className="card-title text-center"),
                                            html.P("Total Duration (hrs)", className="card-text text-center")
                                        ])
                                    ])
                                ], width=3),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H2(id="breakdown-probability", className="card-title text-center"),
                                            html.P("Breakdown Probability", className="card-text text-center")
                                        ])
                                    ])
                                ], width=3)
                            ])
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Risk Level Distribution"),
                        dbc.CardBody([
                            dcc.Graph(id="risk-levels-vehicle-chart")
                        ])
                    ])
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Vehicle Details"),
                        dbc.CardBody([
                            html.Div(id="vehicle-details")
                        ])
                    ])
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Fuel Level Trend"),
                        dbc.CardBody([
                            dcc.Graph(id="fuel-level-chart")
                        ])
                    ])
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Engine Temperature Trend"),
                        dbc.CardBody([
                            dcc.Graph(id="engine-temp-chart")
                        ])
                    ])
                ], width=6)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Vehicle Location & Recent Routes"),
                        dbc.CardBody([
                            html.Div(id="vehicle-map-container", style={"height": "500px"})
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Recent Routes"),
                        dbc.CardBody([
                            html.Div(id="vehicle-recent-routes-table")
                        ])
                    ])
                ], width=12)
            ]),
            
            dcc.Interval(
                id='vehicle-interval-component',
                interval=60*1000,  # in milliseconds (60 seconds)
                n_intervals=0
            ),
            
            # Store for vehicle analysis data
            dcc.Store(id="vehicle-analysis-data"),
            
            # Store for vehicle list
            dcc.Store(id="vehicle-list-data")
        ], width=12)
    ])
], fluid=True)

def setup_vehicle_analysis_callbacks(app):
    """Setup callbacks for the vehicle analysis dashboard"""
    
    @app.callback(
        Output("vehicle-list-data", "data"),
        [
            Input("vehicle-refresh-button", "n_clicks"),
            Input("vehicle-interval-component", "n_intervals")
        ]
    )
    def fetch_vehicle_list(n_clicks, n_intervals):
        """Fetch vehicle list from backend API"""
        try:
            # Get vehicles list
            response = get_api_data("/api/vehicles/", use_session=True, raw_response=True)
            
            if response and response.status_code == 200:
                return response.json().get("vehicles", [])
            return []
        except Exception as e:
            print(f"Error fetching vehicle list: {str(e)}")
            return []
    
    @app.callback(
        Output("vehicle-dropdown", "options"),
        [Input("vehicle-list-data", "data")]
    )
    def update_vehicle_dropdown(vehicles):
        """Update vehicle dropdown options"""
        if not vehicles:
            return []
        
        options = []
        for vehicle in vehicles:
            vehicle_name = f"{vehicle.get('name', 'Vehicle')} ({vehicle.get('make', '')} {vehicle.get('model', '')})"
            options.append({
                "label": vehicle_name,
                "value": vehicle.get("_id", "")
            })
        
        return options
    
    @app.callback(
        Output("vehicle-analysis-data", "data"),
        [
            Input("vehicle-dropdown", "value"),
            Input("vehicle-refresh-button", "n_clicks"),
            Input("vehicle-interval-component", "n_intervals")
        ],
        [State("vehicle-analysis-data", "data")]
    )
    def fetch_vehicle_analysis_data(vehicle_id, n_clicks, n_intervals, current_data):
        """Fetch vehicle analysis data from backend API"""
        if not vehicle_id:
            return {}
        
        try:
            # Get vehicle analysis data
            response = get_api_data(f"/api/dashboard/vehicle-analysis", use_session=True, raw_response=True)
            
            if response and response.status_code == 200:
                all_data = response.json().get("vehicle_analysis", [])
                
                # Find data for selected vehicle
                for vehicle_data in all_data:
                    if vehicle_data.get("vehicle", {}).get("_id") == vehicle_id:
                        return vehicle_data
                
                return {}
            return current_data or {}
        except Exception as e:
            print(f"Error fetching vehicle analysis data: {str(e)}")
            return current_data or {}
    
    @app.callback(
        [
            Output("vehicle-last-update-timestamp", "children"),
            Output("total-routes-vehicle", "children"),
            Output("total-distance-vehicle", "children"),
            Output("total-duration-vehicle", "children"),
            Output("breakdown-probability", "children"),
            Output("risk-levels-vehicle-chart", "figure"),
            Output("vehicle-details", "children"),
            Output("fuel-level-chart", "figure"),
            Output("engine-temp-chart", "figure"),
            Output("vehicle-map-container", "children"),
            Output("vehicle-recent-routes-table", "children")
        ],
        [Input("vehicle-analysis-data", "data")]
    )
    def update_vehicle_analysis_dashboard(data):
        if not data:
            return (
                "No data available",
                "0", "0", "0", "0%",
                go.Figure(),
                html.Div("Please select a vehicle"),
                go.Figure(),
                go.Figure(),
                html.Div("No map data available"),
                html.Div("No routes data available")
            )
        
        # Create timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp_text = f"{now}"
        
        # Extract data
        vehicle = data.get("vehicle", {})
        stats = data.get("stats", {})
        telemetry = data.get("telemetry", {})
        recent_routes = data.get("recent_routes", [])
        
        # Format vehicle stats
        total_routes = stats.get("total_routes", 0)
        total_distance = stats.get("total_distance", 0)
        total_duration = stats.get("total_duration", 0)
        breakdown_probability = f"{stats.get('breakdown_probability', 0)}%"
        
        # Create Risk Levels Pie Chart
        risk_levels = stats.get("risk_levels", {})
        if risk_levels:
            risk_df = pd.DataFrame({
                "Risk Level": ["High", "Medium", "Low"],
                "Count": [
                    risk_levels.get("high", 0),
                    risk_levels.get("medium", 0),
                    risk_levels.get("low", 0)
                ]
            })
            
            # Map risk levels to colors
            colors = {
                "High": "#FF5252",
                "Medium": "#FFC107",
                "Low": "#4CAF50"
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
        
        # Create Vehicle Details Card
        vehicle_details = html.Div([
            dbc.Row([
                dbc.Col([
                    html.P([html.Strong("Name: "), vehicle.get("name", "N/A")]),
                    html.P([html.Strong("Make: "), vehicle.get("make", "N/A")]),
                    html.P([html.Strong("Model: "), vehicle.get("model", "N/A")]),
                    html.P([html.Strong("Year: "), str(vehicle.get("year", "N/A"))]),
                    html.P([html.Strong("Registration: "), vehicle.get("registration", "N/A")])
                ], width=6),
                dbc.Col([
                    html.P([html.Strong("Fuel Type: "), vehicle.get("fuel_type", "N/A")]),
                    html.P([html.Strong("Tank Capacity: "), f"{vehicle.get('tank_capacity', 'N/A')} liters"]),
                    html.P([html.Strong("Average Mileage: "), f"{vehicle.get('average_mileage', 'N/A')} km/l"]),
                    html.P([html.Strong("Last Service: "), 
                           vehicle.get("maintenance", {}).get("last_service_date", "N/A")]),
                    html.P([html.Strong("Next Service: "), 
                           vehicle.get("maintenance", {}).get("next_service_date", "N/A")])
                ], width=6)
            ])
        ])
        
        # Create Fuel Level Chart
        fuel_data = telemetry.get("fuel_data", [])
        if fuel_data:
            # Convert to DataFrame
            fuel_df = pd.DataFrame(fuel_data)
            
            # Add datetime object for better formatting
            if "timestamp" in fuel_df.columns:
                fuel_df["datetime"] = pd.to_datetime(fuel_df["timestamp"])
                fuel_df = fuel_df.sort_values("datetime")
                
                # Create figure
                fuel_fig = px.line(
                    fuel_df, 
                    x="datetime", 
                    y="fuel_level",
                    title="Fuel Level Trend",
                    labels={"datetime": "Date", "fuel_level": "Fuel Level (%)"}
                )
                
                fuel_fig.update_layout(
                    margin=dict(l=40, r=40, t=50, b=40),
                    hovermode="closest"
                )
                
                # Add reference line for low fuel
                fuel_fig.add_shape(
                    type="line",
                    x0=fuel_df["datetime"].min(),
                    x1=fuel_df["datetime"].max(),
                    y0=20,
                    y1=20,
                    line=dict(color="red", width=2, dash="dash")
                )
                
                # Add annotation for low fuel
                fuel_fig.add_annotation(
                    x=fuel_df["datetime"].max(),
                    y=20,
                    text="Low Fuel",
                    showarrow=False,
                    yshift=10,
                    font=dict(color="red")
                )
            else:
                fuel_fig = go.Figure()
        else:
            fuel_fig = go.Figure()
        
        # Create Engine Temperature Chart
        engine_temp_data = telemetry.get("engine_temp_data", [])
        if engine_temp_data:
            # Convert to DataFrame
            temp_df = pd.DataFrame(engine_temp_data)
            
            # Add datetime object for better formatting
            if "timestamp" in temp_df.columns:
                temp_df["datetime"] = pd.to_datetime(temp_df["timestamp"])
                temp_df = temp_df.sort_values("datetime")
                
                # Create figure
                temp_fig = px.line(
                    temp_df, 
                    x="datetime", 
                    y="engine_temp",
                    title="Engine Temperature Trend",
                    labels={"datetime": "Date", "engine_temp": "Engine Temp (°C)"}
                )
                
                temp_fig.update_layout(
                    margin=dict(l=40, r=40, t=50, b=40),
                    hovermode="closest"
                )
                
                # Add reference line for high temperature
                temp_fig.add_shape(
                    type="line",
                    x0=temp_df["datetime"].min(),
                    x1=temp_df["datetime"].max(),
                    y0=110,
                    y1=110,
                    line=dict(color="red", width=2, dash="dash")
                )
                
                # Add annotation for high temperature
                temp_fig.add_annotation(
                    x=temp_df["datetime"].max(),
                    y=110,
                    text="High Temp",
                    showarrow=False,
                    yshift=10,
                    font=dict(color="red")
                )
            else:
                temp_fig = go.Figure()
        else:
            temp_fig = go.Figure()
        
        # Create Vehicle Map with Routes
        if recent_routes:
            # Create map layers
            map_layers = []
            
            # Add vehicle marker if telemetry has location
            latest_telemetry = telemetry.get("fuel_data", [])
            if latest_telemetry and len(latest_telemetry) > 0:
                last_record = latest_telemetry[0]  # Assume sorted by timestamp desc
                if "location" in last_record:
                    location = last_record["location"]
                    
                    # Create popup content
                    popup_content = f"""
                    <strong>{vehicle.get('name', 'Vehicle')}</strong><br>
                    Make: {vehicle.get('make', 'N/A')}<br>
                    Model: {vehicle.get('model', 'N/A')}<br>
                    Fuel: {last_record.get('fuel_level', 'N/A')}%<br>
                    Engine Temp: {last_record.get('engine_temp', 'N/A')}°C
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
                        ],
                        icon={
                            "iconUrl": "/static/img/car-marker.png",
                            "iconSize": [32, 32],
                            "iconAnchor": [16, 16]
                        }
                    )
                    
                    map_layers.append(marker)
            
            # Add route polylines
            center = None
            for route in recent_routes:
                if route.get("polyline"):
                    try:
                        # Use polyline library to decode
                        import polyline
                        points = polyline.decode(route["polyline"])
                        
                        # Set center to first route's midpoint if not set yet
                        if center is None and points:
                            mid_idx = len(points) // 2
                            center = points[mid_idx]
                        
                        # Create polyline with color based on risk level
                        risk_level = route.get("risk_level", "unknown")
                        color = get_risk_color(risk_level)
                        
                        route_line = dl.Polyline(
                            positions=[(p[0], p[1]) for p in points],
                            color=color,
                            weight=4,
                            opacity=0.7,
                            children=[
                                dl.Tooltip(f"Route: {route.get('name', 'Route')}, Risk: {risk_level.title()}")
                            ]
                        )
                        
                        map_layers.append(route_line)
                        
                        # Add markers for origin and destination
                        if "origin" in route and "destination" in route:
                            origin = route["origin"]
                            destination = route["destination"]
                            
                            # Origin marker
                            origin_marker = dl.Marker(
                                position=[origin.get("lat", 0), origin.get("lng", 0)],
                                children=[
                                    dl.Tooltip("Origin: " + origin.get("address", ""))
                                ],
                                icon={
                                    "iconUrl": "/static/img/start-marker.png",
                                    "iconSize": [24, 24],
                                    "iconAnchor": [12, 12]
                                }
                            )
                            
                            # Destination marker
                            dest_marker = dl.Marker(
                                position=[destination.get("lat", 0), destination.get("lng", 0)],
                                children=[
                                    dl.Tooltip("Destination: " + destination.get("address", ""))
                                ],
                                icon={
                                    "iconUrl": "/static/img/end-marker.png",
                                    "iconSize": [24, 24],
                                    "iconAnchor": [12, 12]
                                }
                            )
                            
                            map_layers.append(origin_marker)
                            map_layers.append(dest_marker)
                    except Exception as e:
                        print(f"Error processing route polyline: {str(e)}")
            
            # Create map
            vehicle_map = make_map(map_layers, center=center, zoom=10 if center else 3)
        else:
            vehicle_map = make_map([], zoom=3)
        
        # Create Recent Routes Table
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
        
        return (
            timestamp_text,
            str(total_routes),
            str(total_distance),
            str(total_duration),
            breakdown_probability,
            risk_fig,
            vehicle_details,
            fuel_fig,
            temp_fig,
            vehicle_map,
            routes_table
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