from setuptools import setup


setup(
    name='ansible-sphinx',
    versioning='dev',
    setup_requires='setupmeta',
    install_requires=[
        'myst-parser',
    ],
    extras_require=dict(
        test=[
            'pytest',
        ],
    ),
    author='James Pic',
    author_email='jamespic@gmail.com',
    url='https://yourlabs.io/oss/ansible-sphinx',
    include_package_data=True,
    license='MIT',
    keywords='cli',
    python_requires='>=3.6',
)
