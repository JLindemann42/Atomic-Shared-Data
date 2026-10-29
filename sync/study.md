# Study coach: cards, scheduler and the `study` field (roadmap 2.6)

The study coach schedules the quiz questions a user gets wrong, and offers the ones that are due as a
review run from chat. It is a PRO feature on both platforms: any paid tier (PRO, PRO+ or Ultimate)
counts.

This file defines what both apps must agree on. It comes before either implementation, as D52 did
for favourites.

## Cards

A card is one skill about one element. Its key is `<skill>:<element key>`, for example
`periodic_group:bromine` or `isotope_neutrons:uranium`. The element key is the lower-case English key
the element files use. The skill is a Learning Games category whose generator can ask about one given
element:

| Skill | Asks |
| --- | --- |
| `element_classifications` | which family the element belongs to |
| `periodic_period` | its period |
| `periodic_group` | its group |
| `valence_electrons` | its valence electrons |
| `isotope_neutrons` | the neutrons in one of its isotopes |

A card is reviewed whenever a question about that skill and element is answered: in the Learning
Games, in a chat quiz run, or in a review run. A right answer rates Good (3) and a wrong one Again (1).
A question that names no single element (rankings, molar mass) does not feed a card.

## Scheduler

FSRS-5 with its published default parameters. The reference is `tools/fsrs_golden.py`, and
`golden/fsrs.tsv` holds the vectors both apps' tests check: stability and difficulty to 1e-9
relative, the interval to the day. The constants are DECAY −0.5, FACTOR 19/81 and desired retention
0.9. Stability has a floor of 0.01 days; intervals run from 1 day to 36,500. Intervals round half
up. A review less than a day after the last uses the same-day stability rule.

A card is due when its `due` time has passed. A review run takes the due cards most overdue first, by
how far past `due` they are relative to their interval, up to ten.

## Wire format

In the progress document `users/{uid}`, beside `xp`, `streak` and the rest:

```json
"study": {
  "cards": {
    "periodic_group:bromine": { "s": 5.869, "d": 5.273, "due": 1700518400000, "last": 1700086400000, "reps": 2, "lapses": 0 }
  }
}
```

- `s`: stability in days, a number.
- `d`: difficulty, 1 to 10.
- `due` and `last`: epoch milliseconds, numbers.
- `reps` and `lapses`: integers.

Android writes the field with `SetOptions.merge()`, which deep-merges the map. Windows writes it
with an update mask of `study`.

**Merge, per card:** the card with the later `last` wins. On a tie, the one with more `reps` wins,
and on a further tie the cloud copy. Cards are never deleted, so there is no removal record. A key
either platform does not recognise is carried through untouched. Unknown fields on a card are not
carried: a card is replaced whole.
