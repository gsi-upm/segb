import streamlit as st
import requests
import os
from datetime import datetime
import streamlit.components.v1 as components
from streamlit.components.v1 import declare_component
from graph_utils import generate_modification_graph_pyvis, generate_ttl_graph_pyvis
from rdflib import Graph as RDFGraph
from collections import defaultdict



API_URL = os.getenv("API_URL", "http://amor-segb:5000") 

# App Style
st.set_page_config(page_title="Graph Manager", layout="wide")
st.markdown("""
    <style>
    body::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url('https://img.pikbest.com/backgrounds/20190131/technology-blue-line-dot-matrix-banner-background_1859516.jpg!bwr800');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        opacity: 0.85; /* transparency */
        z-index: -9999; /* at the back */
    }

    .stApp {
        background: transparent;
    }
    .main {
        background-color: rgba(230, 240, 255, 0.85) !important;
        padding: 20px;
        border-radius: 10px;
        backdrop-filter: blur(5px);
        max-width: 500px;
        margin: auto;
    }
    .login-btn {
        position: absolute;
        bottom: 10px;
        right: 10px;
    }

    .section-button {
        font-size: 1.2rem;
        padding: 15px 25px;
        margin-bottom: 10px;
        width: 100%;
        text-align: center;
    }
            
    .stAlert {
        background-color: #ffffff !important;
        opacity: 1 !important;
        color: #000000 !important;
        border: 2px solid #ddd !important;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.2) !important;
        padding: 10px !important;
        border-radius: 8px !important;
    }
    
    .stAlert-success {
        background-color: #d4edda !important;
        color: #155724 !important;
        border-color: #c3e6cb !important;
    }

    .stAlert-error {
        background-color: #f8d7da !important;
        color: #721c24 !important;
        border-color: #f5c6cb !important;
    }

    .stAlert-warning {
        background-color: #fff3cd !important;
        color: #856404 !important;
        border-color: #ffeeba !important;
    }

    .stAlert-info {
        background-color: #cce5ff !important;
        color: #004085 !important;
        border-color: #b8daff !important;
    }
            
    label {
        color: white !important;
    }
            
    /* Forcing checkbox label color to white */
    .stCheckbox > div > label {
        color: white !important;
        font-weight: bold;
    }
                      
    .footer-logo {
        position: fixed;
        bottom: 10px;
        right: 80px;
        z-index: 9999;
    }
    .app-header {
        background-color: #00a9e0;
        padding: 10px 20px;
        font-size: 24px;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 3px solid #005599;
    }
    .app-header span {
        color: #00629b;
    }
    .app-header img {
        height: 40px;
    }           

    .bottom-left-buttons {
        position: fixed;
        bottom: 10px;
        left: 5rem;
        display: flex;
        flex-direction: column;
        gap: 8px;
        z-index: 9999;
    }

    .info-button {
        background-color: #00a9e0;
        color: black;
        padding: 8px 12px;
        text-decoration: none;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        font-size: 25px;
        text-align: center;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
        transition: background-color 0.2s ease;
        cursor: pointer;
    }

    .info-button:hover {
        background-color: #76caff;
    }           

    </style>
    <div class="footer-logo">
        <img src='https://www.gsi.upm.es/images/logos/gsi.png' style="max-width:100px; max-height:100px;">
    </div>   
    <div class="app-header">
        <span>SEGB Knowledge Hub</span>
        <img src='https://gsi.upm.es/images/projects/logo_amor_azulupm.png' style="max-height: 40px;">
    </div>  
    <div class="bottom-left-buttons">
        <a href="https://segb.readthedocs.io/en/latest/index.html" target="_blank" class="info-button" title="More information">𝒊</a>
        <a href="https://www.gsi.upm.es/es/component/jresearch/?view=member&task=show&id=347" target="_blank" class="info-button" title="Contact">✆</a>
    </div>
                 
    """, unsafe_allow_html=True)


# Session State
if "token" not in st.session_state:

    st.session_state.token = None

