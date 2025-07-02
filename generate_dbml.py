#!/usr/bin/env python3
"""
Simple DBML Generator for CARLA Driving Simulator

This script generates DBML content from SQLAlchemy models for use with dbdiagram.io
Run from project root: python generate_dbml.py

Usage:
    python generate_dbml.py                    # Print DBML to console
    python generate_dbml.py --file output.dbml # Save to file
"""

import sys
import os
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.models import Base, Scenario, VehicleData, SensorData, SimulationMetrics
from src.database.config import DATABASE_URL, SCHEMA_NAME


def generate_dbml() -> str:
    """Generate DBML content from SQLAlchemy models"""
    dbml_lines = []
    dbml_lines.append("// Auto-generated DBML for CARLA Driving Simulator")
    dbml_lines.append("// Generated from SQLAlchemy models")
    dbml_lines.append("")
    
    # Define model classes explicitly
    model_classes = [Scenario, VehicleData, SensorData, SimulationMetrics]
    
    # Sort by table name for consistent output
    model_classes.sort(key=lambda x: x.__tablename__)
    
    relationships = []
    
    for model_class in model_classes:
        table_name = model_class.__tablename__
        dbml_lines.append(f"Table {table_name} {{")
        
        # Get columns from the model
        for column in model_class.__table__.columns:
            column_def = format_column_for_dbml(column, table_name, relationships)
            dbml_lines.append(f"  {column_def}")
        
        # Add primary key
        pk_columns = [col.name for col in model_class.__table__.primary_key.columns]
        if pk_columns:
            pk_str = ', '.join(pk_columns)
            dbml_lines.append(f"  indexes {{")
            dbml_lines.append(f"    ({pk_str}) [pk]")
            dbml_lines.append(f"  }}")
        
        dbml_lines.append("}")
        dbml_lines.append("")
    
    # No need for separate Ref statements since we're using inline refs
    
    return '\n'.join(dbml_lines)


def format_column_for_dbml(column, table_name, relationships) -> str:
    """Format a SQLAlchemy column for DBML"""
    name = column.name
    type_info = column.type
    
    # Convert SQLAlchemy types to DBML types
    type_str = str(type_info)
    if 'INTEGER' in type_str or 'SERIAL' in type_str:
        dbml_type = 'int'
    elif 'FLOAT' in type_str or 'REAL' in type_str:
        dbml_type = 'float'
    elif 'VARCHAR' in type_str or 'STRING' in type_str:
        dbml_type = 'varchar'
    elif 'TIMESTAMP' in type_str or 'DATETIME' in type_str:
        dbml_type = 'timestamp'
    elif 'BOOLEAN' in type_str:
        dbml_type = 'boolean'
    elif 'JSON' in type_str or 'JSONB' in type_str:
        dbml_type = 'json'
    elif 'UUID' in type_str:
        dbml_type = 'uuid'
    else:
        dbml_type = 'varchar'
    
    # Handle nullable
    nullable = "" if column.nullable else " [not null]"
    
    # Handle default values
    default = ""
    if column.default is not None:
        # Check if it's a function (like datetime.utcnow)
        default_str = str(column.default)
        if 'utcnow' in default_str or 'datetime' in default_str:
            default = " [default: `now()`]"
        elif hasattr(column.default, 'arg'):
            default_value = column.default.arg
            if isinstance(default_value, str):
                default = f" [default: '{default_value}']"
            else:
                default = f" [default: {default_value}]"
        else:
            # Skip function objects
            pass
    
    # Handle foreign key references
    ref = ""
    for fk in column.foreign_keys:
        ref = f" [ref: > {fk.column.table.name}.{fk.column.name}]"
        break
    
    return f"{name} {dbml_type}{nullable}{default}{ref}"


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate DBML for CARLA database")
    parser.add_argument(
        "--file", 
        type=str,
        help="Output file path (e.g., schema.dbml)"
    )
    
    args = parser.parse_args()
    
    try:
        print("🔧 Generating DBML content...")
        dbml_content = generate_dbml()
        
        if args.file:
            # Save to file
            with open(args.file, 'w', encoding='utf-8') as f:
                f.write(dbml_content)
            print(f"✅ Saved DBML to: {args.file}")
            print(f"📋 Copy the content and paste it into https://dbdiagram.io/d")
        else:
            # Print to console
            print("\n" + "="*80)
            print("DBML CONTENT FOR DBDIAGRAM.IO")
            print("="*80)
            print(dbml_content)
            print("="*80)
            print("\n📋 Copy the above content and paste it into https://dbdiagram.io/d")
            print("🎨 You can then customize the diagram and export to various formats")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 