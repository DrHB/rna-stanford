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
| `exp_14` | Model `RNA_ModelV10` used on `RNA_DatasetBaselineSplitssbppV0`. This experiment iterates over `exp_13` with modifications to the node features for the GAT. The node features now have positional encoding, and the last residual connection in the GAT layer has been removed. Other configurations, including logging with `wandb` on the `CUDA` device, remain consistent with the previous setup.                                                                                             |    `0.1299`   |     `0.15181`    |
| `exp_15` | Model `RNA_ModelV7` used on `RNA_DatasetBaselineSplitbppV1`. This experiment is similar to `exp_13`, but it's a true `B` model with a dimension size of `768` (`192 * 4`). The experiment also uses a longer training duration with `128` epochs and a reduced learning rate of `1e-5`. Other configurations, including logging with `wandb` on the `CUDA` device, remain consistent with the previous setup. Training crsashed segm error                                                                                     |   `n/a`    |         |
| `exp_16` | Model `RNA_ModelV11` used on `RNA_DatasetBaselineSplitssbppV1`. The experiment starts with the Extractor embedding sequences. The Extractor's features are passed to a GAT with edges calculated from the SS. The output is then combined with `bpp` (probability) using `bmm` and applied to a gated residual unit. Previously, I used `bpp` in GAT for pairs exceeding 0.5 probability. The result is concatenated with the Extractor's original features before feeding it to a transformer. This model has so far shown superior performance, perhaps due to the incorporation of full bpp probabilities. | `0.12709`  |  `0.1481`  |
| `exp_17` | Model `RNA_ModelV12` used on `RNA_DatasetBaselineSplitssbppV1`. This experiment is akin to `exp_16`, but the model does not utilize the `GAT` for `ss`. Instead, it merges the raw full probability `bpp` through `bmm` and a gated residual unit in `BppFeedForwardwithRes` layer,  after the initial `4` transformer blocks.                                                                             |   `overfit`    |         |
| `exp_18` | Model `RNA_ModelV13` used on `RNA_DatasetBaselineSplitssbppV1`. This experiment deploys a standard transformer mode with Extractor. However, during its first eight layers, the `BppFeedForwardwithRes` mechanism is used alternately on `ss` and `bpp`. The pattern followed is bpp, ss, bpp, ss, and so on. The idea is to ascertain the potential benefits of this alternating incorporation of structural and base pairing probabilities within the transformer's processing layers.  |       |         |
| `exp_19` | Model `RNA_ModelV14` used on `RNA_DatasetBaselineSplitssbppV1`. This experiment is akin to `exp_16`. Initially, the sequences are embedded using the Extractor. The extracted features are passed to a GAT, using SS as edges. The output from the GAT is then combined with `bpp` via the `BppFeedForwardwithRes` mechanism. To this combination, the original features extracted by the Extractor are added as a residual. The final combined features are then fed into the transformer. Unlike `exp_16`, this experiment doesn't concatenate the features, and each branch takes an input of size `dim//2`. The intent is to see how the combined GAT and transformer mechanism works without concatenating features from different branches. |   `0.1275`    |         |
| `exp_20` | Model `RNA_ModelV15` used on `RNA_DatasetBaselineSplitssbppV1`. This experiment draws inspiration from `exp_16`. The sequences undergo embedding through the Extractor and then move onto a modified GAT with `graph_layers=6` and `heads=8`. In contrast to `exp_16`, which performs the bpp combination immediately post-GAT, this setup introduces the `bpp` combination via `BppFeedForwardwithRes` only after the second transformer encoder layer. The rationale is to allow the initial layers to primarily focus on SS features, and then to incorporate the bpp data. Results indicate that the timing of bpp injection has a minimal impact, and its mere presence significantly influences the outcomes. |   `~exp_16`    |         |
| `exp_21` | Model `RNA_ModelV16` used on `RNA_DatasetBaselineSplitssbppV1`. This experiment deviates from using a GAT. Instead, post extraction, there are two small transformer encoders dedicated to `bpp` and `ss` respectively. Each encoder comprises `3` layers of transformers. Subsequently, the `bpp` or `ss` are combined using a gated residual unit through `GatedResidualCombination`. The features from these encoders are then concatenated and passed to a standard transformer. Initial training showcased promise, however, inconsistency in the form of spikes was observed during the later stages. A slight overfitting was also detected as the training progressed, suggesting the potential need for techniques like SWA. |       |         |
| `exp_22` | Model `RNA_ModelV17` used on `RNA_DatasetBaselineSplitssbppV1`. This iteration avoids GAT and is somewhat aligned with the methodology of `exp_21`. Two separate transformers are in play; one dedicated to `ss` and the other to `bpp`. The block called `EncoderResidualCombBlockV1` is used for each transformer. For `ss`, combination with the extractor layer (via `GatedResidualCombination`) is done before passing to the transformer. In contrast, for `bpp`, the combination is performed post its processing by the transformer. The output features of `ss` and `bpp` transformers are then combined and supplied to a standard transformer. A notable introduction in this experiment is the Exponential Moving Average (EMA), which ensured stable performance during training, quicker convergence, and eliminated spikes in validation. However, mild overfitting was observed, suggesting potential adjustments like increasing dropout. |   `0.1268`    |      `0.14621`   |
| `exp_23` | Model `RNA_ModelV17` utilized on `RNA_DatasetBaselineSplitssbppV2`. This experiment mirrors the architecture and methodology of `exp_22`, with a few differences. The model's dropout rates (`layer_dropout`, `attn_dropout`, and `drop_pat_dropout`) have been increased to 0.25. Furthermore, the `bpp` value now represents an average derived from three packages: 'vienna_2', 'contrafold_2', and organizers' data. This change to the `bpp` is anticipated to introduce a more robust representation. The rest of the configurations remain consistent with `exp_22`. |   `0.1272`    |   `0.14709`  |
| `exp_24` | Model `RNA_ModelV18FM` used on `RNA_DatasetBaselineFM`. In this experiment, finetuning was performed on the publicly available RNA foundation model, known as `RNA-FM`. The model was entirely unfrozen and additional output layers were appended. The dropout rate for this model was set to 0.2. Notably, no `bpp` was utilized in this setup. Given that this is a finetuning on an existing model, it will be interesting to observe how previous knowledge and architectures from `RNA-FM` benefit the training process. |  `bad`     |         |
| `exp_25` | This experiment utilizes the `RNA-FM` model as in `exp_24`. However, rather than merely finetuning the existing model (which resulted in a poor score in `exp_24`), there's a structural adjustment here. The `RNA-FM` functions as an extractor. The embeddings derived from layer 12 of `RNA-FM` are taken and the procedure from `exp_22` is followed. Yet, the transformer architecture is modified. The two primary transformers that integrate `bpp` and `ss` with the features from `RNA-FM` consist of three layers each. The outputs of these transformers are merged and supplied to a 6-layer transformer. It's notable that the `RNA-FM` is kept frozen in this setup, ensuring its weights remain unchanged during the training process. |  `0.1293`     |         |
| `exp_25_unfreeze` | Following the results of `exp_25`, this experiment unfreezes the backbone (`RNA-FM`) and fine-tunes the entire model. The observation reveals that although the score improved compared to `exp_25` (reaching a metric of `0.1277`), the model began to overfit severely after a certain point. It suggests a recurring trend that models which have the `RNA-FM` backbone unfrozen are prone to overfitting. It's also notable that this run used the weights from `exp_25` as its initial state (`md_wt = 'exp_25/models/model.pth'`) and had a modified learning rate that was an average of `5e-5` and `5e-4`. The total epochs for this experiment was reduced to `16` given the observation of overfitting. |   `0.1277`    |         |
| `exp_26` | Model `RNA_ModelV20` used on `RNA_DatasetBaselineSplitssbppV3`. This experiment closely follows the configuration of `exp_22`, but there's a significant change in the input data. Instead of feeding `ss`, an average of extra `bpp` from three distinct packages (Vienna, Contrafold, and RanFormer) is utilized. The architecture still employs two separate transformers, one for the aforementioned average `bpp` and the other for the original `bpp`. The combination of `bpp` or `extrabpp` is achieved using a gated residual unit via `GatedResidualCombination`. These processed features are then merged and supplied to a typical transformer. The two initial transformer mechanisms vary in when the combination takes place: the first integrates before feeding to the encoder, while the latter performs the integration post-encoder. |     `0.1267`  |    `0.14671`     |
| `exp_27` | This experiment introduces an interesting approach where the `RNA-FM` model acts as an evolutionary module due to its training on a large RNA dataset. Its features are extracted and run in parallel with a regular extractor. The extracted features then undergo a combination process with `bpp`. Following this, the features derived from `RNA-FM` and the combination are concatenated and subsequently passed through a standard transformer. The experiment aims to harness the potential of the `RNA-FM` model by leveraging its evolutionary insights while maintaining an independent extraction and combination process. Its resulted in overfit at the end.|   `0.1307`    |         |
| `exp_28` | This experiment employs the `RNA-FM` model, specifically to predict `bpp` values which then undergo transformation through a sigmoid layer. The transformed `bpp` values are combined with features from a regular extractor. Following this combination, the features are concatenated with the original extracted features and then passed to a transformer which has been modified to have a depth of 9. This experimental setup intends to refine the learning process by allowing the `RNA-FM` model to make predictions which are subsequently combined with the traditional extraction process. A future plan is in place to unfreeze the concatenated model, which might enhance the overall model performance. |    `0.1333`   |         |
| `exp_29`   | This experiment replicates the conditions of `exp_28`, known for its high-performing cross-validation results. However, a significant modification is made in the `extra_bpp` feature extraction process. Instead of utilizing the comprehensive set of three different sources (`Vienna`, `Contrafold`, and `RanFormer`) for secondary structure (`ss`) data, this iteration solely employs data from the `rnafm` |   `0.1271`    |  `0.14673`    |
| `exp_30`| In this iteration, the setup is deliberately aligned with the conditions of `exp_19`, which previously achieved a notable score. However, `exp_30` diverges by integrating an averaged `bpp` feature that combines the original `bpp` with that derived from `rnafm`. Despite this strategic fusion, intended to harness more robust or comprehensive structural insights, the model's performance disappointingly declines, as evidenced by a score of `0.1290` compared to the `0.1275` from `exp_19` | `0.1290`|       |
| `exp_31`   | This iteration introduces an innovative approach in handling `bpp` data through the deployment of a `CombinationTransformerEncoder`. This specialized block harmonizes a standard transformer with a subsequent `Combination` layer designed to multiply the input with `bpp`, followed by dual `conv1d` operations activated by `relu`.  This encoder is stratified into 8 distinctive layers, with a strategic injection of `bpp` in one layer, while `extra_bpp`—an averaged ensemble from sources including `rnafm`, `vienna_2`, `contrafold_2`, and `rnaformer`—is integrated into another. Concluding the architecture are 4 blocks of unaltered transformers. | `0.1259`  |   `0.1459`    |
| `exp_32`   | Progressing from the advancements of `exp_31`, this experiment evolves the architecture by implementing the `CombinationTransformerEncoderV1`. This  construct enhances the sequence of interactions by introducing a layout that progresses through a `transformer_encoder`, integrates `bpp`, advances through another `transformer_encoder`, incorporates `extra_bpp`, and concludes with a final `transformer_encoder` with the `ss`. Each segment in this chain is mixed `Combination` layer. Additionally, every block (`CombinationTransformerEncoderV1`) is fortified with a residual connection. The experiment has indicated an improvement over its predecessor, `exp_31`. | `0.1247` | `0.14436`      |
| `exp_32_v1`| This iteration replicates `exp_32`, but incorporates two key changes: 1) `bpp` is stored as a numpy array, simplifying the loading process and potentially speeding up training. 2) The `rnafm` feature, previously deemed noisy, is excluded. The primary goal is to observe any performance variations due to these changes.                                      |  `0.1250`  | `0.14491`   |
| `exp_32_v2`| This variant is modeled after `exp_32_v1`, but incorporates a deeper `bpp_transfomer_depth` of `6`, increased from `4`. Furthermore, the training data has been sourced from `train_corrected.parquet`, which might be a refined or updated dataset. The primary goal is to see if deeper `bpp_transfomer_depth` and the new dataset enhance the performance. |    |    |
| `exp_33`   | This experiment marks a departure from the previous transformer-based approaches, venturing into convolutional neural networks (CNNs) with the implementation of a standard EfficientNetV2_1d (referred to as efnetv2 in the context). The model integrates an initial extractor layer, funneling processed features into the EfficientNet structure. Tthe first attempt at adapting the efnetv2 for sequence data like RNA poses challenges, reflected in a local CV score of `0.1623`. | `0.1623` |       |
| `exp_34`   | Building upon the framework established in `exp_32`, Firstly, it replaces the standard `rnatormer` bpp with `rnaformverv1`. Secondly, a critical fix was implemented in the `combination` layer, resolving an issue related to padding mask that potentially compromised previous models' learning efficiency. Unlike its predecessors, `exp_34` does not employ sampling, really bad score, did not look good, perhaps sampler or mask |    |       |
| `exp_35`   | same as `exp_32`, but it replaces the standard `rnatormer` bpp with `rnaformverv1` , its working fine, i think i can reach same score |  sas `exp_32`  |       |
| `exp_37`   | same as `exp_35`, but it replaces the standard `rnatormer` bpp with `rnaformverv1` removed `rnafm`, its working fine, i think i can reach same score, `RNA_DatasetBaselineSplitssbppV6`, `RNA_ModelV26`, in the model residul replaced with `GRUresidual` |  sas `exp_32`  |       |
| `exp_38`   | The approach in `exp_38` . Notably, this experiment employs a strategic data augmentation method by introducing a 'flip' technique. In addition added `rnafm` to `extra_bpp` as augmentaion because its noisy, `"vienna_2"`, `"contrafold_2"`, and `"rnaformerv1"`, Dataset uses `RNA_DatasetBaselineSplitssbppV7Flip`.  Furthermore, `exp_38` , using `ExtractorV3`, that uses `MLP` instead of `res_block`. In the continued pursuit of architectural excellence, the model uses several blocks of the newly introduced `CombinationTransformerEncoderV2`, each endowed with `GRUGating`. Convergense a bit slow, maybe remove  noise in `rnafm`| TBD   |       |
| `exp_39`   | In `exp_39`, the model architecture shifts to `RnaModelConvV2`, integrating 1D convolutions with `CombinationTransformerEncoderV1` blocks. The focus is to explore the effectiveness of 1D convolutions in the feature extraction phase. While the preliminary outcomes indicate an improvement, they still lag behind the best-performing models like `exp_32` | `0.1332`   |    |




> to do: substitue extracter layer with put gat 

> before `exp_10` i used to mask bpp and ss based on this post organizers might score adaptesr as well(https://www.kaggle.com/competitions/stanford-ribonanza-rna-folding/discussion/442828#2454599)