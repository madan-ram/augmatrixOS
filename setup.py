from setuptools import setup, find_packages

# Read the requirements from the file
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="augmatrix",
    version="1.0.0",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            # If you want to create command-line scripts with your package,
            # add the entry points here
        ],
    },
)
