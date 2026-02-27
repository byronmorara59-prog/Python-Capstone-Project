import streamlit as st
from datetime import date
from Smartspendbackend import (
    create_goal,
    get_active_goal,
    add_transaction,
    import_mpesa_pdf,
    calculate_dashboard_metrics,
    generate_recommendations,
    chart_pie_by_category,
    chart_bar_by_category,
    chart_line_daily_spend
)
import matplotlib.pyplot as plt

st.set_page_config(page_title="SmartSpend", layout="wide")
st.title("SmartSpend 💰")

menu = st.sidebar.selectbox(
    "Navigation",
    ["Create Goal", "Add Transaction", "Import PDF", "Dashboard"]
)
# CREATE GOAL
if menu == "Create Goal":
    st.subheader("Create a Savings Goal")

    saving_for = st.text_input("Saving for")
    saving_amount = st.number_input("Target Amount", min_value=0.0)
    deadline = st.date_input("Deadline")
    monthly_budget = st.number_input("Monthly Budget", min_value=0.0)

    if st.button("Create Goal"):
        goal_id = create_goal(
            saving_for,
            saving_amount,
            deadline.strftime("%Y-%m-%d"),
            monthly_budget
        )
        st.success("Goal created successfully!")

#ADD TRANSACTION
elif menu == "Add Transaction":
    st.subheader("Add Transaction")

    goal = get_active_goal()

    if not goal:
        st.warning("Please create a goal first.")
    else:
        goal_id = goal[0]

        tx_date = st.date_input("Date")
        description = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.0)
        tx_type = st.selectbox("Type", ["expense", "income"])

        if st.button("Add"):
            success, message = add_transaction(
                tx_date.strftime("%Y-%m-%d"),
                description,
                amount,
                tx_type,
                goal_id
            )
            if success:
                st.success(message)
            else:
                st.error(message)

#IMPORT PDF
elif menu == "Import PDF":
    st.subheader("Upload M-Pesa Statement")

    goal = get_active_goal()

    if not goal:
        st.warning("Create a goal first.")
    else:
        goal_id = goal[0]

        uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"])

        if uploaded_pdf is not None:
            if st.button("Import Transactions"):
                count = import_mpesa_pdf(uploaded_pdf, goal_id)
                st.success(f"{count} transactions imported successfully.")

#DASHBOARD
elif menu == "Dashboard":
    st.subheader("Goal Dashboard")

    metrics = calculate_dashboard_metrics()

    if not metrics:
        st.warning("Create a goal first.")
    else:
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Saving For", metrics["saving_for"])
        col2.metric("Current Savings", metrics["current_savings"])
        col3.metric("Remaining", metrics["remaining_amount"])
        col4.metric("Progress %", metrics["progress_percent"])

        st.divider()

        st.subheader("Recommendations")
        recs = generate_recommendations()
        if recs:
            for r in recs:
                st.write("•", r)

        st.divider()

        goal_id = metrics["goal_id"]

        fig1 = chart_pie_by_category(goal_id)
        if fig1:
            st.pyplot(fig1)
            plt.close(fig1)

        fig2 = chart_bar_by_category(goal_id)
        if fig2:
            st.pyplot(fig2)
            plt.close(fig2)

        fig3 = chart_line_daily_spend(goal_id)
        if fig3:
            st.pyplot(fig3)
            plt.close(fig3)