import sys
from importlib.util import find_spec

packages = ["streamlit", "numpy", "pandas", "yfinance", "plotly", "requests", "dotenv", "openai"]

print("Python:", sys.version)
print()
for p in packages:
    print(f"{p:12}:", "OK" if find_spec(p) else "MISSING")

if sys.version_info[:2] != (3, 14):
    print("\n주의: 이 프로젝트는 Python 3.14 환경을 기준으로 준비되었습니다.")
else:
    print("\nPython 3.14 환경 확인 완료.")
