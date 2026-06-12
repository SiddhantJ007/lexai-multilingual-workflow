# Build Notes

This is not meant to be a prompt diary.

I do not think that is the useful way to present AI-assisted engineering work. The real value is not that I can type a prompt. The value is that I can understand a problem deeply, break it down fast, use AI where it actually helps, reject weak outputs, keep pushing through errors, and turn that whole process into something that works in the real world.

That is how I approached LexAi.

I wanted this file to reflect that more honestly.

## How I use AI in this project

I do not use AI as a substitute for engineering judgment. I use it as a force multiplier.

For me, that usually means:

- understanding the real problem first, before touching code
- getting fast drafts, boilerplate, or option space from AI
- reviewing outputs critically instead of accepting them at face value
- debugging through logs, behavior, architecture, and constraints
- iterating until the result matches the product need, not just until the code runs

So the important part is not “AI wrote this.” The important part is:

- I knew what had to be built
- I knew what was broken
- I knew what tradeoff I was making
- I knew when the result was wrong
- I kept refining it until it became right enough to ship as a public demo

That is the lens I would want someone to use when reading this repo.

## What I was actually trying to build

LexAi was not just a translation page.

What mattered to me was the workflow around translation:

- input comes in
- AI improves or interprets it where needed
- translation happens
- the user can judge the result
- a good result can branch into alternatives
- a bad result can feed back into the system for regeneration
- results can be saved, filtered, and exported

That is a more interesting product problem than “call an API and print text.”

The public version of the repo had to preserve that core loop while also being safe to publish and easy for recruiters to try.

## Where AI genuinely helped

AI was useful in the places where speed matters but blind speed is dangerous if you do not review carefully.

Examples from this project:

- restructuring the project for public deployment
- cleaning up and sanitizing old code paths
- migrating the backend toward Vercel compatibility
- scaffolding test coverage and CI
- tightening prompts and error handling
- iterating on frontend workflow details quickly

But the actual engineering work was still in:

- deciding what to keep and what to remove
- tracing real failures through logs
- understanding deployment constraints
- noticing when the behavior drifted from the original product intent
- correcting prompts when outputs were semantically wrong
- knowing when a “working” solution was still not acceptable

That distinction matters to me.

## What this project says about how I work

I like working at two levels at once:

- high level: product shape, deployment strategy, user flow, scope control
- deep level: route behavior, environment variables, request handling, persistence, failure modes, small UX problems

That combination is important in a project like this.

If I only worked at the high level, the demo would sound good and break in practice.

If I only worked at the low level, the code might run but the repo would not communicate a meaningful product.

The work here required both.

## Problem solving style

One thing I care about a lot is staying with the problem.

A lot of engineering work is not glamorous. It is:

- deployment fails
- config is wrong
- backend route works locally and fails in production
- browser reports a CORS error but the real problem is a 500
- OCR cannot be supported the way it originally was
- translation output is technically valid but semantically wrong

That is the real job.

With LexAi, I kept working through those layers instead of stopping at the first “almost working” state.

That included:

- fixing backend entrypoint and Vercel structure issues
- making database failures non-fatal at startup
- switching DeepL auth to the current header-based method
- restoring the OpenAI + DeepL workflow instead of taking the easy fallback path
- fixing response serialization bugs that surfaced as frontend fetch failures
- tightening regeneration prompts when user critique started distorting meaning
- improving UX details like focus, scrolling, spinners, export behavior, and quota visibility

That persistence is part of the engineering work just as much as the final code is.

## Feature notes

### Public live demo deployment

The challenge here was not just “deploy it somewhere.”

The challenge was:

- make it public
- make it usable without local setup
- remove private infrastructure assumptions
- keep the backend real
- keep the repo clean enough for portfolio review

AI helped accelerate config and restructuring, but I still had to reason through the deployment shape, understand Vercel’s serverless expectations, and respond to real failures from actual deploy logs.

What I care about here is that the final system is understandable:

- static frontend
- FastAPI backend
- environment-driven configuration
- Postgres-compatible persistence

