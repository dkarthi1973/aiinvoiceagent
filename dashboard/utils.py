"""
Dashboard utilities and helper functions
"""
import streamlit as st
import requests
from typing import Dict, Any, Optional
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta


def create_metric_card(title: str, value: str, delta: Optional[str] = None, help_text: Optional[str] = None):
    """Create a styled metric card"""
    delta_html = f'<div style="color: #28a745; font-size: 0.8rem;">{delta}</div>' if delta else ""
    help_html = f'<div style="color: #6c757d; font-size: 0.7rem; margin-top: 0.5rem;">{help_text}</div>' if help_text else ""
    
    card_html = f"""
    <div class="metric-card">
        <div style="font-size: 0.8rem; color: #6c757d; margin-bottom: 0.5rem;">{title}</div>
        <div style="font-size: 1.5rem; font-weight: bold; color: #1f77b4;">{value}</div>
        {delta_html}
        {help_html}
    </div>
    """
    return card_html


def create_status_badge(status: str) -> str:
    """Create a colored status badge"""
    colors = {
        "success": "#28a745",
        "failed": "#dc3545", 
        "processing": "#ffc107",
        "pending": "#6c757d",
        "healthy": "#28a745",
        "unhealthy": "#dc3545"
    }
    
    color = colors.get(status.lower(), "#6c757d")
    return f'<span style="background-color: {color}; color: white; padding: 0.2rem 0.5rem; border-radius: 0.3rem; font-size: 0.8rem; font-weight: bold;">{status.upper()}</span>'


def create_processing_timeline_chart(results_data):
    """Create a timeline chart of processing results"""
    if not results_data:
        return None
    
    import pandas as pd
    
    df = pd.DataFrame(results_data)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['hour'] = df['created_at'].dt.floor('H')
    
    # Group by hour and status
    timeline_data = df.groupby(['hour', 'status']).size().reset_index(name='count')
    
    fig = px.bar(
        timeline_data,
        x='hour',
        y='count',
        color='status',
        title='Processing Activity Timeline',
        color_discrete_map={
            'success': '#28a745',
            'failed': '#dc3545',
            'processing': '#ffc107',
            'pending': '#6c757d'
        }
    )
    
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Number of Files",
        showlegend=True
    )
    
    return fig


def create_processing_time_chart(results_data):
    """Create a chart showing processing time distribution"""
    if not results_data:
        return None
    
    import pandas as pd
    
    df = pd.DataFrame(results_data)
    successful_results = df[df['status'] == 'success']
    
    if successful_results.empty:
        return None
    
    fig = px.histogram(
        successful_results,
        x='processing_time',
        title='Processing Time Distribution',
        nbins=20,
        labels={'processing_time': 'Processing Time (seconds)', 'count': 'Number of Files'}
    )
    
    fig.update_layout(
        xaxis_title="Processing Time (seconds)",
        yaxis_title="Number of Files",
        showlegend=False
    )
    
    return fig


def create_file_size_chart(results_data):
    """Create a chart showing file size vs processing time"""
    # This would require file size data to be included in results
    # For now, return None as placeholder
    return None


def format_uptime(uptime_str: str) -> str:
    """Format uptime string for better display"""
    try:
        # Parse uptime string and format nicely
        parts = uptime_str.split(', ')
        if len(parts) >= 2:
            days = parts[0]
            time_part = parts[1]
            return f"{days}, {time_part}"
        return uptime_str
    except:
        return uptime_str


def get_system_health_color(services: Dict[str, str]) -> str:
    """Get overall system health color based on services"""
    if not services:
        return "#6c757d"  # Gray for unknown
    
    healthy_count = sum(1 for status in services.values() if status == "healthy")
    total_count = len(services)
    
    if healthy_count == total_count:
        return "#28a745"  # Green for all healthy
    elif healthy_count > total_count / 2:
        return "#ffc107"  # Yellow for mostly healthy
    else:
        return "#dc3545"  # Red for mostly unhealthy


def create_error_analysis_chart(results_data):
    """Create a chart analyzing error types"""
    if not results_data:
        return None
    
    import pandas as pd
    
    df = pd.DataFrame(results_data)
    failed_results = df[df['status'] == 'failed']
    
    if failed_results.empty:
        return None
    
    # Extract error types from error messages
    error_types = []
    for error_msg in failed_results['error_message'].fillna('Unknown Error'):
        if 'timeout' in error_msg.lower():
            error_types.append('Timeout')
        elif 'format' in error_msg.lower() or 'unsupported' in error_msg.lower():
            error_types.append('Format Error')
        elif 'size' in error_msg.lower():
            error_types.append('File Size')
        elif 'json' in error_msg.lower() or 'parse' in error_msg.lower():
            error_types.append('Parsing Error')
        else:
            error_types.append('Other')
    
    error_df = pd.DataFrame({'error_type': error_types})
    error_counts = error_df['error_type'].value_counts()
    
    fig = px.pie(
        values=error_counts.values,
        names=error_counts.index,
        title='Error Types Distribution'
    )
    
    return fig


@st.cache_data(ttl=60)
def get_folder_stats():
    """Get statistics about incoming and generated folders"""
    try:
        from pathlib import Path
        import os
        
        # This would need to be configured based on actual folder paths
        incoming_path = Path("./incoming")
        generated_path = Path("./generated")
        
        stats = {
            "incoming_files": 0,
            "generated_files": 0,
            "incoming_size_mb": 0,
            "generated_size_mb": 0
        }
        
        if incoming_path.exists():
            incoming_files = list(incoming_path.glob("*"))
            stats["incoming_files"] = len([f for f in incoming_files if f.is_file()])
            stats["incoming_size_mb"] = sum(f.stat().st_size for f in incoming_files if f.is_file()) / (1024 * 1024)
        
        if generated_path.exists():
            generated_files = list(generated_path.glob("*"))
            stats["generated_files"] = len([f for f in generated_files if f.is_file()])
            stats["generated_size_mb"] = sum(f.stat().st_size for f in generated_files if f.is_file()) / (1024 * 1024)
        
        return stats
    except Exception:
        return {
            "incoming_files": 0,
            "generated_files": 0,
            "incoming_size_mb": 0,
            "generated_size_mb": 0
        }

