import streamlit as st
import os
import json

# Page config
st.set_page_config(
    page_title="Synthetic User Research", 
    page_icon="👥", 
    layout="wide"
)

st.title("👥 Synthetic User Research Assistant")
st.markdown("### Setup Required")

# Check if packages are installed
packages_status = {}

try:
    from supabase import create_client
    packages_status['supabase'] = "✅ Installed"
except ImportError as e:
    packages_status['supabase'] = f"❌ Not installed: {str(e)}"

try:
    from langchain_anthropic import ChatAnthropic
    packages_status['langchain-anthropic'] = "✅ Installed"
except ImportError as e:
    packages_status['langchain-anthropic'] = f"❌ Not installed: {str(e)}"

try:
    from sentence_transformers import SentenceTransformer
    packages_status['sentence-transformers'] = "✅ Installed"
except ImportError as e:
    packages_status['sentence-transformers'] = f"❌ Not installed: {str(e)}"

# Show package status
with st.expander("📦 Package Installation Status", expanded=True):
    for package, status in packages_status.items():
        st.write(f"**{package}**: {status}")

# Check if all packages are installed
all_installed = all("✅" in status for status in packages_status.values())

if not all_installed:
    st.error("### ⚠️ Packages Not Installed Correctly")
    st.markdown("""
    **To fix this on Streamlit Cloud:**
    
    1. Make sure these files exist in your repo ROOT:
       - `requirements.txt`
       - `packages.txt`
       - `app.py`
    
    2. In Streamlit Cloud dashboard:
       - Click "Manage app"
       - Click "Reboot app"
       - Wait 2-3 minutes for packages to install
    
    3. If still failing, check the requirements.txt content below.
    """)
    
    st.code("""
streamlit==1.31.0
supabase==2.3.4
langchain==0.1.7
langchain-anthropic==0.1.6
langchain-community==0.0.20
sentence-transformers==2.3.1
anthropic==0.18.1
python-dotenv==1.0.0
    """)
    
    st.markdown("**packages.txt should contain:**")
    st.code("""
build-essential
python3-dev
    """)
    
    st.stop()

# If we get here, all packages are installed!
st.success("### ✅ All Packages Installed Successfully!")

# Now import everything
from supabase import create_client
from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import HumanMessage, SystemMessage

# Initialize session state
if "selected_persona" not in st.session_state:
    st.session_state.selected_persona = None
if "conversation" not in st.session_state:
    st.session_state.conversation = []

# Initialize connections
@st.cache_resource
def init_supabase():
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
    if not url or not key:
        return None
    return create_client(url, key)

@st.cache_resource
def init_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def init_llm():
    api_key = st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY"))
    if not api_key:
        return None
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=api_key,
        temperature=0.8,
        max_tokens=2048
    )

# Check credentials
supabase = init_supabase()
llm = init_llm()

if not supabase or not llm:
    st.warning("### ⚙️ Configuration Needed")
    st.markdown("""
    Add your API keys in Streamlit Cloud:
    
    1. Click "Manage app" (bottom right)
    2. Go to "Settings" → "Secrets"
    3. Add:
    
    ```toml
    SUPABASE_URL = "https://your-project.supabase.co"
    SUPABASE_KEY = "your-anon-key"
    ANTHROPIC_API_KEY = "sk-ant-your-key"
    ```
    
    4. Save and reboot the app
    """)
    st.stop()

# Initialize embeddings (will take a moment first time)
with st.spinner("Loading AI models..."):
    embeddings = init_embeddings()

st.success("✅ App fully initialized and ready!")

# Load personas
def load_personas():
    result = supabase.table("personas").select("*").execute()
    return result.data if result.data else []

def search_evidence(query: str, market: str, limit: int = 5):
    query_embedding = embeddings.embed_query(query)
    
    result = supabase.rpc(
        "search_evidence",
        {
            "query_embedding": query_embedding,
            "market_filter": market,
            "match_threshold": 0.65,
            "match_count": limit
        }
    ).execute()
    
    return result.data if result.data else []

