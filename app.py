import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import re
from typing import Dict, List, Tuple

class DatabaseManager:
    def __init__(self, db_name='company.db'):
        self.db_name = db_name
        self.create_database()
    
    def create_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Employees (
            ID INTEGER PRIMARY KEY,
            Name TEXT NOT NULL,
            Department TEXT NOT NULL,
            Salary INTEGER NOT NULL,
            Hire_Date DATE NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Departments (
            ID INTEGER PRIMARY KEY,
            Name TEXT NOT NULL,
            Manager TEXT NOT NULL
        )
        ''')
        
        sample_employees = [
            (1, 'Alice', 'Sales', 50000, '2021-01-15'),
            (2, 'Bob', 'Engineering', 70000, '2020-06-10'),
            (3, 'Charlie', 'Marketing', 60000, '2022-03-20'),
            (4, 'David', 'Engineering', 75000, '2021-08-15'),
            (5, 'Eva', 'Sales', 55000, '2022-01-10')
        ]
        
        sample_departments = [
            (1, 'Sales', 'Alice'),
            (2, 'Engineering', 'Bob'),
            (3, 'Marketing', 'Charlie')
        ]
        
        cursor.executemany('INSERT OR REPLACE INTO Employees VALUES (?,?,?,?,?)', sample_employees)
        cursor.executemany('INSERT OR REPLACE INTO Departments VALUES (?,?,?)', sample_departments)
        
        conn.commit()
        conn.close()

class QueryEngine:
    def __init__(self, db_name='company.db'):
        self.db_name = db_name
        
    def get_departments(self) -> List[str]:
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT Name FROM Departments")
        departments = [row[0] for row in cursor.fetchall()]
        conn.close()
        return departments

    def get_total_salary_expense(self, department: str) -> float:
        """Calculate total salary expense for a specific department"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(Salary) as total_expense 
            FROM Employees 
            WHERE Department = ?
        """, (department,))
        result = cursor.fetchone()[0]
        conn.close()
        return result if result else 0

    def execute_query(self, query_template: str, **params) -> pd.DataFrame:
        conn = sqlite3.connect(self.db_name)
        try:
            if query_template == "employees_in_department":
                sql = "SELECT * FROM Employees WHERE Department = ?"
                df = pd.read_sql_query(sql, conn, params=(params['department'],))
                
            elif query_template == "department_manager":
                sql = "SELECT * FROM Departments WHERE Name = ?"
                df = pd.read_sql_query(sql, conn, params=(params['department'],))
                
            elif query_template == "employees_after_date":
                sql = "SELECT * FROM Employees WHERE Hire_Date > ?"
                df = pd.read_sql_query(sql, conn, params=(params['date'],))
                
            elif query_template == "department_salary":
                sql = """
                SELECT Department, 
                       COUNT(*) as Employee_Count,
                       SUM(Salary) as Total_Salary,
                       AVG(Salary) as Average_Salary,
                       MIN(Salary) as Min_Salary,
                       MAX(Salary) as Max_Salary
                FROM Employees 
                WHERE Department = ?
                GROUP BY Department
                """
                df = pd.read_sql_query(sql, conn, params=(params['department'],))
                
            elif query_template == "total_salary_expense":
                sql = """
                SELECT Department, 
                       SUM(Salary) as Total_Expense,
                       COUNT(*) as Employee_Count
                FROM Employees 
                WHERE Department = ?
                GROUP BY Department
                """
                df = pd.read_sql_query(sql, conn, params=(params['department'],))
                
            elif query_template == "all_employees":
                df = pd.read_sql_query("SELECT * FROM Employees", conn)
                
            elif query_template == "all_departments":
                df = pd.read_sql_query("SELECT * FROM Departments", conn)
                
            return df
        finally:
            conn.close()

def main_page():
    st.title("Company Database Assistant 💼")
    
    query_engine = QueryEngine()
    departments = query_engine.get_departments()
    
    # Example queries for the search bar
    example_queries = [
        "Show employees in Sales",
        "Who manages Engineering",
        "Show employees hired after 2021-01-01",
        "Total salary in Marketing",
        "Show all employees",
        "Show all departments",
        "Total salary expense for Sales"
    ]
    
    # Search interface
    st.markdown("### 🔍 Search Database")
    search_placeholder = "Try: " + example_queries[0]
    query = st.text_input("Enter your query or choose from suggestions below:", 
                         placeholder=search_placeholder)
    
    # Query suggestions
    st.markdown("#### Quick Suggestions:")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📊 Show all employees"):
            query = "Show all employees"
        if st.button("💰 Show department salaries"):
            query = "Total salary in Sales"
    with col2:
        if st.button("👥 Show all departments"):
            query = "Show all departments"
        if st.button("📅 Show recent hires"):
            query = "Show employees hired after 2021-01-01"
    with col3:
        if st.button("💵 Total salary expense"):
            query = "Total salary expense for Sales"
    
    # Process query
    if query:
        # Parse query and show parameter editor
        if "employees in" in query.lower():
            dept_match = re.search(r"in (\w+)", query)
            if dept_match:
                default_dept = dept_match.group(1)
            else:
                default_dept = departments[0]
            
            department = st.selectbox("Select or edit department:", 
                                    departments,
                                    index=departments.index(default_dept) if default_dept in departments else 0)
            
            df = query_engine.execute_query("employees_in_department", department=department)
            st.markdown(f"### Employees in {department}")
            st.dataframe(df)
            
            # Show summary
            if not df.empty:
                st.markdown("#### Department Summary")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Employees", len(df))
                with col2:
                    st.metric("Average Salary", f"${df['Salary'].mean():,.2f}")
        
        elif "manages" in query.lower():
            dept_match = re.search(r"manages (\w+)", query)
            if dept_match:
                default_dept = dept_match.group(1)
            else:
                default_dept = departments[0]
                
            department = st.selectbox("Select or edit department:", 
                                    departments,
                                    index=departments.index(default_dept) if default_dept in departments else 0)
            
            df = query_engine.execute_query("department_manager", department=department)
            if not df.empty:
                st.success(f"The manager of {department} is {df['Manager'].iloc[0]}")
            else:
                st.info(f"No manager found for {department}")
        
        elif "hired after" in query.lower():
            date_match = re.search(r"after (\d{4}-\d{2}-\d{2})", query)
            if date_match:
                default_date = date_match.group(1)
            else:
                default_date = "2021-01-01"
                
            date = st.date_input("Select or edit date:", 
                               value=datetime.strptime(default_date, '%Y-%m-%d'))
            
            df = query_engine.execute_query("employees_after_date", date=date.strftime('%Y-%m-%d'))
            st.markdown(f"### Employees hired after {date}")
            st.dataframe(df)
            
            if not df.empty:
                st.info(f"Found {len(df)} employees hired after {date}")
        
        elif "salary in" in query.lower():
            dept_match = re.search(r"in (\w+)", query)
            if dept_match:
                default_dept = dept_match.group(1)
            else:
                default_dept = departments[0]
                
            department = st.selectbox("Select or edit department:", 
                                    departments,
                                    index=departments.index(default_dept) if default_dept in departments else 0)
            
            df = query_engine.execute_query("department_salary", department=department)
            if not df.empty:
                st.markdown(f"### Salary Analysis for {department}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Employees", int(df['Employee_Count'].iloc[0]))
                with col2:
                    st.metric("Total Salary", f"${int(df['Total_Salary'].iloc[0]):,}")
                with col3:
                    st.metric("Average Salary", f"${int(df['Average_Salary'].iloc[0]):,}")
                
                st.markdown("#### Salary Range")
                st.info(f"${int(df['Min_Salary'].iloc[0]):,} - ${int(df['Max_Salary'].iloc[0]):,}")
        
        elif "total salary expense for" in query.lower():
            dept_match = re.search(r"for (\w+)", query)
            if dept_match:
                default_dept = dept_match.group(1)
            else:
                default_dept = departments[0]
                
            department = st.selectbox("Select or edit department:", 
                                    departments,
                                    index=departments.index(default_dept) if default_dept in departments else 0)
            
            df = query_engine.execute_query("total_salary_expense", department=department)
            
            if not df.empty:
                st.markdown(f"### Salary Expense Analysis for {department}")
                
                # Display metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Salary Expense", f"${int(df['Total_Expense'].iloc[0]):,}")
                with col2:
                    st.metric("Number of Employees", int(df['Employee_Count'].iloc[0]))
                
                # Calculate average salary
                avg_salary = df['Total_Expense'].iloc[0] / df['Employee_Count'].iloc[0]
                st.metric("Average Salary per Employee", f"${int(avg_salary):,}")
                
                # Add a bar chart
                st.markdown("#### Salary Breakdown")
                employees_df = query_engine.execute_query("employees_in_department", department=department)
                if not employees_df.empty:
                    st.bar_chart(employees_df.set_index('Name')['Salary'])
            else:
                st.warning(f"No salary data found for {department}")
        
        elif "all employees" in query.lower():
            df = query_engine.execute_query("all_employees")
            st.markdown("### All Employees")
            st.dataframe(df)
            
            if not df.empty:
                st.markdown("#### Company Overview")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Employees", len(df))
                with col2:
                    st.metric("Average Salary", f"${df['Salary'].mean():,.2f}")
                with col3:
                    st.metric("Departments", len(df['Department'].unique()))
        
        elif "all departments" in query.lower():
            df = query_engine.execute_query("all_departments")
            st.markdown("### All Departments")
            st.dataframe(df)


def database_view():
    st.title("Database Tables ")
    
    conn = sqlite3.connect('company.db')
    
    st.markdown("###  Employees")
    employees_df = pd.read_sql_query("SELECT * FROM Employees", conn)
    st.dataframe(employees_df)
    
    st.markdown("### Departments")
    departments_df = pd.read_sql_query("SELECT * FROM Departments", conn)
    st.dataframe(departments_df)
    
    conn.close()

def main():
    st.set_page_config(
        page_title="Company Database Assistant",
        page_icon="",
        layout="wide"
    )
    
    # Initialize database
    DatabaseManager()
    
    # Sidebar navigation
    st.sidebar.title("Navigation ")
    page = st.sidebar.radio("Go to:", ["Main Page", "View Database"])
    
    if page == "Main Page":
        main_page()
    else:
        database_view()

if __name__ == "__main__":
    main()