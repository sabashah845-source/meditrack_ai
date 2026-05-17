# =========================================================
# app.py
# AI Pharmacy Batch & Expiry Tracking System
# Single File Streamlit Application
# =========================================================

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import yagmail
import os

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="MediTrack AI",
    page_icon="💊",
    layout="wide"
)

# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

.main {
    background-color: #f5f7fa;
}

h1, h2, h3 {
    color: #023047;
}

.stButton>button {
    background-color: #0077b6;
    color: white;
    border-radius: 10px;
    height: 3em;
    width: 100%;
    font-size: 16px;
}

.stDownloadButton>button {
    background-color: #2a9d8f;
    color: white;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE
# =========================================================

conn = sqlite3.connect(
    "pharmacy.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS medicines (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    medicine_name TEXT,
    batch_no TEXT,
    mfg_date TEXT,
    expiry_date TEXT,
    quantity INTEGER,
    supplier TEXT
)
""")

conn.commit()

# =========================================================
# EMAIL CONFIGURATION
# =========================================================

EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"

EMAIL_RECEIVER = "receiver_email@gmail.com"

# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def insert_medicine(
    medicine_name,
    batch_no,
    mfg_date,
    expiry_date,
    quantity,
    supplier
):

    cursor.execute("""
    INSERT INTO medicines (
        medicine_name,
        batch_no,
        mfg_date,
        expiry_date,
        quantity,
        supplier
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        medicine_name,
        batch_no,
        mfg_date,
        expiry_date,
        quantity,
        supplier
    ))

    conn.commit()


def fetch_data():

    query = "SELECT * FROM medicines"

    df = pd.read_sql_query(query, conn)

    return df

# =========================================================
# EXPIRY STATUS
# =========================================================

def calculate_status(expiry_date):

    today = datetime.today()

    expiry = datetime.strptime(
        str(expiry_date),
        "%Y-%m-%d"
    )

    days_left = (expiry - today).days

    if days_left < 0:
        return "EXPIRED", days_left

    elif days_left <= 30:
        return "HIGH RISK", days_left

    elif days_left <= 90:
        return "MEDIUM RISK", days_left

    else:
        return "SAFE", days_left

# =========================================================
# PDF REPORT GENERATOR
# =========================================================

def generate_pdf(df):

    os.makedirs("reports", exist_ok=True)

    pdf_path = "reports/expiry_report.pdf"

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter
    )

    styles = getSampleStyleSheet()

    elements = []

    title = Paragraph(
        "💊 Pharmacy Expiry Report",
        styles["Title"]
    )

    elements.append(title)

    elements.append(Spacer(1, 20))

    generated = Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        styles["Normal"]
    )

    elements.append(generated)

    elements.append(Spacer(1, 20))

    table_data = [[
        "Medicine",
        "Batch",
        "Expiry",
        "Quantity",
        "Days Left",
        "Status"
    ]]

    for _, row in df.iterrows():

        status, days_left = calculate_status(
            row["expiry_date"]
        )

        table_data.append([
            row["medicine_name"],
            row["batch_no"],
            row["expiry_date"],
            row["quantity"],
            days_left,
            status
        ])

    table = Table(table_data)

    table.setStyle(TableStyle([

        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

        ("GRID", (0, 0), (-1, -1), 1, colors.black),

        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),

        ("ALIGN", (0, 0), (-1, -1), "CENTER"),

    ]))

    elements.append(table)

    doc.build(elements)

    return pdf_path

# =========================================================
# EMAIL ALERT FUNCTION
# =========================================================

