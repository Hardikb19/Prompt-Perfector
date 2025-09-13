from setuptools import setup, find_packages

setup(
    name="promptperfector",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PySide6",
        "uuid"
    ],
    entry_points={
        'console_scripts': [
            'promptperfector=promptperfector.main:main',
            'promptperfector-initdb=promptperfector.logic.__main__:main',
        ],
    },
)
