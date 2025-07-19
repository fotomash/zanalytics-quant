"""
🔧 ZANFLOW Strategy Editor - Interactive Command Center
Transform your dashboard into a true command center for strategy management
"""

import streamlit as st
import requests
import yaml
import json
from datetime import datetime
import pandas as pd
from typing import Dict, Any, List

# Page config
st.set_page_config(
    page_title="Strategy Editor - ZANFLOW",
    page_icon="🔧",
    layout="wide"
)

# Configuration
API_BASE_URL = st.secrets.get("API_BASE_URL", "http://localhost:5010")

# Custom CSS for better UI
st.markdown("""
<style>
    .strategy-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .success-message {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
    }
    .error-message {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
    }
    .parameter-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("⚙️ ZANFLOW Strategy Editor")
st.markdown("""
Welcome to the **Interactive Command Center**. Here you can:
- 📋 View all available trading strategies
- ✏️ Edit strategy configurations in real-time
- 💾 Save changes with automatic backup
- 🔄 Reload strategies into the live system
- 📊 Validate configurations before deployment
""")

# Initialize session state
if 'selected_strategy' not in st.session_state:
    st.session_state.selected_strategy = None
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = 'visual'  # 'visual' or 'yaml'
if 'unsaved_changes' not in st.session_state:
    st.session_state.unsaved_changes = False

# Sidebar for strategy selection
with st.sidebar:
    st.header("📁 Strategy Selection")

    # Fetch strategies
    try:
        response = requests.get(f"{API_BASE_URL}/strategies")
        response.raise_for_status()
        strategies_list = response.json()

        if strategies_list:
            # Create strategy selector
            strategy_options = {s['id']: f"{s['name']} ({s['status']})" for s in strategies_list}

            selected_id = st.selectbox(
                "Select a Strategy",
                options=list(strategy_options.keys()),
                format_func=lambda x: strategy_options[x],
                key="strategy_selector"
            )

            # Display strategy info
            selected_strategy = next((s for s in strategies_list if s['id'] == selected_id), None)
            if selected_strategy:
                st.markdown("### 📊 Strategy Info")
                st.markdown(f"**Name:** {selected_strategy['name']}")
                st.markdown(f"**Status:** {selected_strategy['status']}")
                st.markdown(f"**Last Modified:** {selected_strategy['last_modified'][:10]}")

                if st.button("🔄 Refresh", key="refresh_list"):
                    st.rerun()
        else:
            st.warning("No strategies found")
            selected_id = None

    except requests.exceptions.RequestException as e:
        st.error(f"Could not connect to API: {e}")
        selected_id = None

    # Create new strategy button
    st.markdown("---")
    if st.button("➕ Create New Strategy", key="create_new"):
        st.session_state.show_create_dialog = True

# Main content area
if selected_id:
    # Fetch full strategy configuration
    try:
        config_response = requests.get(f"{API_BASE_URL}/strategies/{selected_id}")
        config_response.raise_for_status()
        config_data = config_response.json()

        # Remove metadata for editing
        metadata = config_data.pop('_metadata', {})

        # Header with edit mode toggle
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.header(f"📝 Editing: {config_data.get('strategy_name', 'Unknown')}")
        with col2:
            edit_mode = st.radio(
                "Edit Mode",
                ["Visual", "YAML"],
                horizontal=True,
                key="edit_mode_toggle"
            )
            st.session_state.edit_mode = edit_mode.lower()
        with col3:
            if st.button("📋 View Backups", key="view_backups"):
                st.session_state.show_backups = True

        # Visual Editor Mode
        if st.session_state.edit_mode == 'visual':
            # Create tabs for different sections
            tabs = st.tabs(["🎯 Basic Info", "📊 Entry Conditions", "🚪 Exit Conditions", 
                           "💰 Risk Management", "⚙️ Parameters", "🔧 Advanced"])

            # Tab 1: Basic Info
            with tabs[0]:
                col1, col2 = st.columns(2)
                with col1:
                    config_data['strategy_name'] = st.text_input(
                        "Strategy Name",
                        value=config_data.get('strategy_name', ''),
                        key="strategy_name"
                    )
                    config_data['description'] = st.text_area(
                        "Description",
                        value=config_data.get('description', ''),
                        key="description",
                        height=100
                    )
                with col2:
                    config_data['status'] = st.selectbox(
                        "Status",
                        options=['active', 'inactive', 'testing', 'deprecated'],
                        index=['active', 'inactive', 'testing', 'deprecated'].index(
                            config_data.get('status', 'active')
                        ),
                        key="status"
                    )

                    # Timeframes
                    all_timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1']
                    selected_timeframes = st.multiselect(
                        "Timeframes",
                        options=all_timeframes,
                        default=config_data.get('timeframes', ['H1']),
                        key="timeframes"
                    )
                    config_data['timeframes'] = selected_timeframes

            # Tab 2: Entry Conditions
            with tabs[1]:
                st.subheader("Entry Conditions")

                # Primary conditions
                st.markdown("**Primary Conditions**")
                primary_conditions = config_data.get('entry_conditions', {}).get('primary', [])

                # Add/remove primary conditions
                col1, col2 = st.columns([3, 1])
                with col1:
                    new_primary = st.text_input("Add Primary Condition", key="new_primary")
                with col2:
                    if st.button("➕ Add", key="add_primary"):
                        if new_primary and new_primary not in primary_conditions:
                            primary_conditions.append(new_primary)

                # Display and manage primary conditions
                for i, condition in enumerate(primary_conditions):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.text(condition)
                    with col2:
                        if st.button("❌", key=f"remove_primary_{i}"):
                            primary_conditions.pop(i)
                            st.rerun()

                # Confirmations
                st.markdown("**Confirmation Conditions**")
                confirmations = config_data.get('entry_conditions', {}).get('confirmations', [])

                # Similar UI for confirmations...
                config_data.setdefault('entry_conditions', {})['primary'] = primary_conditions
                config_data['entry_conditions']['confirmations'] = confirmations

            # Tab 3: Exit Conditions
            with tabs[2]:
                st.subheader("Exit Conditions")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Take Profit**")
                    tp_type = st.selectbox(
                        "Type",
                        ['fixed', 'atr', 'percentage'],
                        key="tp_type"
                    )
                    tp_value = st.number_input(
                        "Value",
                        value=config_data.get('exit_conditions', {}).get('take_profit', {}).get('value', 50),
                        key="tp_value"
                    )

                with col2:
                    st.markdown("**Stop Loss**")
                    sl_type = st.selectbox(
                        "Type",
                        ['fixed', 'atr', 'percentage'],
                        key="sl_type"
                    )
                    sl_value = st.number_input(
                        "Value",
                        value=config_data.get('exit_conditions', {}).get('stop_loss', {}).get('value', 25),
                        key="sl_value"
                    )

                config_data.setdefault('exit_conditions', {})
                config_data['exit_conditions']['take_profit'] = {'type': tp_type, 'value': tp_value}
                config_data['exit_conditions']['stop_loss'] = {'type': sl_type, 'value': sl_value}

            # Tab 4: Risk Management
            with tabs[3]:
                st.subheader("Risk Management")

                col1, col2 = st.columns(2)
                with col1:
                    position_size = st.number_input(
                        "Position Size",
                        min_value=0.01,
                        max_value=1.0,
                        value=config_data.get('risk_management', {}).get('position_size', 0.01),
                        step=0.01,
                        key="position_size"
                    )
                    max_positions = st.number_input(
                        "Max Positions",
                        min_value=1,
                        max_value=10,
                        value=config_data.get('risk_management', {}).get('max_positions', 1),
                        key="max_positions"
                    )

                with col2:
                    max_daily_loss = st.number_input(
                        "Max Daily Loss (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=config_data.get('risk_management', {}).get('max_daily_loss', 5.0),
                        step=0.5,
                        key="max_daily_loss"
                    )
                    max_drawdown = st.number_input(
                        "Max Drawdown (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=config_data.get('risk_management', {}).get('max_drawdown', 10.0),
                        step=0.5,
                        key="max_drawdown"
                    )

                config_data.setdefault('risk_management', {})
                config_data['risk_management']['position_size'] = position_size
                config_data['risk_management']['max_positions'] = max_positions
                config_data['risk_management']['max_daily_loss'] = max_daily_loss
                config_data['risk_management']['max_drawdown'] = max_drawdown

            # Tab 5: Parameters
            with tabs[4]:
                st.subheader("Strategy Parameters")

                # Dynamic parameter editor
                params = config_data.get('parameters', {})

                # Add new parameter
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    new_param_name = st.text_input("Parameter Name", key="new_param_name")
                with col2:
                    new_param_value = st.number_input("Value", key="new_param_value")
                with col3:
                    if st.button("➕ Add Parameter", key="add_param"):
                        if new_param_name:
                            params[new_param_name] = new_param_value

                # Edit existing parameters
                if params:
                    st.markdown("**Current Parameters**")
                    param_cols = st.columns(2)
                    for i, (param_name, param_value) in enumerate(params.items()):
                        with param_cols[i % 2]:
                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                st.text(param_name)
                            with col2:
                                params[param_name] = st.number_input(
                                    "Value",
                                    value=param_value,
                                    key=f"param_{param_name}",
                                    label_visibility="collapsed"
                                )
                            with col3:
                                if st.button("❌", key=f"remove_param_{param_name}"):
                                    del params[param_name]
                                    st.rerun()

                config_data['parameters'] = params

            # Tab 6: Advanced
            with tabs[5]:
                st.subheader("Advanced Configuration")

                # Show raw YAML for advanced editing
                advanced_yaml = st.text_area(
                    "Additional Configuration (YAML)",
                    value=yaml.dump(
                        {k: v for k, v in config_data.items() 
                         if k not in ['strategy_name', 'description', 'status', 'timeframes',
                                     'entry_conditions', 'exit_conditions', 'risk_management', 'parameters']},
                        indent=2
                    ),
                    height=300,
                    key="advanced_yaml"
                )

                # Parse and merge advanced config
                try:
                    advanced_config = yaml.safe_load(advanced_yaml) or {}
                    config_data.update(advanced_config)
                except yaml.YAMLError as e:
                    st.error(f"Invalid YAML in advanced configuration: {e}")

        # YAML Editor Mode
        else:
            st.markdown("### 📝 YAML Editor")

            # Direct YAML editing
            edited_yaml_str = st.text_area(
                "Strategy Configuration (YAML)",
                value=yaml.dump(config_data, indent=2, sort_keys=False),
                height=600,
                key="yaml_editor"
            )

            # Parse edited YAML
            try:
                config_data = yaml.safe_load(edited_yaml_str)
                st.success("✅ Valid YAML format")
            except yaml.YAMLError as e:
                st.error(f"❌ Invalid YAML format: {e}")
                config_data = None

        # Action buttons
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("✅ Validate", key="validate_btn", type="secondary"):
                if config_data:
                    # Validate configuration
                    try:
                        validate_response = requests.post(
                            f"{API_BASE_URL}/strategies/{selected_id}/validate",
                            json=config_data
                        )
                        validate_response.raise_for_status()
                        result = validate_response.json()

                        if result['valid']:
                            st.success("✅ Configuration is valid!")
                        else:
                            st.error("❌ Configuration has errors:")
                            for error in result['errors']:
                                st.error(f"  • {error}")

                        if result.get('warnings'):
                            st.warning("⚠️ Warnings:")
                            for warning in result['warnings']:
                                st.warning(f"  • {warning}")

                    except requests.exceptions.RequestException as e:
                        st.error(f"Validation failed: {e}")

        with col2:
            if st.button("💾 Save Changes", key="save_btn", type="primary"):
                if config_data:
                    # Save configuration
                    with st.spinner("Saving strategy..."):
                        try:
                            save_response = requests.post(
                                f"{API_BASE_URL}/strategies/{selected_id}",
                                json=config_data
                            )
                            save_response.raise_for_status()
                            result = save_response.json()

                            st.success(f"✅ {result['message']}")
                            st.info(f"📁 Backup created: {result['backup']}")
                            if 'reload_command' in result:
                                st.info(f"🔄 Reload command queued: {result['reload_command']}")

                            st.session_state.unsaved_changes = False

                        except requests.exceptions.RequestException as e:
                            st.error(f"Failed to save: {e}")

        with col3:
            if st.button("🔄 Reload Original", key="reload_btn"):
                st.rerun()

        with col4:
            if st.button("📤 Export", key="export_btn"):
                # Export configuration
                st.download_button(
                    label="📥 Download YAML",
                    data=yaml.dump(config_data, indent=2, sort_keys=False),
                    file_name=f"{selected_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yml",
                    mime="text/yaml"
                )

    except requests.exceptions.RequestException as e:
        st.error(f"Could not load strategy: {e}")

else:
    # No strategy selected
    st.info("👈 Select a strategy from the sidebar to begin editing")

# Backup viewer dialog
if 'show_backups' in st.session_state and st.session_state.show_backups:
    with st.expander("📋 Strategy Backups", expanded=True):
        try:
            backups_response = requests.get(f"{API_BASE_URL}/strategies/{selected_id}/backups")
            backups_response.raise_for_status()
            backups = backups_response.json()

            if backups:
                # Display backups in a table
                backup_df = pd.DataFrame(backups)
                st.dataframe(backup_df, use_container_width=True)

                # Restore option
                selected_backup = st.selectbox(
                    "Select backup to restore",
                    options=[b['filename'] for b in backups],
                    key="backup_selector"
                )

                if st.button("🔄 Restore Selected Backup", key="restore_backup"):
                    try:
                        restore_response = requests.post(
                            f"{API_BASE_URL}/strategies/{selected_id}/restore/{selected_backup}"
                        )
                        restore_response.raise_for_status()
                        result = restore_response.json()
                        st.success(f"✅ {result['message']}")
                        st.rerun()
                    except requests.exceptions.RequestException as e:
                        st.error(f"Failed to restore: {e}")
            else:
                st.info("No backups available for this strategy")

        except requests.exceptions.RequestException as e:
            st.error(f"Could not load backups: {e}")

        if st.button("Close", key="close_backups"):
            st.session_state.show_backups = False
            st.rerun()

# Create new strategy dialog
if 'show_create_dialog' in st.session_state and st.session_state.show_create_dialog:
    with st.expander("➕ Create New Strategy", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            new_name = st.text_input("Strategy Name", key="new_strategy_name")
            template = st.selectbox(
                "Template",
                options=['default', 'scalping', 'swing', 'breakout'],
                key="new_strategy_template"
            )

        with col2:
            if st.button("✅ Create", key="create_strategy"):
                if new_name:
                    try:
                        create_response = requests.post(
                            f"{API_BASE_URL}/strategies/create",
                            json={'name': new_name, 'template': template}
                        )
                        create_response.raise_for_status()
                        result = create_response.json()
                        st.success(f"✅ {result['message']}")
                        st.session_state.show_create_dialog = False
                        st.rerun()
                    except requests.exceptions.RequestException as e:
                        st.error(f"Failed to create: {e}")
                else:
                    st.error("Please enter a strategy name")

            if st.button("❌ Cancel", key="cancel_create"):
                st.session_state.show_create_dialog = False
                st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    🚀 ZANFLOW Command Center | Strategy Editor v2.0 | 
    <a href='#' target='_blank'>Documentation</a> | 
    <a href='#' target='_blank'>Help</a>
</div>
""", unsafe_allow_html=True)
