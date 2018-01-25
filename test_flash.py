"""Tests of FLASH transpilation."""

import logging
import pathlib
import subprocess
import unittest

import git
from transpyle.general import CodeReader, CodeWriter
from transpyle.fortran import FortranParser, FortranAstGeneralizer, Fortran2008Unparser

logging.basicConfig()

_LOG = logging.getLogger(__name__)

_HERE = pathlib.Path(__file__).parent.resolve()


def fortran_to_fortran(path: pathlib.Path):
    """Transpile Fortran to Fortran, using Python AST as intermediate (generalized) format.

    Reader reads the code.
    Parser creates a Fortran-specific AST.
    Generalizer transforms it into AST that can be easily processed and unparsed into many outputs.
    Unparsers creates Fortran code from the same generalized AST.
    Original file is moved from "name.ext" to "name.ext.bak", unless the backup already exists.
    Writer writes the transpiled file to where the original file was.
    """
    reader = CodeReader()
    parser = FortranParser()
    generalizer = FortranAstGeneralizer()
    unparser = Fortran2008Unparser()
    writer = CodeWriter(path.suffix)

    code = reader.read_file(path)
    fortran_ast = parser.parse(code, path)
    tree = generalizer.generalize(fortran_ast)
    fortran_code = unparser.unparse(tree)

    backup_path = path.with_suffix(path.suffix + '.bak')
    if not backup_path.is_file():
        pathlib.Path.rename(path, backup_path)
    writer.write_file(fortran_code, path)


