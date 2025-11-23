"""
Extract office building tenant engagement contacts to a separate CSV file
"""
import pandas as pd

# Read the full output
df = pd.read_csv('data/output_all_merchants.csv')

# Filter for office buildings (type contains 'center', 'building', 'realty', etc.)
building_keywords = ['business center', 'office', 'building', 'realty', 'property management', 'real estate']

def is_building(row):
    name = str(row.get('name', '')).lower()
    type_val = str(row.get('type', '')).lower()
    combined = f"{name} {type_val}"

    # Check for specific building entry
    if '330 madison avenue' in name.lower() and 'business center' in type_val.lower():
        return True

    # Check for building-related keywords in type
    for keyword in building_keywords:
        if keyword in type_val:
            return True

    return False

# Filter buildings
buildings = df[df.apply(is_building, axis=1)].copy()

# Select relevant columns for tenant engagement
columns = [
    'name', 'type', 'website',
    'email', 'email_contact_name', 'email_contact_title', 'email_secondary',
    'phone', 'phone_contact_name', 'phone_contact_title', 'phone_secondary',
    'address', 'linkedin',
    'contact_person', 'contact_title'
]

# Keep only columns that exist
columns = [c for c in columns if c in buildings.columns]
buildings = buildings[columns]

# Save to separate file
output_file = 'data/output_building_contacts.csv'
buildings.to_csv(output_file, index=False)

print(f"Extracted {len(buildings)} building contact(s) to {output_file}")
print("\nBuilding contacts:")
for _, row in buildings.iterrows():
    print(f"\nName: {row['name']}")
    print(f"Type: {row['type']}")
    print(f"Email: {row.get('email', 'N/A')}")
    print(f"Phone: {row.get('phone', 'N/A')}")
    print(f"Contact Person: {row.get('contact_person', 'N/A')}")
