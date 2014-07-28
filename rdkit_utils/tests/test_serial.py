"""
Tests for serial.py.
"""
import cPickle
import gzip
import shutil
import tempfile
import unittest

from rdkit import Chem
from rdkit.Chem import AllChem

from rdkit_utils import conformers, serial


class TestMolIO(unittest.TestCase):
    """
    Base test class for molecule I/O.
    """
    def setUp(self):
        """
        Write SDF and SMILES molecules to temporary files.
        """
        self.temp_dir = tempfile.mkdtemp()

        # aspirin
        self.aspirin = self._get_mol_from_smiles('CC(=O)OC1=CC=CC=C1C(=O)O',
                                                 'aspirin')
        self.aspirin_h = Chem.AddHs(self.aspirin)
        self.aspirin_sodium = self._get_mol_from_smiles(
            'CC(=O)OC1=CC=CC=C1C(=O)[O-].[Na+]', 'aspirin sodium')

        # levalbuterol (chiral)
        self.levalbuterol = self._get_mol_from_smiles(
            'CC(C)(C)NC[C@@H](C1=CC(=C(C=C1)O)CO)O', 'levalbuterol')
        self.levalbuterol_hcl = self._get_mol_from_smiles(
            'CC(C)(C)NC[C@@H](C1=CC(=C(C=C1)O)CO)O.Cl',
            'levalbuterol hydrochloride')

        self.ref_mols = [self.aspirin, self.levalbuterol]
        self.reader = serial.MolReader()

    def _get_mol_from_smiles(self, smiles, name=None):
        """
        Construct a molecule from a SMILES string.

        Molecules loaded from SMILES strings have zero conformers, but
        molecules loaded from SDF blocks are treated as 3D and have one
        conformer even if coordinates are not set. This method dumps the
        molecule to SDF and loads it again to obtain a molecule with one
        conformer.

        Parameters
        ----------
        smiles : str
            SMILES string.
        name : str, optional
            Molecule name.
        """
        mol = Chem.MolFromSmiles(smiles)
        if name is not None:
            mol.SetProp('_Name', name)
        AllChem.Compute2DCoords(mol)  # required to preserve stereo
        sdf = Chem.MolToMolBlock(mol, includeStereo=True)
        mol_with_conf = Chem.MolFromMolBlock(sdf)
        return mol_with_conf

    def tearDown(self):
        """
        Clean up temporary files.
        """
        shutil.rmtree(self.temp_dir)


