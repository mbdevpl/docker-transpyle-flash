"""Operate on HPCtoolkit XML database files as pandas DataFrames."""

import logging
import math
import pathlib
import pprint
import re
import typing as t
import xml.etree.ElementTree as ET

import pandas as pd

_LOG = logging.getLogger(__name__)


def _read_xml(path: pathlib.Path) -> ET.ElementTree:
    with path.open() as xml_file:
        xml_data = ET.parse(xml_file)
    return xml_data


def _metrics_formula_sub_predicate(match: t.Match) -> str:
    return 'data.get(self._metrics_by_id[{}])'.format(match.group()[1:])


def _derive_metrics_formulas(metrics: ET.Element) -> dict:
    metrics_formulas = {}
    for metric in metrics:
        formulas = metric.findall('./MetricFormula')
        for formula in formulas:
            if formula.attrib['t'] != 'finalize':
                continue
            raw_formula = formula.attrib['frm']
            # _LOG.debug('%s', raw_formula)
            metrics_formulas[metric.attrib['n']] = re.sub(
                '\$[0-9]+', _metrics_formula_sub_predicate, raw_formula)
            break
        # else:
        #    metrics_formulas[metric.attrib['n']] = 'data["{}"]'.format(metric.attrib['n'])
    return metrics_formulas


