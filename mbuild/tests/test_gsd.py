import numpy as np
import pytest

import mbuild as mb
from mbuild import Box
from mbuild.tests.base_test import BaseTest
from mbuild.utils.io import has_foyer, has_gsd


class TestGSD(BaseTest):
    @pytest.mark.skipif(not has_gsd, reason="GSD package not installed")
    def test_save(self, ethane):
        ethane.save(filename="ethane.gsd")

    @pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
    @pytest.mark.skipif(not has_gsd, reason="GSD package not installed")
    def test_save_forcefield(self, ethane):
        ethane.save(filename="ethane-opls.gsd", forcefield_name="oplsaa")

    @pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
    @pytest.mark.skipif(not has_gsd, reason="GSD package not installed")
    def test_save_box(self, ethane):
        box = Box(lengths=[2.0, 2.0, 2.0], angles=[90.0, 90.0, 90.0])
        ethane.save(
            filename="ethane-box.gsd", forcefield_name="oplsaa", box=box
        )

    @pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
    def test_save_triclinic_box_(self, ethane):
        box = Box(lengths=np.array([2.0, 2.0, 2.0]), angles=[60, 70, 80])
        ethane.save(
            filename="triclinic-box.gsd", forcefield_name="oplsaa", box=box
        )

    @pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
    @pytest.mark.skipif(not has_gsd, reason="GSD package not installed")
    def test_particles(self, ethane):
        from collections import OrderedDict

        import gsd
        import gsd.hoomd

        from mbuild.utils.sorting import natural_sort

        ethane.save(filename="ethane.gsd", forcefield_name="oplsaa")
        with gsd.hoomd.open("ethane.gsd", mode="rb") as f:
            frame = f[0]

        assert frame.configuration.step == 0
        assert frame.configuration.dimensions == 3

        mass_dict = {"C": 12.011, "H": 1.008}
        masses = frame.particles.mass.astype(float)
        for mass, particle in zip(masses, ethane.particles()):
            assert round(mass, 3) == mass_dict[particle.name]

        n_particles = frame.particles.N
        assert n_particles == ethane.n_particles

        positions = frame.particles.position.astype(float)
        shift = positions[0] - (ethane[0].pos * 10)
        shifted_xyz = (ethane.xyz * 10) + shift
        assert np.array_equal(
            np.round(positions, decimals=4), np.round(shifted_xyz, decimals=4)
        )

        opls_type_dict = OrderedDict([("C", "opls_135"), ("H", "opls_140")])
        types_from_gsd = frame.particles.types
        typeids_from_gsd = frame.particles.typeid.astype(int)
        expected_types = [
            opls_type_dict[particle.name] for particle in ethane.particles()
        ]
        unique_types = list(set(expected_types))
        unique_types.sort(key=natural_sort)
        expected_typeids = [
            unique_types.index(atype) for atype in expected_types
        ]
        assert np.array_equal(types_from_gsd, unique_types)
        assert np.array_equal(typeids_from_gsd, expected_typeids)

    @pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
    @pytest.mark.skipif(not has_gsd, reason="GSD package not installed")
    def test_box(self, ethane):
        import gsd
        import gsd.hoomd

        lengths = [2.0, 3.0, 4.0]
        ethane.box = Box(lengths=[2.0, 3.0, 4.0])

        ethane.save(filename="ethane.gsd", forcefield_name="oplsaa")
        with gsd.hoomd.open("ethane.gsd", mode="rb") as f:
            frame = f[0]

        box_from_gsd = frame.configuration.box.astype(float)
        (lx, ly, lz) = ethane.box.lengths
        lx *= 10
        ly *= 10
        lz *= 10
        assert np.array_equal(box_from_gsd[:3], [lx, ly, lz])
        assert not np.any(box_from_gsd[3:])

        ethane.periodicity = (True, True, True)
        ethane.save(filename="ethane-periodicity.gsd", forcefield_name="oplsaa")
        with gsd.hoomd.open("ethane-periodicity.gsd", mode="rb") as f:
            frame = f[0]
        box_from_gsd_periodic = frame.configuration.box.astype(float)
        assert np.array_equal(box_from_gsd, box_from_gsd_periodic)

        box = Box(lengths=np.array([2.0, 2.0, 2.0]), angles=[92, 104, 119])
        # check that providing a box to save overwrites compound.box
        ethane.save(
            filename="triclinic-box.gsd", forcefield_name="oplsaa", box=box
        )
        with gsd.hoomd.open("triclinic-box.gsd", mode="rb") as f:
            frame = f[0]
        lx, ly, lz, xy, xz, yz = frame.configuration.box

        a = lx
        b = np.sqrt(ly ** 2 + xy ** 2)
        c = np.sqrt(lz ** 2 + xz ** 2 + yz ** 2)

        assert np.isclose(np.cos(np.radians(92)), (xy * xz + ly * yz) / (b * c))
        assert np.isclose(np.cos(np.radians(104)), xz / c)
        assert np.isclose(np.cos(np.radians(119)), xy / b)

    @pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
    @pytest.mark.skipif(not has_gsd, reason="GSD package not installed")
    def test_rigid(self, benzene):
        import gsd
        import gsd.hoomd

        benzene.label_rigid_bodies(rigid_particles="C")
        benzene.save(filename="benzene.gsd", forcefield_name="oplsaa")
        with gsd.hoomd.open("benzene.gsd", mode="rb") as f:
            frame = f[0]

        rigid_bodies = frame.particles.body
        expected_bodies = [
            -1 if p.rigid_id is None else p.rigid_id
            for p in benzene.particles()
        ]
        for gsd_body, expected_body in zip(rigid_bodies, expected_bodies):
            assert gsd_body == expected_body

    @pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
    @pytest.mark.skipif(not has_gsd, reason="GSD package not installed")
    def test_bonded(self, ethane):
        import gsd
        import gsd.hoomd
        from foyer import Forcefield

        ethane.save(filename="ethane.gsd", forcefield_name="oplsaa")
        with gsd.hoomd.open("ethane.gsd", mode="rb") as f:
            frame = f[0]

        structure = ethane.to_parmed()
        forcefield = Forcefield(name="oplsaa")
        structure = forcefield.apply(structure)

        # Bonds
        n_bonds = frame.bonds.N
        assert n_bonds == len(structure.bonds)

        expected_unique_bond_types = ["opls_135-opls_135", "opls_135-opls_140"]
        bond_types = frame.bonds.types
        assert np.array_equal(bond_types, expected_unique_bond_types)

        bond_typeids = frame.bonds.typeid
        bond_atoms = frame.bonds.group
        expected_bond_atoms = [
            [bond.atom1.idx, bond.atom2.idx] for bond in structure.bonds
        ]
        assert np.array_equal(bond_atoms, expected_bond_atoms)

        bond_type_dict = {("C", "C"): 0, ("C", "H"): 1, ("H", "C"): 1}
        expected_bond_typeids = []
        for bond in structure.bonds:
            expected_bond_typeids.append(
                bond_type_dict[(bond.atom1.name, bond.atom2.name)]
            )
        assert np.array_equal(bond_typeids, expected_bond_typeids)

        # Angles
        n_angles = frame.angles.N
        assert n_angles == len(structure.angles)

        expected_unique_angle_types = [
            "opls_135-opls_135-opls_140",
            "opls_140-opls_135-opls_140",
        ]
        angle_types = frame.angles.types
        assert np.array_equal(angle_types, expected_unique_angle_types)

        angle_typeids = frame.angles.typeid
        angle_atoms = frame.angles.group
        expected_angle_atoms = [
            [angle.atom1.idx, angle.atom2.idx, angle.atom3.idx]
            for angle in structure.angles
        ]
        assert np.array_equal(angle_atoms, expected_angle_atoms)

        angle_type_dict = {
            ("C", "C", "H"): 0,
            ("H", "C", "C"): 0,
            ("H", "C", "H"): 1,
        }
        expected_angle_typeids = []
        for angle in structure.angles:
            expected_angle_typeids.append(
                angle_type_dict[
                    (angle.atom1.name, angle.atom2.name, angle.atom3.name)
                ]
            )
        assert np.array_equal(angle_typeids, expected_angle_typeids)

        # Dihedrals
        n_dihedrals = frame.dihedrals.N
        assert n_dihedrals == len(structure.rb_torsions)

        expected_unique_dihedral_types = ["opls_140-opls_135-opls_135-opls_140"]
        dihedral_types = frame.dihedrals.types
        assert np.array_equal(dihedral_types, expected_unique_dihedral_types)

        dihedral_typeids = frame.dihedrals.typeid
        dihedral_atoms = frame.dihedrals.group
        expected_dihedral_atoms = []
        for dihedral in structure.rb_torsions:
            expected_dihedral_atoms.append(
                [
                    dihedral.atom1.idx,
                    dihedral.atom2.idx,
                    dihedral.atom3.idx,
                    dihedral.atom4.idx,
                ]
            )
        assert np.array_equal(dihedral_atoms, expected_dihedral_atoms)
        assert np.array_equal(dihedral_typeids, np.zeros(n_dihedrals))

    @pytest.mark.skipif(not has_foyer, reason="Foyer package not installed")
    @pytest.mark.skipif(not has_gsd, reason="GSD package not installed")
    def test_pairs(self, benzene):
        import gsd
        import gsd.hoomd
        from foyer import Forcefield

        benzene.save(filename="benzene.gsd", forcefield_name="oplsaa")
        with gsd.hoomd.open("benzene.gsd", mode="rb") as f:
            frame = f[0]

        structure = benzene.to_parmed()
        forcefield = Forcefield(name="oplsaa")
        structure = forcefield.apply(structure)

        # Pairs
        assert len(frame.pairs.types) == 3
        assert frame.pairs.N == 21

    @pytest.mark.skipif(not has_gsd, reason="GSD package not installed")
    def test_units(self, ethane):
        import gsd
        import gsd.hoomd

        ref_distance = 3.5
        ref_energy = 0.066
        ref_mass = 12.011

        box = Box(lengths=[2.0, 3.0, 4.0], angles=[90.0, 90.0, 90.0])
        ethane.save(
            filename="ethane.gsd",
            forcefield_name="oplsaa",
            ref_distance=ref_distance,
            ref_energy=ref_energy,
            ref_mass=ref_mass,
            box=box,
        )
        with gsd.hoomd.open("ethane.gsd", mode="rb") as f:
            frame = f[0]

        box_from_gsd = frame.configuration.box.astype(float)
        assert np.array_equal(
            np.round(box_from_gsd[:3], decimals=5),
            np.round(np.asarray(box.lengths) * 10 / ref_distance, 5),
        )

        mass_dict = {"C": 12.011, "H": 1.008}
        masses = frame.particles.mass.astype(float)
        for mass, p in zip(masses, ethane.particles()):
            assert round(mass, 3) == round(mass_dict[p.name] / ref_mass, 3)

        charge_dict = {"C": -0.18, "H": 0.06}
        charges = frame.particles.charge.astype(float)
        e0 = 2.39725e-4
        charge_factor = (4.0 * np.pi * e0 * ref_distance * ref_energy) ** 0.5
        for charge, particle in zip(charges, ethane.particles()):
            reduced_charge = charge_dict[particle.name] / charge_factor
            assert round(charge, 3) == round(reduced_charge, 3)

        positions = frame.particles.position.astype(float)
        shift = positions[0] - (ethane[0].pos * 10 / ref_distance)
        shifted_xyz = (ethane.xyz * 10 / ref_distance) + shift
        assert np.array_equal(
            np.round(positions, decimals=4), np.round(shifted_xyz, decimals=4)
        )

    @pytest.mark.skipif(not has_gsd, reason="GSD package not installed")
    def test_box_dimensions(self, benzene):
        import gsd
        import gsd.hoomd

        n_benzenes = 10
        filled = mb.fill_box(
            benzene, n_compounds=n_benzenes, box=[0, 0, 0, 4, 4, 4]
        )
        filled.save(filename="benzene.gsd")
        with gsd.hoomd.open("benzene.gsd", mode="rb") as f:
            frame = f[0]
        positions = frame.particles.position.astype(float)
        for coords in positions:
            assert coords.max() < 20
            assert coords.min() > -20
