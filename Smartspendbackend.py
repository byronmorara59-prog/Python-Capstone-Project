#Importing libraries
import sqlite3
from datetime import datetime, date
import csv
import matplotlib.pyplot as plt
import re
import pdfplumber
import streamlit as st


#Connecting to the db
@st.cache_resource
def get_db():
    conn = sqlite3.connect("Smart_Spend.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.commit()
    return conn

conn = get_db()


#Creating the tables
conn.executescript("""
CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    saving_for TEXT NOT NULL,
    saving_amount REAL NOT NULL CHECK (saving_amount > 0),
    deadline TEXT NOT NULL,                          
    monthly_budget REAL NOT NULL DEFAULT 0 CHECK (monthly_budget >= 0),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1))
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,                              
    description TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    category TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('expense','income')),
    goal_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_goal ON transactions(goal_id);
""")

conn.commit()


#Creating classes and the functions
class Goal:
    def __init__(self, id, saving_for, saving_amount, deadline, monthly_budget=0.0, active=1):
        self.id = id
        self.saving_for = saving_for
        self.saving_amount = saving_amount
        self.deadline = deadline
        self.monthly_budget = monthly_budget
        self.active = active

    def __repr__(self):
        return (
            f"Goal(id={self.id}, "
            f"name='{self.saving_for}', "
            f"saving_amount={self.saving_amount}, "
            f"deadline='{self.deadline}', "
            f"monthly_budget={self.monthly_budget})"
        )


class Transaction:
    def __init__(self, id, date, description, amount, category, transaction_type, goal_id=None):
        self.id = id
        self.date = date
        self.description = description
        self.amount = amount
        self.category = category
        self.transaction_type = transaction_type
        self.goal_id = goal_id

    def __repr__(self):
        return (
            f"Transaction(id={self.id}, "
            f"Date='{self.date}', "
            f"Description='{self.description}', "
            f"Amount={self.amount}, "
            f"Category='{self.category}', "
            f"Transaction_type='{self.transaction_type}', "
            f"Goal_id={self.goal_id})"
        )
    


#Categorization with the regex function
category_patterns = {
    "Groceries": r"(naivas|quickmart|carrefour|supermarket)",
    "Transport": r"(uber|bolt|sacco|fuel|shell|total|rubis)",
    "Utilities": r"(kplc|water|internet|wifi|safaricom|airtel|faiba)",
    "Dining": r"(restaurant|cafe|coffee|kfc|java|pizza|burger)",
    "Rent": r"(rent|landlord|house rent|nyumba)",
    "Shopping": r"(jumia|amazon|mall|clothes|shoe|fashion|shop)",
    "Health": r"(pharmacy|hospital|clinic|medical|doctor)",
    "Entertainment": r"(amazon|showmax|youtubemusic|movie|cinema|game)"
}


def categorize_transaction(description):
    description = description.strip().lower()

    for category, pattern in category_patterns.items():
      
        if re.search(pattern, description, re.I):
            return category

    return "Other"


#Create a new savings goal
def create_goal(saving_for, saving_amount, deadline, monthly_budget):

    conn.execute("UPDATE goals SET active = 0 WHERE active = 1")

    conn.execute("""
        INSERT INTO goals (saving_for, saving_amount, deadline, monthly_budget, active)
        VALUES (?, ?, ?, ?, 1)
    """, (saving_for, saving_amount, deadline, monthly_budget))

    conn.commit()

    return cursor.lastrowid


#Add a new transaction
def add_transaction(date_str, description, amount, transaction_type, goal_id=None):

    if transaction_type not in ("expense", "income"):
        return False, "Transaction type must be 'expense' or 'income'."

    if amount <= 0:
        return False, "Amount must be positive."

    category = categorize_transaction(description)

    conn.execute("""
        INSERT INTO transactions (date, description, amount, category, transaction_type, goal_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (date_str, description, amount, category, transaction_type, goal_id))

    conn.commit()

    return True, "Transaction added successfully."


#Fetch active goal
def get_active_goal():

    row = conn.execute("""
        SELECT * FROM goals WHERE active = 1
    """).fetchone()

    return row


#Fetch all transactions
def get_all_transactions():

    rows = conn.execute("""
        SELECT * FROM transactions
    """).fetchall()

    return rows


#Update monthly budget
def update_monthly_budget(goal_id, new_budget):

    conn.execute("""
        UPDATE goals
        SET monthly_budget = ?
        WHERE id = ?
    """, (new_budget, goal_id))

    conn.commit()

    return True


#Delete transaction
def delete_transaction(transaction_id):

    conn.execute("""
        DELETE FROM transactions
        WHERE id = ?
    """, (transaction_id,))

    conn.commit()

    return True



#Goal Dashboard Metrics
from datetime import datetime, date

def calculate_dashboard_metrics():

    goal = get_active_goal()

    if not goal:
        return None

    goal_id = goal[0]
    saving_for = goal[1]
    saving_amount = goal[2]
    deadline = goal[3]
    monthly_budget = goal[4]

    income = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type = 'income' AND goal_id = ?
    """, (goal_id,)).fetchone()[0]

    expenses = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type = 'expense' AND goal_id = ?
    """, (goal_id,)).fetchone()[0]

    current_savings = income - expenses
    remaining_amount = saving_amount - current_savings

    today = date.today()
    deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
    days_remaining = (deadline_date - today).days

    if days_remaining > 0:
        daily_required = remaining_amount / days_remaining
    else:
        daily_required = 0

    progress_percent = (current_savings / saving_amount) * 100 if saving_amount > 0 else 0

    return {
        "goal_id": goal_id,
        "saving_for": saving_for,
        "target_amount": saving_amount,
        "current_savings": current_savings,
        "remaining_amount": remaining_amount,
        "days_remaining": days_remaining,
        "daily_required": round(daily_required, 2),
        "progress_percent": round(progress_percent, 2),
        "monthly_budget": monthly_budget
    }



#Dynamic Recommendations
def generate_recommendations():

    metrics = calculate_dashboard_metrics()

    if not metrics:
        return None

    goal_id = metrics["goal_id"]
    saving_amount = metrics["target_amount"]
    current_savings = metrics["current_savings"]
    remaining_amount = metrics["remaining_amount"]
    days_remaining = metrics["days_remaining"]

    recommendations = []

    #Behind schedule
    if days_remaining > 0:
        daily_required = remaining_amount / days_remaining
        if daily_required > 0:
            recommendations.append(
                f"You need to save about {round(daily_required, 2)} per day to stay on track."
            )
        else:
            recommendations.append("You have already reached your goal! 🎉")
    else:
        recommendations.append("Deadline has passed.")

    #Income vs expense check
    income = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type = 'income' AND goal_id = ?
    """, (goal_id,)).fetchone()[0]

    expenses = conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type = 'expense' AND goal_id = ?
    """, (goal_id,)).fetchone()[0]

    if expenses > income:
        recommendations.append("Your expenses are higher than your income.")
        recommendations.append("Consider reducing discretionary spending.")

    #Highest spending category
    category_data = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM transactions
        WHERE transaction_type = 'expense' AND goal_id = ?
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
    """, (goal_id,)).fetchone()

    if category_data:
        highest_category = category_data[0]
        highest_amount = category_data[1]
        reduction = highest_amount * 0.10

        recommendations.append(
            f"Your highest spending category is '{highest_category}' ({highest_amount})."
        )

        recommendations.append(
            f"Reducing {highest_category} spending by 10% could save {round(reduction, 2)}."
        )

    return recommendations