class HPCtoolkitDataFrame(pd.DataFrame):

    """Extension of pandas DataFrame tailored to HPCtoolkit"""

    _metadata = ['_metrics_by_id', '_metrics_formulas', '_procedures_by_id', '_max_depth']

    _skip_callsite = True
    """Skip over callsite nodes to avoid over-complicating the calltree."""

    def __init__(self, *args,
                 path: pathlib.Path = None, max_depth: t.Optional[int] = None, **kwargs):
        if path is None:
            super().__init__(*args, **kwargs)
            return

        profile_data = _read_xml(path).find('./SecCallPathProfile')
        _LOG.info('%s', profile_data.attrib['n'])

        self._max_depth = max_depth

        metrics = profile_data.find('./SecHeader/MetricTable')
        _LOG.debug('%s', [(_, _.attrib) for _ in metrics])
        self._metrics_by_id = {int(_.attrib['i']): _.attrib['n'] for _ in metrics}
        _LOG.info('%s', pprint.pformat(self._metrics_by_id))

        self._metrics_formulas = _derive_metrics_formulas(metrics)
        _LOG.info('%s', pprint.pformat(self._metrics_formulas))

        procedures = profile_data.find('./SecHeader/ProcedureTable')
        _LOG.debug('%s', [(_, _.attrib) for _ in procedures])
        self._procedures_by_id = {int(_.attrib['i']): _.attrib['n'] for _ in procedures}
        _LOG.info('%s', pprint.pformat(self._procedures_by_id))

        measurements = profile_data.find('./SecCallPathProfileData')
        _LOG.debug('%s', [(_, _.attrib) for _ in measurements])

        columns = [metric for _, metric in sorted(self._metrics_by_id.items())]
        columns.append('location')

        # super().__init__(data=None, index=None, columns=columns)

        rows = self._add_measurements(measurements)
        index = [str(_['location']) for _ in rows]
        data = rows
        super().__init__(data=data, index=index, columns=columns)
        self._fix_root_measurement()
        self._add_percentage_columns()

    def _evaluate_measurements_data(self, data: dict) -> dict:
        globals_ = None
        locals_ = {'data': data, 'pow': pow, 'sqrt': math.sqrt, 'self': self}
        assert 'data' in locals_
        processed_data = {column: eval(self._metrics_formulas[column], globals_, locals_)
                          if column in self._metrics_formulas else entry
                          for column, entry in data.items()}
        return processed_data

    def _add_measurements(self, measurements: ET.Element, location: tuple = (), *,
                          depth: int = 0, add_local: bool = True) -> t.List[pd.Series]:
        rows = []
        if add_local:
            data = {self._metrics_by_id[int(metric.attrib['n'])]: float(metric.attrib['v'])
                    for metric in measurements if metric.tag == 'M'}
            data['location'] = location
            data = self._evaluate_measurements_data(data)
            # series = pd.Series(data=data, name=location)
            # self.loc[str(location)] = series
            rows.append(data)

        if self._max_depth is not None and depth >= self._max_depth:
            return rows

        add_local = True
        for measurement in measurements:
            if measurement.tag == 'M':  # metric data
                continue
            if measurement.tag == 'PF':  # procedure frame
                _ = '{}.{}'.format(self._procedures_by_id[int(measurement.attrib['n'])],
                                   measurement.attrib['i'])
                new_location = (*location, _)
            elif measurement.tag == 'C':
                if self._skip_callsite:
                    new_location = location
                    add_local = False
                    depth -= 1
                else:
                    _ = '<callsite {}.{}>'.format(measurement.attrib['s'], measurement.attrib['i'])
                    new_location = (*location, _)
            elif measurement.tag == 'S':
                _ = '<statement {}>'.format(measurement.attrib['s'])
                new_location = (*location, _)
            elif measurement.tag == 'L':
                _ = '<loop {}.{}>'.format(measurement.attrib['s'], measurement.attrib['i'])
                new_location = (*location, _)
            else:
                raise NotImplementedError(
                    (measurement.tag, measurement.attrib, [_ for _ in measurement]))
            rows += self._add_measurements(measurement, new_location,
                                           depth=depth + 1, add_local=add_local)

        return rows

    def _fix_root_measurement(self):
        selected_columns = [
            r'CPUTIME (usec):Sum ({})', r'CPUTIME (usec):Mean ({})',
            r'CPUTIME (usec):Min ({})', r'CPUTIME (usec):Max ({})', r'CPUTIME (usec):StdDev ({})']
        for column in selected_columns:
            self.at['()', column.format('E')] = self.at['()', column.format('I')]

    def _add_percentage_columns(self, base_columns: t.Dict[str, str] = None) -> None:
        if base_columns is None:
            base_columns = {
                'CPUTIME (usec):Mean (I)': 'parent',
                'CPUTIME (usec):Mean (E)': 'total'}
        for base_column, method in base_columns.items():
            self._add_percentage_column(base_column, '{} %'.format(base_column), method)

    def _add_percentage_column(self, base_column: str, column_name: str, method: str) -> None:
        assert base_column in self.columns, base_column
        column_index = self.columns.get_loc(base_column) + 1
        simple_self = self[[base_column, 'location']]
        if method == 'total':
            total = simple_self[simple_self['location'] == ()][base_column].item()
            data = [row[base_column] / total for _, row in simple_self.iterrows()]
        else:
            assert method == 'parent'
            data = []
            for _, row in simple_self.iterrows():
                value = row[base_column]
                base_location = row['location']
                base = 0.0
                while base < value:
                    base_location = base_location[:-1]
                    filtered = simple_self[simple_self['location'] == base_location]
                    if len(filtered) == 0:
                        continue
                    assert len(filtered) == 1, \
                        (base_column, row['location'], base_location, filtered)
                    base = filtered[base_column].item()
                data.append(value / base)
        self.insert(column_index, column_name, data)

    @property
    def compact(self):
        compact_columns = [
            'CPUTIME (usec):Mean (I)', 'CPUTIME (usec):Mean (I) %',
            'CPUTIME (usec):Mean (E)', 'CPUTIME (usec):Mean (E) %']
        return self[compact_columns]

    def select_basic(self, category: str) -> pd.DataFrame:
        selected_columns = [
            r'CPUTIME (usec):Sum ({})', r'CPUTIME (usec):Mean ({})', r'CPUTIME (usec):Mean ({}) %',
            r'CPUTIME (usec):Min ({})', r'CPUTIME (usec):Max ({})', r'CPUTIME (usec):StdDev ({})']
        selected_columns = [_.format(category) for _ in selected_columns]
        return self[selected_columns]

    @property
    def basic_i(self):
        return self.select_basic('I')

    @property
    def basic_e(self):
        return self.select_basic('E')

    def at_path(self, location_prefix: tuple):

        def location_prefix_filter(series: pd.Series, location_prefix: tuple):
            series_location = series['location']
            if len(series_location) < len(location_prefix) \
                    or series_location[:len(location_prefix)] != location_prefix:
                return False
            return True

        mask = self.apply(location_prefix_filter, axis=1, args=(location_prefix,))
        return self[mask]

    def hot_path(self, location: tuple = (), threshold: int = 0.1):
        base_column = 'CPUTIME (usec):Mean (I) %'
        simple_self = self[[base_column, 'location']]

        def location_prefix_filter(series: pd.Series, location_prefix: tuple):
            series_location = series['location']
            if len(series_location) < len(location_prefix) \
                    or series_location[:len(location_prefix)] != location_prefix:
                return False
            return True

        def depth_filter(series: pd.Series, depth: int):
            if len(series['location']) != depth:
                return False
            return True

        hot_locations = []

        while True:
            hot_locations.append(location)
            mask = simple_self.apply(location_prefix_filter, axis=1, args=(location,))
            simple_self = simple_self[mask]
            depth_mask = simple_self.apply(depth_filter, axis=1, args=(len(location) + 1,))
            at_depth = simple_self[depth_mask]
            hottest_index = at_depth[base_column].idxmax()
            hottest_row = simple_self.loc[hottest_index]
            location = hottest_row['location']
            if hottest_row[base_column] < threshold:
                break

        return self[self.location.isin(hot_locations)]
