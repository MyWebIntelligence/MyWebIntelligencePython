"""
Test script to verify metadata extraction from Le Monde URL
"""
import os
import sys
from peewee import SqliteDatabase
from mwi import model, core
import settings # Import settings from root

# Ensure we're using the correct database
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data/mwi.db')
print(f"Using database at: {db_path}")
model.DB = SqliteDatabase(db_path)

# Reload settings to ensure the new User-Agent is used
import importlib
importlib.reload(settings)
importlib.reload(core)


def test_lemonde_url():
    """Test metadata extraction from Le Monde URL"""
    url = "https://www.lemonde.fr/histoire/article/2025/03/23/marion-fontaine-historienne-on-ne-sait-plus-tres-bien-ce-que-signifie-etre-republicain_6585111_4655323.html"
    print(f"\nTesting metadata extraction from: {url}")
    print(f"Using User-Agent: {settings.user_agent}")

    metadata = core.extract_metadata(url)
    
    print(f"Extracted metadata: {metadata}")
    
    if metadata and (metadata.get('title') or metadata.get('description') or metadata.get('keywords')):
        print("SUCCESS: Metadata extracted successfully.")
    else:
        print("FAILURE: Failed to extract metadata or metadata is empty.")

if __name__ == "__main__":
    test_lemonde_url()
