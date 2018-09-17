"""Utility functions to assist profiling FLASH across code versions and problem configurations."""

import datetime
import logging
# import math
import pathlib
import subprocess
import typing as t

import git

_HERE = pathlib.Path(__file__).parent.resolve()

_LOG = logging.getLogger(__name__)

_RESULTS_ROOT = pathlib.Path(_HERE, 'results')

_NOW = None

_JUST_RAN = None


def _run_and_check(cmd: str, wd: pathlib.Path, *,
                   test_name: str, phase_name: str):
    _LOG.warning('%s.%s: running "%s" with wd="%s"', test_name, phase_name, cmd, wd)
    # _dir = os.getcwd()
    # os.chdir(str(wd))
    cmd_result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                shell=True, cwd=str(wd))
    # os.chdir(_dir)
    log_dir = logs_path(test_name=test_name)
    log_dir.mkdir(parents=True, exist_ok=True)
    cmd_stdout = cmd_result.stdout.decode()
    with open(str(pathlib.Path(log_dir, '{}_stdout.log'.format(phase_name))),
              'w') as cmd_stdout_file:
        cmd_stdout_file.write(cmd_stdout)
    cmd_stderr = cmd_result.stderr.decode()
    with open(str(pathlib.Path(log_dir, '{}_stderr.log'.format(phase_name))),
              'w') as cmd_stderr_file:
        cmd_stderr_file.write(cmd_stderr)
    cmd_msg = None
    if cmd_result.returncode != 0:
        cmd_msg = '"{}" failed, returncode={}, logs were written to "{}"' \
            ' and last 50 lines of stderr follow:\n{}'.format(
                cmd, cmd_result.returncode, log_dir,
                ''.join(cmd_stderr.splitlines(keepends=True)[-50:]))
    assert cmd_result.returncode == 0, cmd_msg


def make_sfocu():
    return '''cd $FLASH_BASE/tools/sfocu
    make -f Makefile.hello clean
    make -f Makefile.hello'''


def setup_flash(experiment, setup_dir, *,
                test_name: str, phase_name: str = 'setup'):
    _run_and_check('./setup -site spack ' + experiment, setup_dir,
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
    hpcrun = 'hpcrun'  # shutil.which('hpcrun')
    results_path.parent.mkdir(exist_ok=True)
    events_options = [
        ' -e {}{}'.format(event, '' if rate is True else '@{}'.format(
            rate if isinstance(rate, int) else 'f{}'.format(round(1 / rate))))
        for event, rate in events.items()]
    hpcrun_command = '{}{} -o "{}" {}'.format(
        hpcrun, ''.join(events_options), results_path, executable)
    if mpi_proc > 0:
        hpcrun_command = 'mpirun -np {} {}'.format(mpi_proc, hpcrun_command)
    _LOG.warning('%s.%s: running the experiment %i times...', test_name, phase_name, sample_size)
    for i in range(sample_size):
        _run_and_check(hpcrun_command, executable.parent,
                       test_name=test_name, phase_name=phase_name)


def hpctoolkit_summarize(executable: pathlib.Path, results_path: pathlib.Path,
                         source_path: pathlib.Path, *,
                         test_name: str, phase_name: str = 'summarize'):
    hpcstruct = 'hpcstruct'  # shutil.which('hpcstruct')
    hpcprof = 'hpcprof'  # shutil.which('hpcprof')
    # source_path.joinpath('*')
    struct_path = results_path.joinpath(executable.name + '.hpcstruct')
    hpcstruct_command = '{} --verbose -I {} -o {} {}'.format(
        hpcstruct, './\'*\'', struct_path, executable)
    _run_and_check(hpcstruct_command, source_path,
                   test_name=test_name, phase_name='{}.hpcstruct'.format(phase_name))
    # hpcprof -I "${source}" "${results_path}" \
    #   -S "${results_path}/flash4.hpcstruct" \
    #   -M stats \
    #   -o "${results_path}_db"
    # source_path.joinpath('+')
    hpcprof_command = '{} --verbose -I "{}" {} -S {} -M stats -o {}'.format(
        hpcprof, './+', results_path, struct_path, profile_db_path(test_name=test_name))
    _run_and_check(hpcprof_command, source_path,
                   test_name=test_name, phase_name='{}.hpcprof'.format(phase_name))


def profile_flash(app_name: str, executable: pathlib.Path, source_path: pathlib.Path,
                  sample_size: int, events=None, mpi_proc=0, *,
                  test_name: str):
    results_path = profile_path(test_name=test_name)
    hpctoolkit_profile(executable, results_path, sample_size, events, mpi_proc, test_name=test_name)
    hpctoolkit_summarize(executable, results_path, source_path, test_name=test_name)


def profile_experiment(app_name: str, experiment: str, branch: str, sample_size: int, *,
                       rebuild: bool = None,
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
    build_dir = setup_dir.joinpath('object')
    executable = build_dir.joinpath('flash4')
    if rebuild is not False:
        setup_flash(experiment, setup_dir,
                    test_name=test_name)
        make_flash(build_dir,
                   test_name=test_name)
    profile_flash(app_name, executable, app_dir, sample_size, **kwargs,
                  test_name=test_name)
    clean_flash(build_dir,
                test_name=test_name)
    _JUST_RAN = (datetime.datetime.now(), app_name, experiment, branch)


def date_str(date=None) -> str:
    if date is None:
        date = _NOW
    return date.strftime('%Y%m%d-%H%M%S')


def logs_path(date=None, *, test_name) -> pathlib.Path:
    return _RESULTS_ROOT.joinpath('{}_{}'.format(date_str(date), test_name))


def profile_path(date=None, *, test_name) -> pathlib.Path:
    return _RESULTS_ROOT.joinpath('profile_{}_{}'.format(date_str(date), test_name))


def profile_db_path(date=None, *, test_name) -> pathlib.Path:
    profile_dir = profile_path(date, test_name=test_name)
    return profile_dir.with_name(profile_dir.name + '_db')
