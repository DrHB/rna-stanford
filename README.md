| exp_name | description                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | CV    | LB      |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------- |
| `exp_00` | Initial experiment using `RNA_ModelV2` on `RNA_DatasetBaseline`. Utilizes 1D convolution after `nn.Embedding` layer and transformer. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device.                                                                                                                       |       |         |
| `exp_01` | Baseline experiment using `CustomTransformerV0` on `RNA_DatasetBaseline`. Incorporates a simple embedding layer fed to the Encoder and uses rotary embeddings via the `ContinuousTransformerWrapper` class. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device.                                                |       |         |
| `exp_02` | Same as `exp_01` but uses `TransformerWrapper` instead of `ContinuousTransformerWrapper`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device.                                                                                                                                                                  |       |         |
| `exp_03` | Experiment using `CustomTransformerV1` on `RNA_DatasetBaselineSplit`. This version generates a new split based on hd-hit and uses `TransformerWrapper` instead of `ContinuousTransformerWrapper`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. | 13.92 | 0.16144 |
| `exp_04` | Same as `exp_00` but with a new splitting method defined in `fold_split.csv`. Uses `RNA_ModelV2` on `RNA_DatasetBaselineSplit`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device.                                                                                                                            | 0.1347  | 0.1559 |
| `exp_05` | Model `RNA_ModelV3` used on `RNA_DatasetBaselineSplitbppV0`. Incorporates a transformer and every 4th layer a Graph Attention Network (GAT) is added which uses BPP. This BPP is masked (first `26` and last `21`) and further filtered with values > `0.5` to generate edge index. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |   `0.1304`    |    `0.1514`     |
| `exp_06` | Model `RNA_ModelV4` used on `RNA_DatasetBaselineSplitbppV0`. This version uses a transformer that saves intermediate results every n layer. These intermediates are then concatenated and applied to several layers of a Graph Convolutional Network (GCN). The edge index for the GCN is determined by BPP in the same manner as `exp_05`. The final layer of the GCN is concatenated with the final layer of the transformer and passed to a feed-forward network. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |  sas `exp_04`     |         |
| `exp_07` | Model `RNA_ModelV6` used on `RNA_DatasetBaselineSplitbppV0`. This experiment is similar to `exp_05` but tests the use of regular graph convolution instead of attention. The performance observed was similar to `exp_04`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |  sas `exp_04`      |         |
| `exp_08` | Model `RNA_ModelV3` used on `RNA_DatasetBaselineSplitssV0`. This experiment is similar to `exp_05`, but instead of using BPP, it uses `ss_roi` from Vienna, which represents secondary structure prediction without adapters. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |   `0.131570`    |   `0.15175`      |
| `exp_09` | Model `RNA_ModelV7` used on `RNA_DatasetBaselineSplitbppV0`. This experiment differs from `exp_05`. After the extractor layer, the features are fed into a 4-layer GAT attention network with BPP>0.5 serving as edges. Subsequently, these features are concatenated with the extractor feature and passed to the transformer. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |   `0.131179`   | `0.15143`         |

> to do: substitue extracter layer with put gat 