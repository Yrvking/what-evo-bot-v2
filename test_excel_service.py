from app.services.excel_service import excel_service

print("--- TESTING EXCEL SERVICE ---")
print(f"Total Rows: {len(excel_service.df)}")

if not excel_service.df.empty:
    sample = excel_service.df.iloc[0]
    print("Sample Row:")
    print(sample[[col for col in sample.index if col in ['Celular', 'Nombres', 'Proyecto']]])
    
    # Test Phone Logic
    phone_test = sample['Celular'] 
    print(f"\nSearching for phone: {phone_test}")
    users = excel_service.find_users_by_phone(phone_test)
    print("Found Users:", len(users))
    if users:
        print(users[0])
else:
    print("DataFrame is empty.")