if "section" not in st.session_state:
    st.session_state.section = None



# -- Auth Section --
if not st.session_state.token:
    st.markdown("""
    <h1 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        🔐 Login
    </h1>
    """, unsafe_allow_html=True)

    token = st.text_input("Enter your token", type="password")

    cols = st.columns([4, 1.5])    
    with cols[1]:  # Right column
        login = st.button("Login", use_container_width=True)

    if login:
        if token:
            st.session_state.token = token
            headers = {"Authorization": f"Bearer {token}"}
            st.rerun()
        else:
            st.error("Please enter your token.")

    st.stop()

selected_node = st.query_params.get("selected_node")
if isinstance(selected_node, list):
    selected_node = selected_node[0]


if selected_node and st.session_state.section != "mods":
    st.session_state.section = "mods"
    st.session_state.selected_node = selected_node
    st.rerun()

if not st.session_state.section:
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        Insight Access
    </h2>
    """, unsafe_allow_html=True)
    st.markdown("<h4 style='color: #FFFFFF;'> Choose a section </h2>", unsafe_allow_html=True)

    cols = st.columns(2)
    with cols[0]:
        if st.button("➕ Insert Semantic Log", key='insert_btn', help='Insert new Semantic Log into the Knowledge Graph. Allowed for LOGGER and ADMIN.', use_container_width=True):
            st.session_state.section = "insert"
        if st.button("❓ Run SPARQL Query", key='query_btn', help='Run custom SPARQL query to access the Knowledge Graph. Allowed for ADMIN.', use_container_width=True):
            st.session_state.section = "query"
        if st.button("🗑️ Delete All Semantic Logs", key='delete_btn', help='Delete all Semantic Logs in the Knowledge Graph. Allowed for ADMIN. ', use_container_width=True):
            st.session_state.section = "delete"

    with cols[1]:
        if st.button("🔍 View Semantic Logs", key='view_btn', help='View existing Semantic Logs in the Knowledge Graph. Allowed for AUDITOR and ADMIN.', use_container_width=True):
            st.session_state.section = "view"
        if st.button("🔄 View Modifications", key='mods_btn', help='View Modification Logs in the Historical Graph. Allowed for AUDITOR and ADMIN.', use_container_width=True):
            st.session_state.section = "mods"
        if st.button("📅 View Modifications by Date", key='mods_date_btn', help='View Modifications Logs in an specific date. Allowed for AUDITOR and ADMIN.', use_container_width=True):
            st.session_state.section = "mods_date"
        if st.button("『💬』AI Assistant", key='rag_btn', help='Ask Natural Language Questions about the Graph. Allowed for any athenticated user.', use_container_width=True):
            st.session_state.section = "rag"

    st.stop()

section = st.session_state.section

headers = {"Authorization": f"Bearer {st.session_state.token}"}

######################################################################3
# Section Insert
if section == "insert":
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        Insert Semantic Log
    </h2>
    """, unsafe_allow_html=True)   
    ttl_input = st.text_area("Enter Semantic Log in TTL Format", height=200)
    user = st.text_input("User (optional)")
    if st.button("Insert Semantic Log"):
        data = {
            "ttl_content": ttl_input,
            "user": user
        }
        try:
            response = requests.post(f"{API_URL}/ttl", json=data, headers=headers)
            if response.status_code == 201:
                st.success("TTL inserted successfully!")
                st.json(response.json())
            else:
                try:
                    error_detail = response.json().get("detail", response.text)
                except Exception:
                    error_detail = response.text
                st.error(f"Failed to insert semantic log: {error_detail}")

        except Exception as e:
            st.error(f"Request failed: {str(e)}")
    if st.button("🔙"):
        st.session_state.section = None
        st.rerun()

