"""Setup configuration for DAP client"""

from setuptools import setup, find_packages

setup(
    name="symbolic-mlir-dap-client",
    version="0.1.0",
    description="DAP client for automated testing of Symbolic MLIR Debugger",
    author="Symbolic MLIR Debugger Team",
    author_email="team@example.com",
    url="https://github.com/example/symbolic-mlir-debugger",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    install_requires=[
        "jsonschema>=4.0.0",
    ],
    python_requires=">=3.8",
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "mlir-dap-test=examples.basic_session:main",
        ],
    },
)
