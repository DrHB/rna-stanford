# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_dataset.ipynb.

# %% auto 0
__all__ = ['good_luck', 'LenMatchBatchSampler', 'dict_to', 'to_device', 'DeviceDataLoader', 'encode_rna_sequence',
           'generate_edge_data', 'RNA_DatasetBaseline', 'RNA_DatasetBaselineSplit', 'RNA_DatasetV0', 'RNA_DatasetV1',
           'RNA_DatasetV0G', 'generate_base_pair_matrix', 'RNA_DatasetBaselineSplitbppV0', 'dot_to_adjacency',
           'RNA_DatasetBaselineSplitssV0', 'RNA_Dataset_Test', 'RNA_Dataset_TestBpp']

# %% ../nbs/00_dataset.ipynb 2
import pandas as pd
import numpy as np
from pathlib import Path
from torch.utils.data import Dataset, DataLoader
from torch_geometric.data import Data, DataLoader, Batch
import torch
import seaborn as sbn
import torch.nn.functional as F
from tqdm import tqdm
from sklearn.model_selection import KFold
import random

# %% ../nbs/00_dataset.ipynb 4
def good_luck():
    return True

# %% ../nbs/00_dataset.ipynb 5
class LenMatchBatchSampler(torch.utils.data.BatchSampler):
    def __iter__(self):
        buckets = [[]] * 100
        yielded = 0

        for idx in self.sampler:
            s = self.sampler.data_source[idx]
            if isinstance(s,tuple): L = s[0]["mask"].sum()
            else: L = s["mask"].sum()
            L = max(1,L // 16) 
            if len(buckets[L]) == 0:  buckets[L] = []
            buckets[L].append(idx)
            
            if len(buckets[L]) == self.batch_size:
                batch = list(buckets[L])
                yield batch
                yielded += 1
                buckets[L] = []
                
        batch = []
        leftover = [idx for bucket in buckets for idx in bucket]

        for idx in leftover:
            batch.append(idx)
            if len(batch) == self.batch_size:
                yielded += 1
                yield batch
                batch = []

        if len(batch) > 0 and not self.drop_last:
            yielded += 1
            yield batch
            
def dict_to(x, device='cuda'):
    return {k:x[k].to(device) for k in x}

def to_device(x, device='cuda'):
    return tuple(dict_to(e,device) for e in x)

class DeviceDataLoader:
    def __init__(self, dataloader, device='cuda'):
        self.dataloader = dataloader
        self.device = device
    
    def __len__(self):
        return len(self.dataloader)
    
    def __iter__(self):
        for batch in self.dataloader:
            yield tuple(dict_to(x, self.device) for x in batch)

# %% ../nbs/00_dataset.ipynb 6
def encode_rna_sequence(seq):
    L = len(seq)

    # Initialize the tensor with zeros
    tensor = np.zeros((L, L, 8))

    # Define valid base pairs
    valid_pairs = [
        ("A", "U"),
        ("U", "A"),
        ("U", "G"),
        ("G", "U"),
        ("G", "C"),
        ("C", "G"),
    ]

    for i in range(L):
        for j in range(L):
            # Check for valid base pairs
            if (seq[i], seq[j]) in valid_pairs:
                channel = valid_pairs.index((seq[i], seq[j]))
                tensor[i, j, channel] = 1
            # Check for diagonal
            elif i == j:
                tensor[i, j, 6] = 1
            # If not a valid pair and not on the diagonal, set the last channel
            else:
                tensor[i, j, 7] = 1

    return tensor



def generate_edge_data(file_path):
    # Read the file into a DataFrame
    data = pd.read_csv(file_path, sep=" ", header=None, names=["pos1", "pos2", "prob"])
    
    # Convert the pos1 and pos2 columns to 0-based indices and then to a tensor for edge index
    edge_index = torch.tensor([data["pos1"].values - 1, data["pos2"].values - 1], dtype=torch.long)
    
    # Convert the prob column to a tensor for edge features
    edge_features = torch.tensor(data["prob"].values, dtype=torch.float).unsqueeze(1)  # Adding an extra dimension
    
    return edge_index, edge_features


class RNA_DatasetBaseline(Dataset):
    def __init__(self, df, mode='train', seed=2023, fold=0, nfolds=4, mask_only=False, 
                 sn_train=True, **kwargs):
        self.seq_map = {'A':0,'C':1,'G':2,'U':3}
        self.Lmax = 206
        df['L'] = df.sequence.apply(len)
        df_2A3 = df.loc[df.experiment_type=='2A3_MaP']
        df_DMS = df.loc[df.experiment_type=='DMS_MaP']
        
        split = list(KFold(n_splits=nfolds, random_state=seed, shuffle=True).split(df_2A3)
                    )[fold][0 if mode=='train' else 1]
        df_2A3 = df_2A3.iloc[split].reset_index(drop=True)
        df_DMS = df_DMS.iloc[split].reset_index(drop=True)
        
        if mode != 'train' or sn_train:
            m = (df_2A3['SN_filter'].values > 0) & (df_DMS['SN_filter'].values > 0)
            df_2A3 = df_2A3.loc[m].reset_index(drop=True)
            df_DMS = df_DMS.loc[m].reset_index(drop=True)
        
        self.seq = df_2A3['sequence'].values
        self.L = df_2A3['L'].values
        
        self.react_2A3 = df_2A3[[c for c in df_2A3.columns if 'reactivity_0' in c]].values
        self.react_DMS = df_DMS[[c for c in df_DMS.columns if 'reactivity_0' in c]].values
        self.react_err_2A3 = df_2A3[[c for c in df_2A3.columns if 'reactivity_error_0' in c]].values
        self.react_err_DMS = df_DMS[[c for c in df_DMS.columns if 'reactivity_error_0' in c]].values
        self.sn_2A3 = df_2A3['signal_to_noise'].values
        self.sn_DMS = df_DMS['signal_to_noise'].values
        self.mask_only = mask_only
        
    def __len__(self):
        return len(self.seq)  
    
    def __getitem__(self, idx):
        seq = self.seq[idx]
        if self.mask_only:
            mask = torch.zeros(self.Lmax, dtype=torch.bool)
            mask[:len(seq)] = True
            return {'mask':mask},{'mask':mask}
        seq = [self.seq_map[s] for s in seq]
        seq = np.array(seq)
        mask = torch.zeros(self.Lmax, dtype=torch.bool)
        mask[:len(seq)] = True
        seq = np.pad(seq,(0,self.Lmax-len(seq)))
        
        react = torch.from_numpy(np.stack([self.react_2A3[idx],self.react_DMS[idx]],-1))
        react_err = torch.from_numpy(np.stack([self.react_err_2A3[idx],self.react_err_DMS[idx]],-1))
        sn = torch.FloatTensor([self.sn_2A3[idx],self.sn_DMS[idx]])
        
        return {'seq':torch.from_numpy(seq), 'mask':mask}, \
               {'react':react, 'react_err':react_err,
                'sn':sn, 'mask':mask}
               
               
class RNA_DatasetBaselineSplit(Dataset):
    def __init__(self, df, mode='train', seed=2023, fold=0, nfolds=4, mask_only=False, 
                 sn_train=True, **kwargs):
        self.seq_map = {'A':0,'C':1,'G':2,'U':3}
        self.Lmax = 206
        df['L'] = df.sequence.apply(len)
        df_2A3 = df.loc[df.experiment_type=='2A3_MaP'].reset_index(drop=True)
        df_DMS = df.loc[df.experiment_type=='DMS_MaP'].reset_index(drop=True)
        
        if mode != 'train' or sn_train:
            m = (df_2A3['SN_filter'].values > 0) & (df_DMS['SN_filter'].values > 0)
            df_2A3 = df_2A3.loc[m].reset_index(drop=True)
            df_DMS = df_DMS.loc[m].reset_index(drop=True)
        
        self.seq = df_2A3['sequence'].values
        self.L = df_2A3['L'].values
        
        self.react_2A3 = df_2A3[[c for c in df_2A3.columns if 'reactivity_0' in c]].values
        self.react_DMS = df_DMS[[c for c in df_DMS.columns if 'reactivity_0' in c]].values
        self.react_err_2A3 = df_2A3[[c for c in df_2A3.columns if 'reactivity_error_0' in c]].values
        self.react_err_DMS = df_DMS[[c for c in df_DMS.columns if 'reactivity_error_0' in c]].values
        self.sn_2A3 = df_2A3['signal_to_noise'].values
        self.sn_DMS = df_DMS['signal_to_noise'].values
        self.mask_only = mask_only
        
    def __len__(self):
        return len(self.seq)  
    
    def __getitem__(self, idx):
        seq = self.seq[idx]
        if self.mask_only:
            mask = torch.zeros(self.Lmax, dtype=torch.bool)
            mask[:len(seq)] = True
            return {'mask':mask},{'mask':mask}
        seq = [self.seq_map[s] for s in seq]
        seq = np.array(seq)
        mask = torch.zeros(self.Lmax, dtype=torch.bool)
        mask[:len(seq)] = True
        seq = np.pad(seq,(0,self.Lmax-len(seq)))
        
        react = torch.from_numpy(np.stack([self.react_2A3[idx],self.react_DMS[idx]],-1))
        react_err = torch.from_numpy(np.stack([self.react_err_2A3[idx],self.react_err_DMS[idx]],-1))
        sn = torch.FloatTensor([self.sn_2A3[idx],self.sn_DMS[idx]])
        
        return {'seq':torch.from_numpy(seq), 'mask':mask}, \
               {'react':react, 'react_err':react_err,
                'sn':sn, 'mask':mask}

class RNA_DatasetBaseline(Dataset):
    def __init__(self, df, mode='train', seed=2023, fold=0, nfolds=4, mask_only=False, 
                 sn_train=True, **kwargs):
        self.seq_map = {'A':0,'C':1,'G':2,'U':3}
        self.Lmax = 206
        df['L'] = df.sequence.apply(len)
        df_2A3 = df.loc[df.experiment_type=='2A3_MaP']
        df_DMS = df.loc[df.experiment_type=='DMS_MaP']
        
        split = list(KFold(n_splits=nfolds, random_state=seed, shuffle=True).split(df_2A3)
                    )[fold][0 if mode=='train' else 1]
        df_2A3 = df_2A3.iloc[split].reset_index(drop=True)
        df_DMS = df_DMS.iloc[split].reset_index(drop=True)
        
        if mode != 'train' or sn_train:
            m = (df_2A3['SN_filter'].values > 0) & (df_DMS['SN_filter'].values > 0)
            df_2A3 = df_2A3.loc[m].reset_index(drop=True)
            df_DMS = df_DMS.loc[m].reset_index(drop=True)
        
        self.seq = df_2A3['sequence'].values
        self.L = df_2A3['L'].values
        
        self.react_2A3 = df_2A3[[c for c in df_2A3.columns if 'reactivity_0' in c]].values
        self.react_DMS = df_DMS[[c for c in df_DMS.columns if 'reactivity_0' in c]].values
        self.react_err_2A3 = df_2A3[[c for c in df_2A3.columns if 'reactivity_error_0' in c]].values
        self.react_err_DMS = df_DMS[[c for c in df_DMS.columns if 'reactivity_error_0' in c]].values
        self.sn_2A3 = df_2A3['signal_to_noise'].values
        self.sn_DMS = df_DMS['signal_to_noise'].values
        self.mask_only = mask_only
        
    def __len__(self):
        return len(self.seq)  
    
    def __getitem__(self, idx):
        seq = self.seq[idx]
        if self.mask_only:
            mask = torch.zeros(self.Lmax, dtype=torch.bool)
            mask[:len(seq)] = True
            return {'mask':mask},{'mask':mask}
        seq = [self.seq_map[s] for s in seq]
        seq = np.array(seq)
        mask = torch.zeros(self.Lmax, dtype=torch.bool)
        mask[:len(seq)] = True
        seq = np.pad(seq,(0,self.Lmax-len(seq)))
        
        react = torch.from_numpy(np.stack([self.react_2A3[idx],self.react_DMS[idx]],-1))
        react_err = torch.from_numpy(np.stack([self.react_err_2A3[idx],self.react_err_DMS[idx]],-1))
        sn = torch.FloatTensor([self.sn_2A3[idx],self.sn_DMS[idx]])
        
        return {'seq':torch.from_numpy(seq), 'mask':mask}, \
               {'react':react, 'react_err':react_err,
                'sn':sn, 'mask':mask}
               
class RNA_DatasetV0(Dataset):
    def __init__(self, df, mask_only=False,prob_for_adj = 0.5 ,**kwargs):

        self.seq_map = {'A':0,'C':1,'G':2,'U':3}
        self.Lmax = 206
        self.prob_for_adj = prob_for_adj
        df['L'] = df.sequence.apply(len)
        df_2A3 = df.loc[df.experiment_type=='2A3_MaP'].reset_index(drop=True)
        df_DMS = df.loc[df.experiment_type=='DMS_MaP'].reset_index(drop=True)


        self.seq = df_2A3['sequence'].values
        self.L = df_2A3['L'].values
        
        self.react_2A3 = df_2A3[[c for c in df_2A3.columns if \
                                 'reactivity_0' in c]].values
        self.react_DMS = df_DMS[[c for c in df_DMS.columns if \
                                 'reactivity_0' in c]].values
        self.react_err_2A3 = df_2A3[[c for c in df_2A3.columns if \
                                 'reactivity_error_0' in c]].values
        self.react_err_DMS = df_DMS[[c for c in df_DMS.columns if \
                                'reactivity_error_0' in c]].values
        self.sn_2A3 = df_2A3['signal_to_noise'].values
        self.sn_DMS = df_DMS['signal_to_noise'].values
        self.bpp = df_2A3['bpp'].values
        self.mask_only = mask_only
        
    def __len__(self):
        return len(self.seq)  
    
    def __getitem__(self, idx):
        seq = self.seq[idx]
        if self.mask_only:
            mask = torch.zeros(self.Lmax, dtype=torch.bool)
            mask[:len(seq)] = True
            return {'mask':mask},{'mask':mask}
        adj_matrix = generate_adj_matrix(self.bpp[idx], self.Lmax, self.prob_for_adj)
        seq = [self.seq_map[s] for s in seq]
        seq = np.array(seq)
        mask = torch.zeros(self.Lmax, dtype=torch.bool)
        mask[:len(seq)] = True
        seq = np.pad(seq,(0,self.Lmax-len(seq)))
        
        react = torch.from_numpy(np.stack([self.react_2A3[idx],
                                           self.react_DMS[idx]],-1))
        react_err = torch.from_numpy(np.stack([self.react_err_2A3[idx],
                                               self.react_err_DMS[idx]],-1))
        return {"seq": torch.from_numpy(seq), "mask": mask, "adj_matrix": adj_matrix}, {
            "react": react,
            "react_err": react_err,
            "mask": mask,
        }
        
        
class RNA_DatasetV1(Dataset):
    #same as v0 but not adj matrix
    def __init__(self, df, mask_only=False,**kwargs):

        self.seq_map = {'A':0,'C':1,'G':2,'U':3}
        self.Lmax = 206
        df['L'] = df.sequence.apply(len)
        df_2A3 = df.loc[df.experiment_type=='2A3_MaP'].reset_index(drop=True)
        df_DMS = df.loc[df.experiment_type=='DMS_MaP'].reset_index(drop=True)


        self.seq = df_2A3['sequence'].values
        self.L = df_2A3['L'].values
        
        self.react_2A3 = df_2A3[[c for c in df_2A3.columns if \
                                 'reactivity_0' in c]].values
        self.react_DMS = df_DMS[[c for c in df_DMS.columns if \
                                 'reactivity_0' in c]].values
        self.react_err_2A3 = df_2A3[[c for c in df_2A3.columns if \
                                 'reactivity_error_0' in c]].values
        self.react_err_DMS = df_DMS[[c for c in df_DMS.columns if \
                                'reactivity_error_0' in c]].values
        self.sn_2A3 = df_2A3['signal_to_noise'].values
        self.sn_DMS = df_DMS['signal_to_noise'].values
        self.bpp = df_2A3['bpp'].values
        self.mask_only = mask_only
        
    def __len__(self):
        return len(self.seq)  
    
    def __getitem__(self, idx):
        seq = self.seq[idx]
        if self.mask_only:
            mask = torch.zeros(self.Lmax, dtype=torch.bool)
            mask[:len(seq)] = True
            return {'mask':mask},{'mask':mask}
        seq = [self.seq_map[s] for s in seq]
        seq = np.array(seq)
        mask = torch.zeros(self.Lmax, dtype=torch.bool)
        mask[:len(seq)] = True
        seq = np.pad(seq,(0,self.Lmax-len(seq)))
        
        react = torch.from_numpy(np.stack([self.react_2A3[idx],
                                           self.react_DMS[idx]],-1))
        react_err = torch.from_numpy(np.stack([self.react_err_2A3[idx],
                                               self.react_err_DMS[idx]],-1))
        return {"seq": torch.from_numpy(seq), "mask": mask}, {
            "react": react,
            "react_err": react_err,
            "mask": mask,
        }
        
        



class RNA_DatasetV0G(Dataset):
    def __init__(self, df, path_to_bpp_folder, mask_only=False, **kwargs):

        self.seq_map = {'A':0,'C':1,'G':2,'U':3}
        self.Lmax = 206
        df['L'] = df.sequence.apply(len)
        df_2A3 = df.loc[df.experiment_type=='2A3_MaP'].reset_index(drop=True)
        df_DMS = df.loc[df.experiment_type=='DMS_MaP'].reset_index(drop=True)


        self.seq = df_2A3['sequence'].values
        self.L = df_2A3['L'].values
        
        self.react_2A3 = df_2A3[[c for c in df_2A3.columns if \
                                 'reactivity_0' in c]].values
        self.react_DMS = df_DMS[[c for c in df_DMS.columns if \
                                 'reactivity_0' in c]].values
        self.react_err_2A3 = df_2A3[[c for c in df_2A3.columns if \
                                 'reactivity_error_0' in c]].values
        self.react_err_DMS = df_DMS[[c for c in df_DMS.columns if \
                                'reactivity_error_0' in c]].values
        self.sn_2A3 = df_2A3['signal_to_noise'].values
        self.sn_DMS = df_DMS['signal_to_noise'].values
        self.bpp = df_2A3['bpp'].values
        self.mask_only = mask_only
        
    def __len__(self):
        return len(self.seq)  
    
    def __getitem__(self, idx):
        seq = self.seq[idx]
        if self.mask_only:
            mask = torch.zeros(self.Lmax, dtype=torch.bool)
            mask[:len(seq)] = True
            return {'mask':mask},{'mask':mask}
        edge_index, edge_features = generate_edge_data(self.bpp[idx])
        seq = [self.seq_map[s] for s in seq]
        seq = np.array(seq)

        
        react = torch.from_numpy(np.stack([self.react_2A3[idx],
                                           self.react_DMS[idx]],-1))
        react_err = torch.from_numpy(np.stack([self.react_err_2A3[idx],
                                               self.react_err_DMS[idx]],-1))
        return Data(x=torch.from_numpy(seq), edge_index=edge_index, edge_features= edge_features, y=react, y_err=react_err)
    
    

class LenMatchBatchSampler(torch.utils.data.BatchSampler):
    def __iter__(self):
        buckets = [[]] * 100
        yielded = 0

        for idx in self.sampler:
            s = self.sampler.data_source[idx]
            if isinstance(s, tuple):
                L = s[0]["mask"].sum()
            else:
                L = s["mask"].sum()
            L = max(1, L // 16)
            if len(buckets[L]) == 0:
                buckets[L] = []
            buckets[L].append(idx)

            if len(buckets[L]) == self.batch_size:
                batch = list(buckets[L])
                yield batch
                yielded += 1
                buckets[L] = []

        batch = []
        leftover = [idx for bucket in buckets for idx in bucket]

        for idx in leftover:
            batch.append(idx)
            if len(batch) == self.batch_size:
                yielded += 1
                yield batch
                batch = []

        if len(batch) > 0 and not self.drop_last:
            yielded += 1
            yield batch
            

            
def generate_base_pair_matrix(file_path, L):
    """
    Reads a TXT file of base pair probabilities and generates an n x n matrix.
    
    Args:
    - file_path (str): Path to the TXT file.
    
    Returns:
    - np.array: An n x n matrix of base pair probabilities.
    """
    # Read the data using pandas
    data = pd.read_csv(file_path, sep=" ", header=None, names=["pos1", "pos2", "prob"])
    
    # Find the largest position in the 'pos1' column
    largest_position = data['pos1'].max()
    
    ids = torch.from_numpy(data[['pos1','pos2']].values)
    matrix = torch.zeros((L, L))
    matrix[ids[:,0]-1,ids[:,1]-1] = torch.from_numpy(data['prob'].values).float()
    matrix[ids[:,1]-1,ids[:,0]-1] = torch.from_numpy(data['prob'].values).float()
    

    matrix[:26, :] = 0
    matrix[:, :26] = 0
    
    # Adjust the end based on the largest_position and set the last 21 positions to 0
    adjusted_end = largest_position - 21
    matrix[adjusted_end:, :] = 0
    matrix[:, adjusted_end:] = 0
    
    return matrix
               
class RNA_DatasetBaselineSplitbppV0(Dataset):
    def __init__(self, df, mode='train', seed=2023, fold=0, nfolds=4, mask_only=False, 
                 sn_train=True, **kwargs):
        self.seq_map = {'A':0,'C':1,'G':2,'U':3}
        self.Lmax = 206
        df['L'] = df.sequence.apply(len)
        df_2A3 = df.loc[df.experiment_type=='2A3_MaP'].reset_index(drop=True)
        df_DMS = df.loc[df.experiment_type=='DMS_MaP'].reset_index(drop=True)
        
        if mode != 'train' or sn_train:
            m = (df_2A3['SN_filter'].values > 0) & (df_DMS['SN_filter'].values > 0)
            df_2A3 = df_2A3.loc[m].reset_index(drop=True)
            df_DMS = df_DMS.loc[m].reset_index(drop=True)
        
        self.seq = df_2A3['sequence'].values
        self.bpp = df_2A3['bpp'].values
        self.L = df_2A3['L'].values
        self.react_2A3 = df_2A3[[c for c in df_2A3.columns if 'reactivity_0' in c]].values
        self.react_DMS = df_DMS[[c for c in df_DMS.columns if 'reactivity_0' in c]].values
        self.react_err_2A3 = df_2A3[[c for c in df_2A3.columns if 'reactivity_error_0' in c]].values
        self.react_err_DMS = df_DMS[[c for c in df_DMS.columns if 'reactivity_error_0' in c]].values
        self.sn_2A3 = df_2A3['signal_to_noise'].values
        self.sn_DMS = df_DMS['signal_to_noise'].values
        self.mask_only = mask_only
        
    def __len__(self):
        return len(self.seq)  
    
    def __getitem__(self, idx):
        seq = self.seq[idx]
        if self.mask_only:
            mask = torch.zeros(self.Lmax, dtype=torch.bool)
            mask[:len(seq)] = True
            return {'mask':mask},{'mask':mask}
        seq = [self.seq_map[s] for s in seq]
        seq = np.array(seq)
        mask = torch.zeros(self.Lmax, dtype=torch.bool)
        mask[:len(seq)] = True
        seq = np.pad(seq,(0,self.Lmax-len(seq)))
        bpp = (generate_base_pair_matrix(self.bpp[idx], self.Lmax) > 0.5).int()
        
        react = torch.from_numpy(np.stack([self.react_2A3[idx],self.react_DMS[idx]],-1))
        react_err = torch.from_numpy(np.stack([self.react_err_2A3[idx],self.react_err_DMS[idx]],-1))
        sn = torch.FloatTensor([self.sn_2A3[idx],self.sn_DMS[idx]])
        
        return {'seq':torch.from_numpy(seq), 'mask':mask, "adj_matrix": bpp}, \
               {'react':react, 'react_err':react_err,
                'sn':sn, 'mask':mask}
               
def dot_to_adjacency(dot_notation, n):
    adjacency_matrix = np.zeros((n, n), dtype=int)
    dot_notation = (26 * '.') + dot_notation + (21 * '.')
    stack = []
    for i, char in enumerate(dot_notation):
        if char == '(':
            stack.append(i)
        elif char == ')':
            j = stack.pop()
            adjacency_matrix[i][j] = adjacency_matrix[j][i] = 1
            
    return adjacency_matrix
               
class RNA_DatasetBaselineSplitssV0(Dataset):
    def __init__(self, df, mode='train', seed=2023, fold=0, nfolds=4, mask_only=False, 
                 sn_train=True, **kwargs):
        """
        short sequence without adapters 
        """
        self.seq_map = {'A':0,'C':1,'G':2,'U':3}
        self.Lmax = 206
        df['L'] = df.sequence.apply(len)
        df_2A3 = df.loc[df.experiment_type=='2A3_MaP'].reset_index(drop=True)
        df_DMS = df.loc[df.experiment_type=='DMS_MaP'].reset_index(drop=True)
        
        if mode != 'train' or sn_train:
            m = (df_2A3['SN_filter'].values > 0) & (df_DMS['SN_filter'].values > 0)
            df_2A3 = df_2A3.loc[m].reset_index(drop=True)
            df_DMS = df_DMS.loc[m].reset_index(drop=True)
        
        self.seq = df_2A3['sequence'].values
        self.ss = df_2A3['ss_roi'].values
        self.L = df_2A3['L'].values
        self.react_2A3 = df_2A3[[c for c in df_2A3.columns if 'reactivity_0' in c]].values
        self.react_DMS = df_DMS[[c for c in df_DMS.columns if 'reactivity_0' in c]].values
        self.react_err_2A3 = df_2A3[[c for c in df_2A3.columns if 'reactivity_error_0' in c]].values
        self.react_err_DMS = df_DMS[[c for c in df_DMS.columns if 'reactivity_error_0' in c]].values
        self.sn_2A3 = df_2A3['signal_to_noise'].values
        self.sn_DMS = df_DMS['signal_to_noise'].values
        self.mask_only = mask_only
        
    def __len__(self):
        return len(self.seq)  
    
    def __getitem__(self, idx):
        seq = self.seq[idx]
        if self.mask_only:
            mask = torch.zeros(self.Lmax, dtype=torch.bool)
            mask[:len(seq)] = True
            return {'mask':mask},{'mask':mask}
        seq = [self.seq_map[s] for s in seq]
        seq = np.array(seq)
        mask = torch.zeros(self.Lmax, dtype=torch.bool)
        mask[:len(seq)] = True
        seq = np.pad(seq,(0,self.Lmax-len(seq)))
        bpp = torch.tensor(dot_to_adjacency(self.ss[idx], self.Lmax)).int()
        
        react = torch.from_numpy(np.stack([self.react_2A3[idx],self.react_DMS[idx]],-1))
        react_err = torch.from_numpy(np.stack([self.react_err_2A3[idx],self.react_err_DMS[idx]],-1))
        sn = torch.FloatTensor([self.sn_2A3[idx],self.sn_DMS[idx]])
        
        return {'seq':torch.from_numpy(seq), 'mask':mask, "adj_matrix": bpp}, \
               {'react':react, 'react_err':react_err,
                'sn':sn, 'mask':mask}


# %% ../nbs/00_dataset.ipynb 9
class RNA_Dataset_Test(Dataset):
    def __init__(self, df, mask_only=False, **kwargs):
        self.seq_map = {'A':0,'C':1,'G':2,'U':3}
        df['L'] = df.sequence.apply(len)
        self.Lmax = df['L'].max()
        self.df = df
        self.mask_only = mask_only
        
    def __len__(self):
        return len(self.df)  
    
    def __getitem__(self, idx):
        id_min, id_max, seq = self.df.loc[idx, ['id_min','id_max','sequence']]
        mask = torch.zeros(self.Lmax, dtype=torch.bool)
        L = len(seq)
        mask[:L] = True
        if self.mask_only: return {'mask':mask},{}
        ids = np.arange(id_min,id_max+1)
        
        seq = [self.seq_map[s] for s in seq]
        seq = np.array(seq)
        seq = np.pad(seq,(0,self.Lmax-L))
        ids = np.pad(ids,(0,self.Lmax-L), constant_values=-1)
        
        return {'seq':torch.from_numpy(seq), 'mask':mask}, \
               {'ids':ids}
               
               
class RNA_Dataset_TestBpp(Dataset):
    def __init__(self, df, mask_only=False, **kwargs):
        self.seq_map = {'A':0,'C':1,'G':2,'U':3}
        df['L'] = df.sequence.apply(len)
        self.Lmax = df['L'].max()
        self.df = df
        self.mask_only = mask_only
        
    def __len__(self):
        return len(self.df)  
    
    def __getitem__(self, idx):
        id_min, id_max, seq = self.df.loc[idx, ['id_min','id_max','sequence']]
        mask = torch.zeros(self.Lmax, dtype=torch.bool)
        L = len(seq)
        mask[:L] = True
        if self.mask_only: return {'mask':mask},{}
        ids = np.arange(id_min,id_max+1)    
        seq = [self.seq_map[s] for s in seq]
        seq = np.array(seq)
        seq = np.pad(seq,(0,self.Lmax-L))
        ids = np.pad(ids,(0,self.Lmax-L), constant_values=-1)
        bpp = self.df['bpp'][idx]
        bpp = (generate_base_pair_matrix(bpp, self.Lmax) > 0.5).int()
        
        return {'seq':torch.from_numpy(seq), 'mask':mask,  "adj_matrix": bpp}, \
               {'ids':ids}

