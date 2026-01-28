import streamlit as st

st.title("Persona-Aware Interview Assistant")

persona = st.selectbox("Select persona", personas)

query = st.chat_input("Ask a question")

if query:
    response = run_langgraph(query, persona)
    st.chat_message("assistant").write(response["answer"])

    with st.expander("Sources"):
        for src in response["sources"]:
            st.write(src)

