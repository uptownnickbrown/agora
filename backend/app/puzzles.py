"""The Common Threads puzzle bank (the Daily Ledger's daily game).

Connections-style: each puzzle is four groups of four terms, ordered easiest
(tier 0, gold) to trickiest (tier 3, plum). Written by hand — economics
vocabulary, Agora world flavor, and wordplay, with deliberate traps between
groups. Terms must be unique within a puzzle (enforced by a test).

Selection: worlds walk the bank in a seeded order, one puzzle per world day,
so a whole class shares the same board and can argue about it at lunch.
"""
from __future__ import annotations

# (category name, [four terms]) — index in the list IS the difficulty tier.
Puzzle = list[tuple[str, list[str]]]

PUZZLES: list[Puzzle] = [
    [  # 1
        ("Gathered in the Workshop", ["Grain", "Wood", "Wool", "Herbs"]),
        ("Shifts demand", ["Tastes", "Income", "Expectations", "Population"]),
        ("___ cost", ["Opportunity", "Sunk", "Fixed", "Marginal"]),
        ("___ market", ["Black", "Stock", "Flea", "Bull"]),
    ],
    [  # 2
        ("Places in the Agora", ["Docks", "Guild Hall", "Workshop", "Market Square"]),
        ("Shifts supply", ["Technology", "Input prices", "Weather", "Taxes"]),
        ("The -opolies", ["Monopoly", "Duopoly", "Oligopoly", "Monopsony"]),
        ("Price ___", ["Ceiling", "Floor", "War", "Tag"]),
    ],
    [  # 3
        ("Read in the Crier", ["Headline", "Decree", "Market report", "Gossip"]),
        ("Sends buyers rushing in", ["Fashion", "Festival", "Caravan", "Payday"]),
        ("Elasticity varieties", ["Price", "Income", "Cross", "Unitary"]),
        ("Invisible ___", ["Hand", "Ink", "Man", "Fence"]),
    ],
    [  # 4
        ("Crown interventions", ["Quota", "Levy", "Decree", "Edict"]),
        ("Factors of production", ["Land", "Labor", "Capital", "Enterprise"]),
        ("Ways to run an auction", ["English", "Dutch", "Sealed-bid", "Vickrey"]),
        ("Golden ___", ["Goose", "Handshake", "Ratio", "Age"]),
    ],
    [  # 5
        ("Finished goods", ["Bread", "Garments", "Tapestries", "Tools"]),
        ("On the order book", ["Bid", "Ask", "Spread", "Fill"]),
        ("Types of goods", ["Public", "Private", "Club", "Common"]),
        ("___ run", ["Bank", "Dry", "Trial", "Home"]),
    ],
    [  # 6
        ("A pigeon's day", ["Coo", "Preen", "Roost", "Peck"]),
        ("Shrinks the harvest", ["Drought", "Blight", "Bandits", "Frost"]),
        ("Cartel words", ["Collude", "Fix", "Ring", "Rig"]),
        ("Bear ___", ["Market", "Hug", "Trap", "Cub"]),
    ],
    [  # 7
        ("The cloth trade", ["Wool", "Cloth", "Garments", "Tapestries"]),
        ("Ways to pay", ["Coppers", "Barter", "Credit", "IOU"]),
        ("Game theory", ["Nash", "Payoff", "Dominant", "Equilibrium"]),
        ("___ trade", ["Free", "Fair", "Horse", "Day"]),
    ],
    [  # 8
        ("Fishing tackle", ["Cast", "Hook", "Bobber", "Bait"]),
        ("Tragedy of the commons", ["Open access", "Overfishing", "Quota", "Collapse"]),
        ("___ surplus", ["Consumer", "Producer", "Trade", "Budget"]),
        ("___ line", ["Bottom", "Bread", "Poverty", "Picket"]),
    ],
    [  # 9
        ("Boutique swagger", ["Awning", "Sign", "Fountain", "Peacock"]),
        ("Workshop verbs", ["Gather", "Craft", "Build", "Upgrade"]),
        ("___ curve", ["Demand", "Supply", "Learning", "Bell"]),
        ("Curves with surnames", ["Laffer", "Lorenz", "Phillips", "Engel"]),
    ],
    [  # 10
        ("Pulled from the water", ["Trout", "Whiskerjaw", "Leviathan", "Boot"]),
        ("Market day verbs", ["Buy", "Sell", "Haggle", "Browse"]),
        ("Gray Skies vocabulary", ["Smog", "Scrubber", "Soot", "Levy"]),
        ("___ money", ["Pocket", "Hush", "Seed", "Smart"]),
    ],
    [  # 11
        ("Ore to anvil", ["Ore", "Iron", "Smelter", "Smithy"]),
        ("Shopkeeping", ["Shelf", "Stock", "Till", "Window"]),
        ("Kinds of capital", ["Human", "Physical", "Venture", "Social"]),
        ("___ interest", ["Self", "Compound", "Vested", "Public"]),
    ],
    [  # 12
        ("Guild Hall business", ["Compact", "License", "Loan", "Boutique"]),
        ("When the ceiling binds", ["Shortage", "Queues", "Rationing", "Scalpers"]),
        ("Trade across borders", ["Import", "Export", "Tariff", "Embargo"]),
        ("___ bank", ["Piggy", "Blood", "Food", "River"]),
    ],
    [  # 13
        ("Crier headlines", ["Festival", "Drought", "Levy", "Tournament"]),
        ("It pays to specialize", ["Specialize", "Aptitude", "Advantage", "Exchange"]),
        ("Goods, by income", ["Normal", "Inferior", "Luxury", "Necessity"]),
        ("___ share", ["Market", "Lion's", "Fair", "Time"]),
    ],
    [  # 14
        ("Measured in coppers", ["Price", "Wage", "Upkeep", "Fine"]),
        ("Commons verbs", ["Share", "Deplete", "Graze", "Overuse"]),
        ("Marginal ___", ["Cost", "Revenue", "Utility", "Product"]),
        ("___ economy", ["Gig", "Shadow", "Command", "Mixed"]),
    ],
    [  # 15
        ("Field to table", ["Grain", "Flour", "Mill", "Bread"]),
        ("Market moods", ["Bull", "Bear", "Panic", "Rally"]),
        ("Auction day cast", ["Bidder", "Crier", "Reserve", "Lot"]),
        ("___ boom", ["Sonic", "Baby", "Oil", "Housing"]),
    ],
    [  # 16
        ("The herbalist's chain", ["Herbs", "Medicine", "Apothecary", "Garden"]),
        ("Words for scarce", ["Rare", "Tight", "Short", "Dear"]),
        ("Taxes, by shape", ["Flat", "Progressive", "Regressive", "Lump-sum"]),
        ("___ value", ["Face", "Market", "Street", "Sentimental"]),
    ],
    [  # 17
        ("Loom country", ["Wool", "Loom", "Cloth", "Tailor"]),
        ("Life of an order", ["Post", "Fill", "Expire", "Withdraw"]),
        ("What monopolies do", ["Restrict", "Markup", "Exclude", "Gouge"]),
        ("___ ceiling", ["Price", "Glass", "Debt", "Cathedral"]),
    ],
    [  # 18
        ("Leaderboard fodder", ["Wealth", "Houses", "Streaks", "Catches"]),
        ("Ways coins leave you", ["Splurge", "Upkeep", "Fine", "Tithe"]),
        ("Inequality math", ["Gini", "Gap", "Quintile", "Percentile"]),
        ("Flush with coin", ["Loaded", "Flush", "Minted", "Rolling"]),
    ],
    [  # 19
        ("Tournament week", ["Market Wars", "Houses", "Glory", "Spoils"]),
        ("Stops on a trade route", ["Saltharbor", "Milltown", "Crossroads", "Agora"]),
        ("What you give up", ["Tradeoff", "Forgone", "Alternative", "Sacrifice"]),
        ("___ war", ["Price", "Bidding", "Trade", "Tug-of"]),
    ],
    [  # 20
        ("Tutor time", ["Quiz", "Check", "Mastery", "Feedback"]),
        ("Diminishing returns", ["Workers", "Crowding", "Bottleneck", "Fatigue"]),
        ("A commons is…", ["Rival", "Open", "Finite", "Shared"]),
        ("___ floor", ["Price", "Dance", "Ocean", "Shop"]),
    ],
    [  # 21
        ("Timberline", ["Wood", "Lumber", "Timber", "Woodlot"]),
        ("Fancy purchases", ["Luxury", "Finery", "Swagger", "Peacock"]),
        ("Income words", ["Wage", "Salary", "Earnings", "Takings"]),
        ("Free ___", ["Market", "Rider", "Lunch", "Range"]),
    ],
    [  # 22
        ("Smithy stock", ["Iron", "Lumber", "Tools", "Forge"]),
        ("Ways to ration", ["Queue", "Lottery", "Coupon", "Favoritism"]),
        ("Efficiency words", ["Pareto", "Optimal", "Lean", "Frontier"]),
        ("Money, colloquially", ["Dough", "Cheddar", "Clams", "Loot"]),
    ],
    [  # 23
        ("What the night brings", ["Close", "Report", "Restock", "Dawn"]),
        ("Barriers to entry", ["License", "Charter", "Patent", "Moat"]),
        ("Takeover talk", ["Horizontal", "Vertical", "Hostile", "Friendly"]),
        ("___ Street", ["Wall", "Main", "Easy", "High"]),
    ],
    [  # 24
        ("Weigh station", ["Dram", "Scale", "Weight", "Whopper"]),
        ("Signals of quality", ["Brand", "Warranty", "Reputation", "Badge"]),
        ("Asymmetric information", ["Lemons", "Signaling", "Screening", "Moral hazard"]),
        ("___ check", ["Reality", "Rain", "Sanity", "Fact"]),
    ],
    [  # 25
        ("Topbar chips", ["Coins", "Effort", "Week", "Smog"]),
        ("Adam Smith's pin factory", ["Division", "Labor", "Pins", "Factory"]),
        ("Incentives", ["Carrot", "Stick", "Bonus", "Penalty"]),
        ("Famous economists", ["Smith", "Marshall", "Keynes", "Ricardo"]),
    ],
    [  # 26
        ("Crier sections", ["News", "Report", "Gossip", "Headline"]),
        ("Haggling verbs", ["Quote", "Counter", "Accept", "Walk"]),
        ("Negotiation economics", ["Reservation", "Surplus", "Anchor", "Leverage"]),
        ("Bargain ___", ["Bin", "Hunter", "Basement", "Chip"]),
    ],
    [  # 27
        ("Built in week two", ["Farm", "Mill", "Bakery", "Loom"]),
        ("Overheads", ["Rent", "Upkeep", "Insurance", "Wages"]),
        ("Economies of scale", ["Scale", "Bulk", "Mass", "Volume"]),
        ("___ house", ["Ware", "Power", "Full", "Open"]),
    ],
    [  # 28
        ("The Guild's mercy", ["Debt", "Interest", "Outstanding", "Fresh start"]),
        ("Borrowing vocabulary", ["Principal", "Rate", "Term", "Collateral"]),
        ("When loans go wrong", ["Default", "Arrears", "Grace", "Forgiveness"]),
        ("___ shark", ["Loan", "Card", "Pool", "Nurse"]),
    ],
    [  # 29
        ("The Glowdye affair", ["Glowdye", "License", "Auction", "Exclusive"]),
        ("Auction actions", ["Bid", "Raise", "Snipe", "Lowball"]),
        ("Auction pathologies", ["Curse", "Remorse", "Fever", "Bubble"]),
        ("Royal ___", ["Decree", "Flush", "Treatment", "Jelly"]),
    ],
    [  # 30
        ("Smog season", ["Soot", "Haze", "Chimney", "Gray"]),
        ("Fixing externalities", ["Tax", "Subsidy", "Nudge", "Fine"]),
        ("Felt by third parties", ["Spillover", "Nuisance", "Harm", "Benefit"]),
        ("___ air", ["Fresh", "Hot", "Thin", "Open"]),
    ],
    [  # 31
        ("Starting kit", ["Coppers", "Wagon", "Aptitude", "Endowment"]),
        ("Trade verbs", ["Swap", "Exchange", "Barter", "Truck"]),
        ("Kinds of advantage", ["Absolute", "Comparative", "Relative", "Edge"]),
        ("___ deal", ["Raw", "Done", "Big", "New"]),
    ],
    [  # 32
        ("Podium finishes", ["First", "Second", "Third", "Laurel"]),
        ("Standings math", ["Rank", "Score", "Tally", "Tie"]),
        ("Photo finish", ["Neck-and-neck", "Dead heat", "Tiebreak", "Squeaker"]),
        ("Gold ___", ["Rush", "Standard", "Digger", "Mine"]),
    ],
    [  # 33
        ("The merchant's wagon", ["Crates", "Capacity", "Bankroll", "Ports"]),
        ("Arbitrage anatomy", ["Spread", "Margin", "Markup", "Gap"]),
        ("Why prices converge", ["Arbitrage", "Competition", "Information", "Mobility"]),
        ("___ route", ["Trade", "Scenic", "En", "Spice"]),
    ],
    [  # 34
        ("Pip's credentials", ["Professor", "Tenured", "Pigeon", "Tutor"]),
        ("Streak vocabulary", ["Daily", "Best", "Alive", "Broken"]),
        ("How learning sticks", ["Recall", "Spacing", "Mastery", "Transfer"]),
        ("___ bird", ["Early", "Lady", "Jail", "Mocking"]),
    ],
    [  # 35
        ("Fresh from the oven", ["Loaf", "Crumb", "Bake", "Rye"]),
        ("The Bread Decree arc", ["Ceiling", "Decree", "Granary", "Repeal"]),
        ("Demand for necessities", ["Inelastic", "Essential", "Staple", "Urgent"]),
        ("Upper ___", ["Crust", "Hand", "Class", "Case"]),
    ],
    [  # 36
        ("Bookkeeping", ["Credit", "Debit", "Entry", "Folio"]),
        ("Net worth pieces", ["Coins", "Inventory", "Facilities", "Loans"]),
        ("Balance sheet words", ["Asset", "Liability", "Equity", "Solvency"]),
        ("Balance of ___", ["Trade", "Power", "Payments", "Nature"]),
    ],
    [  # 37
        ("Things that deplete", ["Stock", "Effort", "Coins", "Patience"]),
        ("Things that replenish", ["Dawn", "Regen", "Harvest", "Restock"]),
        ("Renewable or not", ["Renewable", "Finite", "Fossil", "Solar"]),
        ("___ out", ["Sold", "Burn", "Cash", "Miss"]),
    ],
    [  # 38
        ("Compacts corner", ["Compact", "Sign", "Defect", "Dissolve"]),
        ("Cartel lifecycle", ["Form", "Cheat", "Undercut", "Unravel"]),
        ("Prisoner's dilemma", ["Prisoner", "Dilemma", "Betray", "Silence"]),
        ("___ breaker", ["Deal", "Tie", "Ice", "Circuit"]),
    ],
    [  # 39
        ("By royal order", ["Quota", "Ban", "Closure", "Writ"]),
        ("When the well runs dry", ["Scarce", "Depleted", "Exhausted", "Spent"]),
        ("Permit economics", ["Permit", "Tradable", "Allowance", "Cap"]),
        ("___ limit", ["Speed", "City", "Credit", "Sky"]),
    ],
    [  # 40
        ("Lantern Festival", ["Lantern", "Reveler", "Parade", "Garland"]),
        ("Demand spike crowd", ["Rush", "Surge", "Frenzy", "Stampede"]),
        ("After the party", ["Hangover", "Slump", "Correction", "Lull"]),
        ("Green ___", ["Light", "Back", "Horn", "Thumb"]),
    ],
    [  # 41
        ("Shop window dressing", ["Awning", "Sign", "Shelf", "Tag"]),
        ("Customer types", ["Regular", "Browser", "Haggler", "Tourist"]),
        ("Demand, personified", ["Willing", "Able", "Ready", "Eager"]),
        ("Window ___", ["Shopping", "Seat", "Pane", "Sill"]),
    ],
    [  # 42
        ("End of term", ["Epilogue", "Recap", "Story", "Honors"]),
        ("Final tallies", ["Net worth", "Grade", "Mastery", "Standing"]),
        ("What compounds", ["Interest", "Learning", "Habits", "Regret"]),
        ("___ cap", ["Market", "Night", "Ice", "Knee"]),
    ],
]
