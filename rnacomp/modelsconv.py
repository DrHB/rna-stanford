# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_modelsconv.ipynb.

# %% auto 0
__all__ = ['good_luck', 'conv_block', 'up_conv', 'U_Net', 'UnetWrapper2D', 'generate_batches', 'make_pair_mask',
           'ScaledSinuEmbedding', 'CustomEmbedding', 'SeqToImage', 'Attn_pool', 'FeedForwardV5', 'RnaModelConvV0',
           'SELayer', 'Conv1D', 'ResBlock', 'Extractor', 'LocalBlock', 'EffBlock', 'MappingBlock', 'ResidualConcat',
           'LegNet', 'RnaModelConvV1', 'EffBlockV2', 'LocalBlockV2', 'ConvolutionConcatBlockV2', 'CustomConvdV2',
           'RnaModelConvV2']

# %% ../nbs/01_modelsconv.ipynb 1
import sys
sys.path.append('/opt/slh/rna/')
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
from .models import CombinationTransformerEncoderV1

# %% ../nbs/01_modelsconv.ipynb 3
def good_luck():
    return True

# %% ../nbs/01_modelsconv.ipynb 4
class conv_block(nn.Module):
    def __init__(self, ch_in, ch_out):
        super(conv_block, self).__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(ch_in, ch_out, kernel_size=3, stride=1, padding=1, bias=True),
            nn.BatchNorm2d(ch_out),
            nn.ReLU(inplace=True),
            nn.Conv2d(ch_out, ch_out, kernel_size=3, stride=1, padding=1, bias=True),
            nn.BatchNorm2d(ch_out),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        x = self.conv(x)
        return x


class up_conv(nn.Module):
    def __init__(self, ch_in, ch_out):
        super(up_conv, self).__init__()
        self.up = nn.Sequential(
            nn.Upsample(scale_factor=2),
            nn.Conv2d(ch_in, ch_out, kernel_size=3, stride=1, padding=1, bias=True),
            nn.BatchNorm2d(ch_out),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        x = self.up(x)
        return x


class U_Net(nn.Module):
    def __init__(self, img_ch=3, output_ch=1, CH_FOLD2=1):
        super(U_Net, self).__init__()

        self.Maxpool = nn.MaxPool2d(kernel_size=2, stride=2)

        self.Conv1 = conv_block(ch_in=img_ch, ch_out=int(32 * CH_FOLD2))
        self.Conv2 = conv_block(ch_in=int(32 * CH_FOLD2), ch_out=int(64 * CH_FOLD2))
        self.Conv3 = conv_block(ch_in=int(64 * CH_FOLD2), ch_out=int(128 * CH_FOLD2))
        self.Conv4 = conv_block(ch_in=int(128 * CH_FOLD2), ch_out=int(256 * CH_FOLD2))
        self.Conv5 = conv_block(ch_in=int(256 * CH_FOLD2), ch_out=int(512 * CH_FOLD2))

        self.Up5 = up_conv(ch_in=int(512 * CH_FOLD2), ch_out=int(256 * CH_FOLD2))
        self.Up_conv5 = conv_block(
            ch_in=int(512 * CH_FOLD2), ch_out=int(256 * CH_FOLD2)
        )

        self.Up4 = up_conv(ch_in=int(256 * CH_FOLD2), ch_out=int(128 * CH_FOLD2))
        self.Up_conv4 = conv_block(
            ch_in=int(256 * CH_FOLD2), ch_out=int(128 * CH_FOLD2)
        )

        self.Up3 = up_conv(ch_in=int(128 * CH_FOLD2), ch_out=int(64 * CH_FOLD2))
        self.Up_conv3 = conv_block(ch_in=int(128 * CH_FOLD2), ch_out=int(64 * CH_FOLD2))

        self.Up2 = up_conv(ch_in=int(64 * CH_FOLD2), ch_out=int(32 * CH_FOLD2))
        self.Up_conv2 = conv_block(ch_in=int(64 * CH_FOLD2), ch_out=int(32 * CH_FOLD2))

        self.Conv_1x1 = nn.Conv2d(
            int(32 * CH_FOLD2), output_ch, kernel_size=1, stride=1, padding=0
        )

    def forward(self, x):
        # encoding path
        x1 = self.Conv1(x)

        x2 = self.Maxpool(x1)
        x2 = self.Conv2(x2)

        x3 = self.Maxpool(x2)
        x3 = self.Conv3(x3)

        x4 = self.Maxpool(x3)
        x4 = self.Conv4(x4)

        x5 = self.Maxpool(x4)
        x5 = self.Conv5(x5)

        # decoding + concat path
        d5 = self.Up5(x5)
        d5 = torch.cat((x4, d5), dim=1)

        d5 = self.Up_conv5(d5)

        d4 = self.Up4(d5)
        d4 = torch.cat((x3, d4), dim=1)
        d4 = self.Up_conv4(d4)

        d3 = self.Up3(d4)
        d3 = torch.cat((x2, d3), dim=1)
        d3 = self.Up_conv3(d3)

        d2 = self.Up2(d3)
        d2 = torch.cat((x1, d2), dim=1)
        d2 = self.Up_conv2(d2)

        d1 = self.Conv_1x1(d2)
        d1 = d1.squeeze(1)
        out = torch.transpose(d1, -1, -2) * d1

        return out


class UnetWrapper2D(nn.Module):
    def __init__(self, md, output_chans=2):
        super().__init__()
        self.md = md
        self.output_chans = output_chans

    def do_forward(self, x, crop16, crop):
        out = torch.zeros(
            x.shape[0], self.output_chans, x.shape[2], x.shape[3], device=x.device
        )
        res = self.md(x[:, :, :crop16, :crop16])
        out[:, :, :crop, :crop] = res[:, :, :crop, :crop]
        return out

    def forward(self, xs, crop_to_16, crop_original, original_order):
        res = []
        for x, crop16, crop in zip(xs, crop_to_16, crop_original):
            res.append(self.do_forward(x, crop16, crop))
        return torch.cat(res)[original_order]


@torch.no_grad()
def generate_batches(tensor, nn_out):
    # Sort the tensor
    if tensor.unique().shape[0] == 1:
        return [nn_out], torch.arange(len(tensor), device=tensor.device)
    sorted_tensor, order = tensor.sort()
    nn_out = nn_out.index_select(0, order)

    # Find the change points
    diff = torch.cat([torch.tensor([1]), torch.diff(sorted_tensor)])
    change_indices = torch.where(diff != 0)[0]
    change_indices = torch.cat([change_indices, torch.tensor([len(tensor)])])
    b = [
        nn_out[change_indices[i] : change_indices[i + 1]]
        for i in range(len(change_indices) - 1)
    ]
    return b, order.argsort()


def make_pair_mask(seq, seq_len):
    encode_mask = torch.arange(seq.shape[1], device=seq.device).expand(
        seq.shape[:2]
    ) < seq_len.unsqueeze(1)
    pair_mask = encode_mask[:, None, :] * encode_mask[:, :, None]
    assert isinstance(pair_mask, torch.BoolTensor) or isinstance(
        pair_mask, torch.cuda.BoolTensor
    )
    return torch.bitwise_not(pair_mask)


class ScaledSinuEmbedding(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.scale = nn.Parameter(
            torch.ones(
                1,
            )
        )
        inv_freq = 1.0 / (10000 ** (torch.arange(0, dim, 2).float() / dim))
        self.register_buffer("inv_freq", inv_freq)

    def forward(self, x):
        n, device = x.shape[1], x.device
        t = torch.arange(n, device=device).type_as(self.inv_freq)
        sinu = einsum("i , j -> i j", t, self.inv_freq)
        emb = torch.cat((sinu.sin(), sinu.cos()), dim=-1)
        return emb * self.scale


class CustomEmbedding(nn.Module):
    def __init__(self, dim, vocab=4):
        super().__init__()
        self.embed_seq = nn.Embedding(vocab, dim)
        self.pos_enc = ScaledSinuEmbedding(dim)

    def forward(self, x):
        x = self.embed_seq(x)
        x = x + self.pos_enc(x)
        return x


class SeqToImage(nn.Module):
    def __init__(self, dim, vocab=4):
        super().__init__()
        self.embed_h = CustomEmbedding(dim=dim, vocab=vocab)
        self.embed_w = CustomEmbedding(dim=dim, vocab=vocab)
        self.norm = nn.LayerNorm(dim)

    def forward(self, seq, mask):
        seq_h = self.embed_h(seq)
        seq_w = self.embed_w(seq)
        x = seq_h.unsqueeze(1) + seq_w.unsqueeze(2)
        x = self.norm(x)
        x.masked_fill_(mask[:, :, :, None], 0.0)  # bs, h, w, dim
        x = x.permute(0, 3, 1, 2)  # bs, dim, h, w
        return x


class Attn_pool(nn.Module):
    def __init__(self, n):
        super().__init__()
        self.conv = nn.Conv2d(n, n, 1)
        self.attn = nn.Conv2d(n, n, 1)

    def forward(self, x, key_padding_mask=None):
        emb = self.conv(x)
        attn = self.attn(x)

        # Apply the mask to attention scores before softmax
        if key_padding_mask is not None:
            attn = attn.masked_fill(key_padding_mask.unsqueeze(1), float("-inf"))
        # attn = torch.clamp(attn, min=-1e9, max=1e9)
        attn = attn.softmax(dim=-1)
        x = (emb * attn).sum(-1)
        return x, attn


class FeedForwardV5(nn.Module):
    def __init__(self, dim, hidden_dim, dropout=0.2, out=2):
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, out),
        )

    def forward(self, x):
        return self.net(x)


