import pyodbc

def get_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=ABDEYALI\\SQLEXPRESS;'
        'DATABASE=Face_Recognization;'
        'UID=jobportal;'
        'PWD=123;'
    )
    return conn
