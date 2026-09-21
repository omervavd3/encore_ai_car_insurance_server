# Part B — Flow Design & Build Sheet

Conversation Flow Agent for car insurance onboarding, calling the Part A API.

**7 nodes total**: Start, 4 × Conversation, 1 × API Call, End (+ 1 optional Speak Message on the
hard-failure path). The assignment's "past ~7 nodes you're overengineering it" is the constraint that
shapes the whole design — each conversation node owns one coherent chunk of dialogue rather than one
question.

> Field names in the platform UI are not documented here where I haven't seen them. Everything below is
> described by *what it must do*; map it onto whatever the actual node config calls it.

---

## Graph

```
                    Start
                      │
                      ▼
        ┌────► [A] Conversation ── insurance_type + license_plate
        │             │
        │             ▼
        │      [API] POST /vehicle/info
        │        │      │
        │        │      └── error: not_found / invalid ──┐
        │        │      └── error: unavailable ──► Speak ──► End
        │        ▼ success                                │
        │    [B] Conversation ── confirm vehicle          │
        │         + full_name / phone / email             │
        │             │                                   │
        │             ├── insurance_type == "comprehensive" ──► [C] Conversation ── coverage
        │             │                                                │
        │             └── else ─────────────────────────────►──────────┤
        │                                                              ▼
        │                                          [D] Conversation ── summary + confirm
        └──────────────── "wants to change plate/type" ◄────┤     │
                          "wants to change details" ──► B   │     ▼
                          "wants to change coverage" ─► C   │    End
```

---

## Variables saved across the flow

All collected via the **conversation node's save tool** — no Collect Node anywhere (explicit assignment
requirement).

| Variable | Saved in | Values / format |
|---|---|---|
| `insurance_type` | A | `comprehensive` \| `mandatory` |
| `license_plate` | A | 7–8 digits |
| vehicle details | API response | `manufacturer`, `model`, `year`, `color` |
| `full_name` | B | free text |
| `phone` | B | validated phone number |
| `email` | B | validated email address |
| `coverage_options` | C | multi-select: windshield, extended third-party, replacement vehicle |

---

## Start — initial greeting

**Does:** Welcome message only.

**Configure:** The greeting text. Nothing else — don't try to collect the insurance type here; A does
that so the question and the save live in the same node.

**Edge out:** Unconditional → **A**.

---

## [A] Conversation — intake (insurance type + license plate)

**Covers flow step 1 and the first half of step 2.**

**Does:** Asks which insurance type the user wants and for the license plate, saving both as they come
up. Also the landing point for retries — when the API says the plate is unknown, or when the user
later asks to change the plate or insurance type from the summary.

**Configure:**
- **Save fields:** `insurance_type` (constrained to `comprehensive` / `mandatory`), `license_plate`.
- **Instructions:**
  - Accept both values in a single message if the user volunteers them, and don't re-ask for anything
    already saved. This is the agentic payoff — a scripted flow would force two turns here.
  - Plate format is 7–8 digits; if the user gives obvious junk, re-ask before burning an API call.
  - If arriving with an error from the API step, apologize and re-ask only the plate — the insurance
    type is still valid.
  - If arriving from the summary, address only what the user wants to change.

**Exit (LLM-evaluated):** "the user has provided both an insurance type and a license plate" → **API**.

LLM exit rather than deterministic because the judgment is conversational — the user might say
"comprehensive for my Corolla, 12345678" or spread it over three turns with a side question in between.

---

## [API] API Call — POST /vehicle/info

**Covers the API call in flow step 2.**

**Does:** Calls the Part A service with the saved plate and puts the vehicle details into the flow.

**Configure:**
- **Method/URL:** `POST https://<your-cloud-url>/vehicle/info`
- **Headers:** `Content-Type: application/json`, `X-API-Key: <your key>`
- **Body:** `{"license_plate": "{{license_plate}}"}`

**Routing — deterministic, not LLM.** This is data, not judgment:

| Condition | Goes to |
|---|---|
| `success == true` | **B** |
| `error_code` = `vehicle_not_found` | **A** (re-ask plate) |
| `error_code` = `invalid_license_plate` | **A** (re-ask plate) |
| `error_code` = `upstream_unavailable` | **Speak Message** → End |
| `error_code` = `upstream_error` | **Speak Message** → End |

This covers all three error cases the assignment requires: vehicle not found, validation failed, API not
responding.

> ### ⚠️ Check this before building the rest
> The Part A service returns **HTTP 200 on every error** (see `app/routers/vehicle.py` — the `_error()`
> helper is returned, not raised). So if the API node's success/error routing keys off the **status
> code**, every failure will take the success edge and the not-found branch will never fire.
>
> Two ways out, pick one:
> 1. Branch on the **response body**: `success == false`, then on `error_code`.
> 2. Change the service to return real HTTP status codes (400/404/502) and branch on status.
>
> Verify which the API node actually supports before wiring the error edges.

---

## [B] Conversation — vehicle confirmation + customer details

**Covers the rest of flow step 2 and all of step 3.**

**Does:** Two jobs in one node — shows the vehicle the API returned and gets confirmation it's the right
car, then collects the customer's name, phone and email. Merging them keeps the graph inside the node
budget and reads naturally: "Found a white 2020 Toyota Corolla — is that yours? Great, let's get your
details."

