
## SmartSpend

### 1. Project Description
This project is a personal finance intelligence tool designed to help users reach specific savings goals by managing their daily spending habits. The main problem it solves is the disconnect between daily small expenses and long-term financial targets. The system calculates a dynamic "Daily Spending Limit" and uses Regex to automatically categorize transactions from raw text inputs, ensuring the user stays on the path to their savings goal.

Many people struggle to save because they lack a clear connection between a small daily purchase and a large future goal. This project solves that by automating data processing and providing a dynamic "Daily Spend Limit" that adjusts based on how much the user has already spent.


### 2. Proposed Features
1. Goal Initialization - Users can set a target savings amount and a deadline date.

2. Automated Expense Logging - Uses Regular Expressions to parse raw text (e.g., "Spent 200 on Lunch") and extract both the category and the amount.

3. Real-time Progress Analysis - Automatically calculates the daily spending allowance based on remaining days and current savings.

4. Persistent Database Storage - Uses SQLite to store user profiles, goals, and a full history of transactions.

5. Interactive Menu - A text based navigation system to log expenses, view goal progress, and update settings.


### 3. Python Concepts
1. Advanced OOP - Implementing classes like User, SavingsGoal, and Transaction with Encapsulation to protect financial data.

2. Regular Expressions (Regex) - Identifying and extracting currency patterns and keywords from unstructured user input.

3. Database Integration - Using SQL queries (INSERT, SELECT, UPDATE) to manage and retrieve financial records from an SQLite database.

4. Error Handling - Using try-except blocks to validate user inputs and prevent program crashes during data entry.

5. Data Handling - Using Dictionaries and Lists to process transaction history before saving to the database.


### 4. Tools and Libraries
1. re (Regular Expressions) - to scan user input and extract numbers and categories.

2. datetime - for calculating how many days are left until savings deadline.

3. json - for handling configuration files or temporary data exports if needed.

4. requests - to connect to a financial API to fetch a single data point, such as a currency exchange rate.

5. pandas - to create a clean summary table of spending habits.

6. matplotlib or plotly - to generate a bar chart or line graph showing your spending trends over time.