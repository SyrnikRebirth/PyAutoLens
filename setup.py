from codecs import open
from os.path import abspath, dirname, join
from subprocess import call

from setuptools import Command, find_packages, setup

from autolens import __version__

this_dir = abspath(dirname(__file__))
with open(join(this_dir, 'README.md'), encoding='utf-8') as file:
    long_description = file.read()


class RunTests(Command):
    """Run all tests."""
    description = 'run tests'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """Run all tests!"""
        errno = call(['py.test', '--cov=autolens', '--cov-report=term-missing'])
        raise SystemExit(errno)


setup(
    name='autolens',
    version=__version__,
    description='Automated Strong Gravitational Lens Modeling',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Jammy2211/PyAutoLens',
    author='James Nightingale and Richard Hayes',
    author_email='james.w.nightingale@durham.ac.uk',
    include_package_data=True,
    license='MIT License',
    classifiers=[
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Physics',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ],
    keywords='cli',
    packages=find_packages(exclude=['docs', 'tests*', 'workspace', 'workspace_jam']),
    install_requires=['docopt',
                      'numpy==1.16.2',
                      'astropy',
                      'scipy==1.2.0',
                      'GetDist',
                      'pymultinest',
                      'scikit-learn',
                      'scikit-image==0.14.2',
                      'numba',
                      'matplotlib==3.0.3',
                      'colorama',
                      'autofit==0.20.0',
                      'Cython==0.28.0',
                      'pyquad'
                      ],
    extras_require={
        'test': ['coverage', 'pytest', 'pytest-cov'],
    },
    entry_points={
        'console_scripts': [
            'autolens=autolens.cli:main',
        ],
    },
    cmdclass={'test': RunTests},
)
