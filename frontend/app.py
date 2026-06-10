
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
    
    if "revised_key" not in st.session_state:
        st.session_state.revised_key = 0

    revised_pdf = st.file_uploader(
        "Upload Revised Contract",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"revised_{st.session_state.revised_key}"
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
    if not revised_pdf:
        st.warning("Please upload a revised contract")
    else:

        with st.spinner("Analyzing contract..."):

            files = []
            for pdf in revised_pdf:
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
                f"{FASTAPI_URL}/analyze",
                files=files
            )

        if response.status_code == 200:
            data = response.json()

            st.session_state.terminal_logs.extend([
                "",
                "> Starting analysis...",
                *data["logs"],
                ""
             ])

            for idx, result in enumerate(data["results"], start=1):
                st.session_state.terminal_logs.extend([
                    f"> Revised Contract #{idx} {result['revised_contract_name']}",
                    f"> Matched Contract: {result['matched_contract']}",
                    "",
                    result["analysis"],
                    "",
                    "-" * 80,
                    ""
                ])

            output_placeholder.code("\n".join(st.session_state.terminal_logs), language="bash")

        else:
            st.session_state.terminal_logs.append(
                f"> Analysis Failed ({response.status_code})"
            )

            st.session_state.terminal_logs.append(
                response.text
            )

            output_placeholder.code(
                "\n".join(st.session_state.terminal_logs),
                language="bash"
            )