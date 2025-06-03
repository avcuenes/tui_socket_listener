# setup.py
from setuptools import setup, find_packages

setup(
    name='netutil-tui',  # The name of your package
    version='0.1.1',     # The current version of your package
    author='Mehmet Enes Avcu',  # Your name or organization
    author_email='your.email@example.com', # Your email
    description='A TUI-based network utility for TCP/UDP listen/write operations.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/avcuenes/tui_socket_listener', # Optional: Link to your project repository
    packages=find_packages(), # Automatically find all packages in the directory
    install_requires=[
        # List your project's dependencies here.
        # 'curses' is a standard library on Unix, but 'windows-curses' is needed for Windows.
        # We'll handle this conditionally in the entry point or rely on user to install.
    ],
    # Define console scripts to make your package executable from the terminal
    entry_points={
        'console_scripts': [
            'netutil = netutil.network_utility_tui:main', # 'netutil' is the command,
                                                          # 'netutil.network_utility_tui' is the module,
                                                          # 'main' is the function to call.
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License', # Or your chosen open-source license
        'Operating System :: OS Independent',
        'Environment :: Console :: Curses',
        'Topic :: System :: Networking',
        'Topic :: Utilities',
    ],
    python_requires='>=3.6', # Minimum Python version required
)