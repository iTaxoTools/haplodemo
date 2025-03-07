from pathlib import Path

from pytest import mark

from itaxotools.haplodemo.window import Window

test_demos = [
    "load_demo_simple",
    "load_demo_fields",
    "load_demo_tiny_tree",
    "load_demo_long_tree",
    "load_demo_heavy_tree",
    "load_demo_cycled_graph",
    "load_demo_members_tree",
    # "load_demo_many",
]


@mark.parametrize("demo", test_demos)
def test_demos(qapp, demo):
    window = Window()
    demo = getattr(window.demos, demo)
    demo()


def test_yaml(qapp):
    here = Path(__file__).parent
    window = Window()
    window.load_yaml(str(here / "members_graph.yaml"))
