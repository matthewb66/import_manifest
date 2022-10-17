import setuptools
import platform

platform_system = platform.system()

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="bd_import_manifest",
    version=1.3,
    author="Matthew Brady",
    author_email="mbrad@synopsys.com",
    description="Import components into Black Duck",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/matthewb66/import_manifest",
    packages=setuptools.find_packages(),
    install_requires=[
        'blackduck>=1.0.7',
        "aiohttp",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.0',
    entry_points={
        'console_scripts': ['bd-import-manifest=import_manifest.import_manifest:main'],
    },
)
