| exp_name | description                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | CV    | LB      |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------- |
| `exp_00` | Initial experiment using `RNA_ModelV2` on `RNA_DatasetBaseline`. Utilizes 1D convolution after `nn.Embedding` layer and transformer. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device.                                                                                                                       |       |         |
| `exp_01` | Baseline experiment using `CustomTransformerV0` on `RNA_DatasetBaseline`. Incorporates a simple embedding layer fed to the Encoder and uses rotary embeddings via the `ContinuousTransformerWrapper` class. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device.                                                |       |         |
| `exp_02` | Same as `exp_01` but uses `TransformerWrapper` instead of `ContinuousTransformerWrapper`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device.                                                                                                                                                                  |       |         |
| `exp_03` | Experiment using `CustomTransformerV1` on `RNA_DatasetBaselineSplit`. This version generates a new split based on hd-hit and uses `TransformerWrapper` instead of `ContinuousTransformerWrapper`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. | `13.92` | `0.16144` |
| `exp_04` | Same as `exp_00` but with a new splitting method defined in `fold_split.csv`. Uses `RNA_ModelV2` on `RNA_DatasetBaselineSplit`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device.                                                                                                                            | `0.1347`  |` 0.1559` |
| `exp_05` | Model `RNA_ModelV3` used on `RNA_DatasetBaselineSplitbppV0`. Incorporates a transformer and every 4th layer a Graph Attention Network (GAT) is added which uses BPP. This BPP is masked (first `26` and last `21`) and further filtered with values > `0.5` to generate edge index. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |   `0.1304`    |    `0.1514`     |
| `exp_06` | Model `RNA_ModelV4` used on `RNA_DatasetBaselineSplitbppV0`. This version uses a transformer that saves intermediate results every n layer. These intermediates are then concatenated and applied to several layers of a Graph Convolutional Network (GCN). The edge index for the GCN is determined by BPP in the same manner as `exp_05`. The final layer of the GCN is concatenated with the final layer of the transformer and passed to a feed-forward network. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |  sas `exp_04`     |         |
| `exp_07` | Model `RNA_ModelV6` used on `RNA_DatasetBaselineSplitbppV0`. This experiment is similar to `exp_05` but tests the use of regular graph convolution instead of attention. The performance observed was similar to `exp_04`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |  sas `exp_04`      |         |
| `exp_08` | Model `RNA_ModelV3` used on `RNA_DatasetBaselineSplitssV0`. This experiment is similar to `exp_05`, but instead of using BPP, it uses `ss_roi` from Vienna, which represents secondary structure prediction without adapters. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |   `0.131570`    |   `0.15175`      |
| `exp_09` | Model `RNA_ModelV7` used on `RNA_DatasetBaselineSplitbppV0`. This experiment differs from `exp_05`. After the extractor layer, the features are fed into a 4-layer GAT attention network with BPP>0.5 serving as edges. Subsequently, these features are concatenated with the extractor feature and passed to the transformer. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |   `0.131179`   | `0.15143`         |
| `exp_10` | Model `RNA_ModelV2SS` used on `RNA_DatasetBaselineSplitssV1`. This experiment mirrors `exp_04` in terms of utilizing the original transformer model. However, the unique aspect of this experiment is the use of `ss_full`, which is embedded using the Extractor layer. This layer also serves to embed the sequence. Post embedding, both the sequence and ss features are concatenated and passed to the transformer. Configuration matches previous settings and the experiment is running on the `CUDA` device, using the custom fold split defined in `fold_split.csv`. not FT|  `0.1351`     |         |
| `exp_11` | Model `RNA_ModelV8` used on `RNA_DatasetBaselineSplitbppV1`. An iteration similar to `exp_12` but integrates a graph attention layer at the end instead of concatenating. This results in a decreased performance, indicating the potential downside of adding local attention at the final stage. The experiment uses a doubled dimension size of `192 * 2`, and all other configurations, including logging with `wandb` on the `CUDA` device, remain consistent with the previous setup. |   `bad`    |         |
| `exp_12` | Model `RNA_ModelV7` used on `RNA_DatasetBaselineSplitbppV1`. This experiment is an iteration over `exp_09` with an increased dimension size (`192 * 2`). This version utilizes the full BPP matrix, taking into account adapter probabilities. As in previous experiments, BPP values greater than `0.5` are chosen for edges. Other configurations remain consistent with prior settings, and the experiment is logged with `wandb` and running on the `CUDA` device using the custom fold split in `fold_split.csv`. |  `0.1310`     |  `0.15345`       |
| `exp_13` | Model `RNA_ModelV9` used on `RNA_DatasetBaselineSplitssbppV0`. This experiment combines both full BPP and SS (with adapters). Two separate small GNNs operate on SS and BPP independently. The outputs from these GNNs are then concatenated and supplied to a transformer. The model uses a doubled dimension size of `192 * 2`. Other configurations, including logging with `wandb` on the `CUDA` device, remain consistent with the previous setup.                            |   `0.1304`    |  `0.15218`       |
| `exp_14` | Model `RNA_ModelV10` used on `RNA_DatasetBaselineSplitssbppV0`. This experiment iterates over `exp_13` with modifications to the node features for the GAT. The node features now have positional encoding, and the last residual connection in the GAT layer has been removed. Other configurations, including logging with `wandb` on the `CUDA` device, remain consistent with the previous setup.                                                                                             |       |         |
| `exp_15` | Model `RNA_ModelV7` used on `RNA_DatasetBaselineSplitbppV1`. This experiment is similar to `exp_13`, but it's a true `B` model with a dimension size of `768` (`192 * 4`). The experiment also uses a longer training duration with `128` epochs and a reduced learning rate of `1e-5`. Other configurations, including logging with `wandb` on the `CUDA` device, remain consistent with the previous setup.                                                                                     |       |         |

> to do: substitue extracter layer with put gat 

> before `exp_10` i used to mask bpp and ss based on this post organizers might score adaptesr as well(https://www.kaggle.com/competitions/stanford-ribonanza-rna-folding/discussion/442828#2454599)