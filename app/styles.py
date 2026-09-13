import streamlit as st


def apply_theme():
    st.markdown(
        """
        <style>

        /* ================================
           GLOBAL TYPOGRAPHY
           ================================ */

        .stApp {
            font-family: "Segoe UI", Arial, sans-serif;
        }

        h1 {
            font-size: 2.45rem !important;
            font-weight: 650 !important;
            letter-spacing: -0.025em !important;
            line-height: 1.15 !important;
            margin-bottom: 0.35rem !important;
        }

        h2 {
            font-size: 1.65rem !important;
            font-weight: 600 !important;
            letter-spacing: -0.015em !important;
            line-height: 1.25 !important;
            margin-top: 0.6rem !important;
            margin-bottom: 0.45rem !important;
        }

        h3 {
            font-size: 1.15rem !important;
            font-weight: 600 !important;
            line-height: 1.3 !important;
        }

        p {
            line-height: 1.55;
        }


        /* ================================
           MAIN CONTENT WIDTH / SPACING
           ================================ */

        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
            max-width: 1450px;
        }


        /* ================================
           METRIC CARDS
           ================================ */

        div[data-testid="stMetric"] {
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 8px;
            padding: 14px 16px;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.82rem;
            font-weight: 500;
        }

        div[data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 650;
        }


        /* ================================
           BUTTONS
           ================================ */

        .stButton > button {
            border-radius: 7px;
            min-height: 42px;
            font-weight: 500;
            transition: border-color 0.15s ease;
        }

        .stButton > button:hover {
            border-color: rgba(255, 255, 255, 0.45);
        }


        /* ================================
           SELECT BOXES
           ================================ */

        div[data-baseweb="select"] > div {
            border-radius: 7px;
        }


        /* ================================
           ALERTS
           ================================ */

        div[data-testid="stAlert"] {
            border-radius: 8px;
        }


        /* ================================
           DIVIDERS
           ================================ */

        hr {
            margin-top: 1.4rem;
            margin-bottom: 1.4rem;
            border-color: rgba(255, 255, 255, 0.14);
        }


        /* ================================
           CAPTIONS / SECONDARY TEXT
           ================================ */

        .stCaption {
            line-height: 1.5;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )