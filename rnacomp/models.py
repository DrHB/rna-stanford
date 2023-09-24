# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_models.ipynb.

# %% auto 0
__all__ = ['List', 'exists', 'default', 'PreNorm', 'Residual', 'GatedResidual', 'Attention', 'FeedForward',
           'GraphTransformerAdjacent', 'full_attention_conv', 'gcn_conv', 'DIFFormerConv', 'DIFFormer',
           'to_graph_batch', 'DifformerCustomV0', 'DropPath', 'Mlp', 'RotaryEmbedding', 'rotate_half',
           'apply_rotary_pos_emb', 'Conv1D', 'ResBlock', 'Extractor', 'Block', 'Block_conv', 'RNA_ModelV2',
           'CustomTransformerV0', 'CustomTransformerV1', 'GAT', 'to_graph_batchv1', 'PytorchBatchWrapper',
           'RNA_ModelV3', 'GCN', 'LayerNorm', 'GEGLU', 'FeedForwardV0', 'RNA_ModelV4', 'RNA_ModelV5', 'RNA_ModelV6',
           'RNA_ModelV7']

# %% ../nbs/01_models.ipynb 1
import torch
from torch import nn, einsum
from einops import rearrange, repeat
from rotary_embedding_torch import RotaryEmbedding, apply_rotary_emb

import torch.nn.functional as F
import torch.utils.checkpoint as checkpoint
import math
from timm.models.layers import drop_path, to_2tuple, trunc_normal_
from torch_sparse import SparseTensor, matmul
from torch_geometric.utils import degree
from torch_geometric.data import Data, Batch
import numpy as np
from torch_geometric.utils import to_dense_batch
from x_transformers import ContinuousTransformerWrapper, Encoder, TransformerWrapper
from torch_geometric.nn import GATConv, GCNConv

# %% ../nbs/01_models.ipynb 2
def exists(val):
    return val is not None

def default(val, d):
    return val if exists(val) else d

List = nn.ModuleList

# normalizations

class PreNorm(nn.Module):
    def __init__(
        self,
        dim,
        fn
    ):
        super().__init__()
        self.fn = fn
        self.norm = nn.LayerNorm(dim)

    def forward(self, x, *args, **kwargs):
        x = self.norm(x)
        return self.fn(x, *args,**kwargs)

# gated residual

class Residual(nn.Module):
    def forward(self, x, res):
        return x + res

