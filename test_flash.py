"""Tests of FLASH transpilation."""

import logging
import os
import pathlib
import subprocess
import unittest

from transpyle.general import CodeReader, CodeWriter
from transpyle.fortran import FortranParser, FortranAstGeneralizer, Fortran2008Unparser

logging.basicConfig()

_LOG = logging.getLogger(__name__)

_HERE = pathlib.Path(__file__).parent.resolve()


def fortran_to_fortran(path: pathlib.Path):
    """Transpile Fortran to Fortran, using Python AST as intermediate (generalized) format.

    Parser creates a Fortran-specific AST.
    Generalizer transforms it into AST that can be easily processed and unparsed into many outputs.
    Unparsers creates Fortran code from the same generalized AST.
    """
    reader = CodeReader()
    parser = FortranParser()
    generalizer = FortranAstGeneralizer()
    unparser = Fortran2008Unparser()
    writer = CodeWriter('.f90')

    code = reader.read_file(path)
    fortran_ast = parser.parse(code, path)
    tree = generalizer.generalize(fortran_ast)
    fortran_code = unparser.unparse(tree)

    pathlib.Path.rename(path, path.with_suffix('.bak.f90'))
    writer.write_file(fortran_code, path)


class FlashTests(unittest.TestCase):

    root_path = None
    source_path = None
    setup_cmd = './setup'
    object_path = pathlib.Path('object')
    run_cmd = 'mpirun -np 2 flash4'

    def run_transpyle(self, transpiled_paths):
        absolute_transpiled_paths = [pathlib.Path(_HERE, self.source_path, path)
                                     for path in transpiled_paths]
        all_failed = True
        for path in absolute_transpiled_paths:
            with self.subTest(path=path):
                fortran_to_fortran(path)
        if all_failed:
            self.fail(msg=absolute_transpiled_paths)

    def run_flash(self, flash_args):
        absolute_flash_path = pathlib.Path(_HERE, self.root_path)
        absolute_object_path = pathlib.Path(_HERE, self.object_path)
        if isinstance(flash_args, str):
            flash_args = flash_args.split(' ')
        flash_setup_cmd = [self.setup_cmd] + flash_args
        flash_run_cmd = self.un_cmd.split(' ')

        with self.subTest(setup_cmd=flash_setup_cmd, run_cmd=flash_run_cmd):
            os.chdir(str(absolute_flash_path))
            setup_result = subprocess.run(flash_setup_cmd)
            self.assertEqual(setup_result.returncode, 0, msg=setup_result)
            os.chdir(str(absolute_object_path))
            run_result = subprocess.run(flash_run_cmd)
            self.assertEqual(run_result.returncode, 0, msg=run_result)

    def run_problem(self, transpiled_paths, flash_args):
        run_transpyle(transpiled_paths)

    def run_sod_problem(self, transpiled_paths):
        args = './setup -auto -2d'
        self.run_problem(transpiled_paths, args)

    def run_mhd_rotor_problem(self, transpiled_paths):
        args = \
            'magnetoHD/CurrentSheet -auto -2d -objdir=mhdrotor -site=sauc.xps' \
            ' -gridinterpolation=native -debug'
        self.run_problem(transpiled_paths, args)

    def test_hy_uhd_getFaceFlux(self):
        """Initially issue #1, now "contains in subroutine"."""
        paths = ['physics/Hydro/HydroMain/unsplit/hy_uhd_getFaceFlux.F90']
        self.run_sod_problem(paths, args)

    def test_eos_idealGamma(self):
        """Issue #4."""
        paths = ['physics/Eos/EosMain/Gamma/eos_idealGamma.F90']
        self.run_mhd_rotor_problem(paths, args)

    def test_(self):
        paths = []
        args = ''
        # self.run_problem(paths, args)


class FlashSubsetTests(FlashTests):

    root_path = pathlib.Path('flash-subset')
    source_path = pathlib.Path('FLASH4.4', 'source')

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
        self.run_mhd_rotor_problem(paths, args)

    def test_hy_8wv_fluxes(self):
        """Initially issue #3, now "contains in subroutine"."""
        paths = ['physics/Hydro/HydroMain/split/MHD_8Wave/hy_8wv_fluxes.F90']
        self.run_mhd_rotor_problem(paths, args)

    def test_hy_8wv_sweep(self):
        """Issue #5."""
        paths = ['physics/Hydro/HydroMain/split/MHD_8Wave/hy_8wv_sweep.F90']
        self.run_mhd_rotor_problem(paths, args)

    def test_hy_uhd_DataReconstructNormalDir_MH(self):
        """Issue #6."""
        paths = ['physics/Hydro/HydroMain/unsplit/hy_uhd_DataReconstructNormalDir_MH.F90']
        self.run_sod_problem(paths, args)

    def test_hy_uhd_upwindTransverseFlux(self):
        """Issue #7."""
        paths = ['physics/Hydro/HydroMain/unsplit/hy_uhd_upwindTransverseFlux.F90']
        self.run_sod_problem(paths, args)

    def test_hy_uhd_TVDslope(self):
        """Issue #8."""
        paths = ['physics/Hydro/HydroMain/unsplit/hy_uhd_TVDslope.F90']
        self.run_sod_problem(paths, args)

    def test_hy_uhd_Roe(self):
        """Issue #9."""
        paths = ['physics/Hydro/HydroMain/unsplit/hy_uhd_Roe.F90']
        self.run_sod_problem(paths, args)


class Flash45Tests(FlashTests):

    root_path = pathlib.Path('flash-4.5')
    source_path = pathlib.Path('source')

    def test_eos_idealGamma(self):
        paths = ['physics/Eos/EosMain/Gamma/eos_idealGamma.F90']
        self.run_mhd_rotor_problem(paths, args)