class RnaModelConvV0(nn.Module):
    def __init__(self, embed_size, conv_out=8, vecob_size=4):
        super().__init__()
        self.seq_to_image = SeqToImage(embed_size, vocab=vecob_size)
        self.md = UnetWrapper2D(U_Net(embed_size, conv_out), conv_out)
        self.attnpool = Attn_pool(conv_out)
        self.out = FeedForwardV5(conv_out, conv_out, out=2)

    def forward(self, batch):
        L_seq = batch["mask"].sum(1)
        L0 = batch["mask"].shape[1]

        crop_to_original = L_seq.unique()  # unique lengths
        crop_to_16 = [
            ((i // 16) + 1) * 16 for i in crop_to_original
        ]  # for each unique length, find the nearest 16 miltip
        seq = batch["seq"][:, : crop_to_16[-1]]  # shortening to largest 16 multiple

        # make a square mask [bs, crop_to_16[-1], crop_to_16[-1]]  #crop_to_16[-1] is the largest 16 multiple
        square_mask = make_pair_mask(seq, L_seq)

        x = self.seq_to_image(seq, square_mask)
        x, idc = generate_batches(L_seq, x)
        x = self.md(x, crop_to_16, crop_to_original, idc)
        x, attn = self.attnpool(x, square_mask)
        x = self.out(x.permute(0, 2, 1))
        x = F.pad(x, (0, 0, 0, L0 - x.shape[1], 0, 0))
        return x


class SELayer(nn.Module):
    def __init__(self, inp, oup, reduction=4):
        super().__init__()

        # self.avg_pool = nn.AdaptiveAvgPool1d(1)

        self.fc = nn.Sequential(
            nn.Linear(oup, int(inp // reduction)),
            nn.SiLU(),
            nn.Linear(int(inp // reduction), oup),
            # Concater(Bilinear(int(inp // reduction), int(inp // reduction // 2), rank=0.5, bias=True)),
            # nn.SiLU(),
            # nn.Linear(int(inp // reduction) +  int(inp // reduction // 2), oup),
            nn.Sigmoid(),
        )

    def forward(self, x):
        (
            b,
            c,
            _,
        ) = x.size()
        y = x.view(b, c, -1).mean(dim=2)
        y = self.fc(y).view(b, c, 1)
        return x * y


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


class LocalBlock(nn.Module):
    def __init__(self, in_ch, ks, activation, out_ch=None):
        super().__init__()
        self.in_ch = in_ch
        self.out_ch = self.in_ch if out_ch is None else out_ch
        self.ks = ks

        self.block = nn.Sequential(
            nn.Conv1d(
                in_channels=self.in_ch,
                out_channels=self.out_ch,
                kernel_size=self.ks,
                padding="same",
                bias=False,
            ),
            nn.BatchNorm1d(self.out_ch),
            activation(),
        )

    def forward(self, x):
        return self.block(x)


class EffBlock(nn.Module):
    def __init__(
        self,
        in_ch,
        ks,
        resize_factor,
        filter_per_group,
        activation,
        out_ch=None,
        se_reduction=None,
        se_type="simple",
        inner_dim_calculation="out",
    ):
        super().__init__()
        self.in_ch = in_ch
        self.out_ch = self.in_ch if out_ch is None else out_ch
        self.resize_factor = resize_factor
        self.se_reduction = resize_factor if se_reduction is None else se_reduction
        self.ks = ks
        self.inner_dim_calculation = inner_dim_calculation

        """
        `in` refers to the original method of EfficientNetV2 to set the dimensionality of the EfficientNetV2-like block
        `out` is the mode used in the original LegNet approach

        This parameter slighly changes the mechanism of channel number calculation 
        which can be seen in the figure above (C, channel number is highlighted in red).
        """
        if inner_dim_calculation == "out":
            self.inner_dim = self.out_ch * self.resize_factor
        elif inner_dim_calculation == "in":
            self.inner_dim = self.in_ch * self.resize_factor
        else:
            raise Exception(f"Wrong inner_dim_calculation: {inner_dim_calculation}")

        self.filter_per_group = filter_per_group

        se_constructor = SELayer

        block = nn.Sequential(
            nn.Conv1d(
                in_channels=self.in_ch,
                out_channels=self.inner_dim,
                kernel_size=1,
                padding="same",
                bias=False,
            ),
            nn.BatchNorm1d(self.inner_dim),
            activation(),
            nn.Conv1d(
                in_channels=self.inner_dim,
                out_channels=self.inner_dim,
                kernel_size=ks,
                groups=self.inner_dim // self.filter_per_group,
                padding="same",
                bias=False,
            ),
            nn.BatchNorm1d(self.inner_dim),
            activation(),
            se_constructor(
                self.in_ch, self.inner_dim, reduction=self.se_reduction
            ),  # self.in_ch is not good
            nn.Conv1d(
                in_channels=self.inner_dim,
                out_channels=self.in_ch,
                kernel_size=1,
                padding="same",
                bias=False,
            ),
            nn.BatchNorm1d(self.in_ch),
            activation(),
        )

        self.block = block

    def forward(self, x):
        return self.block(x)


"""
The `activation()` in the optimized architecture simply equals `nn.Identity`
In the original LegNet approach it was `nn.SiLU`
"""


class MappingBlock(nn.Module):
    def __init__(self, in_ch, out_ch, activation):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv1d(
                in_channels=in_ch,
                out_channels=out_ch,
                kernel_size=1,
                padding="same",
            ),
            activation(),
        )

    def forward(self, x):
        return self.block(x)


class ResidualConcat(nn.Module):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def forward(self, x, **kwargs):
        return torch.concat([self.fn(x, **kwargs), x], dim=1)


import torch.nn.functional as F

from typing import Type


class LegNet(nn.Module):
    __constants__ = "resize_factor"

    def __init__(
        self,
        input_size: int,
        use_single_channel: bool,
        use_reverse_channel: bool,
        block_sizes: list[int] = [256, 128, 128, 64, 64, 64, 64],
        ks: int = 7,
        resize_factor: int = 4,
        activation: Type[nn.Module] = nn.SiLU,
        final_activation: Type[nn.Module] = nn.Identity,
        filter_per_group: int = 1,
        se_reduction: int = 4,
        res_block_type: str = "concat",
        se_type: str = "simple",
        inner_dim_calculation: str = "in",
    ):
        super().__init__()
        self.input_size = input_size
        self.block_sizes = block_sizes
        self.resize_factor = resize_factor
        self.se_reduction = se_reduction
        self.use_single_channel = use_single_channel
        self.use_reverse_channel = use_reverse_channel
        self.filter_per_group = filter_per_group
        self.final_ch = 2  # number of bins in the competition
        self.inner_dim_calculation = inner_dim_calculation
        self.res_block_type = res_block_type

        residual = ResidualConcat

        self.stem_block = LocalBlock(
            in_ch=self.in_channels, out_ch=block_sizes[0], ks=ks, activation=activation
        )

        blocks = []
        for ind, (prev_sz, sz) in enumerate(zip(block_sizes[:-1], block_sizes[1:])):
            block = nn.Sequential(
                residual(
                    EffBlock(
                        in_ch=prev_sz,
                        out_ch=sz,
                        ks=ks,
                        resize_factor=4,
                        activation=activation,
                        filter_per_group=self.filter_per_group,
                        se_type=se_type,
                        inner_dim_calculation=inner_dim_calculation,
                    )
                ),
                LocalBlock(in_ch=2 * prev_sz, out_ch=sz, ks=ks, activation=activation),
            )
            blocks.append(block)

        self.main = nn.Sequential(*blocks)

        self.mapper = MappingBlock(
            in_ch=block_sizes[-1], out_ch=self.final_ch, activation=final_activation
        )

    @property
    def in_channels(self) -> int:
        return self.input_size

    def forward(self, x):
        x = x.permute(0, 2, 1)
        x = self.stem_block(x)
        x = self.main(x)
        x = x.permute(0, 2, 1)
        return x


class RnaModelConvV1(nn.Module):
    def __init__(self, dim=192, block_sizes=[256, 128, 128, 64, 64, 64, 64]):
        super().__init__()
        self.extractor = Extractor(dim)
        self.cnn_model = LegNet(
            input_size=dim,
            use_single_channel=False,
            use_reverse_channel=False,
            block_sizes=block_sizes,
        )
        self.proj_out = nn.Sequential(nn.Linear(block_sizes[-1], 2))
        

    def forward(self, x0):
        mask = x0["mask"]
        L0 = mask.shape[1]
        Lmax = mask.sum(-1).max()
        mask = mask[:, :Lmax]
        x = x0["seq"][:, :Lmax]

        x = self.extractor(x, src_key_padding_mask=~mask)
        x = self.cnn_model(x)
        x = self.proj_out(x)
        x = F.pad(x, (0, 0, 0, L0 - Lmax, 0, 0))
        return x


class EffBlockV2(nn.Sequential):
    def __init__(
        self,
        in_ch,
        ks,
        resize_factor,
        filter_per_group,
        activation,
        out_ch=None,
        se_reduction=None,
        se_type="simple",
        inner_dim_calculation="out",
        dropout=0.2,
    ):
        self.in_ch = in_ch
        self.out_ch = self.in_ch if out_ch is None else out_ch
        self.resize_factor = resize_factor
        self.se_reduction = resize_factor if se_reduction is None else se_reduction
        self.ks = ks
        self.inner_dim_calculation = inner_dim_calculation

        if inner_dim_calculation == "out":
            self.inner_dim = self.out_ch * self.resize_factor
        elif inner_dim_calculation == "in":
            self.inner_dim = self.in_ch * self.resize_factor
        else:
            raise Exception(f"Wrong inner_dim_calculation: {inner_dim_calculation}")

        self.filter_per_group = filter_per_group

        super().__init__(
            Conv1D(
                in_channels=self.in_ch,
                out_channels=self.inner_dim,
                kernel_size=1,
                padding="same",
                bias=False,
            ),
            nn.LayerNorm(self.inner_dim),
            activation(),
            nn.Dropout(dropout),
            Conv1D(
                in_channels=self.inner_dim,
                out_channels=self.inner_dim,
                kernel_size=ks,
                groups=self.inner_dim // self.filter_per_group,
                padding="same",
                bias=False,
            ),
            nn.LayerNorm(self.inner_dim),
            activation(),
            nn.Dropout(dropout),
            Conv1D(
                in_channels=self.inner_dim,
                out_channels=self.in_ch,
                kernel_size=1,
                padding="same",
                bias=False,
            ),
            nn.LayerNorm(self.in_ch),
            activation(),
            nn.Dropout(dropout)
        )

        self.src_key_padding_mask = None

    def forward(self, x, src_key_padding_mask=None):
        for i in [0, 3, 6]:
            self[i].src_key_padding_mask = src_key_padding_mask
        return super().forward(x)


class LocalBlockV2(nn.Sequential):
    def __init__(self, in_ch, ks, activation, dropout = 0.2, out_ch=None):
        self.in_ch = in_ch
        self.out_ch = self.in_ch if out_ch is None else out_ch
        self.ks = ks

        super().__init__(
            Conv1D(
                in_channels=self.in_ch,
                out_channels=self.out_ch,
                kernel_size=self.ks,
                padding="same",
                bias=False,
            ),
            nn.LayerNorm(self.out_ch),
            activation(),
            nn.Dropout(dropout),
        )

    def forward(self, x, src_key_padding_mask=None):
        for i in [0]:
            self[i].src_key_padding_mask = src_key_padding_mask
        return super().forward(x)


class ConvolutionConcatBlockV2(nn.Module):
    def __init__(
        self,
        in_ch=256,
        ks=7,
        resize_factor=4,
        filter_per_group=1,
        activation=nn.GELU,
        out_ch=None,
        dropout = 0.2,
    ):
        super().__init__()
        self.effblock = EffBlockV2(
            in_ch=in_ch,
            ks=ks,
            resize_factor=resize_factor,
            filter_per_group=filter_per_group,
            activation=activation,
            out_ch=out_ch,
            dropout=dropout,
        )

        self.localblock = LocalBlockV2(
            in_ch=in_ch * 2, ks=ks, activation=activation, out_ch=out_ch, dropout=dropout,
        )

    def forward(self, x, src_key_padding_mask=None):
        res = x
        x = self.effblock(x, src_key_padding_mask=src_key_padding_mask)
        x = torch.cat([x, res], dim=-1)
        x = self.localblock(x, src_key_padding_mask=src_key_padding_mask)
        return x



class CustomConvdV2(nn.Module):
    def __init__(
        self,
        dim: int,
        block_sizes: list[int] = [256, 128, 128, 64, 64, 64, 64],
        ks: int = 7,
        resize_factor: int = 4,
        activation: Type[nn.Module] = nn.SiLU,
        dropout = 0.2, 
    ):
        super().__init__()

        self.stem_block = LocalBlockV2(
            in_ch=dim, out_ch=block_sizes[0], ks=ks, activation=activation
        )

        self.blocks = nn.ModuleList()
        for ind, (prev_sz, sz) in enumerate(zip(block_sizes[:-1], block_sizes[1:])):
            block = ConvolutionConcatBlockV2(
                in_ch=prev_sz,
                out_ch=sz,
                ks=ks,
                resize_factor=resize_factor,
                activation=activation,
                dropout = dropout,
            )
            self.blocks.append(block)

    def forward(self, x, src_key_padding_mask=None):
        x = self.stem_block(x, src_key_padding_mask=src_key_padding_mask)
        for block in self.blocks:
            x = block(x, src_key_padding_mask=src_key_padding_mask)
        return x


class RnaModelConvV2(nn.Module):
    def __init__(
        self,
        dim=192,
        resize_factor=4,
        ks=7,
        activation=nn.SiLU,
        head_size=32,
        drop_pat_dropout=0.2,
        dropout=0.2,
        bpp_transfomer_depth=3,
    ):
        super().__init__()
        block_sizes = [dim, dim, dim, dim//2, dim//2, dim//2]
        self.extractor = Extractor(dim)
        self.cnn_model = CustomConvdV2(
            dim=dim,
            block_sizes=block_sizes,
            resize_factor=resize_factor,
            ks=ks,
            activation=activation,
            dropout = 0.0,
        )
        
        self.bb_comb_blocks = nn.ModuleList(
            [
                CombinationTransformerEncoderV1(
                    dim//2,
                    head_size=head_size,
                    dropout=dropout,
                    drop_path=drop_pat_dropout * (i / (bpp_transfomer_depth - 1)),
                )
                for i in range(bpp_transfomer_depth)
            ]
        )

        self.proj_out = nn.Linear( dim//2, 2)

    def forward(self, x0):
        mask = x0["mask"]
        L0 = mask.shape[1]
        Lmax = mask.sum(-1).max()
        mask = mask[:, :Lmax]
        x = x0["seq"][:, :Lmax]

        bpp = x0["bb_matrix_full_prob"][:, :Lmax, :Lmax]
        bpp_extra = x0["bb_matrix_full_prob_extra"][:, :Lmax, :Lmax].float()
        ss = x0["ss_adj"][:, :Lmax, :Lmax].float()

        x = self.extractor(x, src_key_padding_mask=~mask)
        x = self.cnn_model(x, src_key_padding_mask=~mask)
        
        for i, blk in enumerate(self.bb_comb_blocks):
            x = blk(x, bpp, bpp_extra, ss, mask)
            
        x = self.proj_out(x)
        x = F.pad(x, (0, 0, 0, L0 - Lmax, 0, 0))
        return x
