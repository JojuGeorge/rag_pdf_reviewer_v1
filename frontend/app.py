
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

# --------------------------------------------------
# LEFT SIDE
# --------------------------------------------------

with left:

    st.subheader("Company Contract Upload")

    company_pdfs = st.file_uploader(
        "Upload Contracts",
        type=["pdf"],
        accept_multiple_files=True
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

            

            if response.status_code == 200:
                st.success("Contract uploaded successfully")
            else:
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

if upload_res:
    terminal_text = "\n".join(upload_res["logs"])

    output_placeholder.code(
        terminal_text,
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

            terminal_output = f"""
> Searching vector database...

> Similar contract found:
{data["matched_contract"]}

> Running comparison...

{data["analysis"]}
"""

            output_placeholder.code(
                terminal_output,
                language="bash"
            )

        else:
            output_placeholder.error(
                "Analysis failed"
            )