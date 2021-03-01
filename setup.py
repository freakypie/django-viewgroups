from setuptools import setup, find_packages

setup(
    name='django-viewgroups',
    version='0.1.32',
    author='John Leith',
    author_email='leith.john@gmail.com',
    packages=find_packages(),
    url='https://github.com/freakypie/django-viewgroups.git',
    description='Django admin like groups of CBVs',
#     long_description=open('README.rst').read(),
    install_requires=[
        "six"
    ],
    include_package_data=True,
    zip_safe=False,
)
