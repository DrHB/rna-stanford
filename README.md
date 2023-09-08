This file will be overwritten by `index.ipynb`
| Subtype           | Optimization Strategy | Source of Graphs | Search Strategy  | Description                                                                                                       | Total Graphs + Configs |
|-------------------|-----------------------|------------------|------------------|-------------------------------------------------------------------------------------------------------------------|------------------------|
| Layout:XLA:Default | Layout                | XLA              | Default          | Focuses on layout optimization using a genetic algorithm from default configurations. Graphs are sourced from XLA benchmarks and cover various ML models.    | 771,496                |
| Layout:XLA:Random  | Layout                | XLA              | Random           | Focuses on layout optimization using a random search strategy. Graphs are sourced from XLA benchmarks and cover various ML models.                  | 908,561                |
| Layout:NLP:Default | Layout                | NLP              | Default          | Focuses on layout optimization using a genetic algorithm from default configurations. Graphs are sourced exclusively from various BERT models for NLP tasks. | 13,285,415             |
| Layout:NLP:Random  | Layout                | NLP              | Random           | Focuses on layout optimization using a random search strategy. Graphs are sourced exclusively from various BERT models for NLP tasks.                 | 16,125,781             |
| Tile:XLA           | Tile                  | XLA              | N/A              | Focuses on tile size optimization. All possible tile sizes are enumerated as the search space is smaller. Graphs are sourced from XLA benchmarks and cover various ML models. | 12,870,077             |


f
