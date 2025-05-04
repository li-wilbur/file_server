from setuptools import setup, find_packages

setup(
    name='files_server',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask==3.0.2',
        'Werkzeug==3.0.1',
        'python-dotenv==1.0.1',
        'prometheus-client==0.19.0',
    ],
    entry_points={
        'console_scripts': [
            'files_server=run:app',
        ],
    },
) 