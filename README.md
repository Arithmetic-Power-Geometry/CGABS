# CGABS — reproducible finite-archive charging-policy selection

This repository contains the **standalone computational materials** for the retrospective finite-archive analysis of charging-policy selection and deterministic winner certification.

## Contents

- `selection.csv`: 27 public-source development outcomes (nine policies, three observations each), with replicate identifiers.
- `reproduce.py`: self-contained, standard-library Python implementation of seven allocation rules, paired replay comparisons, finite-archive certificate analysis, and the synthetic interval diagnostic.
- `results.json`: generated locally by the script; not required as an input.

## Reproduce

Use Python 3.9 or later:

```bash
python reproduce.py
```

The script can be invoked from any working directory. It verifies the canonical development-data SHA-256 digest, reproduces 28 algorithm-by-budget means to the reported precision, evaluates the exact earliest-certificate budgets for upper bounds of 1,500, 2,000 and 2,500 cycles, and runs 5,000 independently generated synthetic coverage trials using seed 14. Results are written to `results.json` in this directory.

The archive SHA-256 is `7ad2caa267ad466db92afc9240aaf4376d8a7bfd1c76cf16bbd912f03c244321`. The initial outcome-independent replicate split used seed 20261110; replay orders use seeds 20261110–20261409. The CSV is converted to the canonical JSON representation inside the script before its checksum is verified.

The 18 separate evaluation outcomes are **not included, accessed, or evaluated** here. The scores are retrospective policy means within the fixed 27-observation development archive and do not estimate prospective battery-life improvements.

## Source

Original battery study: Attia et al., *Nature* 578, 397–402 (2020), DOI [10.1038/s41586-020-1994-5](https://doi.org/10.1038/s41586-020-1994-5). Original validation endpoints: [battery-parameter-spaces](https://github.com/petermattia/battery-parameter-spaces/blob/master/Validation/final_results.csv).

This repository contains only development data and the minimal code required to reproduce the reported computational analysis. No hardware experiments, independent-cell validation, or physical safety claims are made.
