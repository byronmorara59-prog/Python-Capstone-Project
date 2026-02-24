
## SmartSpend

### 1. Project Description
SmartSpend is a personal finance intelligence tool designed to help users bridge the gap between their daily spending habits and their long-term financial goals. Unlike a simple spreadsheet, this system uses Python’s advanced capabilities to automatically categorize expenses, track progress toward a specific savings target, and provide real time "course corrections" to ensure the user stays on track.



### 2. Problem Statement
Many people struggle to save because they lack a clear connection between a small daily purchase and a large future goal. Existing apps often require tedious manual entry. This project solves that by automating data processing and providing a dynamic "Daily Spend Limit" that adjusts based on how much the user has already spent.



### 3. Proposed Features
1. Flexible Transaction Input - Users can manually input transactions or upload CSV/Excel bank statements for bulk processing.

2. Smart Categorization - The system uses Regular Expressions (Regex) to automatically sort expenses into categories like "Groceries," "Transport," or "Utilities".

3. Goal Progress Dashboard - A visual summary showing current progress, remaining days, and a dynamically updated "daily allowance".

4. Dynamic Recommendations - Based on spending trends, the app provides suggestions, such as "Reducing coffee expenses by 10% will help you meet your goal 5 days faster".

5. Persistent Data Storage - All user goals and transaction history are saved in a structured SQLite database to ensure records are preserved.



### 4. Python Concepts
1. Advanced OOP - Implementing classes like User, Account, and Transaction with Encapsulation to protect financial data.

2. Regular Expressions (Regex) - Parsing messy bank statement text to extract amounts and vendor names automatically.

3. File Handling & Data Types - Reading and writing CSV/JSON files for statement uploads and data persistence.

4. Database Integration - Using SQL queries to store, update, and retrieve financial records efficiently.

5. Conditional Logic & Functions - Calculating daily "burn rates" and providing personalized financial advice based on user habits.



### 5. Tools and Libraries
1. Built-in Modules - sqlite3 for the database, re for text parsing, and datetime for tracking deadlines.

2. Data Handling - pandas to process uploaded CSV statements and summarize spending.

3. Web Services (APIs) - The requests library to fetch real-time exchange rates for multi-currency support.

4. Visualization - Streamlit or Matplotlib to create clear charts of spending trends.



### 6. Success Criteria
The project will be considered successful if:

1. The user can set a savings goal and see an accurate, updated daily spending limit.

2. The system successfully parses and categorizes at least 5 different transaction types from a CSV upload.

3. The program provides at least one "Dynamic Recommendation" based on the user's spending habits.

4. All data is correctly saved to and retrieved from the SQLite database.