# Section view TTLs
elif section == "view":
    # Section get TTLs
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        View Existing Semantic Logs
    </h2>
    """, unsafe_allow_html=True) 
    if st.button("Load Semantic Logs"):
        try:
            response = requests.get(f"{API_URL}/events", headers=headers)
            if response.ok:
                #g = RDFGraph()
                #g.parse(data=response.text, format="turtle")

                # if there are no inserted ttls, show a message
                if len(response.text) == 0:
                    st.info("No TTLs have been inserted yet.")
                else:
                # to return the TTL (not using s,o,p) with prefixes
                    ttl_with_prefixes = response.text
                    st.code(ttl_with_prefixes, language="turtle")
            else:
                try:
                    error_detail = response.json().get("detail", response.text)
                except Exception:
                    error_detail = response.text
                st.error(f"Failed to view TTL: {error_detail}")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")


    # Section TTL Graph
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        View Knowledge Graph
    </h2>
    """, unsafe_allow_html=True) 
    if st.button("Load Graph"):
        try:
            response = requests.get(f"{API_URL}/events", headers=headers)
            if response.ok:
                g = RDFGraph()
                g.parse(data=response.text, format="turtle")

                if len(g) == 0:
                    st.info("No TTLs have been inserted yet.")
                else:

                    html_path = generate_ttl_graph_pyvis(g)

                    # Display the HTML file in Streamlit
                    with open(html_path, "r", encoding="utf-8") as f:
                        graph_html = f.read()
                    components.html(graph_html, height=700, scrolling=True)

            else:
                try:
                    error_detail = response.json().get("detail", response.text)
                except Exception:
                    error_detail = response.text
                st.error(f"Failed to view Graph: {error_detail}")

        except Exception as e:
            st.error(f"Request failed: {str(e)}")
    if st.button("🔙"):
        st.session_state.section = None
        st.rerun()