#Parser
def import_mpesa_pdf(pdf_path, goal_id):

    #Pattern to detect start of transaction row: Receipt + Date (YYYY-MM-DD or DD/MM/YYYY) + Time
    start_pattern = re.compile(
        r"^([A-Z0-9]{8,12})\s+"
        r"((\d{4}-\d{2}-\d{2})|(\d{2}/\d{2}/\d{4}))\s+"
        r"(\d{2}:\d{2}:\d{2})\s+(.*)"
    )

    #Pattern to detect money values (e.g. 2,500.00 or 2500.00)
    money_pattern = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2}|\d+")

    inserted = 0
    current = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            for line in lines:

                #Skip header lines
                if any(word in line for word in [
                    "MPESA FULL STATEMENT",
                    "Receipt No",
                    "Completion Time",
                    "Disclaimer",
                    "Page "
                ]):
                    continue

                match = start_pattern.match(line)

                #If new transaction row detected
                if match:

                    #Process previous transaction
                    if current:
                        numbers = money_pattern.findall(current["text"])

                        if len(numbers) >= 2:
                            paid_in = float(numbers[-3].replace(",", "")) if len(numbers) >= 3 else 0
                            withdrawn = float(numbers[-2].replace(",", ""))

                            if paid_in > 0:
                                transaction_type = "income"
                                amount = paid_in
                            else:
                                transaction_type = "expense"
                                amount = withdrawn

                            description = re.sub(r"\s+", " ", current["text"]).strip()

                            success, _ = add_transaction(
                                current["date"],
                                description,
                                amount,
                                transaction_type,
                                goal_id
                            )

                            if success:
                                inserted += 1

                    #Start new transaction
                    current = {
                        "date": match.group(2),
                        "text": match.group(6)
                    }

                else:
                    #Handle wrapped lines
                    if current:
                        current["text"] += " " + line

        #Process final transaction
        if current:
            numbers = money_pattern.findall(current["text"])

            if len(numbers) >= 2:
                paid_in = float(numbers[-3].replace(",", "")) if len(numbers) >= 3 else 0
                withdrawn = float(numbers[-2].replace(",", ""))

                if paid_in > 0:
                    transaction_type = "income"
                    amount = paid_in
                else:
                    transaction_type = "expense"
                    amount = withdrawn

                description = re.sub(r"\s+", " ", current["text"]).strip()

                success, _ = add_transaction(
                    current["date"],
                    description,
                    amount,
                    transaction_type,
                    goal_id
                )

                if success:
                    inserted += 1

    return inserted




