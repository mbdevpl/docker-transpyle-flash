"""Utility functions to assist profiling FLASH across code versions and problem configurations."""

import datetime
import logging
# import math
import pathlib
import typing as t

import git

from common import HPCRUN_EXE, HPCSTRUCT_EXE, HPCPROF_EXE, FLASH_SITE, profile_path, profile_db_path, _run_and_check

_HERE = pathlib.Path(__file__).parent.resolve()

_LOG = logging.getLogger(__name__)

_JUST_RAN = None


def make_sfocu(flash_dir: pathlib.Path):
    sfocu_dir = flash_dir.joinpath('tools', 'sfocu')
    _run_and_check('make -f Makefile.hello clean', sfocu_dir,
                   test_name='sfocu', phase_name='clean')
    _run_and_check('make -f Makefile.hello', sfocu_dir,
                   test_name='sfocu', phase_name='make')


def setup_flash(experiment, objdir: str, setup_dir, *,
                test_name: str, phase_name: str = 'setup'):
    setup_command = './setup -site {} {}'.format(FLASH_SITE, experiment)
    if objdir != 'object':
        setup_command += ' -objdir={}'.format(objdir)
    _run_and_check(setup_command, setup_dir,
                   test_name=test_name, phase_name=phase_name)


def make_flash(build_dir, *,
               test_name: str, phase_name: str = 'make'):
    _run_and_check('make', build_dir,
                   test_name=test_name, phase_name=phase_name)


def clean_flash(build_dir, *,
                test_name: str, phase_name: str = 'clean'):
    _run_and_check('make clean', build_dir,
                   test_name=test_name, phase_name=phase_name)


def hpctoolkit_profile(executable: pathlib.Path, results_path: pathlib.Path, sample_size: int,
                       events: t.Dict[str, t.Union[bool, int]] = None, mpi_proc: int = 0, *,
                       test_name: str, phase_name: str = 'profile'):
    assert isinstance(executable, pathlib.Path), type(executable)
    if events is None:
        events = {}
    results_path.parent.mkdir(exist_ok=True)
    events_options = [
        ' -e {}{}'.format(event, '' if rate is True else '@{}'.format(
            rate if isinstance(rate, int) else 'f{}'.format(round(1 / rate))))
        for event, rate in events.items()]
    hpcrun_command = '{}{} -o "{}" {}'.format(
        HPCRUN_EXE, ''.join(events_options), results_path, executable)
    if mpi_proc > 0:
        hpcrun_command = 'mpirun -np {} {}'.format(mpi_proc, hpcrun_command)
    _LOG.warning('%s.%s: running the experiment %i times...', test_name, phase_name, sample_size)
    for i in range(sample_size):
        _run_and_check(hpcrun_command, executable.parent,
                       test_name=test_name, phase_name=phase_name)


def hpctoolkit_summarize(executable: pathlib.Path, results_path: pathlib.Path,
                         source_path: pathlib.Path, *,
                         test_name: str, phase_name: str = 'summarize'):
    struct_path = results_path.joinpath(executable.name + '.hpcstruct')
    hpcstruct_command = '{} -I "{}" --verbose -o {} {}'.format(
        HPCSTRUCT_EXE, source_path.joinpath('*'), struct_path, executable)
    _run_and_check(hpcstruct_command, source_path,
                   test_name=test_name, phase_name='{}.hpcstruct'.format(phase_name))
    hpcprof_command = '{} -I "{}" --replace-path "{}=." {} -S {} -M stats -o {}'.format(
        HPCPROF_EXE, source_path.joinpath('+'), source_path, results_path, struct_path,
        profile_db_path(test_name=test_name))
    _run_and_check(hpcprof_command, source_path,
                   test_name=test_name, phase_name='{}.hpcprof'.format(phase_name))


def profile_flash(app_name: str, executable: pathlib.Path, source_path: pathlib.Path,
                  sample_size: int, events=None, mpi_proc=0, *,
                  test_name: str):
    results_path = profile_path(test_name=test_name)
    hpctoolkit_profile(executable, results_path, sample_size, events, mpi_proc, test_name=test_name)
    hpctoolkit_summarize(executable, results_path, source_path, test_name=test_name)


def profile_experiment(app_name: str, experiment: str, branch: str, objdir: str,
                       sample_size: int, *,
                       rebuild: bool = None, clean: bool = False,
                       test_name: str, **kwargs):
    global _JUST_RAN
    if rebuild is None and _JUST_RAN \
            and datetime.datetime.now() - _JUST_RAN[0] < datetime.timedelta(seconds=10) \
            and _JUST_RAN[1:] == (app_name, experiment, branch):
        _JUST_RAN = None
        rebuild = False
    app_dir = pathlib.Path(_HERE, app_name)
    setup_dir = {
        'flash-subset': app_dir.joinpath('FLASH4.4')
        }.get(app_name, app_dir)
    repo = git.Repo(str(app_dir))
    assert not repo.is_dirty(untracked_files=True), repo
    if str(repo.active_branch) != branch:
        _LOG.warning('%s: checking out %s', test_name, branch)
        repo.git.checkout(branch)
        rebuild = True
    build_dir = setup_dir.joinpath(objdir)
    executable = build_dir.joinpath('flash4')
    if rebuild is not False:
        setup_flash(experiment, objdir, setup_dir,
                    test_name=test_name)
        make_flash(build_dir,
                   test_name=test_name)
    profile_flash(app_name, executable, app_dir, sample_size, **kwargs,
                  test_name=test_name)
    if clean:
        clean_flash(build_dir,
                    test_name=test_name)
    _JUST_RAN = (datetime.datetime.now(), app_name, experiment, branch)
