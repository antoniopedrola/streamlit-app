import streamlit as st
import os
from supabase import create_client
from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

# Simple config
st.set_page_config(page_title="Synthetic User Demo", page_icon="👤", layout="wide")

st.title("👤 Synthetic User Research Demo")
st.caption("Before/After: Generic vs. Grounded in Real Transcripts")

# Initialize
@st.cache_resource
def init_services():
    supabase = create_client(
        st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL")),
        st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
    )
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=st.secrets.get("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY")),
        temperature=0.7
    )
    return supabase, embeddings, llm

supabase, embeddings, llm = init_services()

# THE PERSONA (Component 1: Persona Profile JSON)
PERSONA = {
    "name": "Ji-woo Kim",
    "household": "Single, Seoul apartment",
    "age": 28,
    "occupation": "Digital Marketing Manager",
    "devices": ["Coupang Rocket delivery", "Naver Shopping app"],
    "routines": ["Online shopping 3-4x/week", "Check blog reviews before buying"],
    "tensions": ["Too many apps to download", "Delivery times matter", "Trust influencer vs real reviews"],
    "language_style": "informal, tech-savvy, a bit impatient"
}

# Component 3: Retriever - Get relevant transcript chunks
def retrieve_evidence(question: str, limit: int = 3):
    """Retrieve top relevant transcript chunks"""
    query_embedding = embeddings.embed_query(question)
    
    result = supabase.rpc(
        "search_evidence",
        {
            "query_embedding": query_embedding,
            "market_filter": "korea",
            "match_threshold": 0.60,
            "match_count": limit
        }
    ).execute()
    
    return result.data if result.data else []

# Component 4: Synthetic User Prompts
def generate_response(question: str, use_transcripts: bool = False):
    """Generate response - with or without transcript grounding"""
    
    # Base persona context
    persona_text = f"""You are {PERSONA['name']}, a {PERSONA['age']}-year-old {PERSONA['occupation']} living in {PERSONA['household']}.

Your situation:
- Devices you use: {', '.join(PERSONA['devices'])}
- Your routines: {', '.join(PERSONA['routines'])}
- Your tensions: {', '.join(PERSONA['tensions'])}

Speak in this style: {PERSONA['language_style']}"""

    if use_transcripts:
        # AFTER: With transcript grounding
        evidence = retrieve_evidence(question, limit=3)
        
        if evidence:
            evidence_text = "\n\n".join([
                f"Real quote from research: \"{ev['content']}\""
                for ev in evidence
            ])
            
            system_prompt = f"""{persona_text}

CRITICAL INSTRUCTIONS:
- Answer based ONLY on the real quotes below and your persona profile
- NEVER invent facts, ownership, or experiences not in the quotes
- If you're unsure or the quotes don't cover it, say "I'm not sure" or "that wasn't mentioned"
- Prefer direct evidence from the quotes when possible

Real research quotes:
{evidence_text}"""
        else:
            evidence = []
            system_prompt = f"""{persona_text}

Note: No specific research quotes found for this question. Answer based only on your persona profile, and acknowledge uncertainty."""
    else:
        # BEFORE: Generic (persona only, no transcripts)
        evidence = []
        system_prompt = f"""{persona_text}

Answer the question based on your persona profile."""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question)
    ]
    
    response = llm.invoke(messages)
    return response.content, evidence

# UI: Component 5 - Calibration Switch
st.markdown("---")

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader(f"Talking to: {PERSONA['name']}")
    st.caption(f"{PERSONA['age']} • {PERSONA['occupation']} • Seoul, Korea")
with col2:
    mode = st.radio(
        "**Grounding Mode:**",
        ["BEFORE: Generic (Persona only)", "AFTER: Grounded (Persona + Transcripts)"],
        key="mode"
    )

use_grounding = "AFTER" in mode

# Show what's different
if use_grounding:
    st.info("🎯 **GROUNDED MODE**: Answers use real interview transcripts + persona profile. Shows supporting evidence.")
else:
    st.warning("⚠️ **GENERIC MODE**: Answers use only persona profile. No real data - just assumptions.")

st.markdown("---")

# Chat interface
question = st.text_input("Ask a question:", placeholder="e.g., What frustrates you about online shopping?")

if st.button("Ask", type="primary") or question:
    if question:
        with st.spinner("Thinking..."):
            answer, evidence = generate_response(question, use_grounding)
        
        # Show the answer
        st.markdown("### 💬 Response:")
        st.markdown(f"> {answer}")
        
        # Component 6: Trace/Evidence Panel
        if use_grounding and evidence:
            st.markdown("---")
            st.markdown("### 📊 Supporting Evidence (from real transcripts)")
            st.caption("These actual quotes were used to ground the response:")
            
            for idx, ev in enumerate(evidence, 1):
                with st.container():
                    col1, col2 = st.columns([1, 10])
                    with col1:
                        st.markdown(f"**{idx}.**")
                    with col2:
                        st.info(f'"{ev["content"]}"')
                        st.caption(f"Source: {ev['source_type']} • Market: {ev['market'].upper()}")
        
        elif use_grounding and not evidence:
            st.warning("⚠️ No transcript evidence found for this question - answer based on persona only")

# Sidebar: Show the persona profile
with st.sidebar:
    st.markdown("## 📋 Persona Profile")
    st.json(PERSONA)
    
    st.markdown("---")
    st.markdown("## 🎯 Demo Purpose")
    st.markdown("""
    **Show the difference:**
    
    **BEFORE (Generic)**  
    ❌ Synthetic user makes assumptions  
    ❌ No supporting evidence  
    ❌ Could be making things up  
    
    **AFTER (Grounded)**  
    ✅ Answers backed by real quotes  
    ✅ Shows the evidence used  
    ✅ Transparent and trustworthy  
    """)
    
    st.markdown("---")
    st.markdown("## 💡 Try These Questions")
    st.markdown("""
    - What frustrates you about online shopping?
    - How do you discover new products?
    - What makes you trust a seller?
    - Why do you prefer certain platforms?
    - What stops you from buying?
    """)

st.markdown("---")
st.caption("Built with Streamlit + Supabase (pgvector) + Claude API • Synthetic User Research Demo")