That is a clean story.

### Translation and regeneration quality

This was one of the most important parts to get right because it reveals whether the workflow has real intelligence or just stitched-together API calls.

I wanted the system to behave like this:

- DeepL remains important to translation quality
- OpenAI acts as the intelligence layer around it
- user feedback should improve the result, not replace the original meaning

That sounds simple, but it is not simple in practice.

The hard part was noticing when the regeneration loop started obeying the critique too literally and drifting away from the original phrase. That is where prompting becomes engineering: not writing something flashy, but tightening constraints based on observed failure.

So when I saw that a critique like “make it more context related to attract the locals” risked changing the meaning of the source phrase, I treated that as a product and system bug, not just a model quirk.

That is exactly the kind of thing I would want to discuss in an interview because it shows I do not confuse model output with correctness.

### Feedback loop and alternatives

I cared about preserving the interaction loop because it says more about product thinking than a one-shot output demo.

The good path and the bad path both matter:

- good result -> save -> ask if the user wants more options
- bad result -> ask what is wrong -> regenerate based on that feedback

I also wanted those outputs to remain traceable through saved history and export, because otherwise the workflow loses a lot of its practical value.

This is a good example of where AI can help write pieces of the implementation quickly, but the real design still comes from understanding what the product loop is supposed to feel like.

### Serverless-safe persistence

Moving away from local SQLite was not just a deployment detail. It changed how the demo keeps state.

I wanted:

- per-session separation
- live persistence
- exportable history
- no reliance on local files

That meant the database layer had to be adapted for a hosted environment, and the app had to fail gracefully when the database was not reachable.

That is another example of engineering ownership: not just getting the happy path working, but deciding what should happen when part of the system is down.

### Frontend polish

A recruiter usually experiences the frontend first, so small details matter more than people think.

I treated the frontend as part of the engineering quality, not decoration.

That included:

- backend connection state
- visible loading states
- focus and scroll behavior
- usable quota feedback
- clean navigation
- honest error messages

None of those things are individually dramatic, but together they change whether the app feels reliable or fragile.

I like that kind of work because it sits right at the boundary between implementation quality and user trust.

## What I learned about using AI well

The biggest lesson is that AI looks strongest when the human driving it is strongest.

If I am vague, impatient, or not paying attention to failure modes, AI just helps me make mistakes faster.

If I am clear about:

- the system goal
- the constraints
- what “good” looks like
- what broke
- what tradeoff is acceptable

then AI becomes genuinely powerful.

That is the skill I care about building and showing.

Not “I used AI.”

More like:

- I used AI dynamically
- I used it fast
- I used it across product, code, debugging, and docs
- I knew when to trust it and when not to
- I kept enough conceptual depth to guide it instead of being guided by it

## Engineering ownership

If someone asked me what part of this project is “mine,” my answer would be: the decisions, the direction, the corrections, and the final standard.

That includes:

- deciding what the public repo should be
- choosing what to sanitize
- shaping the live deployment
- preserving the right product behavior
- catching incorrect outputs
- tightening prompts
- restoring missing features
- deciding what limitations to expose honestly
- adding testing, CI, security notes, deployment notes, and engineering docs

AI helped me move faster, but the system still needed engineering ownership at every step.

## The process how I would describe

If I had to summarize the process behind this repo, I would put it this way:

1. I understood the original product and what was worth preserving.
2. I reduced scope aggressively so the public version stayed honest and safe.
3. I rebuilt the deployment story around a live recruiter-usable demo.
4. I used AI to accelerate implementation, debugging, and documentation.
5. I kept reviewing outputs against real constraints instead of accepting the first working draft.
6. I iterated on semantics, infrastructure, persistence, UX, testing, and documentation until the project looked like engineering work rather than just AI output.

That is really what I want this file to show.

Not every prompt.

Not performative secrecy about using AI either.

Just the actual process:

- understand deeply
- move fast
- stay critical
- solve the real problem
- optimize continuously
- own the result
