"""
Streamlit Dashboard for AI Invoice Processing Agent
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime, timedelta
import json
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="AI Invoice Processing Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    .status-processing {
        color: #ffc107;
        font-weight: bold;
    }
    .status-pending {
        color: #6c757d;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = "http://localhost:8000"
REFRESH_INTERVAL = 5  # seconds


@st.cache_data(ttl=30)
def fetch_api_data(endpoint: str):
    """Fetch data from API with caching"""
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: {str(e)}")
        return None


def get_status_color(status: str) -> str:
    """Get color for status"""
    colors = {
        "success": "#28a745",
        "failed": "#dc3545",
        "processing": "#ffc107",
        "pending": "#6c757d"
    }
    return colors.get(status.lower(), "#6c757d")


def format_status(status: str) -> str:
    """Format status with color"""
    color = get_status_color(status)
    return f'<span style="color: {color}; font-weight: bold;">{status.upper()}</span>'


def main():
    """Main dashboard function"""
    
    # Header
    st.markdown('<h1 class="main-header">🤖 AI Invoice Processing Dashboard</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto Refresh", value=True)
        
        if auto_refresh:
            refresh_rate = st.selectbox(
                "Refresh Rate (seconds)",
                [5, 10, 30, 60],
                index=0
            )
        
        st.divider()
        
        # Manual actions
        st.header("🔧 Actions")
        
        if st.button("🔄 Refresh Now"):
            st.cache_data.clear()
            st.rerun()
        
        if st.button("▶️ Trigger Processing"):
            try:
                response = requests.post(f"{API_BASE_URL}/process")
                if response.status_code == 200:
                    st.success("Processing triggered successfully!")
                else:
                    st.error("Failed to trigger processing")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        st.divider()
        
        # File upload
        st.header("📁 Upload Invoice")
        uploaded_file = st.file_uploader(
            "Choose an invoice file",
            type=['jpg', 'jpeg', 'png', 'pdf', 'tiff'],
            help="Upload an invoice image for processing"
        )
        
        if uploaded_file is not None:
            if st.button("📤 Upload & Process"):
                try:
                    files = {"file": uploaded_file}
                    response = requests.post(f"{API_BASE_URL}/upload", files=files)
                    if response.status_code == 200:
                        st.success("File uploaded successfully!")
                        st.cache_data.clear()
                    else:
                        st.error("Failed to upload file")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Main content
    # System Status
    st.header("🏥 System Health")
    
    health_data = fetch_api_data("/")
    if health_data:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("System Status", health_data.get("status", "Unknown").title())
        
        with col2:
            st.metric("Version", health_data.get("version", "Unknown"))
        
        with col3:
            services = health_data.get("services", {})
            healthy_services = sum(1 for status in services.values() if status == "healthy")
            st.metric("Services", f"{healthy_services}/{len(services)} Healthy")
        
        with col4:
            timestamp = health_data.get("timestamp", "")
            if timestamp:
                last_check = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                st.metric("Last Check", last_check.strftime("%H:%M:%S"))
    
    st.divider()
    
    # Processing Statistics
    st.header("📊 Processing Statistics")
    
    stats_data = fetch_api_data("/stats")
    if stats_data:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Total Processed",
                stats_data.get("total_processed", 0),
                help="Total number of files processed"
            )
        
        with col2:
            st.metric(
                "Successful",
                stats_data.get("successful", 0),
                delta=stats_data.get("successful", 0),
                delta_color="normal",
                help="Successfully processed files"
            )
        
        with col3:
            st.metric(
                "Failed",
                stats_data.get("failed", 0),
                delta=stats_data.get("failed", 0),
                delta_color="inverse",
                help="Failed processing attempts"
            )
        
        with col4:
            st.metric(
                "Processing",
                stats_data.get("processing", 0),
                help="Currently processing files"
            )
        
        with col5:
            avg_time = stats_data.get("average_processing_time", 0)
            st.metric(
                "Avg Time",
                f"{avg_time:.2f}s",
                help="Average processing time per file"
            )
        
        # Success Rate Chart
        total = stats_data.get("total_processed", 0)
        if total > 0:
            success_rate = (stats_data.get("successful", 0) / total) * 100
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Pie chart for processing results
                labels = ['Successful', 'Failed']
                values = [stats_data.get("successful", 0), stats_data.get("failed", 0)]
                colors = ['#28a745', '#dc3545']
                
                fig = px.pie(
                    values=values,
                    names=labels,
                    title="Processing Results Distribution",
                    color_discrete_sequence=colors
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Success rate gauge
                fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=success_rate,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Success Rate"},
                    delta={'reference': 95},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 80], 'color': "yellow"},
                            {'range': [80, 100], 'color': "lightgreen"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ))
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Recent Processing Results
    st.header("📋 Recent Processing Results")
    
    results_data = fetch_api_data("/results?limit=20")
    if results_data and isinstance(results_data, list):
        if results_data:
            # Convert to DataFrame
            df = pd.DataFrame(results_data)
            
            # Format data for display
            display_df = df.copy()
            display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
            display_df['processing_time'] = display_df['processing_time'].apply(
                lambda x: f"{x:.2f}s" if pd.notna(x) else "N/A"
            )
            
            # Select columns for display
            columns_to_show = [
                'original_filename', 'status', 'processing_time', 
                'created_at', 'error_message'
            ]
            
            display_df = display_df[columns_to_show].fillna("")
            
            # Rename columns
            display_df.columns = [
                'Original File', 'Status', 'Processing Time', 
                'Created At', 'Error Message'
            ]
            
            # Style the dataframe
            def style_status(val):
                if val.lower() == 'success':
                    return 'color: #28a745; font-weight: bold'
                elif val.lower() == 'failed':
                    return 'color: #dc3545; font-weight: bold'
                elif val.lower() == 'processing':
                    return 'color: #ffc107; font-weight: bold'
                else:
                    return 'color: #6c757d; font-weight: bold'
            
            styled_df = display_df.style.applymap(style_status, subset=['Status'])
            
            st.dataframe(
                styled_df,
                use_container_width=True,
                height=400
            )
            
            # Download results as CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv,
                file_name=f"invoice_processing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No processing results available yet.")
    
    st.divider()
    
    # System Information
    with st.expander("🔍 System Information", expanded=False):
        status_data = fetch_api_data("/status")
        if status_data and status_data.get("success"):
            data = status_data.get("data", {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("System Settings")
                settings = data.get("settings", {})
                for key, value in settings.items():
                    st.text(f"{key.replace('_', ' ').title()}: {value}")
            
            with col2:
                st.subheader("Uptime")
                uptime = data.get("uptime", "Unknown")
                st.text(f"System Uptime: {uptime}")
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()


if __name__ == "__main__":
    main()

