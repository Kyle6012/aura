import streamlit as st
import os
import tempfile
from dotenv import load_dotenv
import streamlit.components.v1 as components
from agentic_system.src.retriever import SemanticRetriever
from agentic_system.src.tools import ToolRegistry
from agentic_system.src.control_plane import ControlPlane
from agentic_system.src.agent import TutorAgent

# page config
st.set_page_config(
    page_title="AURA - AI Tutor", 
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🎓"
)

# custom css styling
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    
    /* Compact UI - smaller buttons and text */
    .stButton button {
        font-size: 0.85rem !important;
        padding: 0.35rem 0.75rem !important;
        height: auto !important;
    }
    
    .stSelectbox, .stMultiSelect, .stTextInput {
        font-size: 0.85rem !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    
    /* Chat messages - User messages */
    [data-testid="stChatMessageContainer"] div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        border-radius: 20px 20px 5px 20px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 8px 16px rgba(59, 130, 246, 0.3);
        border: 1px solid rgba(147, 197, 253, 0.2);
    }
    
    [data-testid="stChatMessageContainer"] div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) * {
        color: #ffffff !important;
    }
    
    /* Chat messages - Assistant messages */
    [data-testid="stChatMessageContainer"] div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
        background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
        border-radius: 20px 20px 20px 5px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 8px 16px rgba(139, 92, 246, 0.3);
        border: 1px solid rgba(196, 181, 253, 0.2);
    }
    
    [data-testid="stChatMessageContainer"] div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) * {
        color: #ffffff !important;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    /* Input boxes */
    .stTextInput input, .stTextArea textarea {
        border-radius: 12px;
        border: 2px solid #475569 !important;
        background: rgba(30, 41, 59, 0.8) !important;
        color: #e2e8f0 !important;
        padding: 12px;
    }
    
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }
    
    /* Buttons */
    .stButton button {
        border-radius: 12px;
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    }
    
    /* Info/Warning boxes */
    .stAlert {
        border-radius: 12px;
        border: none;
        background: rgba(59, 130, 246, 0.15) !important;
        border-left: 4px solid #3b82f6 !important;
    }
    
    .stWarning {
        background: rgba(251, 191, 36, 0.15) !important;
        border-left: 4px solid #fbbf24 !important;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        background: rgba(30, 41, 59, 0.6);
        border-radius: 12px;
        padding: 20px;
        border: 2px dashed #475569;
    }
    
    /* Chat input */
    [data-testid="stChatInput"] {
        background: rgba(30, 41, 59, 0.8);
        border-radius: 16px;
        border: 2px solid #475569;
    }
    
    [data-testid="stChatInput"] textarea {
        background: transparent !important;
        color: #e2e8f0 !important;
    }
    
    /* Markdown in messages */
    .stMarkdown {
        color: inherit !important;
    }
    
    /* System messages */
    .stInfo {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
        color: white !important;
        border-radius: 12px;
        padding: 15px;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# load env
load_dotenv()

def init_agent():
    """Initialize or re-initialize the agent and its dependencies."""
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        st.error("TOGETHER_API_KEY not found. Please set it in .env")
        st.stop()
    
    try:
        # initialize database first
        try:
            from agentic_system.src.db import DatabaseManager
            db_manager = DatabaseManager()
        except Exception as db_error:
            print(f"warning: database not available: {db_error}")
            db_manager = None
        
        # pass database to retriever
        retriever = SemanticRetriever(db_manager=db_manager)
        tool_registry = ToolRegistry(retriever)
        control_plane = ControlPlane(tool_registry)
        
        # Force reload of agent module to get latest class definition
        import sys
        import importlib
        
        # Reload agent module safely
        if 'agentic_system.src.agent' in sys.modules:
            try:
                importlib.reload(sys.modules['agentic_system.src.agent'])
                print("Reloaded agent module")
            except Exception as e:
                print(f"Failed to reload agent module: {e}")
        
        from agentic_system.src.agent import TutorAgent
        
        st.session_state.agent = TutorAgent(control_plane, api_key)
        st.session_state.tool_registry = tool_registry
        st.session_state.db_manager = db_manager
        return True
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")
        print(f"Agent init error: {e}")
        return False

# initialize session state
if "agent" not in st.session_state:
    if not init_agent():
        st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

# Voice Manager Component (Unified Input/Output)
last_assistant_response = ""
for msg in reversed(st.session_state.messages):
    if msg["role"] == "assistant":
        last_assistant_response = msg["content"]
        break

voice_manager_html = f"""
<script>
    var recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;
    
    var voiceMode = {str(st.session_state.get('voice_mode', False)).lower()};
    var lastResponse = {repr(last_assistant_response)};
    var isRecording = false;
    var hasTranscript = false;
    
    recognition.onstart = function() {{
        isRecording = true;
        hasTranscript = false;
        document.getElementById("status").innerHTML = "🔴 Listening...";
    }};
    
    recognition.onend = function() {{
        isRecording = false;
        
        // If voice mode is still on and we didn't get a transcript, restart
        if (voiceMode && !hasTranscript) {{
            document.getElementById("status").innerHTML = "⏸️ Waiting...";
            setTimeout(() => {{
                if (voiceMode) {{
                    startRecording();
                }}
            }}, 1000);
        }} else {{
            document.getElementById("status").innerHTML = "💤 Idle";
        }}
    }};
    
    recognition.onresult = function(event) {{
        hasTranscript = true;
        var transcript = event.results[0][0].transcript;
        
        const input = window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
        if (input) {{
            input.value = transcript;
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            
            setTimeout(() => {{
                const sendBtn = window.parent.document.querySelector('button[data-testid="stChatInputSubmitButton"]');
                if (sendBtn) sendBtn.click();
            }}, 100);
        }}
    }};
    
    recognition.onerror = function(event) {{
        console.error('Speech recognition error:', event.error);
        // Don't restart on some errors
        if (event.error === 'no-speech' || event.error === 'audio-capture') {{
            hasTranscript = false; // Will trigger restart in onend
        }}
    }};
    
    function startRecording() {{
        if (!isRecording && voiceMode) {{
            try {{
                recognition.start();
            }} catch (e) {{
                console.error('Failed to start recognition:', e);
                // If already started error, ignore it
                if (e.name !== 'InvalidStateError') {{
                    setTimeout(startRecording, 1000);
                }}
            }}
        }}
    }}
    
    function runVoiceFlow() {{
        if (!voiceMode) return;
        
        const alreadySpoken = sessionStorage.getItem('lastSpoken') === lastResponse;
        
        if (lastResponse && !alreadySpoken) {{
            sessionStorage.setItem('lastSpoken', lastResponse);
            document.getElementById("status").innerHTML = "🔊 Speaking...";
            
            const utterance = new SpeechSynthesisUtterance(lastResponse);
            utterance.onend = () => {{
                if (voiceMode) {{
                    setTimeout(startRecording, 500);
                }}
            }};
            window.speechSynthesis.speak(utterance);
        }} else {{
            startRecording();
        }}
    }}
    
    if (voiceMode) {{
        setTimeout(runVoiceFlow, 500);
    }}
</script>
<div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px; text-align: center;">
    <div id="status" style="margin-bottom: 5px; font-weight: bold;">💤 Idle</div>
    <div style="font-size: 0.8em; color: #666;">Voice Mode: {"ON" if st.session_state.get('voice_mode', False) else "OFF"}</div>
</div>
"""

# sidebar
with st.sidebar:
    st.markdown("## 🤖 System Status")
    st.markdown("---")
    
    # user profile
    st.markdown("### 👤 User Profile")
    if st.session_state.tool_registry.db:
        profile = st.session_state.tool_registry.db.get_profile()
        st.info(f"**Proficiency:** {profile['proficiency']}")
        if profile['topics_covered']:
            st.write("**Topics Covered:**")
            for topic in profile['topics_covered']:
                st.markdown(f"✓ {topic}")
        else:
            st.write("_No topics covered yet_")
    else:
        st.warning("Database not connected. Using in-memory profile.")
        st.write(f"**Proficiency:** {st.session_state.tool_registry.user_state['proficiency']}")

    st.markdown("---")
    
    # Session Documents
    st.markdown("### 📎 Session Documents")
    if st.session_state.get('db_manager') and st.session_state.get('current_session_id'):
        docs = st.session_state.db_manager.get_session_documents(st.session_state.current_session_id)
        
        if docs:
            st.caption(f"{len(docs)} file(s) uploaded in this session")
            for doc in docs:
                with st.container():
                    # File type icon
                    file_ext = doc['filename'].split('.')[-1].lower()
                    icon = {
                        'pdf': '📕',
                        'docx': '📘',
                        'odt': '📗',
                        'png': '🖼️',
                        'jpg': '🖼️',
                        'jpeg': '🖼️'
                    }.get(file_ext, '📄')
                    
                    st.markdown(f"{icon} **{doc['filename'][:30]}{'...' if len(doc['filename']) > 30 else ''}**")
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("📖 View", key=f"view_{doc['id']}", use_container_width=True):
                            st.info(f"File path: {doc.get('file_path', 'N/A')}")
                    with col2:
                        if st.button("🤔 Ask Aura", key=f"ask_{doc['id']}", use_container_width=True):
                            # Auto-fill chat with question about this document
                            st.session_state['doc_query'] = f"Can you tell me about the document {doc['filename']}?"
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.caption("_No documents uploaded yet_")
            st.info("💡 Upload PDFs, DOCX, or images below")
    
    st.markdown("---")
    
    # file explorer
    st.markdown("### 📂 Filesystem Access")
    path = st.text_input("Directory Path", value="/host_fs")
    if st.button("List Files"):
        result = st.session_state.tool_registry.list_directory(path)
        if "error" in result:
            st.error(result["error"])
        else:
            st.write(result["items"])
    
    st.markdown("---")
    
    # Analytics Dashboard
    st.markdown("### 📊 Analytics Dashboard")
    if st.session_state.get('db_manager'):
        with st.expander("View Analytics"):
            analytics = st.session_state.db_manager.get_analytics()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Sessions", analytics.get('total_sessions', 0))
                st.metric("Total Messages", analytics.get('total_messages', 0))
            with col2:
                st.metric("Archived", analytics.get('archived_sessions', 0))
                st.metric("Documents", analytics.get('total_documents', 0))
            
            st.markdown("**Recent Activity (7 days)**")
            recent = analytics.get('recent_activity', {})
            st.write(f"- Sessions: {recent.get('sessions_7d', 0)}")
            st.write(f"- Messages: {recent.get('messages_7d', 0)}")
            
            if analytics.get('tag_usage'):
                st.markdown("**Tag Usage**")
                for tag, count in analytics['tag_usage'].items():
                    st.write(f"- {tag}: {count}")
            
    st.markdown("---")
            
    st.markdown("### 📚 Session Management")
    
    # Initialize DB manager if not exists
    if 'db_manager' not in st.session_state:
        try:
            from agentic_system.src.db import DatabaseManager
            st.session_state.db_manager = DatabaseManager()
        except Exception as e:
            st.error(f"Database not available: {e}")
            st.session_state.db_manager = None
    
    # Get or create current session
    if 'current_session_id' not in st.session_state:
        if st.session_state.db_manager:
            session_id = st.session_state.db_manager.create_session("New Chat")
            st.session_state.current_session_id = session_id
            st.session_state.messages = []
        else:
            st.session_state.current_session_id = "temp_session"
    
    # New session button
    if st.button("➕ New Session", use_container_width=True):
        if st.session_state.db_manager:
            session_id = st.session_state.db_manager.create_session("New Chat")
            st.session_state.current_session_id = session_id
            st.session_state.messages = []
            st.rerun()
    
    # Import session
    with st.expander("📥 Import Session"):
        uploaded_file = st.file_uploader("Upload Session JSON", type=["json"], key="session_import")
        if uploaded_file and st.session_state.db_manager:
            try:
                import json
                session_data = json.load(uploaded_file)
                new_session_id = st.session_state.db_manager.import_session(session_data)
                
                if not new_session_id.startswith("error"):
                    st.success(f"Session imported successfully!")
                    st.session_state.current_session_id = new_session_id
                    # Load messages for new session
                    st.session_state.messages = st.session_state.db_manager.get_session_messages(new_session_id)
                    st.rerun()
                else:
                    st.error(new_session_id)
            except Exception as e:
                st.error(f"Failed to import: {str(e)}")
    
    st.markdown("---")
    
    # Toggle for showing archived sessions
    if 'show_archived' not in st.session_state:
        st.session_state.show_archived = False
    
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("#### Past Sessions")
    with col2:
        if st.button("🗄️ Archive" if not st.session_state.show_archived else "📋 Active", 
                     key="toggle_archived",
                     use_container_width=True):
            st.session_state.show_archived = not st.session_state.show_archived
            st.rerun()
    
    # List past sessions
    if st.session_state.db_manager:
        sessions = st.session_state.db_manager.get_all_sessions(
            include_archived=st.session_state.show_archived
        )
        
        for session in sessions[:15]:  # Show last 15
            is_current = session['session_id'] == st.session_state.current_session_id
            is_archived = session.get('is_archived', False)
            
            # Get stats for current session
            if is_current:
                stats = st.session_state.db_manager.get_session_stats(session['session_id'])
                msg_count = stats.get('message_count', 0)
            else:
                msg_count = 0
            
            # Session display with actions
            col1, col2, col3 = st.columns([5, 1, 1])
            
            with col1:
                icon = "▶️" if is_current else ("🗄️" if is_archived else "📝")
                title_display = session['title'][:30]
                if len(session['title']) > 30:
                    title_display += "..."
                
                button_text = f"{icon} {title_display}"
                if is_current and msg_count > 0:
                    button_text += f" ({msg_count})"
                
                if st.button(button_text, key=f"sess_{session['session_id']}", use_container_width=True):
                    # Load session
                    st.session_state.current_session_id = session['session_id']
                    messages = st.session_state.db_manager.get_session_messages(session['session_id'])
                    st.session_state.messages = messages
                    st.rerun()
            
            with col2:
                # Export button
                if st.button("💾", key=f"export_{session['session_id']}", help="Export session"):
                    import json
                    export_data = st.session_state.db_manager.export_session(session['session_id'])
                    if 'error' not in export_data:
                        st.session_state.export_ready = {
                            'session_id': session['session_id'],
                            'data': json.dumps(export_data, indent=2)
                        }
                        st.rerun()
            
            with col3:
                # Delete/Restore button
                if is_archived:
                    if st.button("♻️", key=f"restore_{session['session_id']}", help="Restore session"):
                        st.session_state.db_manager.restore_session(session['session_id'])
                        st.rerun()
                else:
                    if st.button("🗑️", key=f"del_{session['session_id']}", help="Archive session"):
                        if session['session_id'] != st.session_state.current_session_id:
                            st.session_state.db_manager.archive_session(session['session_id'])
                            st.rerun()
        
        # Handle export download
        if 'export_ready' in st.session_state:
            export_info = st.session_state.export_ready
            st.download_button(
                label=f"📥 Download {export_info['session_id']}.json",
                data=export_info['data'],
                file_name=f"session_{export_info['session_id']}.json",
                mime="application/json",
                use_container_width=True,
                key="download_export"
            )
            if st.button("✖ Close", use_container_width=True):
                del st.session_state.export_ready
                st.rerun()
        
        # Show session documents
        if st.session_state.current_session_id:
            st.markdown("---")
            st.markdown("#### Session Documents")
            docs = st.session_state.db_manager.get_session_documents(st.session_state.current_session_id)
            if docs:
                for doc in docs:
                    st.caption(f"📄 {doc['file_type']}: {doc['doc_id'][:15]}...")
            else:
                st.caption("No documents in this session")
    
    # Voice Mode Toggle
    st.markdown("### 🎙️ Voice Interaction")
    st.toggle("Voice Mode", key="voice_mode")
    
    # Render Voice Manager
    components.html(voice_manager_html, height=80)
    
    st.markdown("---")
    st.markdown("### 📤 Upload Documents")
    
    # document upload
    uploaded_doc = st.file_uploader(
        "Upload PDF/DOCX/ODT",
        type=["pdf", "docx", "odt", "txt", "md"],
        key="doc_uploader"
    )
    
    if uploaded_doc:
        with st.spinner("Processing document..."):
            # save file
            file_path = os.path.join("agentic_system/uploads", uploaded_doc.name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "wb") as f:
                f.write(uploaded_doc.getbuffer())
            
            # process with document processor
            from agentic_system.src.document_processor import DocumentProcessor
            processor = DocumentProcessor()
            result = processor.process_file(file_path)
            
            if result.get("status") == "success":
                # add to knowledge base
                content = result.get("content", "")
                metadata = {
                    "filename": uploaded_doc.name,
                    "type": uploaded_doc.type,
                    "session_id": st.session_state.current_session_id
                }
                
                st.session_state.tool_registry.retriever.add_document(content, metadata)
                
                # Track in session
                if st.session_state.db_manager:
                    st.session_state.db_manager.add_session_document(
                        st.session_state.current_session_id,
                        result.get("doc_id", uploaded_doc.name),
                        file_path,
                        "document"
                    )
                
                st.success(f"✓ Processed: {uploaded_doc.name}")
            else:
                st.error(f"Error: {result.get('error')}")
    
    st.markdown("---")
    st.markdown("### 🖼️ Upload Image")
    
    # image upload
    uploaded_image = st.file_uploader(
        "Upload Image",
        type=["png", "jpg", "jpeg", "gif"],
        key="image_uploader"
    )
    
    if uploaded_image:
        # save image
        image_path = os.path.join("agentic_system/uploads", uploaded_image.name)
        with open(image_path, "wb") as f:
            f.write(uploaded_image.getbuffer())
        
        # Track in session
        if st.session_state.db_manager:
            st.session_state.db_manager.add_session_document(
                st.session_state.current_session_id,
                uploaded_image.name,
                image_path,
                "image"
            )
        
        st.image(image_path, caption=uploaded_image.name, use_container_width=True)
        st.success("✓ Image uploaded")
        
        # ask about image
        if st.button("Ask about this image"):
                    st.session_state.pending_image = image_path

        st.info("Ask me about this image!")

# main interface
st.markdown("# 🎓 AURA")
st.markdown("_Your Agentic AI Programming Tutor by Meshack Bahati Ouma_")
st.markdown("")

# chat history first
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Interactive Coding Workspace
st.markdown("---")
with st.expander("💻 **Interactive Coding Workspace**", expanded=False):
    st.markdown("### Multi-Language Code Editor")
    st.caption("Write and execute code in Python, JavaScript, Go, Rust, C, and C++!")
    
    # Initialize session state
    if 'workspace_code' not in st.session_state:
        st.session_state.workspace_code = "# Write your code here\nprint('Hello, World!')"
    if 'workspace_language' not in st.session_state:
        st.session_state.workspace_language = "python"
    if 'current_assignment' not in st.session_state:
        st.session_state.current_assignment = None
    
    # Display assignment if set by agent
    if st.session_state.current_assignment:
        st.info(f"**📋 Assignment ({st.session_state.current_assignment['language']}):** {st.session_state.current_assignment['description']}")
        if st.button("Clear Assignment"):
            st.session_state.current_assignment = None
            st.rerun()
    
    # Language selector
    language_map = {
        "Python": "python",
        "JavaScript": "javascript",
        "Go": "golang",
        "Rust": "rust",
        "C": "c_cpp",
        "C++": "c_cpp"
    }
    
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_lang = st.selectbox(
            "Language",
            options=list(language_map.keys()),
            index=list(language_map.keys()).index("Python") if st.session_state.workspace_language == "python" else 0
        )
        
        # Map display name to internal name
        internal_lang = selected_lang.lower().replace(" ", "")
        if selected_lang in ["C", "C++"]:
            internal_lang = "c" if selected_lang == "C" else "cpp"
        
        st.session_state.workspace_language = internal_lang
    
    # Ace editor with syntax highlighting
    try:
        from streamlit_ace import st_ace
        
        code = st_ace(
            value=st.session_state.workspace_code,
            language=language_map[selected_lang],
            theme="monokai",
            height=300,
            key="ace_editor",
            font_size=14
        )
        st.session_state.workspace_code = code if code else st.session_state.workspace_code
    except ImportError:
        st.warning("Advanced editor not available. Install streamlit-ace for syntax highlighting.")
        code = st.text_area(
            f"{selected_lang} Code Editor",
            value=st.session_state.workspace_code,
            height=300,
            key="fallback_editor"
        )
        st.session_state.workspace_code = code
    
    # Control buttons
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        run_button = st.button("▶️ Run Code", type="primary", use_container_width=True)
    with col2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)
    
    if clear_button:
        default_templates = {
            "python": "# Write your Python code here\nprint('Hello, World!')",
            "javascript": "// Write your JavaScript code here\nconsole.log('Hello, World!');",
            "go": "package main\nimport \"fmt\"\n\nfunc main() {\n    fmt.Println(\"Hello, World!\")\n}",
            "rust": "fn main() {\n    println!(\"Hello, World!\");\n}",
            "c": "#include <stdio.h>\n\nint main() {\n    printf(\"Hello, World!\\n\");\n    return 0;\n}",
            "cpp": "#include <iostream>\n\nint main() {\n    std::cout << \"Hello, World!\" << std::endl;\n    return 0;\n}"
        }
        st.session_state.workspace_code = default_templates.get(internal_lang, "")
        st.rerun()
    
    if run_button and code.strip():
        with st.spinner(f"Executing {selected_lang} code..."):
            result = st.session_state.tool_registry.run_code(code, internal_lang)
        
        # Display output
        st.markdown("#### 📤 Output")
        if result.get("status") == "success":
            if result.get("stdout"):
                st.code(result["stdout"], language="text")
            else:
                st.info("Code executed successfully with no output.")
            
            if result.get("stderr"):
                st.error("**Error/Warning:**")
                st.code(result["stderr"], language="text")
        elif result.get("status") == "compilation_error":
            st.error("**Compilation Error:**")
            st.code(result["stderr"], language="text")
        else:
            st.error(f"**Execution Error:** {result.get('error', 'Unknown error')}")

