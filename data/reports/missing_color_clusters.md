# Missing Color Cluster Report

## Overall Summary

- Total registry rows checked: 1987
- Total clusters found: 1776
- Complete clusters: 1455
- Can propagate clusters: 0
- Entire cluster missing: 321
- Total rows missing Hex/RGB: 337

## Cluster Status Breakdown

| Cluster Status | Count |
|---|---:|
| COMPLETE | 1455 |
| ENTIRE_CLUSTER_MISSING | 321 |

## Missing Rows by Company

| Company | Missing Rows |
|---|---:|
| Army Painter | 300 |
| Games Workshop | 4 |
| Vallejo | 33 |

## Largest Missing Clusters

| Company | Paint Name | Missing Rows | Product Lines | Action |
|---|---|---:|---|---|
| Army Painter | Glittering Green | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Greedy Gold | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Vallejo | Glaze Medium | 2 | Game Color Auxiliary | Model Color | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Bright Gold | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Vallejo | Airbrush Thinner | 2 | Game Color Auxiliary | Model Air | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Evil Chrome | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Gloss Varnish | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Matt Varnish | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Gemstone Red | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Plate Mail Metal | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Rough Iron | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Shining Silver | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Tainted Gold | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | True Copper | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Weapon Bronze | 2 | Air | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Vallejo | Metal Medium | 2 | Game Color Metallic | Model Color | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Vallejo | Decal Fix | 1 | Model Color Related | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Vallejo | Decal Softener | 1 | Model Color Related | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Vallejo | Drying Retarder | 1 | Model Color | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Vallejo | Gloss Medium | 1 | Model Color | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Vallejo | Gloss Poly. Varnish | 1 | Game Color Special FX | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Vallejo | Gloss Varnish | 1 | Model Color | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Vallejo | Glossy Varnish | 1 | Model Color | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Abyssal Blue | 1 | Fanatic | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |
| Army Painter | Aztec Gold | 1 | Speedpaint | Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color. |

## Recommended Workflow

1. Filter the CSV by `CAN_PROPAGATE` first. These are easy wins.
2. Then filter by `ENTIRE_CLUSTER_MISSING` and prioritize clusters with multiple rows.
3. Research one Hex/RGB value per cluster instead of one value per row.
4. Do not blindly copy values across product lines if the paint is a medium, varnish, primer, metallic, effect paint, or technical paint.
