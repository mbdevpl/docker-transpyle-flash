"""Operate on HPCtoolkit XML database files as pandas DataFrames."""

from cmath import sqrt  # used in formulas for metrics
import logging
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


def _derive_metrics_formulas(
        metrics: ET.Element) -> t.Dict[str, t.Tuple[str, t.Callable[[pd.DataFrame, dict], t.Any]]]:
    metrics_formulas = {}
    for metric in metrics:
        formulas = metric.findall('./MetricFormula')
        for formula in formulas:
            if formula.attrib['t'] != 'finalize':
                continue
            raw_formula = formula.attrib['frm']
            formula_code = re.sub('\$[0-9]+', _metrics_formula_sub_predicate, raw_formula)
            compiled_formula = eval('lambda self, data: {}'.format(formula_code), None, None)
            metrics_formulas[metric.attrib['n']] = (formula_code, compiled_formula)
            break
    return metrics_formulas


def _location_filter(series: pd.Series, fragments: t.Sequence[tuple],
                     prefix: tuple, suffix: tuple) -> bool:
    location = series.at['location']
    for fragment in fragments:
        if fragment:
            raise NotImplementedError('filtering by arbitrary fragment not supported')
    if prefix:
        if len(location) < len(prefix):
            return False
        for location_item, prefix_item in zip(location[:len(prefix)], prefix):
            if not (prefix_item.fullmatch(location_item) if isinstance(prefix_item, t.Pattern)
                    else prefix_item == location_item):
                return False
    if suffix:
        if len(location) < len(suffix):
            return False
        for location_item, suffix_item in zip(location[-len(suffix):], suffix):
            if not (suffix_item.fullmatch(location_item) if isinstance(suffix_item, t.Pattern)
                    else suffix_item == location_item):
                return False
    return True


def _depth_filter(
        series: pd.Series, min_depth: t.Optional[int], max_depth: t.Optional[int]) -> bool:
    depth = len(series.at['location'])
    if min_depth is not None and depth < min_depth or max_depth is not None and depth > max_depth:
        return False
    return True


