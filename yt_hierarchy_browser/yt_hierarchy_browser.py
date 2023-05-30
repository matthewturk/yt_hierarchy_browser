"""Main module."""

from rich.segment import Segment
from rich.style import Style

from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Header, Footer, Tree, Static
from textual.reactive import reactive
from textual.strip import Strip
from textual.color import Color

import yt
import unyt
import cmyt
from yt.data_objects.index_subobjects import AMRGridPatch
from yt.data_objects.api import Dataset

import numpy as np

class ImagePlotViewer(Widget):
    min_value: reactive[float | None] = reactive(None)
    max_value: reactive[float | None] = reactive(None)
    color_map: reactive[str] = reactive("arbre")
    data_values: reactive[tuple[unyt.unyt_array] | None] = reactive(None, always_update=True)

    def compute_min_value(self) -> float:
        if self.data_values is None: return 0.0
        return self.data_values[0].min()

    def compute_max_value(self) -> float:
        if self.data_values is None: return 0.0
        return self.data_values[0].max()

    def render_line(self, y: int) -> Segment:
        if self.data_values is None: return Strip([])
        if y >= self.data_values[0].shape[1]: return Strip([])
        cmap = getattr(cmyt, self.color_map)
        dv = self.data_values[0][:, y]
        dv = (dv - self.min_value)/(self.max_value - self.min_value)
        segments = []
        for val in dv:
            color = [int(_*255) for _ in cmap(val)][:-1]
            c = Color(*color).css
            segments.append(Segment("\u2588", Style.parse(c)))
        return Strip(segments)

class GridSliceView(Static):

    grid_values: reactive[unyt.unyt_array | None] = reactive(None)
    coord: int = reactive(0)
    axis: int = reactive(0)

    def watch_data_values(self, data_values: unyt.unyt_array | None) -> None:
        pass

    def validate_coord(self, coord) -> int:
        if self.grid_values is None: return coord
        shape = self.grid_values.shape
        coord = max(min(shape[self.axis] - 1, coord), 0)
        return coord

    def watch_coord(self, coord: int) -> None:
        pass

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
        yield GridHierarchyBrowser()
        yield GridViewer()
        yield ImagePlotViewer()
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        ghv = self.query_one(GridHierarchyBrowser)
        ds = yt.load_sample("IsolatedGalaxy")
        ipv = self.query_one(ImagePlotViewer)
        assert ds is not None
        ghv.dataset = ds
        #print(ds.index.grids[0]["density"][:,:,16])
        ipv.data_values = (ds.index.grids[0]["density"][:,:,16].d,)
        ipv.refresh()

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted) -> None:
        if event.node.data is None: return
        gv = self.query_one(GridViewer)
        gv.grid = event.node.data['grid']

if __name__ == "__main__":
    app = DatasetBrowser()
    app.run()
