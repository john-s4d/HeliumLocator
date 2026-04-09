# HeliumLocator

HeliumLocator was my attempt to build a hotspot siting and link analysis tool for the Helium network.

The goal was not just to map nearby hotspots, but to evaluate whether a proposed location could plausibly reach them. To do that, I combined hotspot discovery from the Helium API with terrain and altitude data, simple RF link-budget calculations, and line-of-sight style checks that accounted for antenna gain, elevation, Fresnel clearance, and earth curvature.

The repository includes code to collect nearby Helium nodes, organize them spatially on a reference grid, estimate received signal levels to a candidate point, and test whether links were likely to be viable under different antenna and installation assumptions. In practice, this was an attempt to reason about hotspot placement and expected connectivity, not just visualize network geography.

This repository is incomplete and should be treated as an archival prototype. The propagation model is simplified, some pieces are still rough, and the project reflects an exploratory engineering effort rather than a polished product, but it captures a serious attempt to turn Helium deployment into a quantitative siting problem.

## Concepts explored

- Helium hotspot discovery and local network analysis
- RF link-budget estimation
- terrain and altitude-aware line-of-sight checks
- Fresnel clearance and earth curvature effects
- candidate hotspot siting and viability analysis
- geospatial grid and mapping utilities

## Status

Circa 2021. Archival prototype preserved for historical interest.
