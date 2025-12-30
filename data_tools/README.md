# Data Tools

Scripts for preparing test datasets used in this project.

## pick_visdrone_base.py
- Selects base (normal) images from VisDrone-DET
- Filters by person/vehicle presence
- Copies selected images to datasets/base
- Updates datasets/manifest.csv

NOTE:
These scripts are for dataset preparation only.
They are NOT used in runtime inference.