# Section view mods
elif section == "mods":
    # Section get modifications
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        View Modification Logs
    </h2>
    """, unsafe_allow_html=True) 
    limit = st.number_input("Limit", min_value=1, max_value=100, value=10)
    if st.button("Load Modifications"):
        try:
            response = requests.get(f"{API_URL}/modifications", params={"limit": limit}, headers=headers)
            if response.ok:
                # Check if empty
                logs = response.json()
                if not logs:
                    st.info("No modifications have been made.")
                else:                  
                    for log in response.json():
                        st.json(log)
            else:
                try:
                    error_detail = response.json().get("detail", response.text)
                except Exception:
                    error_detail = response.text
                st.error(f"Failed to view modifications: {error_detail}")

        except Exception as e:
            st.error(f"Request failed: {str(e)}")

    # Section get modifications graph
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        Historical Graph Visualization
    </h2>
    """, unsafe_allow_html=True) 
    
    if st.button("Visualize Graph"):
        st.session_state["show_graph"] = True

    if st.session_state.get("show_graph", False):
        try:
            response = requests.get(f"{API_URL}/modifications", params={"limit": 100}, headers=headers)
            if response.ok:
                logs = response.json()
                # Check if empty
                if not logs:
                    st.info("No modifications have been made.")
                else:
                    # Generate the graph using pyvis
                    st.session_state["logs_data"] = logs
                    html_path = generate_modification_graph_pyvis(logs)
                    with open(html_path, "r", encoding="utf-8") as f:
                        graph_html = f.read()
                    components.html(graph_html, height=700, scrolling=True)

                    # Display legend for graph
                    st.markdown(
                        """
                        <div style='color: white; font-size: 16px; margin-top: 20px;'>
                            <strong>Graph Legend:</strong><br>
                            <ul>
                                <li><span style='color: orange; font-weight: bold;'>●</span> Deletion (deleted triple)</li>
                                <li><span style='color: limegreen; font-weight: bold;'>●</span> Insertion (inserted triple)</li>
                                <li><span style='color: deepskyblue; font-weight: bold;'>●</span> User node (center of the modification)</li>
                            </ul>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Group logs by user
                    grouped_logs = defaultdict(list)
                    for log in logs:
                        user = log.get('user', 'Unknown')
                        grouped_logs[user].append(log)

                    st.markdown(
                    "<h1 style='color:#FFFFFF; font-weight: bold;'>Users - Click to View Their Logs</h1>",
                    unsafe_allow_html=True
                    )   

                    for user, user_logs in grouped_logs.items():
                        if st.button(f"{user}", key=f"user_{user}"):
                            st.session_state["selected_user"] = user
                            st.session_state["show_user_logs"] = True
                            st.session_state["selected_log_id"] = None
                            st.session_state["show_ttl"] = False
                            st.rerun()                                   

                    # List change IDs (log_ids) for each user
                    selected_user = st.session_state.get("selected_user")
                    if selected_user and st.session_state.get("show_user_logs", False):
                        st.markdown(
                            f"<h2 style='color:white;'>Logs for user: {selected_user}</h2>",
                            unsafe_allow_html=True
                        )
                        for log in grouped_logs[selected_user]:
                            log_id = log["log_id"]
                            ttl = log.get('ttl_content', '')[:80].replace('\n', ' ') + "..."
                            if st.button(f"{log_id}", key=f"log_{log_id}"):
                                st.session_state["selected_log_id"] = log_id
                                st.session_state["show_ttl"] = True

                                st.rerun()# refresh to show TTL content
         
            else:
                try:
                    error_detail = response.json().get("detail", response.text)
                except Exception:
                    error_detail = response.text
                st.error(f"Failed to view Graph: {error_detail}")

        except Exception as e:
            st.error(f"Request failed: {str(e)}")

    # Show TTL content for selected log ID
    selected_log_id = st.session_state.get("selected_log_id")
    logs_data = st.session_state.get("logs_data", [])

    if selected_log_id and logs_data and st.session_state.get("show_ttl", False):
        selected_log = next((log for log in logs_data if log['log_id'] == selected_log_id), None)
        if selected_log:
            ttl_text = selected_log.get("ttl_content", "")
            st.markdown(f"<h3 style='color:white;'>Log ID: {selected_log_id}</h3>", unsafe_allow_html=True)
            st.text_area("TTL content", ttl_text, height=300)
        else:
            st.error("Selected log ID not found in loaded data.")


    # Back
    if st.button("🔙"):
        st.session_state.section = None
        st.session_state.show_graph = False
        st.session_state.selected_log_id = None
        st.rerun()



# Section view mods by date
elif section == "mods_date":
    # Section get modifications by date
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        View Modifications by Date
    </h2>
    """, unsafe_allow_html=True)
    start_date = st.date_input("Start Date")
    start_time = st.time_input("Start Time")
    end_date = st.date_input("End Date")
    end_time = st.time_input("End Time")

    start_datetime = datetime.combine(start_date, start_time).isoformat()
    end_datetime = datetime.combine(end_date, end_time).isoformat()

    if st.button("Fetch Logs by Date"):
        try:
            response = requests.get(
                f"{API_URL}/modifications_date",
                params={"start_date": start_datetime, "end_date": end_datetime},
                headers=headers
            )
            if response.ok:
                logs = response.json()
                if not logs:
                    st.info("No modifications available for the selected range.")
                else:
                    st.session_state["logs_data_date"] = logs
                    for log in logs:
                        st.json(log)

            else:
                try:
                    error_detail = response.json().get("detail", response.text)
                except Exception:
                    error_detail = response.text
                st.error(f"Failed to view logs by date: {error_detail}")

        except Exception as e:
            st.error(f"Request failed: {str(e)}")

    # Section get modifications graph by date
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        Historical Graph Visualization
    </h2>
    """, unsafe_allow_html=True)
    if st.button("Visualize Graph by Date"):    
        try:
            response = requests.get(
                f"{API_URL}/modifications_date",
                params={"start_date": start_datetime, "end_date": end_datetime},
                headers=headers
            )
            if response.ok:
                logs = response.json()
                if not logs:
                    st.info("No modifications available for the selected range.")
                else:
                    st.session_state["logs_data_date"] = logs  # Store logs for TTL buttons
                    html_path = generate_modification_graph_pyvis(logs)
                    with open(html_path, "r", encoding="utf-8") as f:
                        graph_html = f.read()
                    components.html(graph_html, height=700, scrolling=True)

                    # Display legend for graph
                    st.markdown(
                        """
                        <div style='color: white; font-size: 16px; margin-top: 20px;'>
                            <strong>Graph Legend:</strong><br>
                            <ul>
                                <li><span style='color: orange; font-weight: bold;'>●</span> Deletion (deleted triple)</li>
                                <li><span style='color: limegreen; font-weight: bold;'>●</span> Insertion (inserted triple)</li>
                                <li><span style='color: deepskyblue; font-weight: bold;'>●</span> User node (center of the modification)</li>
                            </ul>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


                    # Group logs by user
                    grouped_logs = defaultdict(list)
                    for log in logs:
                        user = log.get('user', 'Unknown')
                        grouped_logs[user].append(log)

                    st.markdown(
                    "<h1 style='color:#FFFFFF; font-weight: bold;'>Users - Click to View Their Logs</h1>",
                    unsafe_allow_html=True
                    )   

                    for user, user_logs in grouped_logs.items():
                        if st.button(f"{user}", key=f"user_{user}"):
                            st.session_state["selected_user"] = user
                            st.session_state["show_user_logs"] = True
                            st.session_state["selected_log_id"] = None
                            st.session_state["show_ttl"] = False
                            st.rerun()                                   

                    # List change IDs (log_ids) for each user
                    selected_user = st.session_state.get("selected_user")
                    if selected_user and st.session_state.get("show_user_logs", False):
                        st.markdown(
                            f"<h2 style='color:white;'>Logs for user: {selected_user}</h2>",
                            unsafe_allow_html=True
                        )
                        for log in grouped_logs[selected_user]:
                            log_id = log["log_id"]
                            ttl = log.get('ttl_content', '')[:80].replace('\n', ' ') + "..."
                            if st.button(f"{log_id}", key=f"log_{log_id}"):
                                st.session_state["selected_log_id"] = log_id
                                st.session_state["show_ttl"] = True

                                st.rerun()# refresh to show TTL content
         
            else:
                try:
                    error_detail = response.json().get("detail", response.text)
                except Exception:
                    error_detail = response.text
                st.error(f"Failed to view Graph: {error_detail}")

        except Exception as e:
            st.error(f"Request failed: {str(e)}")

    # Show TTL content for selected log ID
    selected_log_id = st.session_state.get("selected_log_id")
    logs_data = st.session_state.get("logs_data", [])

    if selected_log_id and logs_data and st.session_state.get("show_ttl", False):
        selected_log = next((log for log in logs_data if log['log_id'] == selected_log_id), None)
        if selected_log:
            ttl_text = selected_log.get("ttl_content", "")
            st.markdown(f"<h3 style='color:white;'>Log ID: {selected_log_id}</h3>", unsafe_allow_html=True)
            st.text_area("TTL content", ttl_text, height=300)
        else:
            st.error("Selected log ID not found in loaded data.")

    # Back
    if st.button("🔙"):
        st.session_state.section = None
        st.session_state.show_graph = False
        st.session_state.selected_log_id = None
        st.rerun()