**Configure:**
- **Save fields:** `full_name`, `phone`, `email`.
- **Instructions:**
  - Open by displaying the returned vehicle from the API response variables
    (`manufacturer`, `model`, `year`, `color`) and ask the user to confirm it.
  - Validation lives here: phone and email must be well-formed, and the node re-asks conversationally
    on a malformed value instead of saving it.
  - If arriving back from the summary, only address the field the user wants to change — everything
    already saved stays saved.

**Exits (LLM-evaluated):**
| Condition | Goes to |
|---|---|
| "vehicle confirmed and name, phone and email are all collected and valid" | edge below |
| "the user says this is not their vehicle / wrong plate" | **A** |

**Edge out — deterministic (expression):**
- `insurance_type == "comprehensive"` → **C**
- otherwise → **D**

This is the clearest deterministic edge in the flow: coverage eligibility is business logic, not
conversational judgment, so it must not be an LLM exit. Expect to be asked about exactly this in the
interview.

---

## [C] Conversation — additional coverage (comprehensive only)

**Covers flow step 4.** Mandatory-insurance users never reach this node.

**Does:** Offers the three add-ons and saves the selection.

**Configure:**
- **Save field:** `coverage_options` — multi-select over windshield, extended third-party,
  replacement vehicle.
- **Instructions:** Present all three, allow any combination including none, and briefly answer
  questions about what each one covers before saving.

**Exit (LLM-evaluated):** "the user has chosen their coverage options or explicitly declined all of
them" → **D**.

---

## [D] Conversation — summary & confirmation

**Covers flow step 5, and satisfies the "user can correct their own details" requirement.**

**Does:** Renders every saved variable back to the user and asks for final confirmation. Critically,
it's not a dead end — a user who spots a wrong email can fix it from here.

**Configure:**
- **Instructions:**
  - Display insurance type, vehicle details, name, phone, email, and coverage options.
  - If `insurance_type` is mandatory, omit the coverage section rather than showing it blank.
    (Handling this in the prompt avoids spending a whole Set Variables node on it.)
  - Invite corrections explicitly — "does everything look right, or would you like to change
    anything?"

**Exits (all LLM-evaluated — correction requests are conversational judgment):**
| Condition | Goes to |
|---|---|
| user confirms everything is correct | **End** |
| wants to fix name, phone or email | **B** |
| wants to change coverage options | **C** |
| wants to change plate or insurance type | **A** |

---

## Speak Message — service unavailable (optional 8th node)

**Does:** Fixed apology when the vehicle registry is unreachable, with no LLM involved — you don't want
a model improvising during a failure.

**Configure:** A short "we can't reach the vehicle registry right now, please try again shortly"
message.

**Edge out:** → **End**.

**Alternative:** use a **Transfer** node instead to hand off to a human. Either is defensible; Transfer
is the more realistic production answer, Speak Message is the simpler one.

---

## Nodes deliberately not used

| Node | Why not |
|---|---|
| **Collect** | Explicitly forbidden by the assignment — all fields come from the conversation node's save tool. |
| **Set Variables** | Only plausible use was blanking coverage for mandatory users; cheaper to handle in D's prompt. |
| **Code** | A regex validator for phone/email is the deterministic alternative to validating in B's instructions. Costs a node plus a round-trip, and B still has to do the re-ask. Judgment call — be ready to explain choosing the conversational route. |
| **Computer Use** | Irrelevant to this flow. |
| **Transfer** | Optional, on the hard-failure path only. |

---

## Requirements checklist

| Requirement | Where it's met |
|---|---|
| Conversation Flow Agent, not Single Prompt | Agent type at creation |
| API integration, success **and** error paths | API node routing table |
| Deterministic edges for business logic | `insurance_type == "comprehensive"` (B → C/D); API error-code routing |
| LLM exits for conversational judgment | A, B, C, D exit conditions |
| No Collect Node | All fields via conversation save tool |
| Input validation | Plate format in A; phone/email in B; authoritative plate check by the API |
| User can correct their own details | D's three back-edges to A, B and C |
| Error: API not responding | `upstream_unavailable` → Speak → End |
| Error: validation failed | `invalid_license_plate` → A |
| Error: vehicle not found | `vehicle_not_found` → A |
| ~7 nodes | 7, or 8 with the Speak Message |

---

## Before you start building

1. **Deploy the Part A service** and confirm it's reachable over public HTTPS — the platform has to call
   it from the outside.
2. **Set `API_KEY` in the deployment environment.** If it's empty, `app/auth.py` rejects every request
   with 401, including the platform's.
3. **Confirm the API node can send a custom header** (`X-API-Key`). The auth isn't required by the
   assignment — it's your own "I don't leave endpoints open" choice — but it has to work end to end.
4. **Settle the status-code question** in the API node warning above.
5. **Verify the upstream really 404s** on an unknown plate. The `vehicle_not_found` branch depends on
   it, and it's currently an untested assumption in the wrapper.
6. **Turn on Test Agent's debug view** (⋮ menu → Show debug info) before your first test run — it shows
   which node you're on, what's saved, and why a branch fired.
