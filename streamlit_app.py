import streamlit as st
import os
from datetime import datetime
from supabase import create_client, Client
from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import HumanMessage, SystemMessage
import json

# Page config
st.set_page_config(
    page_title="Synthetic User Research", 
    page_icon="👥", 
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .quote-box {
        background-color: #f9f9f9;
        border-left: 4px solid #2196F3;
        padding: 15px;
        margin: 10px 0;
        font-style: italic;
    }
    .market-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 12px;
        font-weight: bold;
        margin-right: 5px;
    }
    .korea { background-color: #e3f2fd; color: #1976d2; }
    .poland { background-color: #fce4ec; color: #c2185b; }
    .turkey { background-color: #fff3e0; color: #f57c00; }
    .global { background-color: #e8f5e9; color: #388e3c; }
</style>
""", unsafe_allow_html=True)

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
        st.error("⚠️ Please set SUPABASE_URL and SUPABASE_KEY")
        st.stop()
    return create_client(url, key)

@st.cache_resource
def init_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def init_llm():
    api_key = st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY"))
    if not api_key:
        st.error("⚠️ Please set ANTHROPIC_API_KEY")
        st.stop()
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=api_key,
        temperature=0.8,
        max_tokens=2048
    )

supabase = init_supabase()
embeddings = init_embeddings()
llm = init_llm()

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

# Main App
st.title("👥 Synthetic User Research Assistant")
st.markdown("Ask questions to real user personas backed by research data from Korea, Poland, and Turkey")

# Sidebar
with st.sidebar:
    st.header("📊 About")
    
    if st.button("🔄 Refresh Data"):
        st.cache_resource.clear()
        st.rerun()
    
    st.markdown("---")
    
    with st.expander("ℹ️ How it works"):
        st.markdown("""
        1. Select a persona from a market
        2. Ask questions about their needs/behaviors
        3. Get authentic responses backed by:
           - Interview transcripts
           - Social listening
           - Search queries
        4. See real quotes and evidence
        """)
    
    with st.expander("💡 Example Questions"):
        st.markdown("""
        - What frustrates you about shopping online?
        - How do you discover new products?
        - What's your biggest challenge right now?
        - Why do you prefer this brand?
        """)

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
                    st.markdown(
                        f'<span class="market-badge {market_class}">{ev["market"].upper()}</span>'
                        f'<span style="color: #666; font-size: 12px;">  {ev["source_type"]}</span>', 
                        unsafe_allow_html=True
                    )
                    st.markdown(f'<div class="quote-box">"{ev["content"]}"</div>', unsafe_allow_html=True)
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
                        market_class = ev['market'].lower()
                        st.markdown(
                            f'<span class="market-badge {market_class}">{ev["market"].upper()}</span>'
                            f'<span style="color: #666; font-size: 12px;">  {ev["source_type"]}</span>', 
                            unsafe_allow_html=True
                        )
                        st.markdown(f'<div class="quote-box">"{ev["content"]}"</div>', unsafe_allow_html=True)
                        st.markdown("")
        
        st.session_state.conversation.append({
            'question': question,
            'answer': answer,
            'evidence': all_evidence
        })
        st.rerun()

st.markdown("---")
st.caption("Powered by Claude + Supabase • Synthetic User Research")

