"""Learning objectives + tutor-check question bank.

LOs are adapted from OpenStax *Principles of Microeconomics 3e* chapter
objectives (CC BY 4.0 — see ATTRIBUTION in docs). Question bank is original.
MCQ answers auto-grade; free-response grades via LLM rubric with a keyword
fallback (graceful degradation, DECISIONS.md #7).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LO:
    id: str
    chapter: int
    week: int
    text: str


LEARNING_OBJECTIVES: dict[str, LO] = {
    lo.id: lo
    for lo in [
        # Week 1 — Ch.2 scarcity & choice (+ Ch.6 budget threads)
        LO("ch2-opportunity-cost", 2, 1, "Explain opportunity cost and apply it to allocation decisions"),
        LO("ch2-budget-constraint", 2, 1, "Use a budget constraint to describe feasible choices"),
        LO("ch2-comparative-advantage", 2, 1, "Explain why specialization and trade create gains for both sides"),
        LO("ch2-marginal-thinking", 2, 1, "Compare marginal benefits and marginal costs in decisions"),
        # Week 2 — Ch.3 demand & supply
        LO("ch3-demand-vs-qd", 3, 2, "Distinguish demand from quantity demanded"),
        LO("ch3-shift-vs-movement", 3, 2, "Distinguish a shift of a curve from movement along it"),
        LO("ch3-equilibrium", 3, 2, "Explain how equilibrium price and quantity emerge"),
        LO("ch3-shortage-surplus", 3, 2, "Predict shortage or surplus from prices away from equilibrium"),
        # Week 3 — Ch.5 elasticity, price controls
        LO("ch5-elasticity-def", 5, 3, "Define and compute price elasticity of demand"),
        LO("ch5-determinants", 5, 3, "Identify determinants of elasticity (substitutes, necessity, time)"),
        LO("ch5-total-revenue", 5, 3, "Use the total revenue test to infer elasticity"),
        LO("ch3-price-ceiling", 3, 3, "Predict the consequences of binding price ceilings and floors"),
        LO("ch3-deadweight", 3, 3, "Explain the intuition of deadweight loss from price controls"),
        # Week 4 — Ch.7 production & costs
        LO("ch7-fixed-variable", 7, 4, "Distinguish fixed, variable, and marginal cost"),
        LO("ch7-diminishing-returns", 7, 4, "Explain diminishing marginal returns to a variable input"),
        LO("ch7-average-cost", 7, 4, "Relate marginal cost to average cost curves"),
        LO("ch7-breakeven-shutdown", 7, 4, "Apply break-even and shut-down logic to a firm's choices"),
        # Week 5 — Ch.8/9 competition & monopoly
        LO("ch8-price-taker", 8, 5, "Explain why competitive firms are price takers"),
        LO("ch9-barriers", 9, 5, "Identify barriers to entry and their role in monopoly"),
        LO("ch9-mr-lt-p", 9, 5, "Explain why a monopolist's marginal revenue is below price"),
        LO("ch9-entry-profits", 9, 5, "Predict what entry does to prices and profits"),
        # Week 6 — Ch.12/13 externalities & commons
        LO("ch12-private-social", 12, 6, "Distinguish private cost from social cost"),
        LO("ch12-pigouvian", 12, 6, "Explain how corrective taxes internalize externalities"),
        LO("ch13-commons", 13, 6, "Explain the tragedy of the commons and open-access incentives"),
        LO("ch13-public-goods", 13, 6, "Explain free riding and why public goods are underprovided"),
        # Week 7 — Ch.10/11 oligopoly & antitrust
        LO("ch10-interdependence", 10, 7, "Explain strategic interdependence among oligopolists"),
        LO("ch10-cartel-cheating", 10, 7, "Explain why cartels form and why members defect"),
        LO("ch10-differentiation", 10, 7, "Describe monopolistic competition and product differentiation"),
        LO("ch11-antitrust", 11, 7, "Explain the rationale for antitrust policy"),
    ]
}


@dataclass(frozen=True)
class Question:
    id: str
    week: int
    los: tuple[str, ...]
    kind: str               # mcq | free
    prompt: str
    choices: tuple[str, ...] = ()
    answer: int = -1        # index into choices (mcq)
    rubric: str = ""        # grading rubric (free)
    keywords: tuple[str, ...] = ()  # fallback grading (free)
    context_tags: tuple[str, ...] = ()  # gameplay hooks: trade, ceiling, festival...


QUESTIONS: dict[str, Question] = {
    q.id: q
    for q in [
        # ---- Week 1
        Question("w1-opp-1", 1, ("ch2-opportunity-cost",), "mcq",
                 "You spent 10 effort gathering wool instead of grain. The opportunity cost of that wool is:",
                 ("The coins you could sell the wool for",
                  "The grain you could have gathered with that same effort",
                  "Nothing — effort renews daily",
                  "The effort itself"),
                 1, context_tags=("gathered",)),
        Question("w1-opp-2", 1, ("ch2-opportunity-cost", "ch2-marginal-thinking"), "mcq",
                 "When does it make sense to spend one MORE effort point fishing?",
                 ("Whenever you enjoy fishing",
                  "When the expected catch is worth more to you than your best alternative use of that effort",
                  "Only when fish prices are rising",
                  "Whenever your effort bar is full"),
                 1, context_tags=("fishing_cast",)),
        Question("w1-trade-1", 1, ("ch2-comparative-advantage",), "mcq",
                 "You gather wool 3x faster than grain; your classmate gathers grain 3x faster than wool. Trading wool-for-grain makes:",
                 ("Only you better off", "Only them better off",
                  "Both of you better off", "Neither — trade just moves goods around"),
                 2, context_tags=("trade",)),
        Question("w1-budget-1", 1, ("ch2-budget-constraint",), "mcq",
                 "With 100 coins, grain at 25 and wool at 50, which bundle is NOT affordable?",
                 ("4 grain", "2 wool", "2 grain and 1 wool", "3 grain and 1 wool"),
                 3),
        Question("w1-free-1", 1, ("ch2-comparative-advantage",), "free",
                 "In one sentence: why did the Traveling Merchant make money buying cloth in Milltown and selling it in Saltharbor?",
                 rubric="Credit answers identifying price differences across locations / buying low & selling high / arbitrage.",
                 keywords=("price", "cheap", "low", "high", "differ", "arbitrage"),
                 context_tags=("merchant_completed",)),
        # ---- Week 2
        Question("w2-shift-1", 2, ("ch3-shift-vs-movement",), "mcq",
                 "The Lantern Festival raised garment prices. On the garment market diagram, the festival itself was:",
                 ("A movement along the demand curve", "A rightward shift of the demand curve",
                  "A leftward shift of the supply curve", "A movement along the supply curve"),
                 1, context_tags=("festival",)),
        Question("w2-shift-2", 2, ("ch3-shift-vs-movement",), "mcq",
                 "After the festival prices rose, more students started producing garments. That response was:",
                 ("A shift of demand", "A shift of supply over time",
                  "A movement along demand only", "Deadweight loss"),
                 1, context_tags=("festival",)),
        Question("w2-eq-1", 2, ("ch3-equilibrium",), "mcq",
                 "In your order-book market, the 'market price' is best described as:",
                 ("Whatever the Crown decrees", "The price where arriving bids and asks keep crossing",
                  "The average of all prices ever traded", "The highest ask anyone posts"),
                 1, context_tags=("trade",)),
        Question("w2-shortage-1", 2, ("ch3-shortage-surplus",), "mcq",
                 "During the festival rush you saw bids piling up unfilled. That is the textbook picture of:",
                 ("A surplus", "A shortage at the current price", "Equilibrium", "Elastic demand"),
                 1, context_tags=("festival", "shortage")),
        Question("w2-demand-qd", 2, ("ch3-demand-vs-qd",), "mcq",
                 "Bread got cheaper and you bought more bread. Your demand curve for bread:",
                 ("Shifted right", "Shifted left",
                  "Did not move — you moved along it", "Became more elastic"),
                 2),
        Question("w2-free-1", 2, ("ch3-equilibrium", "ch3-shortage-surplus"), "free",
                 "Look at your garment price chart from festival week. In 1-2 sentences, tell the story of what happened and why.",
                 rubric="Credit: demand shift up at announcement/festival, price spike, supply response with lag, post-festival glut/fall.",
                 keywords=("demand", "spike", "rose", "supply", "fell", "glut", "festival"),
                 context_tags=("festival",)),
        # ---- Week 3
        Question("w3-elastic-1", 3, ("ch5-determinants",), "mcq",
                 "Medicine stayed expensive during the drought but people kept buying. Tapestry sales collapsed when prices rose. Why?",
                 ("Medicine demand is elastic; tapestry demand is inelastic",
                  "Medicine demand is inelastic (a necessity); tapestry demand is elastic (a luxury)",
                  "Both are inelastic", "The Crown subsidizes medicine"),
                 1, context_tags=("drought",)),
        Question("w3-tr-1", 3, ("ch5-total-revenue",), "mcq",
                 "You raised your shop's bread price 20% and your bread REVENUE fell. Demand for your bread is:",
                 ("Inelastic", "Elastic", "Unit elastic", "Perfectly inelastic"),
                 1, context_tags=("shop_sale",)),
        Question("w3-ceiling-1", 3, ("ch3-price-ceiling",), "mcq",
                 "The Bread Decree capped bread at its old price during a grain drought. The empty shelves happened because:",
                 ("Bakers forgot how to bake",
                  "At the legal price, quantity demanded exceeded what sellers would supply",
                  "The Crown bought all the bread", "Demand fell"),
                 1, context_tags=("ceiling", "shortage")),
        Question("w3-ceiling-2", 3, ("ch3-price-ceiling", "ch3-deadweight"), "mcq",
                 "Who was helped by the Bread Decree?",
                 ("Everyone", "Bakers",
                  "The few buyers who got bread at the legal price",
                  "Buyers who found only empty shelves"),
                 2, context_tags=("ceiling",)),
        Question("w3-elastic-def", 3, ("ch5-elasticity-def",), "mcq",
                 "Price rises 10%, quantity demanded falls 30%. Price elasticity of demand is (in magnitude):",
                 ("0.33 — inelastic", "1.0 — unit", "3.0 — elastic", "30 — perfectly elastic"),
                 2),
        Question("w3-free-1", 3, ("ch3-price-ceiling",), "free",
                 "A classmate says 'the bread ceiling kept bread affordable.' In 1-2 sentences, what did it actually do in your world?",
                 rubric="Credit: shortage/empty shelves, sellers withdrew, hard to buy at any legal price, possibly gray market.",
                 keywords=("shortage", "empty", "withdrew", "couldn't buy", "stopped selling", "gray"),
                 context_tags=("ceiling",)),
        # ---- Week 4
        Question("w4-fc-1", 4, ("ch7-fixed-variable",), "mcq",
                 "Your bakery's build cost vs the flour it consumes daily are, respectively:",
                 ("Both fixed costs", "Both variable costs",
                  "Fixed cost; variable cost", "Variable cost; fixed cost"),
                 2, context_tags=("facility_built",)),
        Question("w4-dim-1", 4, ("ch7-diminishing-returns",), "mcq",
                 "Each worker you add to the smithy raises output by less than the one before. That is:",
                 ("Economies of scale", "Diminishing marginal returns",
                  "Diseconomies of scope", "Deadweight loss"),
                 1, context_tags=("workers_set",)),
        Question("w4-shut-1", 4, ("ch7-breakeven-shutdown",), "mcq",
                 "Demand slumped and your factory's output sells below its input + upkeep cost. For THIS WEEK you should:",
                 ("Produce anyway — you paid for the factory",
                  "Idle the facility: the build cost is sunk; avoid the variable losses",
                  "Sell the factory immediately", "Raise your prices to cover costs"),
                 1, context_tags=("demand_shock",)),
        Question("w4-mc-1", 4, ("ch7-average-cost",), "mcq",
                 "A charter factory has huge build cost but cheap per-unit production. Its average cost per unit ___ as output grows.",
                 ("Rises", "Falls (the fixed cost spreads over more units)",
                  "Stays constant", "Equals marginal cost always"),
                 1),
        Question("w4-free-1", 4, ("ch7-breakeven-shutdown",), "free",
                 "You chose charter or artisan this week. In a sentence: what would have to happen to demand for the OTHER choice to have been better?",
                 rubric="Charter wins with high sustained demand (spread fixed costs); artisan wins when demand is low/volatile.",
                 keywords=("demand", "high", "low", "fixed", "volume", "spread"),
                 context_tags=("facility_built",)),
        # ---- Week 5
        Question("w5-taker-1", 5, ("ch8-price-taker",), "mcq",
                 "In the grain market no single student can move the price. Each seller there is:",
                 ("A monopolist", "A price taker", "A price maker", "A cartel"),
                 1),
        Question("w5-barrier-1", 5, ("ch9-barriers",), "mcq",
                 "Glowdye sellers earn fat margins; grain sellers don't. The difference is:",
                 ("Glowdye is prettier", "A legal barrier to entry — the Crown license",
                  "Grain is harder to make", "Glowdye buyers are richer"),
                 1, context_tags=("license_granted",)),
        Question("w5-mr-1", 5, ("ch9-mr-lt-p",), "mcq",
                 "As the only glowdye seller, selling one more unit means dropping your price on ALL units. Your marginal revenue is therefore:",
                 ("Above the price", "Equal to the price", "Below the price", "Zero"),
                 2, context_tags=("license_granted",)),
        Question("w5-entry-1", 5, ("ch9-entry-profits",), "mcq",
                 "The Second Charter added new glowdye licenses. Prices and incumbent profits should:",
                 ("Both rise", "Both fall toward the competitive level",
                  "Stay the same", "Become more volatile only"),
                 1, context_tags=("license_granted",)),
        Question("w5-free-1", 5, ("ch9-mr-lt-p", "ch9-entry-profits"), "free",
                 "You hold a glowdye license and more licenses are coming. Price high now or low for loyalty? Defend your choice in a sentence.",
                 rubric="Either defensible: harvest surplus before entry vs deter/lock demand pre-entry. Credit recognition of the entry threat.",
                 keywords=("entry", "competition", "before", "loyal", "harvest", "margin"),
                 context_tags=("license_granted",)),
        # ---- Week 6
        Question("w6-ext-1", 6, ("ch12-private-social",), "mcq",
                 "Your smelter's smog slows EVERYONE's facilities. Your private cost of smelting differs from social cost by:",
                 ("Nothing", "The upkeep you pay",
                  "The damage your smog does to others", "The smog tax"),
                 2, context_tags=("production",)),
        Question("w6-pigou-1", 6, ("ch12-pigouvian",), "mcq",
                 "The soot levy charges per unit of smoke. Economists like this because it:",
                 ("Punishes the rich", "Makes polluters face the social cost of their choices",
                  "Raises revenue for the Crown", "Bans pollution outright"),
                 1, context_tags=("smog_tax",)),
        Question("w6-commons-1", 6, ("ch13-commons",), "mcq",
                 "The fishery collapsed even though every student would prefer it healthy. Why?",
                 ("Students are irrational",
                  "Each fisher keeps the whole benefit of a catch but shares the cost of depletion",
                  "Fish prices were too low", "The Crown overfished"),
                 1, context_tags=("fishery",)),
        Question("w6-commons-2", 6, ("ch13-commons",), "mcq",
                 "Which fixes open-access overfishing WITHOUT closing the fishery?",
                 ("A subsidy on fish", "Quotas or tradable catch shares",
                  "A price ceiling on fish", "Advertising"),
                 1, context_tags=("fishery",)),
        Question("w6-free-1", 6, ("ch13-public-goods",), "free",
                 "The lighthouse subscription raised less than the lighthouse benefits the town. In a sentence, why?",
                 rubric="Free riding: non-payers can't be excluded from the benefit, so people understate willingness to pay.",
                 keywords=("free ride", "free-rid", "everyone benefits", "can't exclude", "non-exclud", "others pay"),
                 context_tags=()),
        # ---- Week 7
        Question("w7-cartel-1", 7, ("ch10-cartel-cheating",), "mcq",
                 "Your price accord holds garments at 200. Each member's strongest private temptation is to:",
                 ("Raise the price to 250", "Quietly sell below 200 and capture volume",
                  "Leave the market", "Buy garments"),
                 1, context_tags=("compact_created",)),
        Question("w7-inter-1", 7, ("ch10-interdependence",), "mcq",
                 "In the Market Wars, your best price depends on what rival houses charge. That is the defining feature of:",
                 ("Perfect competition", "Monopoly", "Oligopoly", "A commons"),
                 2, context_tags=("tournament_start",)),
        Question("w7-diff-1", 7, ("ch10-differentiation",), "mcq",
                 "Custom tapestry patterns command premiums over plain cloth because differentiation:",
                 ("Eliminates competition entirely",
                  "Gives each maker a little price-setting power over their own variety",
                  "Lowers production costs", "Is required by the Guild"),
                 1, context_tags=("crafted",)),
        Question("w7-anti-1", 7, ("ch11-antitrust",), "mcq",
                 "The Crown's antitrust suit forced a hoarder to divest iron. The economic argument FOR doing this is:",
                 ("Hoarders are unpopular",
                  "Restoring competition moves price and quantity toward the efficient outcome",
                  "The Crown needed the iron", "It raises tax revenue"),
                 1, context_tags=("antitrust",)),
        Question("w7-free-1", 7, ("ch10-cartel-cheating",), "free",
                 "Your cartel collapsed (or held!). In 1-2 sentences, explain the prisoner's dilemma your compact faced.",
                 rubric="Credit: individually rational to defect/undercut though collectively better to cooperate; trust/enforcement absent.",
                 keywords=("defect", "cheat", "undercut", "cooperate", "trust", "tempt"),
                 context_tags=("compact_created",)),
    ]
}


def questions_for_week(week: int) -> list[Question]:
    return [q for q in QUESTIONS.values() if q.week == week]


def questions_for_context(week: int, tags: set[str]) -> list[Question]:
    return [q for q in QUESTIONS.values()
            if q.week <= week and tags.intersection(q.context_tags)]
