"""
Test script to verify expression metadata is being saved to the database
"""
import os
import sys
from peewee import SqliteDatabase
from mwi import model, core

# Ensure we're using the correct database
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data/mwi.db')
print(f"Using database at: {db_path}")
model.DB = SqliteDatabase(db_path)

def test_expression_metadata():
    """Test expression metadata extraction and saving"""
    # Create a test land if it doesn't exist
    land, land_created = model.Land.get_or_create(name='test_land', description='Test Land')
    
    # Create a test domain if it doesn't exist
    domain, domain_created = model.Domain.get_or_create(name='github.com')
    
    # Create or get the expression
    expression, expr_created = model.Expression.get_or_create(
        land=land,
        domain=domain,
        url="https://github.com",
        defaults={'depth': 0}
    )
    
    # Reset metadata fields
    expression.title = None
    expression.description = None
    expression.keywords = None
    expression.save()
    
    print(f"Expression before metadata extraction: title={expression.title}, description={expression.description}, keywords={expression.keywords}")
    
    # Fetch and process the expression
    try:
        request = core.requests.get(
            "https://github.com",
            headers={"User-Agent": core.settings.user_agent},
            timeout=5)
        
        # Process the expression content
        core.process_expression_content(expression, request.text, [])
        
        # Save the expression
        expression.save()
        
        # Verify the expression was updated
        updated_expr = model.Expression.get(model.Expression.url == "https://github.com")
        print(f"Expression after metadata extraction: title={updated_expr.title}, description={updated_expr.description}, keywords={updated_expr.keywords}")
        
        # Check if metadata was saved
        if updated_expr.description or updated_expr.keywords:
            print("SUCCESS: Expression metadata was saved to the database")
        else:
            print("FAILURE: Expression metadata was not saved to the database")
            
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    test_expression_metadata()
