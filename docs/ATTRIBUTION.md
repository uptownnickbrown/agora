# Attribution

## OpenStax Principles of Microeconomics 3e

The learning-objective graph in `backend/app/pedagogy/bank.py` is adapted from
the chapter objectives of OpenStax *Principles of Microeconomics 3e*, © Rice
University, licensed under Creative Commons Attribution 4.0 International
(CC BY 4.0). https://openstax.org/details/books/principles-microeconomics-3e

Changes: objectives were paraphrased, condensed, rewritten against Bloom's
taxonomy, and re-mapped onto the Agora seven-week arc. The tutor-check
question bank is original work written for this project.

`backend/app/pedagogy/openstax.py` contains the verbatim "Key Concepts and
Summary" text of chapters 2, 3, 5, 7-13 of the same book (CC BY 4.0),
fetched by `backend/scripts/scrape_openstax.py`. It grounds Professor Pip's
chat answers and on-the-fly generated practice questions in the course text.

## Game art

All images under `frontend/public/assets/` were generated with Google Gemini
(`gemini-3-pro-image`) via the pipeline in `scripts/generate_assets.py` and
`scripts/assetlib.py`, then post-processed (chroma-key background removal,
crop, resize) for this project. The `ui/felt_texture.png` tile and the PWA
icon compositions (`brand/icon_192.png`, `brand/icon_512.png`) are procedural.

## Design lineage

The classroom-experiment designs behind the weekly events (continuous double
auctions, price-control experiments, common-pool resource games, sealed-bid
auctions) follow the experimental-economics literature; see spec §15.
