import os
from setuptools import setup, find_packages


try:
    with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except:
    long_description = ''


setup(
    name='pretix-eupago',
    version='1.0.0',
    description='EuPago payment provider for pretix',
    long_description=long_description,
    url='https://github.com/jgomes-03/plugin-pretix-eupago',
    author='Jorge Gomes',
    author_email='jorge.gomes211@gmail.com',
    license='Proprietary',
    install_requires=['requests>=2.20.0'],
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,

    entry_points="""
[pretix.plugin]
eupago=eupago:PluginApp.PretixPluginMeta
""",
)
