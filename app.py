import streamlit as st
import os
import json

# Page config
st.set_page_config(
    page_title="Synthetic User Research", 
    page_icon="👥", 
    layout="wide"
)

# Custom CSS for better evidence display
st.markdown("""
<style>
    .evidence-badge {
        display: inline-block;
        padding: 4px 12px;
        margin: 4px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        color: white;
    }
    .interview { background-color: #2196F3; }
    .social { background-color: #FF9800; }
    .search { background-color: #4CAF50; }
    .quote { background-color: #9C27B0; }
    .behavioral { background-color: #607D8B; }
    .evidence-preview {
        background-color: #f5f5f5;
        border-left: 3px solid #2196F3;
        padding: 8px 12px;
        margin: 8px 0;
        font-size: 13px;
        font-style: italic;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.title("👥 Synthetic User Research Assistant")
st.caption("v2.4 - Simplified Evidence Display")

# Add database setup instructions
with st.expander("⚙️ DATABASE SETUP REQUIRED", expanded=False):
    st.markdown("""
    ### 📋 Step 1: Set Up Supabase Database
    
    If you haven't set up your database yet, you need to:
    
    1. **Download the database setup file**: 
       - [database_setup.sql](https://github.com/antoniopedrola/streamlit-app/blob/main/database_setup.sql)
       - Or find it in your project files
    
    2. **Go to your Supabase project**: https://supabase.com
    
    3. **Open SQL Editor** (in the left sidebar)
    
    4. **Copy and paste the ENTIRE `database_setup.sql` file**
    
    5. **Click "Run"** (or press Ctrl+Enter)
    
    6. **Verify it worked**: You should see "Success. No rows returned"
    
    This creates:
    - ✅ Personas table (6 sample personas)
    - ✅ Research evidence table (18+ sample evidence items WITH embeddings)
    - ✅ Vector search function
    - ✅ All necessary indexes
    
    ### 🔍 Check if Database is Set Up
    
    If you've already run the SQL, you can verify by checking in Supabase:
    - Go to **Table Editor** → Look for `personas` and `research_evidence` tables
    - `personas` should have 6 rows
    - `research_evidence` should have 18+ rows
    
    ### ❌ Common Issues
    
    - **"No evidence found"** → Database not set up or empty
    - **"Function search_evidence does not exist"** → SQL wasn't run completely
    - **"No rows in research_evidence"** → Evidence wasn't inserted
    """)

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
streamlit>=1.31.0
supabase>=2.3.0
langchain>=0.1.0
langchain-anthropic>=0.1.0
langchain-community>=0.0.20
sentence-transformers>=2.2.0
anthropic>=0.18.0
python-dotenv>=1.0.0
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
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

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

# Helper function to get evidence badge emoji
def get_evidence_badge(source_type):
    """Return emoji badge for evidence type"""
    badge_map = {
        'interview_transcript': '🎤 Interview',
        'social_listening': '💬 Social',
        'search_query': '🔍 Search',
        'user_quote': '💭 Quote',
        'behavioral_data': '📊 Analytics'
    }
    return badge_map.get(source_type, f'📄 {source_type}')

def display_evidence_sources(evidence_list, market=None):
    """Display evidence source counts by type"""
    
    # DEBUG: Show what we received
    st.write(f"DEBUG: Received {len(evidence_list) if evidence_list else 0} evidence items")
    
    if not evidence_list:
        st.warning("⚠️ No evidence found for this query")
        return
    
    # Count evidence by type
    type_counts = {}
    for ev in evidence_list:
        source_type = ev['source_type']
        if source_type not in type_counts:
            type_counts[source_type] = 0
        type_counts[source_type] += 1
    
    # DEBUG: Show what we counted
    st.write(f"DEBUG: Found {len(type_counts)} different source types: {list(type_counts.keys())}")
    
    st.markdown("**📚 Sources used for this answer:**")
    
    # Display counts in a simple, visible way
    badge_map = {
        'interview_transcript': '🎤 Interview',
        'social_listening': '💬 Social',
        'search_query': '🔍 Search',
        'user_quote': '💭 Quote',
        'behavioral_data': '📊 Analytics'
    }
    
    # Show as simple text with counts
    count_text = " | ".join([
        f"**{badge_map.get(source_type, source_type)}: {count}**" 
        for source_type, count in type_counts.items()
    ])
    
    st.markdown(count_text)
    st.markdown("")

# Load personas
def load_personas():
    result = supabase.table("personas").select("*").execute()
    return result.data if result.data else []

def search_evidence(query: str, market: str, limit: int = 5):
    query_embedding = embeddings.embed_query(query)
    
    # DEBUG - Check if we have evidence at all
    try:
        check_result = supabase.table("research_evidence").select("id, market, source_type, embedding").eq("market", market).limit(3).execute()
        st.write(f"🔍 DEBUG: Database check for market '{market}':")
        if check_result.data:
            st.write(f"   - Found {len(check_result.data)} evidence items in database")
            for item in check_result.data:
                has_embedding = item.get('embedding') is not None
                st.write(f"   - {item.get('source_type')}: Embedding = {'✅ Yes' if has_embedding else '❌ MISSING'}")
        else:
            st.error(f"   - ❌ No evidence found in database for market '{market}'")
    except Exception as e:
        st.error(f"   - Error checking database: {str(e)}")
    
    # Now try the search
    st.write(f"🔍 DEBUG: Searching with vector similarity (threshold=0.65)...")
    
    try:
        result = supabase.rpc(
            "search_evidence",
            {
                "query_embedding": query_embedding,
                "market_filter": market,
                "match_threshold": 0.65,
                "match_count": limit
            }
        ).execute()
        
        if result.data:
            st.success(f"   - ✅ Vector search found {len(result.data)} matching items")
        else:
            st.warning(f"   - ⚠️ Vector search returned 0 results (embeddings might be missing or no matches above threshold)")
        
        return result.data if result.data else []
    except Exception as e:
        st.error(f"   - ❌ Search function error: {str(e)}")
        st.info("   - This usually means the search_evidence function doesn't exist or has wrong parameters")
        return []

def generate_synthetic_response(persona, question, evidence_data, conversation_history):
    """Generate response using full conversation context and evidence"""
    
    # Build evidence context
    evidence_context = []
    for item in evidence_data:
        evidence_context.append(f"Source: {item['source_type']} ({item['market']})\nContent: {item['content']}\n---")
    
    evidence_text = "\n".join(evidence_context) if evidence_context else "No specific evidence found."
    
    # Build conversation history summary
    history_text = ""
    if conversation_history:
        history_text = "\n\nPrevious conversation context:\n"
        for item in conversation_history[-6:]:  # Last 3 exchanges (6 messages)
            history_text += f"User asked: {item['question']}\n"
            history_text += f"You responded: {item['answer']}\n\n"
    
    system_prompt = f"""You are {persona['name']}, a {persona['age']}-year-old {persona['occupation']} from {persona['market'].upper()}.

Your background: {persona['bio']}
Your pain points: {', '.join(persona.get('pain_points', []))}
Your goals: {', '.join(persona.get('goals', []))}

IMPORTANT INSTRUCTIONS:
1. Answer questions AS THIS PERSON in first person
2. Be authentic and conversational (2-4 sentences)
3. Use ONLY the evidence from {persona['market'].upper()} below - this is real data from your market
4. Remember the conversation history - build on previous answers
5. Stay consistent with what you've said before
6. Speak naturally as this persona would, reflecting your market's culture

Evidence from {persona['market'].upper()} research:
{evidence_text}
{history_text}

Now answer the current question naturally as a person from {persona['market'].upper()}, using the evidence from your market."""

    # Build message history for LLM
    messages = [SystemMessage(content=system_prompt)]
    
    # Add conversation history to maintain context
    for item in conversation_history[-4:]:  # Last 2 exchanges
        messages.append(HumanMessage(content=item['question']))
        messages.append(AIMessage(content=item['answer']))
    
    # Add current question
    messages.append(HumanMessage(content=question))
    
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
        
        # Show conversation context indicator
        if st.session_state.conversation:
            st.caption(f"📝 Conversation context: {len(st.session_state.conversation)} exchanges")
        
        st.markdown("---")
        
        # Display conversation
        for item in st.session_state.conversation:
            with st.chat_message("user"):
                st.write(item['question'])
            
            with st.chat_message("assistant", avatar="👤"):
                # Show evidence source COUNTS at TOP
                if item.get('evidence'):
                    display_evidence_sources(item['evidence'], persona['market'])
                    st.markdown("---")
                
                # Show answer
                st.write(item['answer'])
                
                # Show detailed evidence quotes (expandable)
                if item.get('evidence'):
                    with st.expander(f"📊 View {len(item['evidence'])} evidence quotes", expanded=False):
                        for ev in item['evidence']:
                            badge_text = get_evidence_badge(ev['source_type'])
                            st.markdown(f"**{badge_text}** • {ev['market'].upper()}")
                            st.info(f'"{ev["content"]}"')
                            if ev.get('metadata'):
                                st.caption(f"Metadata: {ev['metadata']}")
                            st.markdown("")
        
        # Chat input
        question = st.chat_input("Ask a question...")
        
        if question:
            with st.chat_message("user"):
                st.write(question)
            
            with st.chat_message("assistant", avatar="👤"):
                with st.spinner("Thinking..."):
                    # Get evidence from persona's market and global
                    local_evidence = search_evidence(question, persona['market'], limit=5)
                    global_evidence = search_evidence(question, 'global', limit=2)
                    all_evidence = local_evidence + global_evidence
                    
                    # FALLBACK: If no evidence found via vector search, get ANY evidence from market
                    if not all_evidence:
                        st.warning("⚠️ Vector search found nothing. Trying fallback: getting random evidence...")
                        try:
                            fallback = supabase.table("research_evidence").select("*").eq("market", persona['market']).limit(3).execute()
                            if fallback.data:
                                st.info(f"✅ Fallback found {len(fallback.data)} items (not semantically matched)")
                                all_evidence = fallback.data
                            else:
                                st.error("❌ Even fallback found nothing - database might be empty")
                        except Exception as e:
                            st.error(f"❌ Fallback error: {str(e)}")
                    
                    # Show evidence source COUNTS at TOP
                    if all_evidence:
                        display_evidence_sources(all_evidence, persona['market'])
                        st.markdown("---")
                    
                    # Generate response with full conversation context
                    answer = generate_synthetic_response(
                        persona, 
                        question, 
                        all_evidence,
                        st.session_state.conversation  # Pass full conversation history
                    )
                    st.write(answer)
                    
                    # Show detailed evidence quotes (expandable)
                    if all_evidence:
                        with st.expander(f"📊 View {len(all_evidence)} evidence quotes", expanded=False):
                            for ev in all_evidence:
                                badge_text = get_evidence_badge(ev['source_type'])
                                st.markdown(f"**{badge_text}** • {ev['market'].upper()}")
                                st.info(f'"{ev["content"]}"')
                                if ev.get('metadata'):
                                    st.caption(f"Metadata: {ev['metadata']}")
                                st.markdown("")
            
            # Save to conversation history
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
# Force update - Wed Jan 28 20:40:37 UTC 2026
