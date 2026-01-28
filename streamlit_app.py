import streamlit as st

st.title("Persona-Aware Interview Assistant")


personas = ["Alex", "Jamie", "Sam"]

persona = st.selectbox("Select persona", personas)

st.write("Selected persona:", persona)

query = st.chat_input("Ask a question")

if query:
    response = run_langgraph(query, persona)
    st.chat_message("assistant").write(response["answer"])

    with st.expander("Sources"):
        for src in response["sources"]:
            st.write(src)