class TestMolReader(TestMolIO):
    """
    Test MolReader.
    """
    def test_read_sdf(self):
        """
        Read an SDF file.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            f.write(Chem.MolToMolBlock(self.aspirin))
        self.reader.open(filename)
        mols = self.reader.get_mols()
        assert mols.next().ToBinary() == self.aspirin.ToBinary()

    def test_read_sdf_gz(self):
        """
        Read a compressed SDF file.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf.gz', dir=self.temp_dir)
        with gzip.open(filename, 'wb') as f:
            f.write(Chem.MolToMolBlock(self.aspirin))
        self.reader.open(filename)
        mols = self.reader.get_mols()
        assert mols.next().ToBinary() == self.aspirin.ToBinary()

    def test_read_smi(self):
        """
        Read a SMILES file.
        """
        ref_mol = Chem.MolFromSmiles(Chem.MolToSmiles(self.aspirin))
        _, filename = tempfile.mkstemp(suffix='.smi', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            f.write(Chem.MolToSmiles(self.aspirin))
        self.reader.open(filename)
        mols = self.reader.get_mols()
        assert mols.next().ToBinary() == ref_mol.ToBinary()

    def test_read_smi_title(self):
        """
        Read a SMILES file with molecule titles.
        """
        ref_mol = Chem.MolFromSmiles(Chem.MolToSmiles(self.aspirin))
        ref_mol.SetProp('_Name', 'aspirin')
        _, filename = tempfile.mkstemp(suffix='.smi', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            f.write('{}\t{}'.format(Chem.MolToSmiles(self.aspirin), 'aspirin'))
        self.reader.open(filename)
        mols = self.reader.get_mols()
        mol = mols.next()
        assert mol.ToBinary() == ref_mol.ToBinary()
        assert mol.GetProp('_Name') == ref_mol.GetProp('_Name')

    def test_read_smi_gz(self):
        """
        Read a compressed SMILES file.
        """
        ref_mol = Chem.MolFromSmiles(Chem.MolToSmiles(self.aspirin))
        _, filename = tempfile.mkstemp(suffix='.smi.gz', dir=self.temp_dir)
        with gzip.open(filename, 'wb') as f:
            f.write(Chem.MolToSmiles(self.aspirin))
        self.reader.open(filename)
        mols = self.reader.get_mols()
        assert mols.next().ToBinary() == ref_mol.ToBinary()

    def test_read_pickle(self):
        """
        Read from a pickle.
        """
        _, filename = tempfile.mkstemp(suffix='.pkl', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            cPickle.dump([self.aspirin], f, cPickle.HIGHEST_PROTOCOL)
        self.reader.open(filename)
        mols = self.reader.get_mols()
        assert mols.next().ToBinary() == self.aspirin.ToBinary()

    def test_read_pickle_gz(self):
        """
        Read from a compressed pickle.
        """
        _, filename = tempfile.mkstemp(suffix='.pkl.gz', dir=self.temp_dir)
        with gzip.open(filename, 'wb') as f:
            cPickle.dump([self.aspirin], f, cPickle.HIGHEST_PROTOCOL)
        self.reader.open(filename)
        mols = self.reader.get_mols()
        assert mols.next().ToBinary() == self.aspirin.ToBinary()

    def test_read_file_like(self):
        """
        Read from a file-like object.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            f.write(Chem.MolToMolBlock(self.aspirin))
        with open(filename) as f:
            reader = serial.MolReader(f, mol_format='sdf')
            mols = reader.get_mols()
            assert mols.next().ToBinary() == self.aspirin.ToBinary()

    def test_read_compressed_file_like(self):
        """
        Read from a file-like object using gzip.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf.gz', dir=self.temp_dir)
        with gzip.open(filename, 'wb') as f:
            f.write(Chem.MolToMolBlock(self.aspirin))
        with gzip.open(filename) as f:
            reader = serial.MolReader(f, mol_format='sdf')
            mols = reader.get_mols()
            assert mols.next().ToBinary() == self.aspirin.ToBinary()

    def test_read_multiple_sdf(self):
        """
        Read a multiple-molecule SDF file.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            for mol in self.ref_mols:
                sdf = Chem.MolToMolBlock(mol)
                f.write(sdf)
                f.write('$$$$\n')  # add molecule delimiter
        self.reader.open(filename)
        mols = self.reader.get_mols()
        mols = list(mols)
        assert len(mols) == 2
        for i in xrange(len(mols)):
            assert mols[i].ToBinary() == self.ref_mols[i].ToBinary()

    def test_read_multiple_smiles(self):
        """
        Read a multiple-molecule SMILES file.
        """
        ref_mols = []
        for mol in self.ref_mols:
            mol = Chem.MolFromSmiles(Chem.MolToSmiles(mol))
            ref_mols.append(mol)
        _, filename = tempfile.mkstemp(suffix='.smi', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            for mol in self.ref_mols:
                smiles = Chem.MolToSmiles(mol)
                name = mol.GetProp('_Name')
                f.write('{}\t{}\n'.format(smiles, name))
        self.reader.open(filename)
        mols = self.reader.get_mols()
        mols = list(mols)
        assert len(mols) == 2
        for i in xrange(len(mols)):
            assert mols[i].ToBinary() == ref_mols[i].ToBinary()

    def test_read_multiconformer(self):
        """
        Read a multiconformer SDF file containing multiple molecules.
        """

        # generate conformers
        ref_mols = []
        engine = conformers.ConformerGenerator(max_conformers=3,
                                               pool_multiplier=1)
        for mol in self.ref_mols:
            expanded = engine.generate_conformers(mol)
            assert expanded.GetNumConformers() > 1
            ref_mols.append(expanded)

        # write to disk
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            for mol in ref_mols:
                for conf in mol.GetConformers():
                    f.write(Chem.MolToMolBlock(mol, confId=conf.GetId()))
                    f.write('$$$$\n')  # add molecule delimiter

        # compare
        self.reader.open(filename)
        mols = self.reader.get_mols()
        mols = list(mols)
        assert len(mols) == 2
        for i in xrange(len(mols)):
            assert mols[i].ToBinary() == ref_mols[i].ToBinary()

    def test_are_same_molecule(self):
        """
        Test MolReader.are_same_molecule.
        """
        assert self.reader.are_same_molecule(self.aspirin, self.aspirin)
        assert not self.reader.are_same_molecule(self.aspirin,
                                                 self.levalbuterol)

    def test_no_remove_hydrogens(self):
        """
        Test hydrogen retention.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            f.write(Chem.MolToMolBlock(self.aspirin_h))
        reader = serial.MolReader(remove_hydrogens=False)
        reader.open(filename)
        mols = reader.get_mols()
        assert mols.next().ToBinary() == self.aspirin_h.ToBinary()

    def test_remove_hydrogens(self):
        """
        Test hydrogen removal.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            f.write(Chem.MolToMolBlock(self.aspirin_h))
        reader = serial.MolReader(remove_hydrogens=True)
        reader.open(filename)
        mols = reader.get_mols()
        assert mols.next().ToBinary() == self.aspirin.ToBinary()

    def test_remove_salts(self):
        """
        Test salt removal.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            for mol in [self.aspirin_sodium, self.levalbuterol_hcl]:
                f.write(Chem.MolToMolBlock(mol))
                f.write('$$$$\n')  # molecule delimiter
        ref_mols = [self.aspirin_sodium, self.levalbuterol_hcl]
        reader = serial.MolReader(remove_salts=True)
        reader.open(filename)
        mols = reader.get_mols()
        mols = list(mols)
        assert len(mols) == 2
        for mol, ref_mol in zip(mols, ref_mols):
            assert mol.GetNumAtoms() < ref_mol.GetNumAtoms()
            desalted = self.reader.clean_mol(ref_mol)
            assert mol.ToBinary() == desalted.ToBinary()

    def test_no_remove_salts(self):
        """
        Test salt retention.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        with open(filename, 'wb') as f:
            for mol in [self.aspirin_sodium, self.levalbuterol_hcl]:
                f.write(Chem.MolToMolBlock(mol))
                f.write('$$$$\n')  # molecule delimiter
        ref_mols = [self.aspirin_sodium, self.levalbuterol_hcl]
        reader = serial.MolReader(remove_salts=False)
        reader.open(filename)
        mols = reader.get_mols()
        mols = list(mols)
        assert len(mols) == 2
        for mol, ref_mol in zip(mols, ref_mols):
            assert mol.ToBinary() == ref_mol.ToBinary()
            desalted = self.reader.clean_mol(ref_mol)
            assert mol.GetNumAtoms() > desalted.GetNumAtoms()


class TestMolWriter(TestMolIO):
    """
    Test MolWriter.
    """
    def setUp(self):
        """
        Add writer to inherited setup.
        """
        super(TestMolWriter, self).setUp()
        self.writer = serial.MolWriter()
        self.aspirin_sdf = Chem.MolToMolBlock(self.aspirin)
        self.aspirin_smiles = Chem.MolToSmiles(self.aspirin) + '\taspirin'

    def test_write_sdf(self):
        """
        Write an SDF file.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        self.writer.open(filename)
        self.writer.write([self.aspirin])
        self.writer.close()
        self.reader.open(filename)
        mols = self.reader.get_mols()

        # compare molecules
        assert mols.next().ToBinary() == self.aspirin.ToBinary()

        # compare files
        with open(filename) as f:
            data = f.read()
            assert data == self.aspirin_sdf + '$$$$\n'

    def test_write_sdf_gz(self):
        """
        Write a compressed SDF file.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf.gz', dir=self.temp_dir)
        self.writer.open(filename)
        self.writer.write([self.aspirin])
        self.writer.close()
        self.reader.open(filename)
        mols = self.reader.get_mols()

        # compare molecules
        assert mols.next().ToBinary() == self.aspirin.ToBinary()

        # compare files
        with gzip.open(filename) as f:
            data = f.read()
            assert data == self.aspirin_sdf + '$$$$\n'

    def test_write_smiles(self):
        """
        Write a SMILES file.
        """
        ref_mol = Chem.MolFromSmiles(Chem.MolToSmiles(self.aspirin))
        _, filename = tempfile.mkstemp(suffix='.smi', dir=self.temp_dir)
        self.writer.open(filename)
        self.writer.write([self.aspirin])
        self.writer.close()
        self.reader.open(filename)
        mols = self.reader.get_mols()

        # compare molecules
        assert mols.next().ToBinary() == ref_mol.ToBinary()

        # compare files
        with open(filename) as f:
            data = f.read()
            assert data.strip() == self.aspirin_smiles

    def test_write_smiles_gz(self):
        """
        Write a compressed SMILES file.
        """
        ref_mol = Chem.MolFromSmiles(Chem.MolToSmiles(self.aspirin))
        _, filename = tempfile.mkstemp(suffix='.smi.gz', dir=self.temp_dir)
        self.writer.open(filename)
        self.writer.write([self.aspirin])
        self.writer.close()
        self.reader.open(filename)
        mols = self.reader.get_mols()

        # compare molecules
        assert mols.next().ToBinary() == ref_mol.ToBinary()

        # compare files
        with gzip.open(filename) as f:
            data = f.read()
            assert data.strip() == self.aspirin_smiles

    def test_write_pickle(self):
        """
        Write a pickle.
        """
        _, filename = tempfile.mkstemp(suffix='.pkl', dir=self.temp_dir)
        self.writer.open(filename)
        self.writer.write([self.aspirin])
        self.writer.close()
        self.reader.open(filename)
        mols = self.reader.get_mols()

        # compare molecules
        assert mols.next().ToBinary() == self.aspirin.ToBinary()

        # compare files
        with open(filename) as f:
            data = f.read()
            assert data == cPickle.dumps([self.aspirin],
                                         cPickle.HIGHEST_PROTOCOL)

    def test_write_pickle_gz(self):
        """
        Write a compressed pickle.
        """
        _, filename = tempfile.mkstemp(suffix='.pkl.gz', dir=self.temp_dir)
        self.writer.open(filename)
        self.writer.write([self.aspirin])
        self.writer.close()
        self.reader.open(filename)
        mols = self.reader.get_mols()

        # compare molecules
        assert mols.next().ToBinary() == self.aspirin.ToBinary()

        # compare files
        with gzip.open(filename) as f:
            data = f.read()
            assert data == cPickle.dumps([self.aspirin],
                                         cPickle.HIGHEST_PROTOCOL)

    def test_stereo_setup(self):
        """
        Make sure chiral reference molecule is correct.
        """
        smiles = Chem.MolToSmiles(self.levalbuterol, isomericSmiles=True)
        assert '@' in smiles  # check for stereochemistry flag

        # check that removing stereochemistry changes the molecule
        original = self.levalbuterol.ToBinary()
        AllChem.RemoveStereochemistry(self.levalbuterol)
        assert self.levalbuterol.ToBinary() != original

    def test_stereo_sdf(self):
        """
        Test stereochemistry preservation when writing to SDF.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        writer = serial.MolWriter(stereo=True)
        writer.open(filename)
        writer.write([self.levalbuterol])
        writer.close()
        self.reader.open(filename)
        mols = self.reader.get_mols()
        assert mols.next().ToBinary() == self.levalbuterol.ToBinary()

    def test_stereo_smi(self):
        """
        Test stereochemistry preservation when writing to SMILES.
        """
        ref_mol = Chem.MolFromSmiles(Chem.MolToSmiles(self.levalbuterol,
                                                      isomericSmiles=True))
        _, filename = tempfile.mkstemp(suffix='.smi', dir=self.temp_dir)
        writer = serial.MolWriter(stereo=True)
        writer.open(filename)
        writer.write([self.levalbuterol])
        writer.close()
        self.reader.open(filename)
        mols = self.reader.get_mols()
        assert mols.next().ToBinary() == ref_mol.ToBinary()

    def test_no_stereo_sdf(self):
        """
        Test stereochemistry removal when writing to SDF.
        """
        _, filename = tempfile.mkstemp(suffix='.sdf', dir=self.temp_dir)
        writer = serial.MolWriter(stereo=False)
        writer.open(filename)
        writer.write([self.levalbuterol])
        writer.close()
        self.reader.open(filename)
        mols = self.reader.get_mols()
        mol = mols.next()

        # make sure the written molecule differs from the reference
        assert mol.ToBinary() != self.levalbuterol.ToBinary()

        # check again after removing stereochemistry
        AllChem.RemoveStereochemistry(self.levalbuterol)
        assert mol.ToBinary() == self.levalbuterol.ToBinary()

    def test_no_stereo_smiles(self):
        """
        Test stereochemistry removal when writing to SMILES.
        """
        ref_mol = Chem.MolFromSmiles(Chem.MolToSmiles(self.levalbuterol,
                                                      isomericSmiles=True))
        AllChem.Compute2DCoords(ref_mol)
        _, filename = tempfile.mkstemp(suffix='.smi', dir=self.temp_dir)
        writer = serial.MolWriter(stereo=False)
        writer.open(filename)
        writer.write([self.levalbuterol])
        writer.close()
        self.reader.open(filename)
        mols = self.reader.get_mols()
        mol = mols.next()

        # make sure the written molecule differs from the reference
        assert mol.ToBinary() != self.levalbuterol.ToBinary()

        # check again after removing stereochemistry
        AllChem.RemoveStereochemistry(self.levalbuterol)
        assert mol.ToBinary() == self.levalbuterol.ToBinary()