class FlashTests(unittest.TestCase):

    root_path = None
    source_path = pathlib.Path('source')
    setup_cmd = ['./setup']
    object_path = pathlib.Path('object')
    make_cmd = ['make']
    run_cmd = ['mpirun', '-np', '2', 'flash4']

    def setUp(self):
        if type(self) is FlashTests:
            self.skipTest('...')
        repo = git.Repo(str(pathlib.Path(_HERE, self.root_path)), search_parent_directories=True)
        repo_path = pathlib.Path(repo.working_dir)
        self.assertIn(str(_HERE), str(repo_path), msg=(repo_path, _HERE, repo))
        self.assertNotEqual(repo_path, _HERE, msg=(repo_path, _HERE, repo))
        repo_is_dirty = repo.is_dirty(untracked_files=True)
        if repo_is_dirty:
            repo.git.clean(f=True, d=True, x=True)
            repo.git.reset(hard=True)
            _LOG.warning('Repository %s has been cleaned and reset.', repo)

    def run_transpyle(self, transpiled_paths):
        absolute_transpiled_paths = [pathlib.Path(_HERE, self.root_path, self.source_path, path)
                                     for path in transpiled_paths]
        all_failed = True
        for path in absolute_transpiled_paths:
            self.assertTrue(path.is_file())
            with self.subTest(path=path):
                fortran_to_fortran(path)
                all_failed = False
        if all_failed:
            self.fail(msg='Failed to transpile any of the files {}.'
                      .format(absolute_transpiled_paths))

    def _run_and_check(self, cmd, wd, log_filename_prefix):
        cmd_result = subprocess.run(' '.join(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    shell=True, cwd=str(wd))
        cmd_msg = None
        if cmd_result.returncode != 0:
            log_dir = pathlib.Path(_HERE, self.id())
            log_dir.mkdir(parents=True, exist_ok=True)
            cmd_stdout = cmd_result.stdout.decode()
            with open(str(pathlib.Path(log_dir, '{}_stdout.log'.format(log_filename_prefix))),
                      'w') as cmd_stdout_file:
                cmd_stdout_file.write(cmd_stdout)
            cmd_stderr = cmd_result.stderr.decode()
            with open(str(pathlib.Path(log_dir, '{}_stderr.log'.format(log_filename_prefix))),
                      'w') as cmd_stderr_file:
                cmd_stderr_file.write(cmd_stderr)
            cmd_msg = '"{}" failed, returncode={}, logs were written to "{}"' \
                ' and last 50 lines of stderr follow:\n{}'.format(
                    ' '.join(cmd), cmd_result.returncode, log_dir,
                    ''.join(cmd_stderr.splitlines(keepends=True)[-50:]))
        self.assertEqual(cmd_result.returncode, 0, msg=cmd_msg)

    def run_flash(self, flash_args):
        absolute_flash_path = pathlib.Path(_HERE, self.root_path)
        absolute_object_path = pathlib.Path(_HERE, self.root_path, self.object_path)
        if isinstance(flash_args, str):
            flash_args = flash_args.split(' ')
        flash_setup_cmd = self.setup_cmd + flash_args
        # flash_setup_cmd[0] = str(pathlib.Path(_HERE, self.root_path, flash_setup_cmd[0]))
        flash_make_cmd = self.make_cmd
        flash_run_cmd = self.run_cmd

        something_wrong = True
        with self.subTest(flash_path=absolute_flash_path, setup_cmd=flash_setup_cmd,
                          make_cmd=flash_make_cmd, run_cmd=flash_run_cmd):
            _LOG.warning('Setting up FLASH...')
            self._run_and_check(flash_setup_cmd, absolute_flash_path, 'setup')
            _LOG.warning('Setup succeeded.')

            _LOG.warning('Building FLASH...')
            self._run_and_check(flash_make_cmd, absolute_object_path, 'make')
            _LOG.warning('Build succeeded.')

            run_result = subprocess.run(' '.join(flash_run_cmd), shell=True,
                                        cwd=str(absolute_object_path))
            self.assertEqual(run_result.returncode, 0, msg=run_result)
            something_wrong = False
        if something_wrong:
            self.fail('FLASH setup, build, or run failed.')

    def run_problem(self, transpiled_paths, flash_args, pre_verify=False):
        if pre_verify:
            self.run_flash(flash_args)
        self.run_transpyle(transpiled_paths)
        self.run_flash(flash_args)

    def run_sod_problem(self, transpiled_paths, **kwargs):
        args = 'Sod -auto -2d'
        self.run_problem(transpiled_paths, args, **kwargs)

    def run_mhd_rotor_problem(self, transpiled_paths, **kwargs):
        args = \
            'magnetoHD/CurrentSheet -auto -2d -gridinterpolation=native -debug'
        self.run_problem(transpiled_paths, args, **kwargs)

    @unittest.expectedFailure
    def test_hy_uhd_getFaceFlux(self):
        """Initially issue #1, now "contains in subroutine"."""
        paths = ['physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90']
        self.run_sod_problem(paths)

    def test_eos_idealGamma(self):
        """Issue #4."""
        paths = ['physics/Eos/EosMain/Gamma/eos_idealGamma.F90']
        self.run_mhd_rotor_problem(paths)

    def test_(self):
        self.skipTest('...')
        paths = []
        args = ''
        self.run_problem(paths, args)


class FlashSubsetTests(FlashTests):

    @classmethod
    def setUpClass(cls):
        cls.root_path = pathlib.Path('flash-subset', 'FLASH4.4')

    def test_hy_hllUnsplit(self):
        """First test case proposed for transpilation."""
        paths = ['physics/Hydro/HydroMain/simpleUnsplit/HLL/hy_hllUnsplit.F90']
        args = \
            'Sod -auto -2d -unit=Grid/GridAmrexLike' \
            ' -unit=physics/Hydro/HydroMain/simpleUnsplit/HLL -parfile=demo_simplehydro_2d.par'
        self.run_problem(paths, args)

    def test_hy_8wv_interpolate(self):
        """Issue #2."""
        paths = ['physics/Hydro/HydroMain/split/MHD_8Wave/hy_8wv_interpolate.F90']
        self.run_mhd_rotor_problem(paths)

    @unittest.expectedFailure
    def test_hy_8wv_fluxes(self):
        """Initially issue #3, now "contains in subroutine"."""
        paths = ['physics/Hydro/HydroMain/split/MHD_8Wave/hy_8wv_fluxes.F90']
        self.run_mhd_rotor_problem(paths)

    def test_hy_8wv_sweep(self):
        """Issue #5."""
        paths = ['physics/Hydro/HydroMain/split/MHD_8Wave/hy_8wv_sweep.F90']
        self.run_mhd_rotor_problem(paths, pre_verify=True)

    def test_hy_uhd_DataReconstructNormalDir_MH(self):
        """Issue #6."""
        paths = ['physics/Hydro/HydroMain/unsplit/hy_uhd_DataReconstructNormalDir_MH.F90']
        self.run_sod_problem(paths)

    def test_hy_uhd_upwindTransverseFlux(self):
        """Issue #7."""
        paths = ['physics/Hydro/HydroMain/unsplit/hy_uhd_upwindTransverseFlux.F90']
        self.run_sod_problem(paths)

    def test_hy_uhd_TVDslope(self):
        """Issue #8."""
        paths = ['physics/Hydro/HydroMain/unsplit/hy_uhd_TVDslope.F90']
        self.run_sod_problem(paths)

    def test_hy_uhd_Roe(self):
        """Issue #9."""
        paths = ['physics/Hydro/HydroMain/unsplit/hy_uhd_Roe.F90']
        self.run_sod_problem(paths, pre_verify=True)


class Flash45Tests(FlashTests):

    @classmethod
    def setUpClass(cls):
        cls.root_path = pathlib.Path('flash-4.5')
