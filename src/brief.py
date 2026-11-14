"""GTM brief content (kept as data so the page and the markdown export share one source)."""

ICP = [
    {"segment": "Prediction-market aggregators and data APIs",
     "pain": "They sell one view across Kalshi, Polymarket and others. Every new market has to be linked to its twin by hand or by brittle title rules.",
     "trigger": "A new venue or a new category (sports, macro) doubles the matching backlog.",
     "buyer": "CTO or head of data"},
    {"segment": "Brokerages and sportsbooks adding event contracts",
     "pain": "They list contracts from several exchanges and must avoid showing two listings as the same bet when the terms differ.",
     "trigger": "Launching a prediction-market tab or adding a second venue.",
     "buyer": "Head of product, event contracts"},
    {"segment": "Market makers and arbitrage desks",
     "pain": "Cross-venue spreads are only real if both legs settle on the same outcome. A false match is a naked position.",
     "trigger": "Expanding coverage beyond a handful of hand-mapped markets.",
     "buyer": "Head of trading or quant lead"},
    {"segment": "Exchanges themselves",
     "pain": "Listing teams check new markets against competitors and their own catalog for duplicates and wording conflicts.",
     "trigger": "Thousands of new markets a week, mostly auto-generated.",
     "buyer": "Head of markets or listings ops"},
]

ACCOUNTS = [
    ("Dome", "Aggregator / API", "YC-backed unified API across prediction markets. Cross-venue market linking is the product."),
    ("PolyRouter", "Aggregator / API", "Unified prediction-market API that normalizes markets across venues."),
    ("pmxt", "Open-source library", "\"CCXT for prediction markets.\" Open-source, so a matching endpoint could become the default its users reach for."),
    ("FinFeedAPI", "Market-data vendor", "Sells prediction-market data next to traditional feeds; matched markets are a paid upgrade."),
    ("Predexon", "Analytics", "Prediction-market analytics; cross-venue comparisons need reliable pairs."),
    ("agg.market (Snag Solutions)", "Aggregator", "Consumer aggregator that routes users across venues."),
    ("Robinhood", "Brokerage", "Offers event contracts through Kalshi; adding venues means matching listings."),
    ("Coinbase", "Exchange / brokerage", "Kalshi partnership for event contracts; same listing problem at large scale."),
    ("DraftKings / FanDuel", "Sportsbooks", "Both launched prediction products; sports markets are the hardest to match (halves, props, seasons)."),
    ("Susquehanna (SIG)", "Market maker", "Kalshi's early market maker; cross-venue quoting depends on knowing which contracts are truly equal."),
]

PITCH_LINE = ("Jev tells you whether two markets are the same bet, a variant, or unrelated, with a calibrated "
              "probability, in under a quarter second, for about five cents per thousand pairs.")

OBJECTIONS = [
    ("\"We already use GPT or Claude for this.\"",
     "Jev returns a structured choice plus probabilities, with no prompt parsing, at $0.042 per million input tokens and free output. The trial runs both side by side on your pairs, so the comparison uses your data, not ours."),
    ("\"A wrong match costs us money.\"",
     "Route by confidence. Act automatically only when Jev is confident; send the rest to a reviewer. The three yes/no checks (same subject, same terms, same deadline) tell the reviewer exactly why a pair failed."),
    ("\"Our markets are different from your demo.\"",
     "That is why the trial starts with 200 to 500 of your own pairs and a locked test set we agree on before running anything."),
]

PLAYBOOK = [
    ("Day 0", "Kickoff", "Pick one workflow (listing dedup, arb leads, or catalog linking). Agree the success bar in writing, for example fewer than 2% false matches while catching 90% of true matches."),
    ("Days 1-2", "Data", "Pull 200 to 500 candidate pairs from their catalog. Label them together, or use pairs they already mapped. Split into a dev set and a locked test set."),
    ("Days 3-5", "Wire up", "Map their market fields into Jev's state. Start from this repo's question set. Tune instructions on the dev set only."),
    ("Days 6-10", "Shadow run", "Run Jev next to their current method on live traffic. Log every disagreement and review it with their team."),
    ("Days 11-14", "Readout", "Score the locked test set once. Report accuracy, false matches, missed matches, reviewer hours saved, and cost at their volume. Ask for the decision."),
]
