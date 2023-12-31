import math
import random
import torch_geometric
#from poptorch_geometric import FixedSizeDataLoader, FixedSizeOptions
from rdkit import Chem
import torch
from torch_geometric.data import Dataset
from sklearn.utils import shuffle

from feature_no_pad import Featurisation

class PreProcessing:

    def __init__(self, mols, soms, second_SOMS, third_SOMS, split, batch_size, all_soms = False):
        self.mols = mols
        self.training_prop = split[0]
        self.validate_prop = split[1]
        self.testing_prop = split[2]
        self.batch_size = batch_size

        self.all_soms = all_soms

        self.no_atoms, self.no_bonds = self.find_largest_molecule(self.mols)
        self.soms = self.create_som_list(soms, second_SOMS, third_SOMS, self.no_atoms)

        self.smiles = [Chem.MolToSmiles(mol) for mol in mols]
        self.second = second_SOMS
        self.tert = third_SOMS

    def find_largest_molecule(self, mols):
        lengths = [mol.GetNumAtoms() for mol  in mols]
        bonds = [mol.GetNumBonds() for mol  in mols]
        # max_length = max(lengths)
        # max_bonds = max(bonds)

        return lengths, bonds

    def create_som_list(self, soms, second_SOMS, third_SOMS, max):
        new_soms = []

        if self.all_soms is True:
            soms = soms + second_SOMS + third_SOMS

        for (som, atom_number) in zip(soms, max):
            mol_list = [int(0)]*atom_number
            for element in som:
                mol_list[element-1] = int(1)
            new_soms.append(mol_list)

        return new_soms

    def featurise(self):
        features = Featurisation(self.mols, self.soms, self.no_atoms, self.no_bonds)

        graph_object, num_node_features, max_length, dropped_molecules = features.create_pytorch_geometric_graph_data_list_from_smiles_and_labels()
        return graph_object, num_node_features, max_length, dropped_molecules
    
    def featurise_gnn_som(self):
        features = Featurisation(self.mols, self.soms, self.no_atoms, self.no_bonds)

        graph_object, num_node_features, max_length, dropped_molecules = features.create_pytorch_geometric_graph_data_list_from_smiles_and_labels_gnn_som()
        return graph_object, num_node_features, max_length, dropped_molecules
    
    def test_train_split(self):

        data, num_features, lengths, dropped_molecules = self.featurise()

        for i, s in enumerate(self.smiles):
            if s in dropped_molecules:
                self.smiles.pop(i)
                self.second.pop(i)
                self.tert.pop(i)

        indices = list(range(len(data)))  # Generate a list of indices.
        random.shuffle(indices) 

        data_shuffled = [data[i] for i in indices]
        smiles_shuffled =[self.smiles[i] for i in indices]
        second_shuffled =[self.second[i] for i in indices]
        tert_shuffled = [self.tert[i] for i in indices]

        train_length = math.ceil(self.training_prop*len(data_shuffled))
        remaining = data_shuffled[train_length:]
        validate_length = math.ceil(self.validate_prop*len(data_shuffled))
        test_length = len(data_shuffled) - (train_length+validate_length)

        train_dataset = data_shuffled[:train_length]
        validate_dataset = data_shuffled[train_length:(train_length+validate_length)]
        test_dataset = data_shuffled[(train_length+validate_length):]

        smiles_train = smiles_shuffled[:train_length]
        smiles_validate = smiles_shuffled[train_length:(train_length+validate_length)]
        smiles_test = smiles_shuffled[(train_length+validate_length):]
        secondary_test = second_shuffled[(train_length+validate_length):]
        tertiary_test = tert_shuffled[(train_length+validate_length):]

        return train_dataset, test_dataset, validate_dataset, num_features, lengths, smiles_train, smiles_validate, smiles_test, secondary_test, tertiary_test
    
    def test_train_split_gnn_som(self):

        data, num_features, lengths, dropped_molecules = self.featurise_gnn_som()

        for i, s in enumerate(self.smiles):
            if s in dropped_molecules:
                self.smiles.pop(i)
                self.second.pop(i)
                self.tert.pop(i)

        indices = list(range(len(data)))  # Generate a list of indices.
        random.shuffle(indices) 

        data_shuffled = [data[i] for i in indices]
        smiles_shuffled =[self.smiles[i] for i in indices]
        second_shuffled =[self.second[i] for i in indices]
        tert_shuffled = [self.tert[i] for i in indices]

        train_length = math.ceil(self.training_prop*len(data_shuffled))
        remaining = data_shuffled[train_length:]
        validate_length = math.ceil(self.validate_prop*len(data_shuffled))
        test_length = len(data_shuffled) - (train_length+validate_length)

        train_dataset = data_shuffled[:train_length]
        validate_dataset = data_shuffled[train_length:(train_length+validate_length)]
        test_dataset = data_shuffled[(train_length+validate_length):]

        smiles_train = smiles_shuffled[:train_length]
        smiles_validate = smiles_shuffled[train_length:(train_length+validate_length)]
        smiles_test = smiles_shuffled[(train_length+validate_length):]
        secondary_test = second_shuffled[(train_length+validate_length):]
        tertiary_test = tert_shuffled[(train_length+validate_length):]

        return train_dataset, test_dataset, validate_dataset, num_features, lengths, smiles_train, smiles_validate, smiles_test, secondary_test, tertiary_test


    def create_data_loaders(self):
        train, test, validate, num_features, lengths, smiles_train, smiles_validate, smiles_test, secondary_test, tertiary_test  = self.test_train_split()

        # torch.save(train, 'training_no_pad.pt')
        # torch.save(validate, 'validate_no_pad.pt')
        # torch.save(test, 'test_no_pad.pt')

        train_dataset = MyDataset(train)
        test_dataset = MyDataset(test)
        validate_dataset = MyDataset(validate)

        train_loader = torch_geometric.loader.DataLoader(train_dataset,
                                                         batch_size=self.batch_size,
                                                         shuffle = True)
        test_loader = torch_geometric.loader.DataLoader(test_dataset,
                                                        batch_size=self.batch_size)
        if self.validate_prop != 0:
            validate_loader = torch_geometric.loader.DataLoader(validate_dataset,
                                                                batch_size=self.batch_size)
        else:
            validate_loader = None

        
        return train_loader, validate_loader, test_loader, num_features, lengths, smiles_train, smiles_validate, smiles_test, secondary_test, tertiary_test
    
    def create_data_loaders_gnn_som(self):
        train, test, validate, num_features, lengths, smiles_train, smiles_validate, smiles_test, secondary_test, tertiary_test  = self.test_train_split_gnn_som()

        # torch.save(train, 'training_no_pad.pt')
        # torch.save(validate, 'validate_no_pad.pt')
        # torch.save(test, 'test_no_pad.pt')

        train_dataset = MyDataset(train)
        test_dataset = MyDataset(test)
        validate_dataset = MyDataset(validate)

        train_loader = torch_geometric.loader.DataLoader(train_dataset,
                                                         batch_size=self.batch_size,
                                                         shuffle = True)
        test_loader = torch_geometric.loader.DataLoader(test_dataset,
                                                        batch_size=self.batch_size)
        if self.validate_prop != 0:
            validate_loader = torch_geometric.loader.DataLoader(validate_dataset,
                                                                batch_size=self.batch_size)
        else:
            validate_loader = None

        
        return train_loader, validate_loader, test_loader, num_features, lengths, smiles_train, smiles_validate, smiles_test, secondary_test, tertiary_test
    

class MyDataset(Dataset):
    def __init__(self, dataset, transform=None, pre_transform=None):
        super().__init__(None, transform, pre_transform)
        self.dataset = dataset
    
    def len(self):
        return len(self.dataset)

    def get(self, idx):
        data = self.dataset[idx]
        return data, len(data.x)
