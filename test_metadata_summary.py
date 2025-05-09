"""
Summary of metadata extraction tests
"""
import os
import sys
from peewee import SqliteDatabase
from mwi import model, core

# Ensure we're using the correct database
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data/mwi.db')
print(f"Using database at: {db_path}")
model.DB = SqliteDatabase(db_path)

def test_with_meta_tags():
    """Test with a website that has meta tags"""
    print("\nTesting with a website that has meta tags (github.com):")
    
    # Create a test domain if it doesn't exist
    domain, created = model.Domain.get_or_create(name='github.com')
    
    # Reset metadata fields
    domain.title = None
    domain.description = None
    domain.keywords = None
    domain.save()
    
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
        print(f"Domain metadata: title={updated_domain.title}, description={updated_domain.description}, keywords={updated_domain.keywords}")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")

def test_without_meta_tags():
    """Test with a website that doesn't have meta tags"""
    print("\nTesting with a website that doesn't have meta tags (example.com):")
    
    # Create a test domain if it doesn't exist
    domain, created = model.Domain.get_or_create(name='example.com')
    
    # Reset metadata fields
    domain.title = None
    domain.description = None
    domain.keywords = None
    domain.save()
    
    # Fetch and process the domain
    try:
        request = core.requests.get(
            "https://example.com",
            headers={"User-Agent": core.settings.user_agent},
            timeout=5)
        
        # Process the domain content
        core.process_domain_content(domain, request.text)
        
        # Save the domain
        domain.save()
        
        # Verify the domain was updated
        updated_domain = model.Domain.get(model.Domain.name == 'example.com')
        print(f"Domain metadata: title={updated_domain.title}, description={updated_domain.description}, keywords={updated_domain.keywords}")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")

def test_with_default_values():
    """Test with default values for missing meta tags"""
    print("\nTesting with default values for missing meta tags:")
    
    # Create a test domain if it doesn't exist
    domain, created = model.Domain.get_or_create(name='example.com')
    
    # Reset metadata fields
    domain.title = None
    domain.description = None
    domain.keywords = None
    domain.save()
    
    # Fetch and process the domain
    try:
        request = core.requests.get(
            "https://example.com",
            headers={"User-Agent": core.settings.user_agent},
            timeout=5)
        
        # Process the domain content with default values
        soup = core.BeautifulSoup(request.text, 'html.parser')
        domain.title = core.get_title(soup) or "Default Title"
        domain.description = core.get_description(soup) or "Default Description"
        domain.keywords = core.get_keywords(soup) or "default, keywords"
        domain.save()
        
        # Verify the domain was updated
        updated_domain = model.Domain.get(model.Domain.name == 'example.com')
        print(f"Domain metadata with defaults: title={updated_domain.title}, description={updated_domain.description}, keywords={updated_domain.keywords}")
        
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    test_with_meta_tags()
    test_without_meta_tags()
    test_with_default_values()
