# Beställningsförslag för lagret

Typed answer (`mapping`, partial reward per article). 3-6 articles with stock, reserved units, incoming deliveries (only those arriving by a cut-off date count), a minimum level and a pack size; order the fewest whole packs that reach the minimum, or 0. Replaces the single-article multiple-choice `inventory_order`.
Independent test: recomputes every article from the table parsed from the prompt, counting packs up one at a time.

Run `python3 -m svrl.cli demo inventory_reorder` and `python3 -m svrl.cli check inventory_reorder`. Synthetic, Apache-2.0.
