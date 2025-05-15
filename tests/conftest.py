import pandas as _pd
import os
from pathlib import Path
import sys
import types

# ------------------------------------------------------------------
# Speed-hack: avoid importing the full plotting stack (holoviews/bokeh)
# during tests.  Real application code isn't affected because the sandbox
# blocks these libraries anyway.  This shaves ~2 minutes off the very
# first pytest run in a fresh virtual-env.
# ------------------------------------------------------------------

hv_stub = types.ModuleType("holoviews")

# Minimal classes expected by app.utils.plots and Panel


class _HVMeta(type):  # noqa: D401 – custom meta to allow monkey-patching
    """Bare-bones metaclass so tests can set ``__instancecheck__``."""

    pass


class Element(metaclass=_HVMeta):  # noqa: D401 – placeholder hv.Element
    pass


class Overlay(Element):  # noqa: D401 – placeholder hv.Overlay
    pass


# Fake Store with per-backend registry so opts/lookups don't fail
def _set_current_backend(backend: str):  # noqa: D401 – minimal setter
    hv_stub.Store.current_backend = backend


hv_stub.Store = types.SimpleNamespace(
    registry={},
    current_backend=None,
    renderers={},
    set_current_backend=_set_current_backend,
)


def _extension(*args, **kwargs):  # noqa: D401 – lightweight hv.extension
    backend = args[0] if args else "mock"
    hv_stub.Store.current_backend = backend
    hv_stub.Store.registry.setdefault(backend, {Element: object(), Overlay: object()})
    hv_stub.Store.renderers.setdefault(backend, object())


hv_stub.extension = _extension
hv_stub.Element = Element
hv_stub.Overlay = Overlay

# Additional lightweight element stubs often referenced by result helpers


class _Div(Element):  # noqa: D401 – placeholder hv.Div
    """Lightweight stub mimicking ``holoviews.Div`` constructor signature.

    Accepts arbitrary *args/kwargs so that test-suite calls like
    ``hv.Div(df, height=400)`` do not error.  No real attributes are
    required beyond what the tests inspect (none at the moment).
    """

    def __init__(self, *args, **kwargs):  # noqa: D401 – swallow all params
        # Store raw inputs for potential debugging but ignore otherwise.
        self._args = args
        self._kwargs = kwargs

        # Provide dims so Panel-style access (viz.kdims[0].name) is safe.
        self.kdims = []  # type: ignore[attr-defined]
        self.vdims = []  # type: ignore[attr-defined]

    def __str__(self):  # noqa: D401 – simple representation
        return "DivStub"

    # Minimal .opts proxy to satisfy Panel internals expecting hv objects
    @property  # noqa: D401 – simple accessor
    def opts(self):  # type: ignore[override]
        class _Proxy:
            def get(self, *_a, **_kw):
                class _Res:
                    kwargs: dict = {}

                return _Res()

        return _Proxy()


class _Scatter(Element):  # noqa: D401 – placeholder hv.Scatter
    """Lightweight stub for ``holoviews.Scatter``.

    Tests instantiate via ``hv.Scatter(df)``.  Accept *args/kwargs and set
    minimal dimension metadata expected by downstream helpers.
    """

    def __init__(self, data=None, *args, **kwargs):  # noqa: D401
        self.data = data
        self._args = args
        self._kwargs = kwargs

        # Basic kdims/vdims so attributes exist when accessed.
        self.kdims = [kwargs.get("x", "x")]  # type: ignore[attr-defined]
        self.vdims = [kwargs.get("y", "y")]  # type: ignore[attr-defined]

    def __str__(self):  # noqa: D401 – helpful debug string
        return "ScatterStub"

    # Provide minimal .opts proxy similar to _Div
    @property  # noqa: D401 – simple accessor
    def opts(self):  # type: ignore[override]
        class _Proxy:
            def get(self, *_a, **_kw):
                class _Res:
                    kwargs: dict = {}

                return _Res()

        return _Proxy()


hv_stub.Div = _Div
hv_stub.Scatter = _Scatter

# Additional element class names referenced in advanced correlation tests
hv_stub.Bars = Element
hv_stub.HLine = Element
hv_stub.Curve = Element

# Provide holoviews.core.dimension.Dimensioned import path
hv_core = types.ModuleType("holoviews.core")
hv_core_dimension = types.ModuleType("holoviews.core.dimension")


class _Dimensioned:  # noqa: D401 – placeholder
    pass


hv_core_dimension.Dimensioned = _Dimensioned
hv_core.dimension = hv_core_dimension
hv_stub.core = hv_core

# Register nested modules
sys.modules.setdefault("holoviews", hv_stub)
sys.modules.setdefault("holoviews.core", hv_core)
sys.modules.setdefault("holoviews.core.dimension", hv_core_dimension)

# Lightweight hvplot stub with .pandas submodule so "import hvplot.pandas" works
hvplot_stub = types.ModuleType("hvplot")
hvplot_pandas = types.ModuleType("hvplot.pandas")
setattr(hvplot_stub, "pandas", hvplot_pandas)
sys.modules.setdefault("hvplot", hvplot_stub)
sys.modules.setdefault("hvplot.pandas", hvplot_pandas)

# Ensure project root is on sys.path so pytest can find project modules
# Go up two levels from tests/conftest.py
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force offline mode for ai_helper by removing OPENAI_API_KEY before modules import
os.environ.pop("OPENAI_API_KEY", None)

# You can add shared fixtures here later if needed

os.environ.setdefault("OPENAI_API_KEY", "dummy-test-key")

