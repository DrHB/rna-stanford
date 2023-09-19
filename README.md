| exp_name | description                                                                                                                                                                                                                       | score |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|
| `exp_00` | Initial experiment using `RNA_ModelV2` on `RNA_DatasetBaseline`. Utilizes 1D convolution after `nn.Embedding` layer and transformer. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device. | `0.1299` |
| `exp_01` | Baseline experiment using `CustomTransformerV0` on `RNA_DatasetBaseline`. Incorporates a simple embedding layer fed to the Encoder and uses rotary embeddings via the `ContinuousTransformerWrapper` class. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device.  |  `0.1337`|
| `exp_02` | Same as `exp_01` but uses `TransformerWrapper` instead of `ContinuousTransformerWrapper`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device. |       |
| `exp_03` | Experiment using `CustomTransformerV1` on `RNA_DatasetBaselineSplit`. This version generates a new split based on hd-hit and uses `TransformerWrapper` instead of `ContinuousTransformerWrapper`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device and uses a custom fold split defined in `fold_split.csv`. |       |
| `exp_04` | Same as `exp_00` but with a new splitting method defined in `fold_split.csv`. Uses `RNA_ModelV2` on `RNA_DatasetBaselineSplit`. Configuration includes `64` batch size, `12` workers, `192` dimensions, `12` depth, `32` dim_head, and `64` epochs with `5e-4` learning rate and `0.05` weight decay. The experiment is running on `CUDA` device. |       |
