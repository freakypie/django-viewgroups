from setuptools import setup, find_packages

setup(
    name='django-viewgroups',
    version='0.0.6',
    author='John Leith',
    author_email='leith.john@gmail.com',
    packages=find_packages(),
    url='http://pypi.python.org/pypi/django-viewgroups/',
    description='Django admin like groups of CBVs',
    long_description=open('README.rst').read(),
    install_requires=[
        "Django>=1.4,<=1.5",
    ],
    package_data = {
        '': ['*.txt', '*.rst', '*.md', '*.html'],
    },
)
