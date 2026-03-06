import streamlit as st
import matplotlib.pyplot as plt
from datetime import date

from Smartspendbackend import (
    create_goal,
    get_active_goal,
    add_transaction,
    add_saving,
    recommended_saving_from_income,
    saving_feedback,
    import_mpesa_pdf,
    calculate_dashboard_metrics,
    generate_recommendations,
    chart_pie_by_category,
    chart_bar_by_category,
    chart_line_daily_spend
)

st.set_page_config(page_title="SmartSpend", layout="wide")
st.title("SmartSpend")

menu = st.sidebar.selectbox(
    "Navigation",
    ["Create Goal", "Add Transaction", "Import PDF", "Dashboard"]
)

#Create goal
if menu == "Create Goal":
    st.subheader("Create a Savings Goal")

    saving_for = st.text_input("Saving for")
    saving_amount = st.number_input("Target Amount", min_value=0.0)
    deadline = st.date_input("Deadline")
    monthly_budget = st.number_input("Monthly Budget", min_value=0.0)

    if st.button("Create Goal"):
        if not saving_for.strip():
            st.error("Please enter what you're saving for.")
        elif saving_amount <= 0:
            st.error("Target Amount must be greater than 0.")
        else:
            goal_id = create_goal(
                saving_for.strip(),
                saving_amount,
                deadline.strftime("%Y-%m-%d"),
                monthly_budget
            )
            st.success(f"Goal created successfully! (Goal ID: {goal_id})")

#Adding transactions
elif menu == "Add Transaction":
    st.subheader("Add Transaction")

    goal = get_active_goal()
    if not goal:
        st.warning("Please create a goal first.")
        st.stop()

    goal_id = goal[0]

    tx_date = st.date_input("Date")
    description = st.text_input("Description")
    amount = st.number_input("Amount", min_value=0.0)
    tx_type = st.selectbox("Type", ["expense", "income"])

    pay_cycle = st.selectbox("How often do you get paid?", ["Monthly (30 days)", "Bi-weekly (14 days)", "Weekly (7 days)"])
    pay_cycle_days = 30 if "Monthly" in pay_cycle else (14 if "Bi-weekly" in pay_cycle else 7)

    chosen_save_amount = None
    recommended = None

    if tx_type == "income" and amount > 0:
        recommended = recommended_saving_from_income(goal_id, amount, pay_cycle_days)
        st.info(f"Recommended to save from this income: **{recommended}**")

        chosen_save_amount = st.number_input(
            "How much do you want to save from this income?",
            min_value=0.0,
            max_value=float(amount),
            value=float(recommended) if recommended <= amount else float(amount)
        )

        if recommended is not None:
            st.write(saving_feedback(chosen_save_amount, recommended))

    if st.button("Add"):
        success, message, tx_id = add_transaction(
            tx_date.strftime("%Y-%m-%d"),
            description.strip(),
            amount,
            tx_type,
            goal_id
        )

        if not success:
            st.error(message)
            st.stop()

        #If income it is income also add to savings
        if tx_type == "income":
            if chosen_save_amount is None or chosen_save_amount <= 0:
                st.warning("Income saved, but you did not record any savings amount.")
            else:
                ok, msg = add_saving(
                    tx_date.strftime("%Y-%m-%d"),
                    chosen_save_amount,
                    goal_id,
                    source_transaction_id=tx_id
                )
                if ok:
                    st.success("Income added + Savings recorded successfully")
                else:
                    st.error(msg)
        else:
            st.success(message)

#Immporting the pdf
elif menu == "Import PDF":
    st.subheader("Upload M-Pesa Statement")
    st.info("Statement transactions are NOT used in your goal savings dashboard. They are for spending pattern tracking.")

    uploaded_pdf = st.file_uploader("Upload PDF", type=["pdf"])

    if uploaded_pdf is not None:
        if st.button("Import Transactions"):
            count = import_mpesa_pdf(uploaded_pdf, goal_id=None)
            st.success(f"{count} statement transactions imported successfully.")

#Dashboard for savings
elif menu == "Dashboard":
    st.subheader("Goal Dashboard")

    metrics = calculate_dashboard_metrics()
    if not metrics:
        st.warning("Create a goal first.")
        st.stop()

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