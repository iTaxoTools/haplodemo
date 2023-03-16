
from itaxotools.common.types import Type


class Palette(list, Type):
    label = 'Palette'
    default = 'gray'
    colors = []

    def __init__(self):
        super().__init__(self.colors)

    def __getitem__(self, index):
        if index < len(self):
            return super().__getitem__(index)
        return self.default

    @property
    def label(self):
        return type(self).__name__


class Set1(Palette):
    label = 'Set1'
    default = '#999999'
    colors = [
        '#e41a1c',
        '#377eb8',
        '#4daf4a',
        '#984ea3',
        '#ff7f00',
        '#ffff33',
        '#a65628',
        '#f781bf',
    ]


class Spring(Palette):
    label = 'Spring'
    default = '#aaaaaa'
    colors = [
        '#fd7f6f',
        '#7eb0d5',
        '#b2e061',
        '#bd7ebe',
        '#ffb55a',
        '#ffee65',
        '#beb9db',
        '#fdcce5',
        '#8bd3c7'
    ]


class Pastel(Palette):
    label = 'Pastel'
    default = '#f2f2f2'
    colors = [
        '#fbb4ae',
        '#b3cde3',
        '#ccebc5',
        '#decbe4',
        '#fed9a6',
        '#ffffcc',
        '#e5d8bd',
        '#fddaec',
    ]


class Tab10(Palette):
    label = 'Tab10'
    default = '#c7c7c7'
    colors = [
        '#1f77b4',
        '#ff7f0e',
        '#2ca02c',
        '#d62728',
        '#9467bd',
        '#8c564b',
        '#e377c2',
        '#7f7f7f',
        '#bcbd22',
        '#17becf',
    ]


class RetroMetro(Palette):
    label = 'RetroMetro'
    colors = [
        '#ea5545',
        '#f46a9b',
        '#ef9b20',
        '#edbf33',
        '#ede15b',
        '#bdcf32',
        '#87bc45',
        '#27aeef',
        '#b33dc6'
    ]


class Spectrum(Palette):
    label = 'Spectrum'
    colors = [
        '#0fb5ae',
        '#4046ca',
        '#f68511',
        '#de3d82',
        '#7e84fa',
        '#72e06a',
        '#147af3',
        '#7326d3',
        '#e8c600',
        '#cb5d00',
        '#008f5d',
        '#bce931',
    ]


class Grayscale(Palette):
    label = 'Grayscale'
    default = '#070707'
    colors = [
        '#252525',
        '#cccccc',
        '#636363',
        '#f7f7f7',
        '#969696',
    ]
