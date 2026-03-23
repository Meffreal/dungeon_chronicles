Set-Location backend
uvicorn main:app --reload --port 8000

# admin key online
# -vvxHMRyPK2mBQ8HvNDt5i_EJT1miI7w-asSNfNvedY

# claude code prompt

You are working on Dungeon Chronicles.

Read memory.md and strictly follow it.

Mode:
- Execution only
- No questions
- No brainstorming

Rules:
- Modify existing code only
- Use existing systems (combat, loot, DB)
- Respect architecture (models / routers / game)

When unsure:
- Make assumptions and continue

Output:
- Code
- Minimal explanation