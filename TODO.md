# TODO

## Now
- [x] Add error handling — send error message to Telegram instead of silence
- [x] `/addsource <name> <url> [aggregator]` — add sources via bot
- [x] `/addcategory <name> <description>` — add categories via bot
- [x] `/removesource <name>` — remove a source via bot
- [x] `/removecategory <name>` — remove a category via bot
- [x] `/categories` — list configured categories

## Soon
- [ ] `/report month` — extended lookahead (30 days)
- [ ] `/test <url>` — test-scrape a URL without adding to config
- [ ] `/upcoming` — things in the next 1-2 months that need advance booking
- [ ] Update README to match current state

## Later
- [ ] `/status` — last run, token usage, errors
- [ ] Monthly scheduled report (separate from weekly)
- [ ] Better error messages per source (which failed, why)
- [ ] Web UI for config management
