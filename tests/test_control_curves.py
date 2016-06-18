from pywr.core import Model, Storage, Link, ScenarioIndex
from pywr.parameters import ConstantParameter, load_parameter
from pywr.parameters.control_curves import ControlCurveParameter, ControlCurveInterpolatedParameter
import numpy as np
from numpy.testing import assert_allclose
import pytest


@pytest.fixture
def model(solver):
    return Model(solver=solver)


class TestPiecewiseControlCurveParameter:
    """Tests for ControlCurveParameter """

    @staticmethod
    def _assert_results(m, s):
        """ Correct results for the following tests """
        s.setup(m)  # Init memory view on storage (bypasses usual `Model.setup`)

        si = ScenarioIndex(0, np.array([0], dtype=np.int32))
        s.initial_volume = 90.0
        m.reset()
        assert_allclose(s.get_cost(m.timestepper.current, si), 1.0)

        s.initial_volume = 70.0
        m.reset()
        assert_allclose(s.get_cost(m.timestepper.current, si), 0.7)

        s.initial_volume = 40.0
        m.reset()
        assert_allclose(s.get_cost(m.timestepper.current, si), 0.4)

    def test_with_values(self, model):
        """Test with `values` keyword argument"""
        m = model
        s = Storage(m, 'Storage', max_volume=100.0)

        # Return 10.0 when above 0.0 when below
        s.cost = ControlCurveParameter([0.8, 0.6], [1.0, 0.7, 0.4])
        self._assert_results(m, s)

    def test_with_parameters(self, model):
        """ Test with `parameters` keyword argument. """
        m = model

        s = Storage(m, 'Storage', max_volume=100.0)

        # Two different control curves
        cc = [ConstantParameter(0.8), ConstantParameter(0.6)]
        # Three different parameters to return
        params = [
            ConstantParameter(1.0), ConstantParameter(0.7), ConstantParameter(0.4)
        ]
        s.cost = ControlCurveParameter(cc, parameters=params)

        self._assert_results(m, s)

    def test_values_load(self, model):
        """ Test load of float lists. """

        m = model
        s = Storage(m, 'Storage', max_volume=100.0)

        data = {
            "type": "controlcurve",
            "control_curves": [0.8, 0.6],
            "values": [1.0, 0.7, 0.4]
        }

        s.cost = p = load_parameter(model, data)
        assert isinstance(p, ControlCurveParameter)
        self._assert_results(m, s)

    def test_parameters_load(self, model):
        """ Test load of parameter lists for 'control_curves' and 'parameters' keys. """

        m = model
        s = Storage(m, 'Storage', max_volume=100.0)

        data = {
            "type": "controlcurve",
            "control_curves": [
                {
                    "type": "constant",
                    "values": 0.8
                },
                {
                    "type": "monthlyprofile",
                    "values": [0.6]*12
                }
            ],
            "parameters": [
                {
                    "type": "constant",
                    "values": 1.0,
                },
                {
                    "type": "constant",
                    "values": 0.7
                },
                {
                    "type": "constant",
                    "values": 0.4
                }
            ]
        }

        s.cost = p = load_parameter(model, data)
        assert isinstance(p, ControlCurveParameter)
        self._assert_results(m, s)

    def test_single_cc_load(self, model):
        """ Test load from dict with 'control_curve' key

        This is different to the above test by using singular 'control_curve' key in the dict
        """

        m = model
        s = Storage(m, 'Storage', max_volume=100.0)

        data = {
            "type": "controlcurve",
            "control_curve": 0.8,
        }

        s.cost = p = load_parameter(model, data)
        assert isinstance(p, ControlCurveParameter)

        s.setup(m)  # Init memory view on storage (bypasses usual `Model.setup`)

        si = ScenarioIndex(0, np.array([0], dtype=np.int32))
        s.initial_volume = 90.0
        m.reset()
        assert_allclose(s.get_cost(m.timestepper.current, si), 0)

        s.initial_volume = 70.0
        m.reset()
        assert_allclose(s.get_cost(m.timestepper.current, si), 1)

    def test_with_nonstorage(self, model):
        """ Test usage on non-`Storage` node. """
        # Now test if the parameter is used on a non storage node
        m = model
        s = Storage(m, 'Storage', max_volume=100.0)

        l = Link(m, 'Link')
        cc = ConstantParameter(0.8)
        l.cost = ControlCurveParameter(cc, [10.0, 0.0], storage_node=s)

        s.setup(m)  # Init memory view on storage (bypasses usual `Model.setup`)
        si = ScenarioIndex(0, np.array([0], dtype=np.int32))
        assert_allclose(l.get_cost(m.timestepper.current, si), 0.0)
        # When storage volume changes, the cost of the link changes.
        s.initial_volume = 90.0
        m.reset()
        assert_allclose(l.get_cost(m.timestepper.current, si), 10.0)

    def test_with_nonstorage_load(self, model):
        """ Test load from dict with 'storage_node' key. """
        m = model
        s = Storage(m, 'Storage', max_volume=100.0)
        l = Link(m, 'Link')

        data = {
            "type": "controlcurve",
            "control_curve": 0.8,
            "values": [10.0, 0.0],
            "storage_node": "Storage"
        }

        l.cost = p = load_parameter(model, data)
        assert isinstance(p, ControlCurveParameter)

        s.setup(m)  # Init memory view on storage (bypasses usual `Model.setup`)
        si = ScenarioIndex(0, np.array([0], dtype=np.int32))
        assert_allclose(l.get_cost(m.timestepper.current, si), 0.0)
        # When storage volume changes, the cost of the link changes.
        s.initial_volume = 90.0
        m.reset()
        assert_allclose(l.get_cost(m.timestepper.current, si), 10.0)


def test_control_curve_interpolated(model):
    m = model
    si = ScenarioIndex(0, np.array([0], dtype=np.int32))

    s = Storage(m, 'Storage', max_volume=100.0)

    cc = ConstantParameter(0.8)
    values = [20.0, 5.0, 0.0]
    s.cost = ControlCurveInterpolatedParameter(cc, values)
    s.setup(m)

    for v in (0.0, 10.0, 50.0, 80.0, 90.0, 100.0):
        s.initial_volume = v
        s.reset()
        assert_allclose(s.get_cost(m.timestepper.current, si), np.interp(v/100.0, [0.0, 0.8, 1.0], values[::-1]))

    # special case when control curve is 100%
    cc._value = 1.0
    s.initial_volume == 100.0
    s.reset()
    assert_allclose(s.get_cost(m.timestepper.current, si), values[1])

    # special case when control curve is 0%
    cc._value = 0.0
    s.initial_volume == 0.0
    s.reset()
    assert_allclose(s.get_cost(m.timestepper.current, si), values[0])