# Section custom SPARQL query
elif section == "query":
    # Section run custom SPARQL query
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        Run Custom SPARQL Query
    </h2>
    """, unsafe_allow_html=True) 
    sparql_query = st.text_area("Enter SPARQL query", height=200)

    if st.button("Execute Query"):
        if sparql_query.strip(): # not empty
            try:
                response = requests.get(f"{API_URL}/query", params={"query": sparql_query}, headers=headers)
                if response.ok:
                    st.write("Query Results:")
                    ttl_data = response.text
                    st.code(ttl_data, language="turtle")
                    st.session_state["last_ttl"] = ttl_data # store ttl for graph
                else:
                    try:
                        error_detail = response.json().get("detail", response.text)
                    except Exception:
                        error_detail = response.text
                    st.error(f"Failed to view query: {error_detail}")

            except Exception as e:
                st.error(f"Request failed: {str(e)}")

    # Section visualize query results graph
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        View Knowledge Graph
    </h2>
    """, unsafe_allow_html=True)
    if st.button("Visualize Graph"):
        if "last_ttl" in st.session_state:
            try:
                g = RDFGraph()
                g.parse(data=st.session_state["last_ttl"], format="turtle")
                html_path = generate_ttl_graph_pyvis(g)
                with open(html_path, "r", encoding="utf-8") as f:
                    graph_html = f.read()
                components.html(graph_html, height=700, scrolling=True)

            except Exception as e:
                st.error(f"Failed to visualize graph: {str(e)}")
        else:
            st.warning("First, run a SPARQL query to visualize the results.")

    if st.button("🔙"):
        st.session_state.section = None
        st.rerun()


