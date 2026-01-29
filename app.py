import streamlit as st
import os
import json

# Page config
st.set_page_config(
    page_title="Synthetic User Research", 
    page_icon="👥", 
    layout="wide"
)

# Initialize session state
if "selected_persona" not in st.session_state:
    st.session_state.selected_persona = None
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "show_debug" not in st.session_state:
    st.session_state.show_debug = False

# Sidebar - Debug Toggle
with st.sidebar:
    st.title("⚙️ Settings")
    st.session_state.show_debug = st.checkbox(
        "🔍 Show Debug Info", 
        value=st.session_state.show_debug,
        help="Show detailed debug information and initialization messages"
    )
    st.markdown("---")

st.title("👥 Synthetic User Research Assistant")
st.caption("Ask questions to personas backed by real research data")

# Helper function for debug output
def debug_print(message, type="info"):
    """Only print if debug mode is enabled"""
    if st.session_state.show_debug:
        if type == "info":
            st.info(message)
        elif type == "success":
            st.success(message)
        elif type == "warning":
            st.warning(message)
        elif type == "error":
            st.error(message)
        else:
            st.write(message)

# Initialize connections
@st.cache_resource
def init_supabase():
    debug_print("🔧 Initializing Supabase connection...")
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
    if not url or not key:
        return None
    from supabase import create_client
    debug_print("✅ Supabase connected", "success")
    return create_client(url, key)

@st.cache_resource
def init_embeddings():
    debug_print("🤖 Loading embedding model (sentence-transformers)...")
    from langchain_community.embeddings import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    debug_print("✅ Embedding model loaded (384 dimensions)", "success")
    return embeddings

def init_llm():
    debug_print("🧠 Initializing Claude LLM...")
    from langchain_anthropic import ChatAnthropic
    api_key = st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY"))
    if not api_key:
        return None
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=api_key,
        temperature=0.8,
        max_tokens=2048
    )
    debug_print("✅ Claude initialized", "success")
    return llm

# Initialize services
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

# Initialize embeddings
with st.spinner("Loading AI models..." if not st.session_state.show_debug else None):
    embeddings = init_embeddings()

debug_print("✅ All systems initialized and ready!", "success")

# Helper functions
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
    
    if st.session_state.show_debug:
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
    
    if st.session_state.show_debug:
        st.write(f"DEBUG: Found {len(type_counts)} different source types: {list(type_counts.keys())}")
    
    st.markdown("**📚 Sources used for this answer:**")
    
    # Display counts
    badge_map = {
        'interview_transcript': '🎤 Interview',
        'social_listening': '💬 Social',
        'search_query': '🔍 Search',
        'user_quote': '💭 Quote',
        'behavioral_data': '📊 Analytics'
    }
    
    count_text = " | ".join([
        f"**{badge_map.get(source_type, source_type)}: {count}**" 
        for source_type, count in type_counts.items()
    ])
    
    st.markdown(count_text)
    st.markdown("")

# Load personas
def load_personas():
    debug_print("📋 Loading personas from database...")
    result = supabase.table("personas").select("*").execute()
    debug_print(f"✅ Loaded {len(result.data) if result.data else 0} personas", "success")
    return result.data if result.data else []

