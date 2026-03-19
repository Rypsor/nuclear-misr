import os

try:
    with open("comparison_results.txt", "r", encoding="utf-16") as f:
        print(f.read())
except Exception as e:
    # Try with another encoding if utf-16 fails
    try:
        with open("comparison_results.txt", "r", encoding="utf-8") as f:
            print(f.read())
    except:
        print(f"Error reading file: {e}")