# Section delete all TTLs
elif section == "delete":
    st.markdown("""
    <h2 style='
        color: #FFFFFF;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
    '>
        Delete All Semantic Logs
    </h2>
    """, unsafe_allow_html=True) 
    delete_user = st.text_input("User (optional) for deletion")

    # white text for checkbox label
    st.markdown("<label style='color:white; font-weight:bold;'>Confirm deletion of all triples ⤵</label>", unsafe_allow_html=True)
    # Checkbox with white text
    confirm_delete = st.checkbox("", key="confirm_delete_box", label_visibility="collapsed")
    
    if st.button("Delete All Semantic Logs"):
        if confirm_delete:
            try:
                data = {"user": delete_user}
                response = requests.post(f"{API_URL}/ttl/delete_all", json=data, headers=headers)
                if response.ok:
                    st.success("All TTLs deleted successfully.")
                    st.json(response.json())
                else:
                    try:
                        error_detail = response.json().get("detail", response.text)
                    except Exception:
                        error_detail = response.text
                    st.error(f"Failed to delete TTLs: {error_detail}")

            except Exception as e:
                st.error(f"Request failed: {str(e)}")
        else:
            st.warning("You must confirm deletion before proceeding.")
    if st.button("🔙"):
        st.session_state.section = None
        st.rerun()


# # RAG Assistant
# elif section == "rag":
#     st.markdown("""
#     <h2 style='
#         color: #FFFFFF;
#         text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.7);
#     '>
#         『💬』AI Assistant
#     </h2>
#     """, unsafe_allow_html=True)
    
#     user_question = st.text_input("Ask something about the events graph (natural language)")

#     if st.button("Ask AI Assistant", key="ask_ai_assistant"):
#         if user_question.strip():
#             try:
#                 response = requests.post(
#                     f"{API_URL}/rag/ask",
#                     json={"question": user_question},
#                     headers=headers
#                 )
#                 if response.ok:
#                     result = response.json().get("answer", "No answer returned.")
#                     st.markdown("<h2 style='color: white;'>Assistant Response</h2>", unsafe_allow_html=True)
#                     st.code(result, language="sparql")
#                 else:
#                     try:
#                         error_detail = response.json().get("detail", response.text)
#                     except Exception:
#                         error_detail = response.text
#                     st.error(f"Failed question: {error_detail}")

#             except Exception as e:
#                 st.error(f"Failed to process your question: {str(e)}")
#         else:
#             st.warning("Please enter a question to proceed.")

#     # Botón para evaluar el modelo RAG
#     if st.button("Evaluate RAG Model", key="evaluate_rag_model"):
#         try:
#             response = requests.get(f"{API_URL}/rag/evaluate", headers=headers)
#             if response.ok:
#                 evaluation_result = response.json()
                
#                 # Mostrar los resultados de la evaluación
#                 st.markdown("<h2 style='color: white;'>RAG Model Evaluation</h2>", unsafe_allow_html=True)
#                 st.json(evaluation_result)
#             else:
#                 try:
#                     error_detail = response.json().get("detail", response.text)
#                 except Exception:
#                     error_detail = response.text
#                 st.error(f"Failed to evaluate RAG model: {error_detail}")

