from setuptools import setup, find_packages

setup(
    name='openchemistry-codes',
    version='0.0.1',
    description='Keep track of codes used in OpenChemistry.',
    packages=find_packages(),
    install_requires=[
      'girder>=3.0.0a5'
    ],
    entry_points={
      'girder.plugin': [
          'codes = codes:CodesPlugin'
      ]
    }
)
