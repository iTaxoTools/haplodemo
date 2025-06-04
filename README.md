# Haplodemo

[![PyPI - Version](https://img.shields.io/pypi/v/itaxotools-haplodemo?color=tomato)](
    https://pypi.org/project/itaxotools-haplodemo)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/itaxotools-haplodemo)](
    https://pypi.org/project/itaxotools-haplodemo)
[![GitHub - Tests](https://img.shields.io/github/actions/workflow/status/iTaxoTools/haplodemo/test.yml?label=tests)](
    https://github.com/iTaxoTools/haplodemo/actions/workflows/test.yml)
[![GitHub - Windows](https://img.shields.io/github/actions/workflow/status/iTaxoTools/haplodemo/windows.yml?label=windows)](
    https://github.com/iTaxoTools/haplodemo/actions/workflows/windows.yml)
[![GitHub - macOS](https://img.shields.io/github/actions/workflow/status/iTaxoTools/haplodemo/macos.yml?label=macos)](
    https://github.com/iTaxoTools/haplodemo/actions/workflows/macos.yml)

A graphical backend module to visualize, edit and export haplotype networks.

This is *not* a standalone application. For an implementation that visualizes sequence files, visit [Hapsolutely](https://github.com/iTaxoTools/Hapsolutely/).

## Examples

Lay out the initial graph using a modified spring algorithm:

![Long tree](https://raw.githubusercontent.com/iTaxoTools/haplodemo/v0.3.0/images/long_tree.png)

Interact with the graph before saving the results:

![Heavy tree](https://raw.githubusercontent.com/iTaxoTools/haplodemo/v0.3.0/images/heavy_tree.gif)

Supports haploweb visualization:

![Haploweb](https://raw.githubusercontent.com/iTaxoTools/haplodemo/v0.3.0/images/haploweb.png)

## Installation

Haplodemo is available on PyPI. You can install it through `pip`:

```
pip install itaxotools-haplodemo
```

## Executables

Standalone executables are included for demonstrating the library capabilities.

It is *not* possible to open custom haplotype networks with the demo program.

[![Release](https://img.shields.io/badge/release-0.3.0-red?style=for-the-badge)](
    https://github.com/iTaxoTools/haplodemo/releases/v0.3.0)
[![Windows](https://img.shields.io/badge/Windows-blue.svg?style=for-the-badge&logo=data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPCEtLSBDcmVhdGVkIHdpdGggSW5rc2NhcGUgKGh0dHA6Ly93d3cuaW5rc2NhcGUub3JnLykgLS0+Cjxzdmcgd2lkdGg9IjQ4IiBoZWlnaHQ9IjQ4IiB2ZXJzaW9uPSIxLjEiIHZpZXdCb3g9IjAgMCAxMi43IDEyLjciIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CiA8ZyBmaWxsPSIjZmZmIiBzdHJva2UtbGluZWNhcD0ic3F1YXJlIiBzdHJva2Utd2lkdGg9IjMuMTc0OSI+CiAgPHJlY3QgeD0iLjc5MzczIiB5PSIuNzkzNzMiIHdpZHRoPSI1LjAyNyIgaGVpZ2h0PSI1LjAyNyIvPgogIDxyZWN0IHg9IjcuMTQzNiIgeT0iLjc5MzczIiB3aWR0aD0iNC43NjI0IiBoZWlnaHQ9IjUuMDI3Ii8+CiAgPHJlY3QgeD0iLjc5MzczIiB5PSI2Ljg3OSIgd2lkdGg9IjUuMDI3IiBoZWlnaHQ9IjUuMDI3Ii8+CiAgPHJlY3QgeD0iNy4xNDM2IiB5PSI2Ljg3OSIgd2lkdGg9IjQuNzYyNCIgaGVpZ2h0PSI1LjAyNyIvPgogPC9nPgo8L3N2Zz4K)](
    https://github.com/iTaxoTools/haplodemo/releases/download/v0.3.0/haplodemo-0.3.0-windows-x64.exe)
[![MacOS](https://img.shields.io/badge/macOS-slategray.svg?style=for-the-badge&logo=apple)](
    https://github.com/iTaxoTools/haplodemo/releases/download/v0.3.0/haplodemo-0.3.0-macos-universal2.dmg)

## Usage

Launch the demo application to get an overview of the features: `haplodemo`

![Demo](https://raw.githubusercontent.com/iTaxoTools/haplodemo/v0.3.0/images/demo.png)

To get started on instantiating the scene, view and controls, look at [window.py](https://github.com/iTaxoTools/haplodemo/blob/v0.3.0/src/itaxotools/haplodemo/window.py).

For some examples of data visualization, look at [demos.py](https://github.com/iTaxoTools/haplodemo/blob/v0.3.0/src/itaxotools/haplodemo/demos.py).

For a comprehensive example of a network in YAML format, look at [members_graph.yaml](https://github.com/iTaxoTools/haplodemo/blob/v0.3.0/src/itaxotools/haplodemo/tests/members_graph.py).

The network can be given in tree or graph format using the `HaploTreeNode` and `HaploGraph` types.
It is also possible to load a network from a properly formatted YAML file, or directly from a Python dictionary.
Alternatively, populate the scene manually with nodes and edges.
