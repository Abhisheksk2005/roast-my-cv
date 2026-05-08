# ElevenLabs Client tool parameters — copy-paste

Use **Client** execution. Do **not** add `session_id` here (the Donald web app injects it).

Ready-made JSON (dashboard-style `parameters` array): `elevenlabs-client-tools.json` — includes `research_degree` and `save_roast_quote`.

If your builder only offers **string** per row, use **string** for everything; the app coerces numeric strings for `graduation_year`, `salary`, `years_experience`, and `tuition_paid`. If you have **number** / **integer**, use that for those fields.

---

## Tool: `save_roast_quote`

| Field in UI | What to enter |
|-------------|----------------|
| **Identifier** | `quote` |
| **Data type** | string |
| **Required** | Yes |
| **Value type** | LLM Prompt (or whatever maps “describe extraction”) |
| **Description** | Extract Donald’s single best roast one-liner from **Phase 3 (the roast only)** — not from the post-roast AI survival tips. Verbatim, most screenshot-worthy line, short string. No session_id. |
| **Enum** | *(leave empty)* |

---

## Tool: `research_degree`

Add **one row per identifier** below (all top-level on the tool). The browser bundles them into a `profile` object for the API.

### `degree`

| Field | Value |
|-------|--------|
| Identifier | `degree` |
| Data type | string |
| Required | Yes |
| Description | From the live transcript: the user’s major, field of study, or degree name exactly as they stated it (e.g. “Communications”, “Computer Science”, “MBA”). If unclear, infer the closest standard label they implied. Never invent a degree they did not describe. |

### `university`

| Field | Value |
|-------|--------|
| Identifier | `university` |
| Data type | string |
| Required | Yes |
| Description | From the transcript: the college or university name they said they attended. Use their wording. If they only said “a state school”, put that phrase—do not make up a specific school name. |

### `graduation_year`

| Field | Value |
|-------|--------|
| Identifier | `graduation_year` |
| Data type | string *(or integer if available)* |
| Required | Yes |
| Description | Four-digit graduation year they gave (e.g. 2021). If they said “last year”, convert using the current conversation context to a year. If unknown, use 0. |

### `current_job`

| Field | Value |
|-------|--------|
| Identifier | `current_job` |
| Data type | string |
| Required | Yes |
| Description | Their current job title or role exactly as described in the call (e.g. “marketing coordinator”, “software engineer”). Not the employer name unless that’s all they gave. |

### `name`

| Field | Value |
|-------|--------|
| Identifier | `name` |
| Data type | string |
| Required | No |
| Description | Their first name or how they asked to be called, if mentioned; otherwise empty string. |

### `current_company`

| Field | Value |
|-------|--------|
| Identifier | `current_company` |
| Data type | string |
| Required | No |
| Description | Employer or company name if they said it; otherwise empty string. |

### `salary`

| Field | Value |
|-------|--------|
| Identifier | `salary` |
| Data type | string *(or number)* |
| Required | No |
| Description | Annual salary in USD as a whole number if they stated it or a clear range (use midpoint). If not discussed, leave empty or omit. Do not fabricate. |

### `years_experience`

| Field | Value |
|-------|--------|
| Identifier | `years_experience` |
| Data type | string *(or number)* |
| Required | No |
| Description | Total years in this role or field they mentioned. Integer. If not stated, leave empty or omit. |

### `country_or_region`

| Field | Value |
|-------|--------|
| Identifier | `country_or_region` |
| Data type | string |
| Required | No |
| Description | Where they live or work (e.g. UK, Texas). Drives local salary/tuition search. |

### `currency_code`

| Field | Value |
|-------|--------|
| Identifier | `currency_code` |
| Data type | string |
| Required | No |
| Description | ISO 4217: **GBP**, **USD**, **EUR**, etc. Must match how they stated money (£ → GBP). |

### `tuition_paid`

| Field | Value |
|-------|--------|
| Identifier | `tuition_paid` |
| Data type | string *(or number)* |
| Required | No |
| Description | Total tuition/fees they paid or are paying for the degree (whole number in **major units** of `currency_code`). If they only know annual fees, put that number and set `tuition_is_total` to false. |

### `tuition_is_total`

| Field | Value |
|-------|--------|
| Identifier | `tuition_is_total` |
| Data type | string *(or boolean if supported)* |
| Required | No |
| Description | `true` if `tuition_paid` is full degree cost; `false` if annual/per-year (server scales to approximate total). Default true. |

### `source`

| Field | Value |
|-------|--------|
| Identifier | `source` |
| Data type | string |
| Required | No |
| Description | Always the literal word: voice |

---

## Enum values

Leave **empty** for all of these unless you want to constrain something (e.g. `source` enum: `voice` only).

---

## Alternative: single `profile` object

If ElevenLabs lets you add **one parameter** of type **object** / **JSON** with nested properties, define **nested** properties matching the identifiers above under `profile`. The Donald client also accepts `{ "profile": { ... } }` from the model. If the UI only allows flat parameters, use the **one row per field** list above—that still works with our normalizer.
