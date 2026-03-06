import sqlite3
from datetime import datetime, date
import matplotlib.pyplot as plt
import re
import pdfplumber
import io

#Connecting to the database
def get_db():
    conn = sqlite3.connect("Smart_Spend.db", check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

conn = get_db()


#Migration helpers to avoid deleting the db everytime
def ensure_column(table_name: str, column_name: str, column_def: str):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
    if column_name not in cols:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        conn.commit()


def ensure_table_savings():
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS savings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL CHECK (amount > 0),
        goal_id INTEGER NOT NULL,
        source_transaction_id INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (goal_id) REFERENCES goals(id) ON DELETE CASCADE,
        FOREIGN KEY (source_transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_savings_goal ON savings(goal_id);
    CREATE INDEX IF NOT EXISTS idx_savings_date ON savings(date);
    """)
    conn.commit()


#Date normalizer
def normalize_date(date_str: str) -> str:
    date_str = (date_str or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return date_str


#Creating tables
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

#If there is already had an old DB, add missing columns.
ensure_column("transactions", "source", "TEXT NOT NULL DEFAULT 'manual'")
ensure_column("transactions", "include_in_goal", "INTEGER NOT NULL DEFAULT 1 CHECK (include_in_goal IN (0,1))")
ensure_column("transactions", "statement_label", "TEXT")


#Spending categorization
category_patterns = {
    "Groceries": r"(naivas|quickmart|carrefour|supermarket)",
    "Transport": r"(uber|bolt|sacco|fuel|shell|total|rubis)",
    "Utilities": r"(kplc|water|internet|wifi|safaricom|airtel|faiba)",
    "Dining": r"(restaurant|cafe|coffee|kfc|java|pizza|burger)",
    "Rent": r"(rent|landlord|house rent|nyumba)",
    "Shopping": r"(jumia|amazon|mall|clothes|shoe|fashion|shop)",
    "Health": r"(pharmacy|hospital|clinic|medical|doctor)",
    "Entertainment": r"(showmax|youtubemusic|movie|cinema|game)"
}

def categorize_transaction(description: str) -> str:
    d = (description or "").lower()
    for cat, pat in category_patterns.items():
        if re.search(pat, d, re.I):
            return cat
    return "Other"


#Goals dashboard
def create_goal(saving_for, saving_amount, deadline, monthly_budget):
    conn.execute("UPDATE goals SET active = 0 WHERE active = 1")

    cur = conn.execute("""
        INSERT INTO goals (saving_for, saving_amount, deadline, monthly_budget, active)
        VALUES (?, ?, ?, ?, 1)
    """, (saving_for, saving_amount, deadline, monthly_budget))
    conn.commit()

    return cur.lastrowid


def get_active_goal():
    return conn.execute("SELECT * FROM goals WHERE active = 1").fetchone()


#Savings on the dashboard
def add_saving(date_str, amount, goal_id, source_transaction_id=None):
    if amount <= 0:
        return False, "Savings amount must be greater than 0."

    date_str = normalize_date(date_str)

    conn.execute("""
        INSERT INTO savings (date, amount, goal_id, source_transaction_id)
        VALUES (?, ?, ?, ?)
    """, (date_str, float(amount), goal_id, source_transaction_id))

    conn.commit()
    return True, "Savings added successfully."


def get_total_savings(goal_id):
    return conn.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM savings
        WHERE goal_id = ?
    """, (goal_id,)).fetchone()[0]


#Transacations. They only show spengind trends, and are not added to the savings in anyway
def add_transaction(date_str, description, amount, transaction_type, goal_id=None):
    if transaction_type not in ("expense", "income"):
        return False, "Transaction type must be 'expense' or 'income'.", None
    if amount <= 0:
        return False, "Amount must be greater than 0.", None

    date_str = normalize_date(date_str)
    category = categorize_transaction(description)

    cur = conn.execute("""
        INSERT INTO transactions
            (date, description, amount, category, transaction_type, goal_id, source, include_in_goal, statement_label)
        VALUES (?, ?, ?, ?, ?, ?, 'manual', 1, NULL)
    """, (date_str, description, float(amount), category, transaction_type, goal_id))
    conn.commit()

    return True, "Transaction added successfully.", cur.lastrowid


#Savings progress
def calculate_dashboard_metrics():
    goal = get_active_goal()
    if not goal:
        return None

    goal_id = goal[0]
    saving_for = goal[1]
    target_amount = goal[2]
    deadline = goal[3]
    monthly_budget = goal[4]

    saved = get_total_savings(goal_id)
    remaining_amount = target_amount - saved

    remaining_amount_display = remaining_amount if remaining_amount > 0 else 0

    today = date.today()
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()
        days_remaining = (deadline_date - today).days
    except ValueError:
        days_remaining = 0

    daily_required = (remaining_amount / days_remaining) if (days_remaining > 0 and remaining_amount > 0) else 0

    progress_percent = (saved / target_amount) * 100 if target_amount > 0 else 0
    if progress_percent > 100:
        progress_percent_display = 100.0
    elif progress_percent < 0:
        progress_percent_display = 0.0
    else:
        progress_percent_display = progress_percent

    return {
        "goal_id": goal_id,
        "saving_for": saving_for,
        "target_amount": target_amount,
        "current_savings": round(saved, 2),
        "remaining_amount": round(remaining_amount_display, 2),
        "raw_remaining_amount": round(remaining_amount, 2),
        "days_remaining": days_remaining,
        "daily_required": round(daily_required, 2),
        "progress_percent": round(progress_percent_display, 2),
        "monthly_budget": monthly_budget
    }

def generate_recommendations():
    metrics = calculate_dashboard_metrics()

    if not metrics:
        return None

    goal_id = metrics["goal_id"]
    recs = []

    if metrics["current_savings"] >= metrics["target_amount"]:
        recs.append("You have already reached your goal!")
        return recs

    if metrics["days_remaining"] > 0 and metrics["daily_required"] > 0:
        recs.append(
            f"You need to save about {metrics['daily_required']} per day to stay on track."
        )
    else:
        recs.append("Your deadline has passed or is too close.")

    expense_data = conn.execute("""
        SELECT category, COALESCE(SUM(amount), 0) as total
        FROM transactions
        WHERE goal_id = ?
          AND include_in_goal = 1
          AND transaction_type = 'expense'
        GROUP BY category
        ORDER BY total DESC
        LIMIT 1
    """, (goal_id,)).fetchone()

    if expense_data:
        category = expense_data[0]
        total_spent = expense_data[1]
        reduction = round(total_spent * 0.10, 2)

        recs.append(f"Your highest spending category is '{category}' ({round(total_spent, 2)}).")
        recs.append(f"Reducing {category} spending by 10% could save {reduction}.")

    return recs

#Recommendations for savings
def recommended_saving_from_income(goal_id, income_amount, pay_cycle_days=30):
    metrics = calculate_dashboard_metrics()
    if not metrics:
        return 0.0

    remaining = metrics["raw_remaining_amount"]
    days_remaining = metrics["days_remaining"]

    if remaining <= 0:
        return 0.0

    if days_remaining <= 0:
        #Deadline passed, recommend as much as possible
        return round(min(remaining, income_amount), 2)

    daily_required = remaining / days_remaining
    recommended = daily_required * pay_cycle_days

    #Cap it so it never recommends more than remaining or income
    recommended = min(recommended, remaining)
    recommended = min(recommended, income_amount)

    return round(recommended, 2)


def saving_feedback(chosen_amount, recommended_amount):
    if chosen_amount < recommended_amount:
        diff = recommended_amount - chosen_amount
        return f"You are saving {round(diff, 2)} less than recommended. You may miss your target."
    elif chosen_amount > recommended_amount:
        diff = chosen_amount - recommended_amount
        return f"You are saving {round(diff, 2)} more than recommended. You are ahead of schedule."
    return "Perfect — you’re exactly on track."


#Charts showing expenses
def _fetch_goal_expense_data(goal_id, group_by="category"):
    if group_by == "category":
        query = """
            SELECT category, COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE goal_id = ?
              AND include_in_goal = 1
              AND transaction_type = 'expense'
            GROUP BY category
            HAVING SUM(amount) > 0
            ORDER BY 2 DESC
        """
    else:
        query = """
            SELECT date, COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE goal_id = ?
              AND include_in_goal = 1
              AND transaction_type = 'expense'
            GROUP BY date
            HAVING SUM(amount) > 0
            ORDER BY date
        """
    return conn.execute(query, (goal_id,)).fetchall()


def chart_pie_by_category(goal_id):
    rows = _fetch_goal_expense_data(goal_id, "category")
    if not rows:
        return None
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    fig = plt.figure(figsize=(7, 5))
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    plt.title("Goal Expenses by Category")
    plt.tight_layout()
    return fig


def chart_bar_by_category(goal_id):
    rows = _fetch_goal_expense_data(goal_id, "category")
    if not rows:
        return None
    categories = [r[0] for r in rows]
    totals = [r[1] for r in rows]
    fig = plt.figure(figsize=(9, 5))
    plt.bar(categories, totals)
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Category")
    plt.ylabel("Total Spent")
    plt.title("Goal Total Expenses by Category")
    plt.tight_layout()
    return fig


def chart_line_daily_spend(goal_id):
    rows = _fetch_goal_expense_data(goal_id, "date")
    if not rows:
        return None
    dates = [r[0] for r in rows]
    totals = [r[1] for r in rows]
    fig = plt.figure(figsize=(9, 5))
    plt.plot(dates, totals, marker="o")
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Date")
    plt.ylabel("Total Spent")
    plt.title("Goal Daily Spending Trend")
    plt.tight_layout()
    return fig


#Importing mpesa statements
statement_keywords = {
    "Received": r"\b(received|credited|credit)\b",
    "Sent": r"\b(sent|send|transfer|transferred)\b",
    "Purchased": r"\b(purchased|purchase|bought|buy)\b",
    "Payment": r"\b(payment|paid|paybill|till)\b"
}

def classify_statement_label(description: str) -> str:
    d = (description or "").lower()
    for label, pattern in statement_keywords.items():
        if re.search(pattern, d, re.I):
            return label
    return "Other"


def _extract_amounts(text: str):
    if not text:
        return []
    money_decimal = re.findall(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2}", text)
    amounts = [float(m.replace(",", "")) for m in money_decimal]
    return amounts


def import_mpesa_pdf(pdf_file, goal_id=None):
    inserted = 0
    current = None

    pdf_input = pdf_file
    if hasattr(pdf_file, "read"):
        pdf_input = io.BytesIO(pdf_file.read())
    elif isinstance(pdf_file, (bytes, bytearray)):
        pdf_input = io.BytesIO(pdf_file)

    start_pattern = re.compile(
        r"^([A-Z0-9]{6,14})\s+((\d{4}-\d{2}-\d{2})|(\d{2}/\d{2}/\d{4}))\s+(\d{2}:\d{2}:\d{2})\s+(.*)"
    )

    with pdfplumber.open(pdf_input) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

            for line in lines:
                if any(w in line for w in ["MPESA", "Receipt No", "Completion Time", "Disclaimer", "Page "]):
                    continue

                m = start_pattern.match(line)

                if m:
                    if current:
                        desc = re.sub(r"\s+", " ", current["text"]).strip()
                        amounts = _extract_amounts(desc)

                        if amounts:
                            amount = max(amounts)
                            if amount > 0:
                                label = classify_statement_label(desc)
                                low = desc.lower()
                                tx_type = "income" if ("received" in low or "credit" in low or "credited" in low) else "expense"

                                conn.execute("""
                                    INSERT INTO transactions
                                        (date, description, amount, category, transaction_type, goal_id,
                                         source, include_in_goal, statement_label)
                                    VALUES (?, ?, ?, ?, ?, NULL, 'mpesa_pdf', 0, ?)
                                """, (
                                    normalize_date(current["date"]),
                                    desc,
                                    float(amount),
                                    categorize_transaction(desc),
                                    tx_type,
                                    label
                                ))
                                inserted += 1

                    current = {"date": m.group(2), "text": m.group(6)}
                else:
                    if current:
                        current["text"] += " " + line

        if current:
            desc = re.sub(r"\s+", " ", current["text"]).strip()
            amounts = _extract_amounts(desc)
            if amounts:
                amount = max(amounts)
                if amount > 0:
                    label = classify_statement_label(desc)
                    low = desc.lower()
                    tx_type = "income" if ("received" in low or "credit" in low or "credited" in low) else "expense"

                    conn.execute("""
                        INSERT INTO transactions
                            (date, description, amount, category, transaction_type, goal_id,
                             source, include_in_goal, statement_label)
                        VALUES (?, ?, ?, ?, ?, NULL, 'mpesa_pdf', 0, ?)
                    """, (
                        normalize_date(current["date"]),
                        desc,
                        float(amount),
                        categorize_transaction(desc),
                        tx_type,
                        label
                    ))
                    inserted += 1

    conn.commit()
    return inserted