
import logging
import pathlib
import subprocess
import typing as t

_NOW = None

_LOG = logging.getLogger(__name__)

_HERE = pathlib.Path(__file__).parent.resolve()

_RESULTS_ROOT = pathlib.Path(_HERE, 'results')


# warsaw.m.gsic.titech.ac.jp:
# CROSS_F77_SIZEOF_INTEGER=4 spack install mpich
# spack install hdf5 +cxx +fortran +hl +szip +threadsafe
# spack install hypre ^openblas threads=openmp
# spack install amrex@develop +amrdata dimensions=3 +fortran +particles ^cmake +ownlibs

# mbLab:
#
#
#

ENVIRONMENT = {
    'warsaw.m.gsic.titech.ac.jp': {
        '2d': 'spack load mpich@3.3 && spack load hdf5@1.10.5 && spack load openblas@0.3.5 threads=openmp && spack load hypre@2.15.1 && spack load amrex@develop dimensions=2',
        '3d': 'spack load mpich@3.3 && spack load hdf5@1.10.5 && spack load openblas@0.3.5 threads=openmp && spack load hypre@2.15.1 && spack load amrex@develop dimensions=3'
    },
    'mbLab': {
        '2d': '',
        '3d': ''
    }
}

HPCRUN_EXE = 'hpcrun'  # shutil.which('hpcrun')
HPCSTRUCT_EXE = 'hpcstruct'  # shutil.which('hpcstruct')
HPCPROF_EXE = 'hpcprof'  # shutil.which('hpcprof')

FLASH_SITE = 'spack'


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


def _run_and_check(cmd: t.Union[str, t.List[str]], wd: pathlib.Path, *,
                   test_name: str, phase_name: str):
    cmd = cmd if isinstance(cmd, str) else ' '.join(cmd)

    _LOG.warning('%s.%s: running "%s" with wd="%s"', test_name, phase_name, cmd, wd)
    cmd_result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                shell=True, cwd=str(wd))
    cmd_msg = None
    if cmd_result.returncode != 0:
        log_dir = pathlib.Path(logs_path(test_name=test_name))
        log_dir.mkdir(parents=True, exist_ok=True)
        cmd_stdout = cmd_result.stdout.decode()
        with pathlib.Path(log_dir, '{}_stdout.log'.format(phase_name)).open('w') as cmd_stdout_file:
            cmd_stdout_file.write(cmd_stdout)
        cmd_stderr = cmd_result.stderr.decode()
        with pathlib.Path(log_dir, '{}_stderr.log'.format(phase_name)).open('w') as cmd_stderr_file:
            cmd_stderr_file.write(cmd_stderr)
        cmd_msg = '"{}" failed, returncode={}, logs were written to "{}"' \
            ' and last 50 lines of stderr follow:\n{}'.format(
                cmd, cmd_result.returncode, log_dir,
                ''.join(cmd_stderr.splitlines(keepends=True)[-50:]))
    assert cmd_result.returncode == 0, cmd_msg
