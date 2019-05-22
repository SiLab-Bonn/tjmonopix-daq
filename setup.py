#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages

import tjmonopix

version = tjmonopix.__version__

author = 'Christian Bespin, Ivan Caicedo Sierra, Tomasz Hemperek, Toko Hirono, Konstantinos Moustakas'
author_email = ''

# Requirements
install_requires = ['basil-daq>=3.0.0', 'pixel_clusterizer',
                    'bitarray', 'matplotlib', 'numpy', 'pyyaml',
                    'tables', 'scipy', 'numba', 'tqdm']
setup(
    name='tjmonopix-daq',
    version=version,
    description='DAQ for TJMonoPix prototype',
    url='https://github.com/ChristianBesp/tjmonopix-daq',
    license='',
    long_description='',
    author=author,
    maintainer=author,
    author_email=author_email,
    maintainer_email=author_email,
    install_requires=install_requires,
    packages=find_packages(),
    include_package_data=True,
    platforms='any'
)
