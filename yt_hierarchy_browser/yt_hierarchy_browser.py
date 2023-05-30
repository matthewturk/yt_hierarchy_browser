"""Main module."""

from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Header, Footer, Tree, Static
from textual.reactive import reactive

import yt
from yt.data_objects.index_subobjects import AMRGridPatch
from yt.data_objects.api import Dataset

class GridViewer(Static):
    grid: reactive[AMRGridPatch | None] = reactive(None)

    def compose(self):
        yield Static(id = "grid_info")
        yield Static(id = "grid_view")

    def watch_grid(self, grid: AMRGridPatch) -> None:
        if grid is None: return
        grid_info = self.query_one("#grid_info")
        grid_info.update(f"Left Edge: {grid.LeftEdge}\n"
                         f"Right Edge: {grid.RightEdge}\n"
                         f"Active Dimensions: {grid.ActiveDimensions}\n"
                         f"Level: {grid.Level}\n")

class GridHierarchyBrowser(Static):
    dataset: reactive[Dataset | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Tree(label = "Grid Hierarchy", id = "grid_hierarchy")

    def watch_dataset(self, dataset: Dataset) -> None:
        if dataset is None: return
        def dictify(g):
            return {'ActiveDimensions': g.ActiveDimensions,
                    'LeftEdge': g.LeftEdge,
                    'RightEdge': g.RightEdge,
                    'Level': g.Level,
                    'grid': g}
        tree: Tree[dict] = self.query_one(Tree)
        tree.root.expand()
        def add_children(node, g):
            data = dictify(g)
            if len(g.Children) == 0:
                node.add_leaf(str(g), data = data)
            else:
                n = node.add(str(g), data = data)
                for c in g.Children:
                    add_children(n, c)
        for grid in dataset.index.select_grids(0):
            # These are all the root grids
            node = tree.root.add(str(grid), data = dictify(grid), expand = True)
            for c in grid.Children:
                add_children(node, c)

class DatasetBrowser(App):
    CSS_PATH = "yt_hierarchy_browser.css"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield GridHierarchyBrowser()
        yield GridViewer()

    def on_mount(self) -> None:
        ghv = self.query_one(GridHierarchyBrowser)
        ds = yt.load_sample("IsolatedGalaxy")
        assert ds is not None
        ghv.dataset = ds

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        if event.node.data is None: return
        gv = self.query_one(GridViewer)
        gv.grid = event.node.data['grid']

if __name__ == "__main__":
    app = DatasetBrowser()
    app.run()