class GatedResidual(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.proj = nn.Sequential(
            nn.Linear(dim * 3, 1, bias = False),
            nn.Sigmoid()
        )

    def forward(self, x, res):
        gate_input = torch.cat((x, res, x - res), dim = -1)
        gate = self.proj(gate_input)
        return x * gate + res * (1 - gate)

# attention

class Attention(nn.Module):
    def __init__(
        self,
        dim,
        pos_emb = None,
        dim_head = 64,
        heads = 8,
        edge_dim = None
    ):
        super().__init__()
        edge_dim = default(edge_dim, dim)

        inner_dim = dim_head * heads
        self.heads = heads
        self.scale = dim_head ** -0.5

        self.pos_emb = pos_emb

        self.to_q = nn.Linear(dim, inner_dim)
        self.to_kv = nn.Linear(dim, inner_dim * 2)
        self.edges_to_kv = nn.Linear(edge_dim, inner_dim)

        self.to_out = nn.Linear(inner_dim, dim)

    def forward(self, nodes, edges, mask = None):
        h = self.heads

        q = self.to_q(nodes)
        k, v = self.to_kv(nodes).chunk(2, dim = -1)

        e_kv = self.edges_to_kv(edges)

        q, k, v, e_kv = map(lambda t: rearrange(t, 'b ... (h d) -> (b h) ... d', h = h), (q, k, v, e_kv))

        if exists(self.pos_emb):
            freqs = self.pos_emb(torch.arange(nodes.shape[1], device = nodes.device))
            freqs = rearrange(freqs, 'n d -> () n d')
            q = apply_rotary_emb(freqs, q)
            k = apply_rotary_emb(freqs, k)

        ek, ev = e_kv, e_kv

        k, v = map(lambda t: rearrange(t, 'b j d -> b () j d '), (k, v))
        k = k + ek
        v = v + ev

        sim = einsum('b i d, b i j d -> b i j', q, k) * self.scale

        if exists(mask):
            mask = rearrange(mask, 'b i -> b i ()') & rearrange(mask, 'b j -> b () j')
            mask = repeat(mask, 'b i j -> (b h) i j', h = h)
            max_neg_value = -torch.finfo(sim.dtype).max
            sim.masked_fill_(~mask, max_neg_value)

        attn = sim.softmax(dim = -1)
        out = einsum('b i j, b i j d -> b i d', attn, v)
        out = rearrange(out, '(b h) n d -> b n (h d)', h = h)
        return self.to_out(out)

# optional feedforward

def FeedForward(dim, ff_mult = 4):
    return nn.Sequential(
        nn.Linear(dim, dim * ff_mult),
        nn.GELU(),
        nn.Linear(dim * ff_mult, dim)
    )


# classes

class GraphTransformerAdjacent(nn.Module):
    def __init__(
        self,
        dim,
        depth,
        edge_dim = 16,
        dim_head = 32,
        heads = 8,
        with_feedforwards = False,
        rel_pos_emb = False,
        accept_adjacency_matrix = True,
    ):
        super().__init__()
        self.layers = List([])
        edge_dim = default(edge_dim, dim)


        pos_emb = RotaryEmbedding(dim_head) if rel_pos_emb else None

        for _ in range(depth):
            self.layers.append(List([
                List([
                    PreNorm(dim, Attention(dim, pos_emb = pos_emb, edge_dim = edge_dim, dim_head = dim_head, heads = heads)),
                    GatedResidual(dim)
                ]),
                List([
                    PreNorm(dim, FeedForward(dim)),
                    GatedResidual(dim)
                ]) if with_feedforwards else None
            ]))
            

    def forward(
        self,
        nodes,
        mask, 
        adj_mat,
    ):  
        
        edges = None
        batch, seq, _ = nodes.shape
        all_edges = default(edges, 0) + default(adj_mat, 0)

        for attn_block, ff_block in self.layers:
            attn, attn_residual = attn_block
            nodes = attn_residual(attn(nodes, all_edges, mask = mask), nodes)

            if exists(ff_block):
                ff, ff_residual = ff_block
                nodes = ff_residual(ff(nodes), nodes)
        return nodes
    
    




def full_attention_conv(qs, ks, vs, kernel, output_attn=False):
    '''
    qs: query tensor [N, H, M]
    ks: key tensor [L, H, M]
    vs: value tensor [L, H, D]

    return output [N, H, D]
    '''
    if kernel == 'simple':
        # normalize input
        qs = qs / torch.norm(qs, p=2) # [N, H, M]
        ks = ks / torch.norm(ks, p=2) # [L, H, M]
        N = qs.shape[0]

        # numerator
        kvs = torch.einsum("lhm,lhd->hmd", ks, vs)
        attention_num = torch.einsum("nhm,hmd->nhd", qs, kvs) # [N, H, D]
        all_ones = torch.ones([vs.shape[0]]).to(vs.device)
        vs_sum = torch.einsum("l,lhd->hd", all_ones, vs) # [H, D]
        attention_num += vs_sum.unsqueeze(0).repeat(vs.shape[0], 1, 1) # [N, H, D]

        # denominator
        all_ones = torch.ones([ks.shape[0]]).to(ks.device)
        ks_sum = torch.einsum("lhm,l->hm", ks, all_ones)
        attention_normalizer = torch.einsum("nhm,hm->nh", qs, ks_sum)  # [N, H]

        # attentive aggregated results
        attention_normalizer = torch.unsqueeze(attention_normalizer, len(attention_normalizer.shape))  # [N, H, 1]
        attention_normalizer += torch.ones_like(attention_normalizer) * N
        attn_output = attention_num / attention_normalizer # [N, H, D]

        # compute attention for visualization if needed
        if output_attn:
            attention = torch.einsum("nhm,lhm->nlh", qs, ks) / attention_normalizer # [N, L, H]

    elif kernel == 'sigmoid':
        # numerator
        attention_num = torch.sigmoid(torch.einsum("nhm,lhm->nlh", qs, ks))  # [N, L, H]

        # denominator
        all_ones = torch.ones([ks.shape[0]]).to(ks.device)
        attention_normalizer = torch.einsum("nlh,l->nh", attention_num, all_ones)
        attention_normalizer = attention_normalizer.unsqueeze(1).repeat(1, ks.shape[0], 1)  # [N, L, H]

        # compute attention and attentive aggregated results
        attention = attention_num / attention_normalizer
        attn_output = torch.einsum("nlh,lhd->nhd", attention, vs)  # [N, H, D]

    if output_attn:
        return attn_output, attention
    else:
        return attn_output

def gcn_conv(x, edge_index, edge_weight):
    N, H = x.shape[0], x.shape[1]
    row, col = edge_index
    d = degree(col, N).float()
    d_norm_in = (1. / d[col]).sqrt()
    d_norm_out = (1. / d[row]).sqrt()
    gcn_conv_output = []
    if edge_weight is None:
        value = torch.ones_like(row) * d_norm_in * d_norm_out
    else:
        value = edge_weight * d_norm_in * d_norm_out
    value = torch.nan_to_num(value, nan=0.0, posinf=0.0, neginf=0.0)
    adj = SparseTensor(row=col, col=row, value=value, sparse_sizes=(N, N))
    for i in range(x.shape[1]):
        gcn_conv_output.append( matmul(adj, x[:, i]) )  # [N, D]
    gcn_conv_output = torch.stack(gcn_conv_output, dim=1) # [N, H, D]
    return gcn_conv_output

class DIFFormerConv(nn.Module):
    '''
    one DIFFormer layer
    '''
    def __init__(self, in_channels,
               out_channels,
               num_heads,
               kernel='simple',
               use_graph=True,
               use_weight=True):
        super(DIFFormerConv, self).__init__()
        self.Wk = nn.Linear(in_channels, out_channels * num_heads)
        self.Wq = nn.Linear(in_channels, out_channels * num_heads)
        if use_weight:
            self.Wv = nn.Linear(in_channels, out_channels * num_heads)

        self.out_channels = out_channels
        self.num_heads = num_heads
        self.kernel = kernel
        self.use_graph = use_graph
        self.use_weight = use_weight

    def reset_parameters(self):
        self.Wk.reset_parameters()
        self.Wq.reset_parameters()
        if self.use_weight:
            self.Wv.reset_parameters()

    def forward(self, query_input, source_input, edge_index=None, edge_weight=None, output_attn=False):
        # feature transformation
        query = self.Wq(query_input).reshape(-1, self.num_heads, self.out_channels)
        key = self.Wk(source_input).reshape(-1, self.num_heads, self.out_channels)
        if self.use_weight:
            value = self.Wv(source_input).reshape(-1, self.num_heads, self.out_channels)
        else:
            value = source_input.reshape(-1, 1, self.out_channels)

        # compute full attentive aggregation
        if output_attn:
            attention_output, attn = full_attention_conv(query, key, value, self.kernel, output_attn)  # [N, H, D]
        else:
            attention_output = full_attention_conv(query,key,value,self.kernel) # [N, H, D]

        # use input graph for gcn conv
        if self.use_graph:
            final_output = attention_output + gcn_conv(value, edge_index, edge_weight)
        else:
            final_output = attention_output
        final_output = final_output.mean(dim=1)

        if output_attn:
            return final_output, attn
        else:
            return final_output

class DIFFormer(nn.Module):
    '''
    DIFFormer model class
    x: input node features [N, D]
    edge_index: 2-dim indices of edges [2, E]
    return y_hat predicted logits [N, C]
    '''
    def __init__(self, in_channels, hidden_channels, out_channels, num_layers=2, num_heads=1, kernel='simple',
                 alpha=0.5, dropout=0.5, use_bn=True, use_residual=True, use_weight=True, use_graph=True):
        super(DIFFormer, self).__init__()

        self.convs = nn.ModuleList()
        self.fcs = nn.ModuleList()
        self.fcs.append(nn.Linear(in_channels, hidden_channels))
        self.bns = nn.ModuleList()
        self.bns.append(nn.LayerNorm(hidden_channels))
        for i in range(num_layers):
            self.convs.append(
                DIFFormerConv(hidden_channels, hidden_channels, num_heads=num_heads, kernel=kernel, use_graph=use_graph, use_weight=use_weight))
            self.bns.append(nn.LayerNorm(hidden_channels))

        self.fcs.append(nn.Linear(hidden_channels, out_channels))

        self.dropout = dropout
        self.activation = F.relu
        self.use_bn = use_bn
        self.residual = use_residual
        self.alpha = alpha

    def reset_parameters(self):
        for conv in self.convs:
            conv.reset_parameters()
        for bn in self.bns:
            bn.reset_parameters()
        for fc in self.fcs:
            fc.reset_parameters()

    def forward(self, x, edge_index, edge_weight=None):
        layer_ = []

        # input MLP layer
        x = self.fcs[0](x)
        if self.use_bn:
            x = self.bns[0](x)
        x = self.activation(x)
        x = F.dropout(x, p=self.dropout, training=self.training)

        # store as residual link
        layer_.append(x)

        for i, conv in enumerate(self.convs):
            # graph convolution with DIFFormer layer
            x = conv(x, x, edge_index, edge_weight)
            if self.residual:
                x = self.alpha * x + (1-self.alpha) * layer_[i]
            if self.use_bn:
                x = self.bns[i+1](x)
            x = F.dropout(x, p=self.dropout, training=self.training)
            layer_.append(x)

        # output MLP layer
        x_out = self.fcs[-1](x)
        return x_out

    def get_attentions(self, x):
        layer_, attentions = [], []
        x = self.fcs[0](x)
        if self.use_bn:
            x = self.bns[0](x)
        x = self.activation(x)
        layer_.append(x)
        for i, conv in enumerate(self.convs):
            x, attn = conv(x, x, output_attn=True)
            attentions.append(attn)
            if self.residual:
                x = self.alpha * x + (1 - self.alpha) * layer_[i]
            if self.use_bn:
                x = self.bns[i + 1](x)
            layer_.append(x)
        return torch.stack(attentions, dim=0) # [layer num, N, N]

def to_graph_batch(batch):
    res = []
    seq = batch["seq"]
    mask = batch["mask"]
    adj_matrix = batch["adj_matrix"]
    for i in range(len(seq)):
        res.append(Data(x=seq[i][mask[i]], edge_index=adj_matrix[i].nonzero().T))
    return Batch.from_data_list(res)

class DifformerCustomV0(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, num_layers=2, num_heads=1):
        super().__init__()
        self.encoder = DIFFormer(in_channels, hidden_channels, out_channels, num_layers=num_layers, num_heads=num_heads)
        
    def forward(self, x):
        x  = to_graph_batch(x)
        x = self.encoder(x.x, x.edge_index)
        x, _ = to_dense_batch(x, x.batch)
        return x
        
        
        
        

# %% ../nbs/01_models.ipynb 3
class DropPath(nn.Module):
    def __init__(self, drop_prob=None):
        super(DropPath, self).__init__()
        self.drop_prob = drop_prob

    def forward(self, x):
        return drop_path(x, self.drop_prob, self.training)

    def extra_repr(self) -> str:
        return "p={}".format(self.drop_prob)


class Mlp(nn.Module):
    def __init__(
        self,
        in_features,
        hidden_features=None,
        out_features=None,
        act_layer=nn.GELU,
        drop=0.0,
    ):
        super().__init__()
        out_features = out_features or in_features
        hidden_features = hidden_features or in_features
        self.fc1 = nn.Linear(in_features, hidden_features)
        self.act = act_layer()
        self.fc2 = nn.Linear(hidden_features, out_features)
        self.drop = nn.Dropout(drop)

    def forward(self, x):
        x = self.fc1(x)
        x = self.act(x)
        x = self.fc2(x)
        x = self.drop(x)
        return x


class RotaryEmbedding(nn.Module):
    def __init__(self, dim, scale_base=512, use_xpos=True):
        super().__init__()
        inv_freq = 1.0 / (10000 ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq)

        self.use_xpos = use_xpos
        self.scale_base = scale_base
        scale = (torch.arange(0, dim, 2) + 0.4 * dim) / (1.4 * dim)
        self.register_buffer("scale", scale)

    def forward(self, seq_len, device="cuda"):
        t = torch.arange(seq_len, device=device).type_as(self.inv_freq)
        freqs = torch.einsum("i , j -> i j", t, self.inv_freq)
        freqs = torch.cat((freqs, freqs), dim=-1)

        if not self.use_xpos:
            return freqs, torch.ones(1, device=device)

        power = (t - (seq_len // 2)) / self.scale_base
        scale = self.scale ** rearrange(power, "n -> n 1")
        scale = torch.cat((scale, scale), dim=-1)

        return freqs, scale


def rotate_half(x):
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)


def apply_rotary_pos_emb(pos, t, scale=1.0):
    return (t * pos.cos() * scale) + (rotate_half(t) * pos.sin() * scale)


class Conv1D(nn.Conv1d):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.src_key_padding_mask = None

    def forward(self, x, src_key_padding_mask=None):
        if src_key_padding_mask is not None:
            self.src_key_padding_mask = src_key_padding_mask
        if self.src_key_padding_mask is not None:
            x = torch.where(
                self.src_key_padding_mask.unsqueeze(-1)
                .expand(-1, -1, x.shape[-1])
                .bool(),
                torch.zeros_like(x),
                x,
            )
        return super().forward(x.permute(0, 2, 1)).permute(0, 2, 1)


class ResBlock(nn.Sequential):
    def __init__(self, d_model):
        super().__init__(
            nn.LayerNorm(d_model), nn.GELU(), Conv1D(d_model, d_model, 3, padding=1)
        )
        self.src_key_padding_mask = None

    def forward(self, x, src_key_padding_mask=None):
        self[-1].src_key_padding_mask = (
            src_key_padding_mask
            if src_key_padding_mask is not None
            else self.src_key_padding_mask
        )
        return x + super().forward(x)


class Extractor(nn.Sequential):
    def __init__(self, d_model, in_ch=4):
        super().__init__(
            nn.Embedding(in_ch, d_model // 4),
            Conv1D(d_model // 4, d_model, 7, padding=3),
            ResBlock(d_model),
        )

    def forward(self, x, src_key_padding_mask=None):
        for i in [1, 2]:
            self[i].src_key_padding_mask = src_key_padding_mask
        return super().forward(x)


# BEiTv2 block
class Block(nn.Module):
    def __init__(
        self,
        dim,
        num_heads,
        mlp_ratio=4.0,
        qkv_bias=False,
        qk_scale=None,
        drop=0.0,
        attn_drop=0.0,
        drop_path=0.0,
        init_values=None,
        act_layer=nn.GELU,
        norm_layer=nn.LayerNorm,
        window_size=None,
        attn_head_dim=None,
        **kwargs
    ):
        super().__init__()
        self.norm1 = norm_layer(dim)
        self.attn = nn.MultiheadAttention(
            dim, num_heads, dropout=drop, batch_first=True
        )
        self.drop_path = DropPath(drop_path) if drop_path > 0.0 else nn.Identity()
        self.norm2 = norm_layer(dim)
        mlp_hidden_dim = int(dim * mlp_ratio)
        self.mlp = Mlp(
            in_features=dim,
            hidden_features=mlp_hidden_dim,
            act_layer=act_layer,
            drop=drop,
        )

        if init_values is not None:
            self.gamma_1 = nn.Parameter(
                init_values * torch.ones((dim)), requires_grad=True
            )
            self.gamma_2 = nn.Parameter(
                init_values * torch.ones((dim)), requires_grad=True
            )
        else:
            self.gamma_1, self.gamma_2 = None, None

        self.emb = RotaryEmbedding(dim)

    def forward(self, x, attn_mask=None, key_padding_mask=None):
        q = k = v = self.norm1(x)
        positions, scale = self.emb(x.shape[1], x.device)
        q = apply_rotary_pos_emb(positions, q, scale)
        k = apply_rotary_pos_emb(positions, k, scale**-1)

        if self.gamma_1 is None:
            x = x + self.drop_path(
                self.attn(
                    q,
                    k,
                    v,
                    attn_mask=attn_mask,
                    key_padding_mask=key_padding_mask,
                    need_weights=False,
                )[0]
            )
            x = x + self.drop_path(self.mlp(self.norm2(x)))
        else:
            x = x + self.drop_path(
                self.gamma_1
                * self.attn(
                    q,
                    k,
                    v,
                    attn_mask=attn_mask,
                    key_padding_mask=key_padding_mask,
                    need_weights=False,
                )[0]
            )
            x = x + self.drop_path(self.gamma_2 * self.mlp(self.norm2(x)))
        return x


class Block_conv(Block):
    def __init__(self, dim, mlp_ratio, *args, **kwargs):
        super().__init__(dim, *args, **kwargs)
        self.mlp.fc1 = Conv1D(dim, dim, 3, padding=1)
        self.mlp.fc2 = Conv1D(dim, dim, 3, padding=1)

    def forward(self, *args, key_padding_mask=None, **kwargs):
        self.mlp.fc1.src_key_padding_mask = key_padding_mask
        self.mlp.fc2.src_key_padding_mask = key_padding_mask
        return super().forward(*args, **kwargs)


class RNA_ModelV2(nn.Module):
    def __init__(self, dim=192, depth=12, head_size=32, **kwargs):
        super().__init__()
        # self.emb = nn.Sequential(nn.Embedding(4,dim//4), Conv1D(dim//4,dim,7,padding=3),
        #                        nn.LayerNorm(dim), nn.GELU(), Conv1D(dim,dim,3,padding=1))
        self.extractor = Extractor(dim)
        # self.pos_enc = SinusoidalPosEmb(dim)

        self.blocks = nn.ModuleList(
            [
                Block_conv(
                    dim=dim,
                    num_heads=dim // head_size,
                    mlp_ratio=4,
                    drop_path=0.2 * (i / (depth - 1)),
                    init_values=1,
                    drop=0.1,
                )
                for i in range(depth)
            ]
        )

        # self.transformer = nn.TransformerEncoder(
        #    TransformerEncoderLayer_conv(d_model=dim, nhead=dim//head_size, dim_feedforward=4*dim,
        #        dropout=0.1, activation=nn.GELU(), batch_first=True, norm_first=True), depth)
        self.proj_out = nn.Linear(dim, 2)

    def forward(self, x0):
        mask = x0["mask"]
        L0 = mask.shape[1]
        Lmax = mask.sum(-1).max()
        mask = mask[:, :Lmax]
        x = x0["seq"][:, :Lmax]
        x = self.extractor(x, src_key_padding_mask=~mask)
        for blk in self.blocks:
            x = blk(x, key_padding_mask=~mask)
        x = self.proj_out(x)
        x = F.pad(x, (0, 0, 0, L0 - Lmax, 0, 0))
        return x


class CustomTransformerV0(nn.Module):
    def __init__(self, dim=192, depth=12, attb_heads=8, out=2):
        super().__init__()
        self.emb = nn.Embedding(4, dim)
        self.dec = ContinuousTransformerWrapper(
            dim_in=dim,
            dim_out=out,
            max_seq_len=512,
            attn_layers=Encoder(
                dim=dim,
                depth=depth,
                heads=attb_heads,
                attn_flash=True,
                rotary_pos_emb=True,
            ),
        )

    def forward(self, x0):
        mask = x0["mask"]
        L0 = mask.shape[1]
        Lmax = mask.sum(-1).max()
        mask = mask[:, :Lmax]
        x = x0["seq"][:, :Lmax]
        x = self.emb(x)
        out = self.dec(x, mask=mask)
        return out


class CustomTransformerV1(nn.Module):
    def __init__(self, dim=192, depth=12, attn_heads=8, head_size=32):
        super().__init__()
        self.dec = TransformerWrapper(
            num_tokens=4,
            logits_dim=2,
            max_seq_len=512,
            attn_layers=Encoder(
                dim=dim,
                depth=depth,
                heads=attn_heads,
                attn_flash=True,
                rotary_pos_emb=True,
            ),
        )

    def forward(self, x0):
        mask = x0["mask"]
        L0 = mask.shape[1]
        Lmax = mask.sum(-1).max()
        mask = mask[:, :Lmax]
        x = x0["seq"][:, :Lmax]
        out = self.dec(x, mask=mask)
        return out


class GAT(nn.Module):
    def __init__(
        self,
        in_channels,
        hidden_channels,
        out_channels,
        num_layers=2,
        dropout=0.5,
        use_bn=False,
        heads=2,
        out_heads=1,
    ):
        super(GAT, self).__init__()

        self.convs = nn.ModuleList()
        self.convs.append(
            GATConv(
                in_channels, hidden_channels, dropout=dropout, heads=heads, concat=True
            )
        )

        self.bns = nn.ModuleList()
        self.bns.append(nn.LayerNorm(hidden_channels * heads))
        for _ in range(num_layers - 2):
            self.convs.append(
                GATConv(
                    hidden_channels * heads,
                    hidden_channels,
                    dropout=dropout,
                    heads=heads,
                    concat=True,
                )
            )
            self.bns.append(nn.LayerNorm(hidden_channels * heads))

        self.convs.append(
            GATConv(
                hidden_channels * heads,
                out_channels,
                dropout=dropout,
                heads=out_heads,
                concat=False,
            )
        )

        self.dropout = dropout
        self.activation = F.elu
        self.use_bn = use_bn

    def reset_parameters(self):
        for conv in self.convs:
            conv.reset_parameters()
        for bn in self.bns:
            bn.reset_parameters()

    def forward(self, x, edge_index):
        res = x
        x = F.dropout(x, p=self.dropout, training=self.training)
        for i, conv in enumerate(self.convs[:-1]):
            x = conv(x, edge_index)
            if self.use_bn:
                x = self.bns[i](x)
            x = self.activation(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.convs[-1](x, edge_index)
        x = res + x
        return x


def to_graph_batchv1(seq, mask, adj_matrix):
    res = []
    for i in range(len(seq)):
        res.append(Data(x=seq[i][mask[i]], edge_index=adj_matrix[i].nonzero().T))
    return Batch.from_data_list(res)


class PytorchBatchWrapper(nn.Module):
    def __init__(self, md):
        super().__init__()
        self.md = md

    def forward(self, seq, mask, adj_matrix):
        batch = to_graph_batchv1(seq, mask, adj_matrix)
        out = self.md(batch.x, batch.edge_index)
        out, _ = to_dense_batch(out, batch.batch)
        return out


class RNA_ModelV3(nn.Module):
    def __init__(self, dim=192, depth=12, head_size=32, graph_layers_every=4, **kwargs):
        super().__init__()

        self.extractor = Extractor(dim)

        self.blocks = nn.ModuleList(
            [
                Block_conv(
                    dim=dim,
                    num_heads=dim // head_size,
                    mlp_ratio=4,
                    drop_path=0.2 * (i / (depth - 1)),
                    init_values=1,
                    drop=0.1,
                )
                for i in range(depth)
            ]
        )

        self.graph_layers_every = graph_layers_every
        self.graph_layers = nn.ModuleList(
            [
                PytorchBatchWrapper(
                    GAT(
                        in_channels=dim,
                        hidden_channels=dim // 2,
                        out_channels=dim,
                        num_layers=2,
                        dropout=0.1,
                        use_bn=True,
                        heads=4,
                        out_heads=1,
                    )
                )
                for i in range(depth)
                if i % self.graph_layers_every == 0
            ]
        )

        self.proj_out = nn.Linear(dim, 2)

    def forward(self, x0):
        mask = x0["mask"]
        L0 = mask.shape[1]
        Lmax = mask.sum(-1).max()
        mask = mask[:, :Lmax]
        x = x0["seq"][:, :Lmax]
        x = self.extractor(x, src_key_padding_mask=~mask)

        graph_layer_index = 0
        for i, blk in enumerate(self.blocks):
            x = blk(x, key_padding_mask=~mask)
            if i % self.graph_layers_every == 0:
                x = self.graph_layers[graph_layer_index](x, mask, x0["adj_matrix"])
                graph_layer_index += 1

        x = self.proj_out(x)
        x = F.pad(x, (0, 0, 0, L0 - Lmax, 0, 0))
        return x


class GCN(nn.Module):
    def __init__(
        self,
        in_channels,
        hidden_channels,
        out_channels,
        num_layers=2,
        dropout=0.5,
        save_mem=True,
        use_bn=True,
    ):
        super(GCN, self).__init__()

        self.convs = nn.ModuleList()
        # self.convs.append(
        #     GCNConv(in_channels, hidden_channels, cached=not save_mem, normalize=not save_mem))
        self.convs.append(GCNConv(in_channels, hidden_channels, cached=not save_mem))

        self.bns = nn.ModuleList()
        self.bns.append(nn.LayerNorm(hidden_channels))
        for _ in range(num_layers - 2):
            self.convs.append(
                GCNConv(hidden_channels, hidden_channels, cached=not save_mem)
            )
            self.bns.append(nn.LayerNorm(hidden_channels))

        # self.convs.append(
        #     GCNConv(hidden_channels, out_channels, cached=not save_mem, normalize=not save_mem))
        self.convs.append(GCNConv(hidden_channels, out_channels, cached=not save_mem))

        self.dropout = dropout
        self.activation = F.gelu
        self.use_bn = use_bn

    def reset_parameters(self):
        for conv in self.convs:
            conv.reset_parameters()
        for bn in self.bns:
            bn.reset_parameters()

    def forward(self, x, edge_index):
        for i, conv in enumerate(self.convs[:-1]):
            x = conv(x, edge_index)
            if self.use_bn:
                x = self.bns[i](x)
            x = self.activation(x)
            x = F.dropout(x, p=self.dropout, training=self.training)
        x = self.convs[-1](x, edge_index)
        return x


class LayerNorm(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.g = nn.Parameter(torch.ones(dim))

    def forward(self, x):
        eps = 1e-5 if x.dtype == torch.float32 else 1e-3
        var = torch.var(x, dim=-1, unbiased=False, keepdim=True)
        mean = torch.mean(x, dim=-1, keepdim=True)
        return (x - mean) * (var + eps).rsqrt() * self.g


class GEGLU(nn.Module):
    def forward(self, x):
        x, gate = x.chunk(2, dim=-1)
        return x * F.gelu(gate)


class FeedForwardV0(nn.Module):
    def __init__(self, dim, out=2, mult=4, dropout=0.1):
        super().__init__()
        inner_dim = int(dim * mult)

        self.net = nn.Sequential(
            nn.Linear(dim, inner_dim * 2, bias=False),
            GEGLU(),
            LayerNorm(inner_dim),
            nn.Dropout(dropout),
            nn.Linear(inner_dim, out, bias=False),
        )

    def forward(self, x):
        return self.net(x)


class RNA_ModelV4(nn.Module):
    def __init__(self, dim=192, depth=12, head_size=32, graph_layers_every=3, **kwargs):
        super().__init__()

        self.extractor = Extractor(dim)

        self.blocks = nn.ModuleList(
            [
                Block_conv(
                    dim=dim,
                    num_heads=dim // head_size,
                    mlp_ratio=4,
                    drop_path=0.2 * (i / (depth - 1)),
                    init_values=1,
                    drop=0.1,
                )
                for i in range(depth)
            ]
        )

        self.graph_layers_every = graph_layers_every
        self.graph_layers = PytorchBatchWrapper(
            GCN(
                dim * (depth // graph_layers_every),
                dim,
                dim,
                num_layers=depth // graph_layers_every,
                dropout=0.2,
                use_bn=True,
            )
        )

        self.proj_out = FeedForwardV0(dim * 2, 2)

    def forward(self, x0):
        mask = x0["mask"]
        L0 = mask.shape[1]
        Lmax = mask.sum(-1).max()
        mask = mask[:, :Lmax]
        x = x0["seq"][:, :Lmax]
        x = self.extractor(x, src_key_padding_mask=~mask)

        intermediates = []
        for i, blk in enumerate(self.blocks):
            x = blk(x, key_padding_mask=~mask)
            if i % self.graph_layers_every == 0:
                intermediates.append(x)
        graph = self.graph_layers(
            torch.concat(intermediates, dim=-1), mask, x0["adj_matrix"]
        )

        x = torch.concat([x, graph], dim=-1)
        x = self.proj_out(x)
        x = F.pad(x, (0, 0, 0, L0 - Lmax, 0, 0))
        return x


class RNA_ModelV5(nn.Module):
    def __init__(
        self,
        dim=192,
        depth=12,
        head_size=32,
        graph_layers_every=4,
        edge_dim=8,
        **kwargs
    ):
        super().__init__()

        self.extractor = Extractor(dim)

        self.blocks = nn.ModuleList(
            [
                Block_conv(
                    dim=dim,
                    num_heads=dim // head_size,
                    mlp_ratio=4,
                    drop_path=0.2 * (i / (depth - 1)),
                    init_values=1,
                    drop=0.1,
                )
                for i in range(depth)
            ]
        )
        self.adj_emb = nn.Embedding(2, edge_dim)
        self.graph_layers_every = graph_layers_every
        self.graph_layers = nn.ModuleList(
            [
                GraphTransformerAdjacent(
                    dim=dim,
                    depth=1,
                    heads=4,
                    edge_dim=edge_dim,
                )
                for i in range(depth)
                if i % self.graph_layers_every == 0
            ]
        )

        self.proj_out = nn.Linear(dim, 2)

    def forward(self, x0):
        mask = x0["mask"]
        L0 = mask.shape[1]
        Lmax = mask.sum(-1).max()
        mask = mask[:, :Lmax]
        x = x0["seq"][:, :Lmax]
        adj_matrix = x0["adj_matrix"][:, :Lmax, :Lmax]
        adj_matrix = self.adj_emb(adj_matrix.long())

        x = self.extractor(x, src_key_padding_mask=~mask)

        graph_layer_index = 0
        for i, blk in enumerate(self.blocks):
            x = blk(x, key_padding_mask=~mask)
            if i % self.graph_layers_every == 0:
                x = self.graph_layers[graph_layer_index](x, mask, adj_matrix)
                graph_layer_index += 1

        x = self.proj_out(x)
        x = F.pad(x, (0, 0, 0, L0 - Lmax, 0, 0))
        return x


class RNA_ModelV6(nn.Module):
    def __init__(self, dim=192, depth=12, head_size=32, graph_layers_every=4, **kwargs):
        super().__init__()

        self.extractor = Extractor(dim)

        self.blocks = nn.ModuleList(
            [
                Block_conv(
                    dim=dim,
                    num_heads=dim // head_size,
                    mlp_ratio=4,
                    drop_path=0.2 * (i / (depth - 1)),
                    init_values=1,
                    drop=0.1,
                )
                for i in range(depth)
            ]
        )

        self.graph_layers_every = graph_layers_every
        self.graph_layers = nn.ModuleList(
            [
                PytorchBatchWrapper(
                    GCN(
                        dim,
                        dim//2,
                        dim,
                        num_layers=depth // graph_layers_every,
                        dropout=0.2,
                        use_bn=True,
                    )
                )
                for i in range(depth)
                if i % self.graph_layers_every == 0
            ]
        )

        self.proj_out = nn.Linear(dim, 2)

    def forward(self, x0):
        mask = x0["mask"]
        L0 = mask.shape[1]
        Lmax = mask.sum(-1).max()
        mask = mask[:, :Lmax]
        x = x0["seq"][:, :Lmax]
        x = self.extractor(x, src_key_padding_mask=~mask)

        graph_layer_index = 0
        for i, blk in enumerate(self.blocks):
            x = blk(x, key_padding_mask=~mask)
            if i % self.graph_layers_every == 0:
                x = self.graph_layers[graph_layer_index](x, mask, x0["adj_matrix"])
                graph_layer_index += 1

        x = self.proj_out(x)
        x = F.pad(x, (0, 0, 0, L0 - Lmax, 0, 0))
        return x



class RNA_ModelV7(nn.Module):
    def __init__(self, dim=192, depth=12, head_size=32, graph_layers_every=4, **kwargs):
        super().__init__()

        self.extractor = Extractor(dim//2)

        self.blocks = nn.ModuleList(
            [
                Block_conv(
                    dim=dim,
                    num_heads=dim // head_size,
                    mlp_ratio=4,
                    drop_path=0.2 * (i / (depth - 1)),
                    init_values=1,
                    drop=0.1,
                )
                for i in range(depth)
            ]
        )

        self.graph_layers =PytorchBatchWrapper(
                    GAT(
                        in_channels=dim//2,
                        hidden_channels=dim // 2,
                        out_channels=dim//2,
                        num_layers=4,
                        dropout=0.1,
                        use_bn=True,
                        heads=4,
                        out_heads=1,
                    )
        )

        self.proj_out = nn.Linear(dim, 2)

    def forward(self, x0):
        mask = x0["mask"]
        L0 = mask.shape[1]
        Lmax = mask.sum(-1).max()
        mask = mask[:, :Lmax]
        x = x0["seq"][:, :Lmax]
        x = self.extractor(x, src_key_padding_mask=~mask)
        x = torch.concat([x, self.graph_layers(x, mask, x0["adj_matrix"])],  -1)
    
        for i, blk in enumerate(self.blocks):
            x = blk(x, key_padding_mask=~mask)

        x = self.proj_out(x)
        x = F.pad(x, (0, 0, 0, L0 - Lmax, 0, 0))
        return x
