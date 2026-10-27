# Minsta lagerbeställning

Calculate the smallest whole-pack order that leaves a stated number of available
units after accounting for reservations. Includes cases where no order is needed.
Exactly one of four unit counts satisfies both sufficiency and minimality.

Run `python3 -m svrl.cli demo inventory_order` and `python3 -m svrl.cli smoke inventory_order`.
Independent tests enumerate legal pack purchases and choose the first sufficient
one. Own synthetic generator: Apache-2.0. No external inventory system.
Limitation: one product, no lead times, incoming shipments or warehouse capacity.