def send_expiry_alert():

    df = fetch_data()

    if df.empty:

        st.warning("No inventory data found.")

        return

    alert_data = []

    for _, row in df.iterrows():

        status, days_left = calculate_status(
            row["expiry_date"]
        )

        if status in ["HIGH RISK", "EXPIRED"]:

            alert_data.append({
                "Medicine": row["medicine_name"],
                "Batch": row["batch_no"],
                "Expiry": row["expiry_date"],
                "Days Left": days_left,
                "Status": status
            })

    if len(alert_data) == 0:

        st.success("No high-risk medicines found.")

        return

    alert_df = pd.DataFrame(alert_data)

    message = f"""
AI Pharmacy Expiry Alert

Critical Medicines Detected:
{len(alert_df)}

{alert_df.to_string(index=False)}

Recommended Actions:
- Remove expired medicines
- Prioritize near-expiry sales
- Contact suppliers
- Review inventory immediately

Generated by MediTrack AI
"""

    try:

        yag = yagmail.SMTP(
            EMAIL_SENDER,
            EMAIL_PASSWORD
        )

        yag.send(
            to=EMAIL_RECEIVER,
            subject="🚨 Pharmacy Expiry Alert",
            contents=message
        )

        st.success("Expiry alert email sent successfully!")

    except Exception as e:

        st.error(f"Email Error: {e}")

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("💊 MediTrack AI")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Add Medicine",
        "Upload Inventory",
        "Expiry Report",
        "AI Insights"
    ]
)

# =========================================================
# DASHBOARD
# =========================================================