#         except Exception as e:
#             st.error(f"Failed to process the evaluation: {str(e)}")

#     # Botón para regresar al menú principal con un key único
#     if st.button("🔙", key="back_to_menu"):
#         st.session_state.section = None
#         st.rerun()

elif section == "rag":
    st.markdown("""
    <h2 style='color:#FFFFFF;text-shadow:2px 2px 4px rgba(0,0,0,0.7);'>
        『💬』AI Assistant
    </h2>
    """, unsafe_allow_html=True)

    # Entrada de la pregunta
    question = st.text_input("Ask something about the events graph (natural language)")

    # Campo opcional para la respuesta de referencia
    reference = st.text_input("Reference answer (optional - needed for evaluation)")

    col1, col2, col3 = st.columns(3)
    with col1:
        ask_btn  = st.button("🤖 Obtener respuesta", use_container_width=True)
    with col2:
        eval_btn = st.button("📊 Responder + Evaluar", use_container_width=True)
    with col3:
        batch_btn = st.button("📂 Evaluar JSON", use_container_width=True)

    # ------------------- SOLO PREGUNTAR -------------------
    if ask_btn and question.strip():
        try:
            r = requests.post(
                f"{API_URL}/rag/ask",
                json={"question": question},
                headers=headers,
                timeout=60,
            )
            if r.ok:
                st.subheader("Assistant Response")
                st.code(r.json().get("answer", "No answer returned."), language="text")
            else:
                st.error(r.text)
        except Exception as e:
            st.error(str(e))

    # -------------- PREGUNTAR + EVALUAR -------------------
    if eval_btn:
        if not question.strip() or not reference.strip():
            st.warning("You must enter both the question and the reference answer.")
        else:
            try:
                r = requests.post(
                    f"{API_URL}/rag/evaluate",
                    json={"question": question, "reference": reference},
                    headers=headers,
                    timeout=90,
                )
                if r.ok:
                    data = r.json()
                    st.subheader("Assistant Response")
                    st.code(data.pop("answer"), language="text")

                    st.subheader("Evaluation Metrics")
                    st.json(data)
                else:
                    st.error(r.text)
            except Exception as e:
                st.error(str(e))
   
    # 1. variables persistentes
    if "batch_dataset" not in st.session_state:
        st.session_state.batch_dataset = None
    if "batch_result" not in st.session_state:
        st.session_state.batch_result = None

    # 2. uploader SIEMPRE visible
    uploaded = st.file_uploader(
        "Upload JSON list to evaluate (question / expected_answer)",
        type="json",
        key="batch_json",
    )

    # 3. cuando subes el fichero, lo guardamos una vez
    if uploaded is not None and st.session_state.batch_dataset is None:
        import json
        st.session_state.batch_dataset = json.load(uploaded)
        st.success(f"Loaded {len(st.session_state.batch_dataset)} samples ✔️")

    # 4. botón para lanzar la evaluación (solo si ya hay dataset)
    if st.session_state.batch_dataset is not None:
        if st.button("🚀 Run batch evaluation"):
            try:
                import requests, os
                r = requests.post(
                    f"{API_URL}/rag/evaluate_batch",
                    json={"dataset": st.session_state.batch_dataset},
                    headers=headers,
                    timeout=300,
                )
                r.raise_for_status()
                st.session_state.batch_result = r.json()
            except Exception as e:
                st.error(f"Batch request failed: {e}")

    # 5. mostrar resultados si existen
    if st.session_state.batch_result is not None:
        st.subheader("Averages")
        st.json(st.session_state.batch_result["averages"])
        st.subheader("Per-item results")
        st.json(st.session_state.batch_result["results"])


    # Botón volver
    if st.button("🔙", key="back_to_menu"):
        st.session_state.section = None
        st.rerun()

