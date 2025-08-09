from setuptools import setup, find_packages

setup(
    name="ft8decoder",
    version="0.1.2",
    description="An FT8 message logger that tracks, translates, and organizes CQs, QSOs, and Misc. messages from live WSJT-X packets.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ZappatheHackka/ft8decoder",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Communications :: Ham Radio",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    install_requires=[
        "maidenhead",
        "folium",
    ],
    entry_points={
        "console_scripts": [
            "ft8decoder = ft8decoder.cli:main",
        ]
    },
    author="Christopher Cottone",
    author_email="chriscottone1@gmail.com",
    python_requires=">=3.8",
    project_urls={
        "Documentation": "https://zappathehackka.github.io/ft8decoder/",
        "Source Code": "https://github.com/ZappatheHackka/ft8decoder",
    }
)