if menu == "Dashboard":

    st.title("📊 Pharmacy Dashboard")

    df = fetch_data()

    if df.empty:

        st.warning("No inventory data available.")

    else:

        statuses = []
        days_list = []

        for expiry in df["expiry_date"]:

            status, days = calculate_status(expiry)

            statuses.append(status)
            days_list.append(days)

        df["status"] = statuses
        df["days_left"] = days_list

        total = len(df)

        expired = len(df[df["status"] == "EXPIRED"])

        high = len(df[df["status"] == "HIGH RISK"])

        medium = len(df[df["status"] == "MEDIUM RISK"])

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Medicines", total)
        col2.metric("Expired", expired)
        col3.metric("High Risk", high)
        col4.metric("Medium Risk", medium)

        st.markdown("---")

        fig = px.pie(
            df,
            names="status",
            title="Expiry Status Distribution"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.markdown("## 📋 Inventory Table")

        st.dataframe(
            df,
            use_container_width=True
        )

# =========================================================
# ADD MEDICINE
# =========================================================

elif menu == "Add Medicine":

    st.title("➕ Add Medicine")

    with st.form("medicine_form"):

        medicine_name = st.text_input(
            "Medicine Name"
        )

        batch_no = st.text_input(
            "Batch Number"
        )

        mfg_date = st.date_input(
            "Manufacturing Date"
        )

        expiry_date = st.date_input(
            "Expiry Date"
        )

        quantity = st.number_input(
            "Quantity",
            min_value=1
        )

        supplier = st.text_input(
            "Supplier"
        )

        submit = st.form_submit_button(
            "Save Medicine"
        )

        if submit:

            insert_medicine(
                medicine_name,
                batch_no,
                str(mfg_date),
                str(expiry_date),
                quantity,
                supplier
            )

            st.success(
                "Medicine added successfully!"
            )

# =========================================================
# UPLOAD INVENTORY
# =========================================================

elif menu == "Upload Inventory":

    st.title("📤 Upload Inventory")

    upload_option = st.radio(
        "Choose Upload Method",
        [
            "Upload CSV",
            "Upload Excel",
            "Manual Inventory Entry"
        ],
        key="upload_option"
    )
    st.info("Select the upload method below to import your inventory data.")

    # =====================================================
    # CSV UPLOAD
    # =====================================================

    if upload_option == "Upload CSV":

        uploaded_file = st.file_uploader(
            "Upload CSV File",
            type=["csv"]
            ,
            key="csv_uploader"
        )

        if uploaded_file:

            df = pd.read_csv(uploaded_file)

            st.dataframe(df)

            if st.button("Import CSV Data"):

                for _, row in df.iterrows():

                    insert_medicine(
                        row["medicine_name"],
                        row["batch_no"],
                        row["mfg_date"],
                        row["expiry_date"],
                        int(row["quantity"]),
                        row["supplier"]
                    )

                st.success(
                    "CSV imported successfully!"
                )

    # =====================================================
    # EXCEL UPLOAD
    # =====================================================

    elif upload_option == "Upload Excel":

        uploaded_excel = st.file_uploader(
            "Upload Excel File",
            type=["xlsx"]
            ,
            key="excel_uploader"
        )

        if uploaded_excel:

            df = pd.read_excel(uploaded_excel)

            st.dataframe(df)

            if st.button("Import Excel Data"):

                for _, row in df.iterrows():

                    insert_medicine(
                        row["medicine_name"],
                        row["batch_no"],
                        str(row["mfg_date"]),
                        str(row["expiry_date"]),
                        int(row["quantity"]),
                        row["supplier"]
                    )

                st.success(
                    "Excel imported successfully!"
                )

    # =====================================================
    # MANUAL INVENTORY ENTRY
    # =====================================================

    elif upload_option == "Manual Inventory Entry":

        st.markdown("## ✍ Manual Inventory Sheet")

        manual_df = pd.DataFrame({

            "medicine_name": [""],
            "batch_no": [""],
            "mfg_date": [""],
            "expiry_date": [""],
            "quantity": [0],
            "supplier": [""]

        })

        edited_df = st.data_editor(
            manual_df,
            num_rows="dynamic",
            use_container_width=True
        )

        if st.button("Save Inventory"):

            try:

                for _, row in edited_df.iterrows():

                    if row["medicine_name"] != "":

                        insert_medicine(
                            row["medicine_name"],
                            row["batch_no"],
                            str(row["mfg_date"]),
                            str(row["expiry_date"]),
                            int(row["quantity"]),
                            row["supplier"]
                        )

                st.success(
                    "Inventory saved successfully!"
                )

            except Exception as e:

                st.error(f"Error: {e}")

# =========================================================
# EXPIRY REPORT
# =========================================================

elif menu == "Expiry Report":

    st.title("📄 Expiry Report")

    df = fetch_data()

    if df.empty:

        st.warning("No inventory data available.")

    else:

        statuses = []
        days_list = []

        for expiry in df["expiry_date"]:

            status, days = calculate_status(expiry)

            statuses.append(status)
            days_list.append(days)

        df["status"] = statuses
        df["days_left"] = days_list

        st.dataframe(df)

        if st.button("Generate PDF Report"):

            pdf_path = generate_pdf(df)

            st.success("PDF report generated!")

            with open(pdf_path, "rb") as file:

                st.download_button(
                    label="⬇ Download PDF",
                    data=file,
                    file_name="expiry_report.pdf",
                    mime="application/pdf"
                )

# =========================================================
# AI INSIGHTS
# =========================================================

elif menu == "AI Insights":

    st.title("🤖 AI Insights")

    df = fetch_data()

    if df.empty:

        st.warning("No inventory data found.")

    else:

        statuses = []
        days_list = []

        for expiry in df["expiry_date"]:

            status, days = calculate_status(expiry)

            statuses.append(status)
            days_list.append(days)

        df["status"] = statuses
        df["days_left"] = days_list

        expired = df[df["status"] == "EXPIRED"]

        high = df[df["status"] == "HIGH RISK"]

        medium = df[df["status"] == "MEDIUM RISK"]

        st.info(f"""
AI Analysis Summary

• Expired Medicines: {len(expired)}
• High Risk Medicines: {len(high)}
• Medium Risk Medicines: {len(medium)}

Recommendations:
- Remove expired medicines
- Prioritize near-expiry stock
- Contact suppliers
- Monitor inventory weekly
""")

        st.markdown("## 🚨 High Risk Medicines")

        st.dataframe(high)

        st.markdown("## ❌ Expired Medicines")

        st.dataframe(expired)

        # =====================================================
        # SEND EMAIL ALERT
        # =====================================================

        if st.button("📧 Send Expiry Alert Email"):

            send_expiry_alert()

# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.markdown(
    "<center>💊 MediTrack AI | AI Pharmacy Batch & Expiry Tracking System</center>",
    unsafe_allow_html=True
)