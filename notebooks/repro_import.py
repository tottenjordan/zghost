
import sys
import os
print(f"CWD: {os.getcwd()}")
print(f"sys.path: {sys.path}")

try:
    from trends_and_insights_agent import agent
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
