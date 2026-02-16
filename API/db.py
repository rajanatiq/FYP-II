# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import urllib

username = "sa"
password = "Macbookpro2019"
server = "localhost"           # SQL Server instance
database = "ExamProctoring"
driver = "ODBC Driver 17 for SQL Server"

# Build connection string with proper URL encoding
connection_string = (
    f"mssql+pyodbc://{username}:{password}@{server}/{database}"
    f"?driver={urllib.parse.quote_plus(driver)}"
)
engine = create_engine(connection_string, echo=False)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    """
    Use this in FastAPI routes:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
