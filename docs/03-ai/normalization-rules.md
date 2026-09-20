# Deterministic Posology Normalization Rules

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Module**: `core.domain.normalizer`  
**Guiding Tenet**: The LLM extracts raw strings. Deterministic regex & mapping tables normalize. The system never guesses.

---

## 1. Timing & Frequency Normalization Rules

Prescriptions in India employ two primary notation systems for intake frequency:
1. **Numerical Slot Shorthand** (e.g., `1-0-1`, `0-0-1`, `1-1-1`)
2. **Latin / Clinical Abbreviations** (e.g., `OD`, `BD`, `TDS`, `QID`, `HS`, `SOS`)

### 1.1 Canonical Numerical Slot Shorthand (3-Slot & 4-Slot)

Standard Indian clinical shorthand maps 3 slots to **Morning - Afternoon - Night** and 4 slots to **Morning - Afternoon - Evening - Night**.

| Raw Shorthand String (Normalized Case) | Regex Pattern | Morning | Afternoon | Evening | Night | Frequency/Day | SOS | Deterministic Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `1-0-0` | `^1-0-0$` | 1 | 0 | 0 | 0 | 1 | False | Normalized |
| `0-1-0` | `^0-1-0$` | 0 | 1 | 0 | 0 | 1 | False | Normalized |
| `0-0-1` | `^0-0-1$` | 0 | 0 | 0 | 1 | 1 | False | Normalized |
| `1-0-1` | `^1-0-1$` | 1 | 0 | 0 | 1 | 2 | False | Normalized |
| `1-1-1` | `^1-1-1$` | 1 | 1 | 0 | 1 | 3 | False | Normalized |
| `1-1-0` | `^1-1-0$` | 1 | 1 | 0 | 0 | 2 | False | Normalized |
| `0-1-1` | `^0-1-1$` | 0 | 1 | 0 | 1 | 2 | False | Normalized |
| `1-1-1-1` (4 slots) | `^1-1-1-1$` | 1 | 1 | 1 | 1 | 4 | False | Normalized |
| `1/2-0-1/2` (Fractional) | `^(?:1/2\|0\.5)-0-(?:1/2\|0\.5)$` | 0.5 | 0 | 0 | 0.5 | 1 | False | Normalized |

### 1.2 Latin / Clinical Abbreviation Dictionary

| Abbreviation | Expanded Medical Meaning | Morning | Afternoon | Evening | Night | Frequency/Day | SOS | Deterministic Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `OD` / `QD` | *Omni die* (Once daily) | 1 | 0 | 0 | 0 | 1 | False | Normalized |
| `BD` / `BID` | *Bis in die* (Twice daily) | 1 | 0 | 0 | 1 | 2 | False | Normalized |
| `TDS` / `TID` | *Ter die sumendum* (Three times daily) | 1 | 1 | 0 | 1 | 3 | False | Normalized |
| `QID` | *Quater in die* (Four times daily) | 1 | 1 | 1 | 1 | 4 | False | Normalized |
| `HS` / `BT` | *Hora somni* (At bedtime) | 0 | 0 | 0 | 1 | 1 | False | Normalized |
| `SOS` / `PRN` | *Si opus sit* (As needed / Emergency) | 0 | 0 | 0 | 0 | 0 | True | Normalized (SOS Flag Set) |
| `STAT` | *Statim* (Immediately, single dose) | 1 | 0 | 0 | 0 | 1 | False | Normalized (Immediate) |

### 1.3 Ambiguous or Unrecognized Timing Handling
Any pattern failing exact match against the tables above (e.g., `1-?-1`, `1-2`, `alternate day`, unreadable squiggles):
* `morning`, `afternoon`, `evening`, `night` = `0`
* `timing_uncertain` = `true`
* `requires_review` = `true`
* The system **refuses to guess** whether `1-2` means 1 or 2 tablets, or 1 in morning and 2 at night.

---

## 2. Meal Relationship Normalization

| Raw Extracted String Pattern | Canonical Meal Timing Enum | Action on Match |
| :--- | :--- | :--- |
| `(?:before\s+(?:food\|meal\|eating)\|empty\s+stomach\|AC\|BBF)` | `BEFORE_MEAL` | Sets `before_meal = true, after_meal = false` |
| `(?:after\s+(?:food\|meal\|eating)\|PC\|post\s+lunch)` | `AFTER_MEAL` | Sets `before_meal = false, after_meal = true` |
| `(?:with\s+(?:food\|meal))` | `WITH_MEAL` | Sets `before_meal = false, after_meal = false` |
| `(?:null\|unspecified\|none\|empty)` | `UNSPECIFIED` | Preserves `before_meal = null, after_meal = null` |

*Note*: `BBF` = Before Breakfast; `AC` = *Ante cibum* (Before meals); `PC` = *Post cibum* (After meals).

---

## 3. Duration Normalization Rules

Duration is deterministically parsed into an integer number of days:

```
Pattern: (?P<value>\d+)\s*(?P<unit>day|days|d|week|weeks|w|month|months|m)
```

* If unit is `day`/`days`/`d`: `duration_days = int(value)`
* If unit is `week`/`weeks`/`w`: `duration_days = int(value) * 7`
* If unit is `month`/`months`/`m`: `duration_days = int(value) * 30`
* If duration is missing or unparseable: `duration_days = null` (never default to 5 or 7 days).

---

## 4. Strength Unit Normalization

Allowed canonical metric units:
* `mg` (Milligrams)
* `mcg` (Micrograms)
* `g` / `gm` -> Normalized to `g` (Grams)
* `ml` (Milliliters)
* `IU` (International Units)
* `puffs` (Inhaler doses)
* `drops` (Ophthalmic / Otic)

If strength unit is missing or unmapped (e.g. `Tab 500` with no unit):
* Preserved as `strength_value = 500.0, strength_unit = null`
* Flagged with `requires_review = true` if the drug possesses multiple clinical dosage forms (e.g. 500mg vs 500IU).