def search_evidence(question: str, market: str, limit: int = 5):
    query_embedding = embeddings.embed_query(question)
    
    debug_info = []
    
    # Check if we have evidence
    if st.session_state.show_debug:
        try:
            check_result = supabase.table("research_evidence").select("id, market, source_type, embedding").eq("market", market).limit(3).execute()
            debug_info.append(f"🔍 DEBUG: Database check for market '{market}':")
            if check_result.data:
                debug_info.append(f"   - Found {len(check_result.data)} evidence items in database")
                for item in check_result.data:
                    has_embedding = item.get('embedding') is not None
                    debug_info.append(f"   - {item.get('source_type')}: Embedding = {'✅ Yes' if has_embedding else '❌ MISSING'}")
            else:
                debug_info.append(f"   - ❌ No evidence found in database for market '{market}'")
        except Exception as e:
            debug_info.append(f"   - Error checking database: {str(e)}")
        
        debug_info.append(f"🔍 DEBUG: Searching with vector similarity (threshold=0.65)...")
    
    # Try vector search
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
        
        if st.session_state.show_debug:
            if result.data:
                debug_info.append(f"   - ✅ Vector search found {len(result.data)} matching items")
            else:
                debug_info.append(f"   - ⚠️ Vector search returned 0 results (embeddings might be missing or no matches above threshold)")
        
        return result.data if result.data else [], debug_info
    except Exception as e:
        if st.session_state.show_debug:
            debug_info.append(f"   - ❌ Search function error: {str(e)}")
            debug_info.append("   - This usually means the search_evidence function doesn't exist or has wrong parameters")
        return [], debug_info

def generate_synthetic_response(persona, question, evidence_data, conversation_history):
    """Generate response using full conversation context and evidence"""
    
    # Build evidence context
    evidence_context = []
    for item in evidence_data:
        evidence_context.append(f"Source: {item['source_type']} ({item['market']})\nContent: {item['content']}\n---")
    
    evidence_text = "\n".join(evidence_context) if evidence_context else "No specific evidence found."
    
    # Build conversation history
    history_text = ""
    if conversation_history:
        history_text = "\n\nPrevious conversation context:\n"
        for item in conversation_history[-6:]:
            history_text += f"User asked: {item['question']}\n"
            history_text += f"You responded: {item['answer']}\n\n"
    
    # Updated persona prompt format
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    
    system_prompt = f"""You are {persona['name']}.

Your household: {persona.get('household', 'Not specified')}
Your devices: {', '.join(persona.get('devices', []))}
Your routines: {', '.join(persona.get('routines', []))}
Your tensions: {', '.join(persona.get('tensions', []))}

Speak in this style: {persona.get('language_style', 'conversational')}

IMPORTANT INSTRUCTIONS:
1. Answer questions AS THIS PERSON in first person
2. Be authentic and conversational (2-4 sentences)
3. Use the evidence below to inform your answer
4. Remember the conversation history - build on previous answers
5. Stay consistent with what you've said before
6. Speak naturally as this persona would

Evidence from research:
{evidence_text}
{history_text}

Now answer the current question naturally, considering both the evidence and our conversation so far."""

    messages = [SystemMessage(content=system_prompt)]
    
    # Add conversation history
    for item in conversation_history[-4:]:
        messages.append(HumanMessage(content=item['question']))
        messages.append(AIMessage(content=item['answer']))
    
    messages.append(HumanMessage(content=question))
    
    return llm.invoke(messages).content

# Load personas
personas = load_personas()

