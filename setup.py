from setuptools import find_packages, setup

setup(
    author="UvA",
    author_email="jelle.van.assema@uva.nl",
    classifiers=[
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3",
        "Topic :: Education",
        "Topic :: Utilities"
    ],
    description="This is University of Amsterdam's check50 extension.",
    install_requires=["check50>=3.0.0"],
    keywords=["check", "check50", "uva"],
    name="uva50",
    packages=["uva50"],
    python_requires=">= 3.6",
    url="https://github.com/jelleas/uva_check50",
    version="0.0.0",
)
