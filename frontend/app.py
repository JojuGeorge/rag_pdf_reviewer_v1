
import streamlit as st
import requests

FASTAPI_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Contract Comparison",
    layout="wide"
)

st.title("📄 Contract Comparison System")

left, right = st.columns(2)
upload_res=""

if "terminal_logs" not in st.session_state:
    st.session_state.terminal_logs = [
        "> Contract Comparison System",
        "> Waiting for action...",
        ""
    ]

# --------------------------------------------------
# LEFT SIDE
# --------------------------------------------------

with left:

    st.subheader("Company Contract Upload")
    
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    company_pdfs = st.file_uploader(
        "Upload Contracts",
        type=["pdf"],
        accept_multiple_files=True,
            key=f"company_uploader_{st.session_state.uploader_key}"
    )

    if st.button("Upload Contract"):
        if company_pdfs:
            files = []
            for pdf in company_pdfs:
                files.append(
                    (
                        "files",
                        (
                            pdf.name,
                            pdf,
                            "application/pdf"
                        )
                    )
                )
            response = requests.post(
                f"{FASTAPI_URL}/upload-contracts",
                files=files
            )
            
            upload_res = response.json()
            st.session_state.terminal_logs.extend([
                "",
                "> Uploading contract(s)...",
                *upload_res["logs"],
                "> Upload complete."
            ])

            if response.status_code == 200:
                st.session_state.terminal_logs.append("> Contract uploaded successfully")   
                
                st.session_state.uploader_key += 1
                st.rerun()
            else:
                st.session_state.terminal_logs.append(f"Upload failed: {response.status_code}\n{response.text}")
                 
                st.error(f"Upload failed: {response.status_code}\n{response.text}"
)


# --------------------------------------------------
# RIGHT SIDE
# --------------------------------------------------

with right:

    st.subheader("Revised Contract")

    revised_pdf = st.file_uploader(
        "Upload Revised Contract",
        type=["pdf"],
        key="revised_pdf"
    )

    analyze_clicked = st.button(
        "Analyze Contract",
        type="primary"
    )

# --------------------------------------------------
# OUTPUT AREA
# --------------------------------------------------

st.divider()
st.subheader("Output")

output_placeholder = st.empty()

output_placeholder.code(
    "\n".join(st.session_state.terminal_logs),
    language="bash"
)

if analyze_clicked:
    if revised_pdf is None:
        st.warning("Please upload a revised contract")
    else:

        with st.spinner("Analyzing contract..."):

            files = {
                "file": (
                    revised_pdf.name,
                    revised_pdf,
                    "application/pdf"
                )
            }

            response = requests.post(
                f"{FASTAPI_URL}/analyze",
                files=files
            )

        if response.status_code == 200:
            data = response.json()

            st.session_state.terminal_logs.extend([
    "",
    "> Searching vector database...",
    f"> Similar contract found: {data['matched_contract']}",
    "",
    "> Running comparison...",
    data["analysis"]
])

            output_placeholder.code(
    "\n".join(st.session_state.terminal_logs),
    language="bash"
)

        else:
            output_placeholder.error(
                "\n".join(st.session_state.terminal_logs.append("Analysis Failed...")),
    language="bash"
            )