#Visualizations
def _fetch_expense_data(goal_id, group_by="category"):
    if group_by == "category":
        query = """
            SELECT category, COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE goal_id = ? AND transaction_type = 'expense'
            GROUP BY category
            HAVING SUM(amount) > 0
            ORDER BY 2 DESC
        """
    else:
        query = """
            SELECT date, COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE goal_id = ? AND transaction_type = 'expense'
            GROUP BY date
            HAVING SUM(amount) > 0
            ORDER BY date
        """
    return conn.execute(query, (goal_id,)).fetchall()


def chart_pie_by_category(goal_id):
    rows = _fetch_expense_data(goal_id, "category")
    if not rows:
        return None

    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]

    fig = plt.figure(figsize=(7, 5))
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    plt.title("Expenses by Category")
    plt.tight_layout()
    return fig


def chart_bar_by_category(goal_id):
    rows = _fetch_expense_data(goal_id, "category")
    if not rows:
        return None

    categories = [r[0] for r in rows]
    totals = [r[1] for r in rows]

    fig = plt.figure(figsize=(9, 5))
    plt.bar(categories, totals)
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Category")
    plt.ylabel("Total Spent")
    plt.title("Total Expenses by Category")
    plt.tight_layout()
    return fig


def chart_line_daily_spend(goal_id):
    rows = _fetch_expense_data(goal_id, "date")
    if not rows:
        return None

    dates = [r[0] for r in rows]
    totals = [r[1] for r in rows]

    fig = plt.figure(figsize=(9, 5))
    plt.plot(dates, totals, marker="o")
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Date")
    plt.ylabel("Total Spent")
    plt.title("Daily Spending Trend")
    plt.tight_layout()
    return fig