try:
    from app import ai_helper as _ai_helper

    _ai_helper._OFFLINE_MODE = False  # type: ignore[attr-defined]
except Exception:
    # If ai_helper not yet imported, set flag via importlib when it's loaded
    import builtins

    _orig_import = builtins.__import__

    def _patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        mod = _orig_import(name, globals, locals, fromlist, level)
        if name == "app.ai_helper":
            try:
                mod._OFFLINE_MODE = False  # type: ignore[attr-defined]
            except Exception:
                pass
        return mod

    builtins.__import__ = _patched_import

# Provide holoviews.element submodule and plotting stubs expected by Panel
hv_element_mod = types.ModuleType("holoviews.element")
hv_element_mod.Element = Element
sys.modules.setdefault("holoviews.element", hv_element_mod)

hv_plotting_mod = types.ModuleType("holoviews.plotting")
hv_plotting_bokeh_mod = types.ModuleType("holoviews.plotting.bokeh")
sys.modules.setdefault("holoviews.plotting", hv_plotting_mod)
sys.modules.setdefault("holoviews.plotting.bokeh", hv_plotting_bokeh_mod)

# Some tests import submodules like ``holoviews.plotting.plot`` which don't
# exist in the lightweight stub; register empty stand-ins so the import system
# succeeds without pulling the real plotting stack.
hv_plotting_plot_mod = types.ModuleType("holoviews.plotting.plot")

# Provide a minimal ``Plot`` base-class so ``from holoviews.plotting.plot import Plot`` succeeds.


class _HVPlotBase:  # noqa: D401 – trivial placeholder for hv Plot
    pass


setattr(hv_plotting_plot_mod, "Plot", _HVPlotBase)

sys.modules.setdefault("holoviews.plotting.plot", hv_plotting_plot_mod)

# ------ hvplot accessor -------------------------------------------------
# Provide a dummy .hvplot accessor on DataFrame/Series that returns callables


class _HVPlotAccessor:  # noqa: D401 – minimal stub
    def __getattr__(self, _name):
        class _MockPlot(Element):  # noqa: D401 – inherit Element so isinstance passes
            """Dynamic lightweight plot class returned by hvplot accessor."""

            def __init__(self, *args, **kwargs):  # noqa: D401 – swallow params
                self._args = args
                self._kwargs = kwargs
                # Provide generic dims to satisfy attribute checks.
                self.kdims = []  # type: ignore[attr-defined]
                self.vdims = []  # type: ignore[attr-defined]

            # ``__str__`` helps tests searching for target_field tokens
            def __str__(self):  # noqa: D401 – simple label
                return f"MockPlot({_name})"

            # Minimal .opts proxy similar to other stubs
            @property  # noqa: D401 – simple accessor
            def opts(self):  # type: ignore[override]
                class _Proxy:
                    def get(self, *_a, **_kw):
                        class _Res:
                            kwargs: dict = {}

                        return _Res()

                return _Proxy()

        # Tests usually expect class name ending with 'bars', 'scatter', etc.
        suffix = "s" if not _name.lower().endswith("s") else ""
        _MockPlot.__name__ = _name.capitalize() + suffix

        def _dummy(*_a, **_kw):  # noqa: ANN001 – no-op plot method
            return _MockPlot()

        return _dummy


_pd.DataFrame.hvplot = property(
    lambda _self: _HVPlotAccessor()
)  # type: ignore[attr-defined]
# type: ignore[attr-defined]
_pd.Series.hvplot = property(lambda _self: _HVPlotAccessor())

# ------------------------------------------------------------------
# Patch Panel's HoloViews pane so it accepts lightweight stubs without
# relying on HoloViews internals.  Import **after** inserting hv stubs so
# Panel itself doesn't attempt heavy imports during initialization.
# ------------------------------------------------------------------
try:
    import panel as _pn

    class _StubHoloViewsPane(_pn.pane.Markdown):  # type: ignore[misc]
        """Fallback pane that just renders string representation of object."""

        _source_transforms = {}

        def __init__(self, obj=None, **kwargs):  # noqa: D401 – minimal ctor
            text = str(obj) if obj is not None else "[HoloViews]"
            super().__init__(text, **kwargs)

        # Panel expects ``object`` attribute for updating; keep simple text
        @property
        def object(self):  # type: ignore[override]
            return self._object

        @object.setter
        def object(self, value):  # type: ignore[override]
            self._object = str(value)

    _pn.pane.HoloViews = _StubHoloViewsPane  # type: ignore[attr-defined]

    # Ensure import via 'panel.pane.holoviews' also returns stub class
    import types as _types
    import sys as _sys

    _hv_pane_mod = _types.ModuleType("panel.pane.holoviews")
    setattr(_hv_pane_mod, "HoloViews", _StubHoloViewsPane)
    _sys.modules.setdefault("panel.pane.holoviews", _hv_pane_mod)

    # Re-register PaneBase type mapping if present
    try:
        from panel.pane.base import PaneBase as _PaneBase  # type: ignore

        # Remove existing HoloViews mapping and add stub
        _PaneBase._pane_type = {
            k: v for k, v in _PaneBase._pane_type.items() if k.__name__ != "HoloViews"
        }
        _PaneBase._pane_type[_StubHoloViewsPane] = lambda obj: True
    except Exception:
        pass

    # Override factory to always use Markdown fallback in tests
    def _panel_factory(obj, *args, **kwargs):  # noqa: D401
        return _pn.pane.Markdown(str(obj), *args, **kwargs)

    _pn.panel = _panel_factory  # type: ignore[assignment]
except Exception:
    pass
