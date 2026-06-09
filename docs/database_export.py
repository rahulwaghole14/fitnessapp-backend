#!/usr/bin/env python3
"""
Database Schema Export Tool
Safely exports database structure (tables, columns, relationships) without sensitive data
"""

import os
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.schema import CreateTable, CreateIndex
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def export_database_schema():
    """Export complete database schema to SQL and JSON files"""
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Get metadata
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    # Create inspector
    inspector = inspect(engine)
    
    # Export SQL schema
    sql_schema = []
    sql_schema.append("-- Database Schema Export")
    sql_schema.append(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sql_schema.append("-- Fitness App Database Structure")
    sql_schema.append("")
    
    # Get all table names
    table_names = inspector.get_table_names()
    
    for table_name in sorted(table_names):
        sql_schema.append(f"-- Table: {table_name}")
        
        # Get table creation SQL
        table = metadata.tables[table_name]
        create_table_sql = str(CreateTable(table).compile(engine))
        sql_schema.append(create_table_sql + ";")
        
        # Get indexes
        indexes = inspector.get_indexes(table_name)
        for index in indexes:
            index_sql = f"CREATE INDEX {'UNIQUE ' if index['unique'] else ''}{index['name']} ON {table_name} ({', '.join(index['column_names'])});"
            sql_schema.append(index_sql)
        
        sql_schema.append("")
    
    # Write SQL file
    with open('fitness_database_schema.sql', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_schema))
    
    # Export JSON schema (more detailed structure)
    json_schema = {
        "database": "fitness_app",
        "generated_on": datetime.now().isoformat(),
        "tables": {}
    }
    
    for table_name in sorted(table_names):
        columns = inspector.get_columns(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        primary_keys = inspector.get_pk_constraint(table_name)
        indexes = inspector.get_indexes(table_name)
        
        json_schema["tables"][table_name] = {
            "columns": [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": str(col["default"]) if col["default"] else None
                }
                for col in columns
            ],
            "primary_keys": primary_keys["constrained_columns"],
            "foreign_keys": [
                {
                    "columns": fk["constrained_columns"],
                    "referenced_table": fk["referred_table"],
                    "referenced_columns": fk["referred_columns"]
                }
                for fk in foreign_keys
            ],
            "indexes": [
                {
                    "name": idx["name"],
                    "columns": idx["column_names"],
                    "unique": idx["unique"]
                }
                for idx in indexes
            ]
        }
    
    # Write JSON file
    with open('fitness_database_schema.json', 'w', encoding='utf-8') as f:
        json.dump(json_schema, f, indent=2, ensure_ascii=False)
    
    print("Database schema exported successfully!")
    print(f"SQL file: fitness_database_schema.sql")
    print(f"JSON file: fitness_database_schema.json")
    print(f"Total tables exported: {len(table_names)}")
    
    # Print table summary
    print("\nTables exported:")
    for table_name in sorted(table_names):
        print(f"   - {table_name}")

def export_sample_data():
    """Export sample data (optional, limited rows for testing)"""
    engine = create_engine(DATABASE_URL)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    sample_data = {
        "database": "fitness_app",
        "generated_on": datetime.now().isoformat(),
        "sample_data": {},
        "note": "This contains limited sample data for testing purposes only"
    }
    
    # Limit to 3 rows per table for safety
    SAMPLE_LIMIT = 3
    
    for table_name in sorted(metadata.tables.keys()):
        with engine.connect() as conn:
            result = conn.execute(f"SELECT * FROM {table_name} LIMIT {SAMPLE_LIMIT}")
            rows = result.fetchall()
            
            if rows:
                columns = [col["name"] for col in inspector.get_columns(table_name)]
                sample_data["sample_data"][table_name] = [
                    dict(zip(columns, row)) for row in rows
                ]
    
    # Write sample data file
    with open('fitness_sample_data.json', 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"Sample data file: fitness_sample_data.json (max {SAMPLE_LIMIT} rows per table)")

if __name__ == "__main__":
    print("Exporting Fitness App Database Schema...")
    print("=" * 50)
    
    try:
        export_database_schema()
        
        # Ask if user wants sample data
        print("\nDo you want to export sample data too?")
        print("   This exports a few rows from each table for testing.")
        print("   Type 'y' to include sample data, or just press Enter to skip: ", end="")
        
        # For automated use, you can uncomment the line below:
        # export_sample_data()
        
    except Exception as e:
        print(f"Error exporting schema: {e}")
        print("\nMake sure:")
        print("   - DATABASE_URL is correctly set in .env file")
        print("   - Database server is running")
        print("   - You have proper database permissions")