class HPCtoolkitDataFrame(pd.DataFrame):

    """Extension of pandas DataFrame tailored to HPCtoolkit"""

    _metadata = ['_metrics_by_id', '_metrics_formulas', '_procedures_by_id', '_max_depth']

    _skip_callsite = True
    """Skip over callsite nodes to avoid over-complicating the calltree."""

    @property
    def _constructor(self):
        return HPCtoolkitDataFrame

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

        rows = self._add_measurements(measurements)
        super().__init__(data=rows, index=[str(_['location']) for _ in rows], columns=columns)
        self._fix_root_measurement()
        self._add_percentage_columns()

    def _evaluate_measurements_data(self, data: dict) -> dict:
        processed_data = {}
        for column, entry in data.items():
            if column not in self._metrics_formulas:
                processed_data[column] = entry
                continue
            formula_code, formula = self._metrics_formulas[column]
            try:
                processed_data[column] = formula(self, data)
            except ValueError as error:
                raise ValueError(
                    'error while evaluating """{}""" to compute "{}" in row {}'
                    .format(formula_code, column, data)) from error
        return processed_data

    def _add_measurements(self, measurements: ET.Element, location: tuple = (), *,
                          depth: int = 0, add_local: bool = True) -> t.List[pd.Series]:
        rows = []

        # split measurements into M and non-M items
        local_measurements = {}
        nonlocal_measurements = []
        for measurement in measurements:
            if measurement.tag == 'M':
                local_measurements[self._metrics_by_id[int(measurement.attrib['n'])]] = \
                    float(measurement.attrib['v'])
            else:
                nonlocal_measurements.append(measurement)

        if add_local:
            local_measurements['location'] = location
            local_measurements = self._evaluate_measurements_data(local_measurements)
            rows.append(local_measurements)

        if self._max_depth is not None and depth >= self._max_depth:
            return rows

        for measurement in nonlocal_measurements:
            add_local = True
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
            base_columns = (
                ('CPUTIME (usec):Mean (I)', 'total'), ('CPUTIME (usec):Mean (I)', 'parent'))
        for base_column, method in base_columns:
            self._add_percentage_column(
                base_column, '{} ratio of {}'.format(base_column, method), method)

    def _add_percentage_column(self, base_column: str, column_name: str, method: str) -> None:
        assert base_column in self.columns, base_column
        column_index = self.columns.get_loc(base_column) + 1
        simple_self = self[[base_column, 'location']]
        if method == 'total':
            filtered = simple_self.loc[['()']]
            total = filtered[base_column].item()
            data = [row.at[base_column] / total for _, row in simple_self.iterrows()]
        else:
            assert method == 'parent'
            data = []
            _cache = {}
            for _, row in simple_self.iterrows():
                value = row.at[base_column]
                base_location = row.at['location']
                base = None
                while base is None or base < value:
                    base_location = base_location[:-1]
                    if base_location in _cache:
                        base = _cache[base_location]
                        break
                    try:
                        filtered = simple_self.loc[[str(base_location)]]
                    except KeyError:
                        _LOG.exception('no measurements for location %s', base_location)
                        continue
                    assert len(filtered) == 1, \
                        (base_column, row.at['location'], base_location, filtered)
                    base = filtered[base_column].item()
                    _cache[base_location] = base
                data.append(value / base)
            del _cache
        self.insert(column_index, column_name, data)

    @property
    def compact(self):
        compact_columns = [
            'CPUTIME (usec):Mean (I)',
            'CPUTIME (usec):Mean (I) ratio of total', 'CPUTIME (usec):Mean (I) ratio of parent']
        return self[compact_columns]

    def select_basic(self, category: str) -> pd.DataFrame:
        selected_columns = [
            r'CPUTIME (usec):Mean ({})',
            r'CPUTIME (usec):Mean ({}) ratio of total', r'CPUTIME (usec):Mean ({}) ratio of parent',
            r'CPUTIME (usec):Min ({})', r'CPUTIME (usec):Max ({})', r'CPUTIME (usec):StdDev ({})']
        selected_columns = [_.format(category) for _ in selected_columns]
        return self[selected_columns]

    @property
    def basic_i(self):
        return self.select_basic('I')

    @property
    def basic_e(self):
        return self.select_basic('E')

    def at_paths(self, *fragments, prefix: tuple = (), suffix: tuple = ()) -> pd.DataFrame:
        mask = self.apply(_location_filter, axis=1, args=(fragments, prefix, suffix))
        return self[mask]

    def at_depths(self, min_depth: t.Optional[int] = None,
                  max_depth: t.Optional[int] = None) -> pd.DataFrame:
        mask = self.apply(_depth_filter, axis=1, args=(min_depth, max_depth))
        return self[mask]

    def at_depth(self, depth: int) -> pd.DataFrame:
        return self.at_depths(depth, depth)

    def hot_path(self, location: tuple = (), threshold: int = 0.05) -> pd.DataFrame:
        base_column = 'CPUTIME (usec):Mean (I) ratio of total'
        simple_self = self[[base_column, 'location']]
        hot_locations = []

        while True:
            hot_locations.append(location)

            simple_self = simple_self.at_paths(prefix=location)
            _LOG.debug('%i at target location', len(simple_self))
            at_depth = simple_self.at_depth(len(location) + 1)
            _LOG.debug('%i at depth %i', len(at_depth), len(location) + 1)

            if at_depth.empty:
                break

            hottest_index = at_depth[base_column].idxmax()
            hottest_row = simple_self.loc[hottest_index]
            location = hottest_row.at['location']
            if hottest_row.at[base_column] < threshold:
                break

        return self[self.location.isin(hot_locations)]


# HPCtoolkitDataFrame(path=pathlib.Path(
#    '/nfs2/mbysiek/Projects/docker-transpyle-flash/results/'
#    'profile_20180905-120519_subset_Sedov_base_a_db/experiment.xml')).hot_path()[-2:].compact
