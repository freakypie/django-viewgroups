from setuptools import setup, find_packages

setup(
    name='django-viewgroups',
    version='0.0.12',
    author='John Leith',
    author_email='leith.john@gmail.com',
    packages=find_packages(),
    url='https://bitbucket.org/freakypie/django-viewsets',
    description='Django admin like groups of CBVs',
#     long_description=open('README.rst').read(),
    install_requires=[
        "Django>=1.4,<1.5",
    ],
    include_package_data=True,
    zip_safe=False,
)