# chat input
if user_input := st.chat_input("Ask me anything..."):
    # add user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Save to database
    if st.session_state.db_manager and st.session_state.current_session_id:
        st.session_state.db_manager.save_message(
            st.session_state.current_session_id,
            "user",
            user_input
        )
        
        # Auto-generate title from first message if still "New Chat"
        stats = st.session_state.db_manager.get_session_stats(st.session_state.current_session_id)
        if stats.get('message_count', 0) == 1:  # First message just added
            # Use first user message as title (truncated)
            title = user_input[:50]
            if len(user_input) > 50:
                title += "..."
            st.session_state.db_manager.update_session_title(
                st.session_state.current_session_id,
                title
            )
    
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Get session documents for agent awareness
            session_docs = []
            if st.session_state.db_manager and st.session_state.current_session_id:
                session_docs = st.session_state.db_manager.get_session_documents(st.session_state.current_session_id)
            
            try:
                response = st.session_state.agent.teach(
                    user_input,
                    session_id=st.session_state.current_session_id,
                    session_context=st.session_state.messages,
                    session_documents=session_docs
                )
            except TypeError as e:
                if "unexpected keyword argument" in str(e):
                    # Stale agent instance, re-initialize
                    st.warning("Updating system components... please wait.")
                    init_agent()
                    # Retry with new agent
                    response = st.session_state.agent.teach(
                        user_input,
                        session_id=st.session_state.current_session_id,
                        session_context=st.session_state.messages,
                        session_documents=session_docs
                    )
                else:
                    raise e
        st.markdown(response)
    
    # add assistant response
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Save to database
    if st.session_state.db_manager and st.session_state.current_session_id:
        st.session_state.db_manager.save_message(
            st.session_state.current_session_id,
            "assistant",
            response
        )
