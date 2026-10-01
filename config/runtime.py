import sys
from importlib.metadata import version, PackageNotFoundError

def runtime_info():
    info = {"python": sys.version.split()[0]}
    for name in ["streamlit", "numpy", "pandas", "yfinance", "plotly", "requests", "openai"]:
        try:
            info[name] = version(name)
        except PackageNotFoundError:
            info[name] = "미설치"
    return info

def validate_runtime():
    problems = []
    if sys.version_info < (3, 11):
        problems.append("Python 3.11 이상이 필요합니다.")
    return problems
