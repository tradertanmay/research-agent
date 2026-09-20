from setuptools import setup, find_packages

setup(
    name="research-agent",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["run"],
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn>=0.28.0",
        "httpx>=0.27.0",
        "pydantic>=2.6.0",
        "pydantic-settings>=2.2.0",
        "beautifulsoup4>=4.12.0",
        "rich>=13.7.0",
        "python-multipart>=0.0.9",
    ],
    entry_points={
        "console_scripts": [
            "research-agent=run:main",
        ],
    },
)