if not personas:
    st.warning("⚠️ No personas found. Please run database setup first.")
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
            display_name = f"{persona['name']}"
            if persona.get('household'):
                display_name += f"\n{persona['household']}"
            
            if st.button(
                display_name,
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
        household_info = persona.get('household', f"{persona.get('age', '')} • {persona.get('occupation', '')} • {persona['market'].upper()}")
        st.caption(household_info)
    with col2:
        if st.button("🔄 Change Persona", use_container_width=True):
            st.session_state.selected_persona = None
            st.session_state.conversation = []
            st.rerun()
    
    with st.expander("📋 Persona Profile"):
        # Display new persona structure
        if persona.get('household'):
            st.write(f"**Household:** {persona['household']}")
        if persona.get('devices'):
            st.write(f"**Devices:** {', '.join(persona['devices'])}")
        if persona.get('routines'):
            st.write(f"**Routines:** {', '.join(persona['routines'])}")
        if persona.get('tensions'):
            st.write(f"**Tensions:** {', '.join(persona['tensions'])}")
        if persona.get('language_style'):
            st.write(f"**Language Style:** {persona['language_style']}")
        
        # Fallback to old structure
        if persona.get('bio'):
            st.write(f"**Bio:** {persona['bio']}")
        if persona.get('pain_points'):
            st.write(f"**Pain Points:** {', '.join(persona['pain_points'])}")
        if persona.get('goals'):
            st.write(f"**Goals:** {', '.join(persona['goals'])}")
    
    if st.session_state.conversation:
        st.caption(f"📝 Conversation context: {len(st.session_state.conversation)} exchanges")
    
    st.markdown("---")
    
    # Display conversation
    for item in st.session_state.conversation:
        with st.chat_message("user"):
            st.write(item['question'])
        
        with st.chat_message("assistant", avatar="👤"):
            # Show DEBUG info if enabled
            if st.session_state.show_debug and item.get('debug_info'):
                with st.expander("🔍 Debug Info", expanded=False):
                    for debug_line in item['debug_info']:
                        st.text(debug_line)
            
            # Show evidence counts
            if item.get('evidence'):
                display_evidence_sources(item['evidence'], persona.get('market'))
                st.markdown("---")
            
            # Show answer
            st.write(item['answer'])
            
            # Show detailed evidence
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
                all_debug_info = []
                
                # Get evidence
                local_evidence, local_debug = search_evidence(question, persona.get('market', 'korea'), limit=5)
                all_debug_info.extend(local_debug)
                
                global_evidence, global_debug = search_evidence(question, 'global', limit=2)
                all_debug_info.extend(global_debug)
                
                all_evidence = local_evidence + global_evidence
                
                # Fallback
                if not all_evidence:
                    all_debug_info.append("⚠️ Vector search found nothing. Trying fallback: getting random evidence...")
                    try:
                        fallback = supabase.table("research_evidence").select("*").eq("market", persona.get('market', 'korea')).limit(3).execute()
                        if fallback.data:
                            all_debug_info.append(f"✅ Fallback found {len(fallback.data)} items (not semantically matched)")
                            all_evidence = fallback.data
                        else:
                            all_debug_info.append("❌ Even fallback found nothing - database might be empty")
                    except Exception as e:
                        all_debug_info.append(f"❌ Fallback error: {str(e)}")
            
            # Display debug info if enabled
            if st.session_state.show_debug and all_debug_info:
                with st.expander("🔍 Debug Info", expanded=False):
                    for debug_line in all_debug_info:
                        st.text(debug_line)
            
            # Show evidence counts
            if all_evidence:
                display_evidence_sources(all_evidence, persona.get('market'))
                st.markdown("---")
            
            # Generate response
            answer = generate_synthetic_response(
                persona, 
                question, 
                all_evidence,
                st.session_state.conversation
            )
            st.write(answer)
            
            # Show detailed evidence
            if all_evidence:
                with st.expander(f"📊 View {len(all_evidence)} evidence quotes", expanded=False):
                    for ev in all_evidence:
                        badge_text = get_evidence_badge(ev['source_type'])
                        st.markdown(f"**{badge_text}** • {ev['market'].upper()}")
                        st.info(f'"{ev["content"]}"')
                        if ev.get('metadata'):
                            st.caption(f"Metadata: {ev['metadata']}")
                        st.markdown("")
        
        # Save to conversation
        st.session_state.conversation.append({
            'question': question,
            'answer': answer,
            'evidence': all_evidence,
            'debug_info': all_debug_info if st.session_state.show_debug else []
        })
        st.rerun()

# Sidebar info
with st.sidebar:
    st.markdown("## 📖 About")
    st.markdown("""
    This app lets you talk to synthetic user personas 
    backed by real research data.
    
    **Features:**
    - Evidence from real interviews
    - Conversation memory
    - Multi-market support
    """)

st.markdown("---")
st.caption("Powered by Claude + Supabase • Synthetic User Research")