def generate_synthetic_response(persona, question, evidence_data):
    evidence_context = []
    for item in evidence_data:
        evidence_context.append(f"Source: {item['source_type']} ({item['market']})\nContent: {item['content']}\n---")
    
    evidence_text = "\n".join(evidence_context) if evidence_context else "No specific evidence found."
    
    system_prompt = f"""You are {persona['name']}, a {persona['age']}-year-old {persona['occupation']} from {persona['market']}.

Your background: {persona['bio']}
Your pain points: {', '.join(persona.get('pain_points', []))}
Your goals: {', '.join(persona.get('goals', []))}

Answer questions AS THIS PERSON. Use first person. Be authentic and conversational (2-4 sentences).
Base your answers on the evidence below when relevant, but speak naturally.

Evidence from research:
{evidence_text}"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ]
    
    return llm.invoke(messages).content

# Main UI
st.markdown("---")

try:
    personas = load_personas()
    
    if not personas:
        st.warning("### 📋 Database Setup Needed")
        st.markdown("""
        Your Supabase database needs to be set up:
        
        1. Go to your Supabase project
        2. Open SQL Editor
        3. Copy and paste the entire `database_setup.sql` file
        4. Run it
        5. Refresh this page
        """)
        st.stop()
    
    # Persona Selection
    st.subheader("🌍 Select a Persona")
    
    markets = {}
    for p in personas:
        if p['market'] not in markets:
            markets[p['market']] = []
        markets[p['market']].append(p)
    
    cols = st.columns(3)
    for idx, (market, market_personas) in enumerate(markets.items()):
        with cols[idx]:
            st.markdown(f"### 🌏 {market.upper()}")
            for persona in market_personas:
                if st.button(
                    f"**{persona['name']}**\n{persona['age']} • {persona['occupation']}", 
                    key=f"p_{persona['id']}",
                    use_container_width=True
                ):
                    st.session_state.selected_persona = persona
                    st.session_state.conversation = []
                    st.rerun()
    
    # Chat Interface
    if st.session_state.selected_persona:
        st.markdown("---")
        persona = st.session_state.selected_persona
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(f"💬 Talking to: {persona['name']}")
            st.caption(f"{persona['age']} • {persona['occupation']} • {persona['market'].upper()}")
        with col2:
            if st.button("🔄 Change Persona", use_container_width=True):
                st.session_state.selected_persona = None
                st.session_state.conversation = []
                st.rerun()
        
        with st.expander("📋 Persona Profile"):
            st.write(f"**Bio:** {persona['bio']}")
            if persona.get('pain_points'):
                st.write(f"**Pain Points:** {', '.join(persona['pain_points'])}")
            if persona.get('goals'):
                st.write(f"**Goals:** {', '.join(persona['goals'])}")
        
        st.markdown("---")
        
        # Display conversation
        for item in st.session_state.conversation:
            with st.chat_message("user"):
                st.write(item['question'])
            
            with st.chat_message("assistant", avatar="👤"):
                st.write(item['answer'])
                
                if item.get('evidence'):
                    st.markdown("#### 📊 Real Evidence")
                    
                    for ev in item['evidence']:
                        market_class = ev['market'].lower()
                        st.markdown(f"**{ev['market'].upper()}** - {ev['source_type']}")
                        st.info(f'"{ev["content"]}"')
                        st.markdown("")
        
        # Chat input
        question = st.chat_input("Ask a question...")
        
        if question:
            with st.chat_message("user"):
                st.write(question)
            
            with st.chat_message("assistant", avatar="👤"):
                with st.spinner("Thinking..."):
                    # Get evidence
                    local_evidence = search_evidence(question, persona['market'], limit=4)
                    global_evidence = search_evidence(question, 'global', limit=2)
                    all_evidence = local_evidence + global_evidence
                    
                    # Generate response
                    answer = generate_synthetic_response(persona, question, all_evidence)
                    st.write(answer)
                    
                    # Show evidence
                    if all_evidence:
                        st.markdown("#### 📊 Real Evidence")
                        
                        for ev in all_evidence:
                            st.markdown(f"**{ev['market'].upper()}** - {ev['source_type']}")
                            st.info(f'"{ev["content"]}"')
                            st.markdown("")
            
            st.session_state.conversation.append({
                'question': question,
                'answer': answer,
                'evidence': all_evidence
            })
            st.rerun()

except Exception as e:
    st.error(f"### ❌ Error: {str(e)}")
    st.markdown("""
    **Common issues:**
    - Database not set up: Run `database_setup.sql` in Supabase
    - Wrong credentials: Check your secrets configuration
    - Network issue: Wait a moment and refresh
    """)
    
    with st.expander("Full error details"):
        st.exception(e)

st.markdown("---")
st.caption("Powered by Claude + Supabase • Synthetic User Research")
