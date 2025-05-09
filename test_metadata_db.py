"""
Test script to verify metadata is being saved to the database
"""
import os
import sys
from peewee import SqliteDatabase
from mwi import model, core

# Ensure we're using the correct database
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data/mwi.db')
print(f"Using database at: {db_path}")
model.DB = SqliteDatabase(db_path)

def test_domain_metadata():
    """Test domain metadata extraction and saving"""
    # Create a test domain if it doesn't exist
    domain, created = model.Domain.get_or_create(name='github.com')
    
    # Reset metadata fields
    domain.title = None
    domain.description = None
    domain.keywords = None
    domain.save()
    
    print(f"Domain before metadata extraction: title={domain.title}, description={domain.description}, keywords={domain.keywords}")
    
    # Fetch and process the domain
    try:
        request = core.requests.get(
            "https://github.com",
            headers={"User-Agent": core.settings.user_agent},
            timeout=5)
        
        # Process the domain content
        core.process_domain_content(domain, request.text)
        
        # Save the domain
        domain.save()
        
        # Verify the domain was updated
        updated_domain = model.Domain.get(model.Domain.name == 'github.com')
        print(f"Domain after metadata extraction: title={updated_domain.title}, description={updated_domain.description}, keywords={updated_domain.keywords}")
        
        # Check if metadata was saved
        if updated_domain.description or updated_domain.keywords:
            print("SUCCESS: Metadata was saved to the database")
        else:
            print("FAILURE: Metadata was not saved to the database")
            
    except Exception as e:
        print(f"Error during test: {str(e)}")

def test_manual_save():
    """Test manually setting and saving metadata"""
    print("\nTesting manual database save...")
    
    # Create a test domain if it doesn't exist
    domain, created = model.Domain.get_or_create(name='test.example.com')
    
    # Set metadata fields directly
    domain.title = "Test Title"
    domain.description = "Test Description"
    domain.keywords = "test, keywords"
    domain.save()
    
    # Verify the domain was updated
    updated_domain = model.Domain.get(model.Domain.name == 'test.example.com')
    print(f"Domain after manual update: title={updated_domain.title}, description={updated_domain.description}, keywords={updated_domain.keywords}")
    
    # Check if metadata was saved
    if updated_domain.description == "Test Description" and updated_domain.keywords == "test, keywords":
        print("SUCCESS: Manual metadata was saved to the database")
    else:
        print("FAILURE: Manual metadata was not saved to the database")

if __name__ == "__main__":
    test_domain_metadata()
    test_manual_save()
