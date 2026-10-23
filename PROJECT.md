# Local Quest project brief

Status: generation workflow confirmed by the owner; remaining scope details are proposed. This folder develops the Local
Quest option without selecting it for the parent reusable starter.

## Product
Help students, newcomers, and visitors discover a walkable neighborhood through
short adventures tailored to their interests, available time, and budget.
Local businesses gain visibility and measurable engagement.

Example request: “I have 90 minutes and $20. Find coffee, art, and somewhere new.”
The response is a three-stop route with estimated costs, walking time, grounded
challenges, and a digital passport.

## Proposed first demo
- One walkable neighborhood; the exact area remains undecided.
- 10–15 curated locations with documented sources and checked opening hours.
- Form for duration, budget, and preferences; missing values use disclosed defaults.
- Three-stop quest with map, estimated spending, travel/visit time, and explanations.
- QR-based simulated check-ins and passport stamps.
- Dashboard distinguishing quest appearances, check-ins, and verified redemptions.
- Meaningful Snowflake top-10 retrieval/analytics and open-weight AI route planning
  and challenge generation.

## Core journey
1. Enter duration, budget, and preferences, with starting-location/time context.
2. Backend validates supplied values and fills missing duration with 90 minutes,
   budget with $30, and interests with no preference; disclose applied defaults.
3. Snowflake returns up to 10 ranked candidates. AI selects and orders three stops;
   backend verifies the proposal and returns a saved quest as JSON for display.
4. Follow the walking route and complete stop challenges/check-ins.
5. See passport progress and resulting business engagement metrics.

## Boundaries
- No payments, real monetary rewards, booking system, or automatic merchant outreach.
- No live crowd claims without a suitable data source.
- Do not invent offers, accessibility attributes, historical facts, or opening hours.
- Estimates are labeled; real prices and access conditions may change.
- No claim that a check-in proves a purchase or increased revenue.
- Social feeds, merchant self-service, and citywide coverage are stretch features.

## Acceptance criteria
- Selected stops exist in the approved dataset; no duplicate stops in one quest.
- A route respects the requested budget and time under its disclosed estimates,
  including walking and visits; check opening hours at expected arrival/departure.
- Infeasible requests return an explanation and proposed adjustments, not a fake route.
- Repeated check-in requests do not create duplicate stamps or counted events.
- AI challenges cite their supporting place records and contain no invented offers.
- Service failures are clearly surfaced and retries are bounded.
- Demo data and simulated activity are visibly labeled and excluded from real metrics.

## AI value
Select and order stops from Snowflake candidates to propose an efficient, relevant
quest, with challenges grounded in approved facts. Code verifies feasibility using
actual walking routes and catalog values; it owns authorization and reward eligibility.
The route is an AI-assisted proposal, not a guarantee of a global mathematical optimum.

## Hackathon target
Complete the scoped journey with labeled simulations where needed. Use
`docs/Deployment.md` to prepare, deploy, smoke check, and roll back the demo.
Public pilot and production scope will be decided separately if pursued.

## Decisions for the owner
- Neighborhood, starting-location fallback, currency code for the $30 default,
  departure-time policy, and data sources: [TO FILL]
- Team size, event deadline, and allowed advance preparation: [TO FILL]
- Budget, expected traffic, and latency target: [TO FILL]
- Authentication, deployment accounts, model runtime, and project license: [TO FILL]
- Retention policy and operating owner: [TO FILL]

## Hackathon
Desired prizes: Best Use of Snowflake and Best Open-Source AI Project.
Event: https://events.mlh.com/events/15095-hacktoberfest-hack-day-pomona-x-computer-science-society
Verify event-specific rules before implementation/submission. Record advance work.
