"""Per-item answer explanations for the MCQ bank — committed content.

Shown after a student answers: why the right choice is right, and why the
tempting wrong one tempts. Drafted once by scripts/gen_explanations.py
(grounded in each item's stem, choices, and learning objective), then
reviewed and committed here. Regenerate only for new items:
    .venv/bin/python scripts/gen_explanations.py   # fills missing ids only
"""
from __future__ import annotations

EXPLANATIONS: dict[str, str] = {
    "u1-budget":
        "The budget constraint maps all combinations that exactly exhaust your income at given prices. Students often confuse it with the optimal choice, but it shows what is affordable, not what is preferred.",
    "u1-compadv":
        "Comparative advantage is about opportunity cost, not speed or price. You have it in wool when you sacrifice fewer other goods to produce it, making specialization and mutual gains from trade possible. \"Faster\" confuses comparative with absolute advantage, a common mistake.",
    "u1-marginal":
        "The next unit is all that matters now because past spending is sunk and averages blur whether one more step helps or hurts. \"What you already invested\" tempts because it feels relevant, but sunk costs cannot be recovered and should not drive new decisions.",
    "u1-opp":
        "The opportunity cost is only the best single alternative you sacrificed, not every possible option. Summing all alternatives is the classic trap; you only truly give up one next-best option when you commit to a choice.",
    "u1-scarcity":
        "Scarcity means wants exceed available resources, so every choice involves a trade-off. A common trap is confusing scarcity with a shortage, which is a temporary gap between quantity demanded and supplied at a given price, not a permanent condition of limited resources.",
    "u1-scarcity-2":
        "Scarcity exists because wants exceed resources, so only making resources unlimited relative to wants removes that gap. Doubling money is a classic trap: it raises nominal wealth but does not create more real goods, leaving scarcity intact.",
    "u1-scarcity-3":
        "Scarcity means your total resource (20 effort) is fixed while desired activities exceed it, forcing trade-offs. A shortage tempts because it sounds similar, but shortages are temporary price-driven gaps, not the permanent fact of limited resources.",
    "u1-scarcity-4":
        "Every choice means forgoing the next-best alternative, which is the opportunity cost. \"Shortage\" is the classic trap: it means supply falls short of demand at a given price, a temporary market condition, not the universal consequence of scarcity.",
    "u1-scarcity-5":
        "Time cannot be bought or created, so even infinite money leaves you with only 24 hours to allocate. The tempting wrong answer assumes scarcity is only about money, but scarcity applies to any limited resource, including time.",
    "u2-demand-qd":
        "A fall in bread's own price causes a movement along the existing demand curve, changing quantity demanded. The other options shift the whole curve by altering a non-price determinant. Income, preferences, and population are classic demand shifters, not price changes.",
    "u2-equilibrium":
        "The correct choice means no surplus or shortage exists, so there is no pressure to change price or quantity. \"Trading has stopped\" is a common trap: equilibrium means quantity supplied equals quantity demanded, not that exchange has ceased.",
    "u2-shift":
        "A curve shifts only when a non-price factor changes; the good's own price falling just moves you along the existing demand curve, which is the classic trap students fall into.",
    "u2-shortage":
        "A shortage means quantity demanded exceeds quantity supplied at the current price. \"The good is scarce\" is a common trap because scarcity is universal, but shortage is a specific price-caused gap between buying and selling quantities.",
    "u3-ceiling":
        "A binding price ceiling is a maximum price lawmakers set below equilibrium, which causes quantity demanded to exceed quantity supplied, creating a shortage. The tempting wrong answer is \"above the market price,\" but a ceiling set above equilibrium is nonbinding and changes nothing.",
    "u3-determinants":
        "A medicine with no substitutes fills a genuine need, so buyers pay almost any price, making demand inelastic. One bakery's bread is a common trap: because close substitutes exist nearby, demand there is actually very elastic.",
    "u3-dwl":
        "Deadweight loss is the value that simply vanishes when price controls or taxes prevent trades both parties would have accepted. It is not a transfer to someone else, which is the common trap: transfers like buyer savings or tax revenue still exist somewhere, but deadweight loss is gone entirely.",
    "u3-elastic":
        "The elasticity coefficient exceeds 1, meaning buyers respond strongly to price changes. A common trap is confusing elasticity with price volatility; elasticity measures buyer responsiveness, not how much prices fluctuate.",
    "u3-revenue":
        "When price rises and revenue falls, quantity dropped sharply enough to more than offset the price gain, so demand is elastic. \"Inelastic\" tempts because raising price sounds like it should earn more money, but that only holds when buyers barely reduce purchases.",
    "u4-dimreturns":
        "Each added worker contributes less extra output than the previous one because the fixed input, like capital or land, gets spread thinner. A common trap is confusing this with total output falling, but output still rises, just more slowly.",
    "u4-fixed":
        "Fixed costs do not change with output; rent or a building cost is the same whether you make 1 unit or 1,000. The tempting wrong answer is \"only exists in the short run,\" which confuses a true fact (fixed costs can become variable long-run) with the definition itself.",
    "u4-marginal-cost":
        "Marginal cost is the added cost from producing one extra unit. A common trap is confusing it with average cost, which is total cost divided by quantity. Average cost falls when marginal cost is below it and rises when marginal cost is above it, hitting its minimum where the two curves cross.",
    "u4-shutdown":
        "Operating at a loss is rational when revenue exceeds variable costs, because fixed costs are owed regardless. The tempting wrong answer flips the logic: if revenue only covers fixed costs but not variable costs, every unit produced makes losses worse, so shutting down saves money.",
    "u5-barriers":
        "A Crown license is a legal barrier: without government permission, rivals simply cannot enter the market, so the monopolist keeps its markup. Strong demand and low prices attract competitors rather than block them, and many sellers describes competition, not monopoly.",
    "u5-entry":
        "Above-normal profits attract entry, which increases supply and drives prices down until economic profit falls to zero. \"Rise, since the market is hot\" tempts students who confuse high demand with the competitive response to it.",
    "u5-mr":
        "Selling one more unit requires lowering price on all previous units, so those units earn less than before. That lost revenue offsets the new unit's price. The last choice tempts students who forget price must fall for all units, not just the new one.",
    "u5-taker":
        "A price taker has no pricing power because buyers instantly switch to identical goods from rivals at the market price. If the seller charges even a penny more, they lose all customers and sell nothing.",
    "u6-commons":
        "It is rival (your catch reduces what remains) but non-excludable (no one can be kept out), so overuse follows. \"Never runs out\" tempts because people confuse common resources with public goods, but rivalry is exactly what makes depletion the problem.",
    "u6-externality":
        "The correct choice captures the defining feature: a third party bears a cost they did not agree to and cannot avoid. A producer's costs rising is tempting but that is a private cost, not an external one borne by bystanders outside the transaction.",
    "u6-freeride":
        "Non-excludability means no one can be blocked from consuming the good, so individuals have no incentive to pay voluntarily. The \"buy on credit\" choice tempts because both involve not paying upfront, but credit still requires eventual payment, which free riding does not.",
    "u6-pigou":
        "The tax adds the external cost to the firm's private cost, so output shrinks to the socially efficient level. Revenue is a side effect, not the goal, which makes \"raise revenue\" a common but wrong reason people cite for Pigouvian taxes.",
    "u7-antitrust":
        "Antitrust law targets harm to the competitive process, not individual competitors. The classic trap is thinking it shields small firms from losing, but losing to a more efficient rival is exactly how competition is supposed to work.",
    "u7-cartel":
        "Cartels coordinate output and pricing among multiple sellers to earn monopoly-style profits. The classic trap is confusing a cartel with a monopoly, but a monopoly is one firm acting alone, while a cartel is competing firms colluding together, and each member is always tempted to secretly undercut the agreed price.",
    "u7-diff":
        "When buyers see your product as distinct, they are willing to pay a bit more rather than switch, so you face a downward-sloping demand curve instead of a flat one. \"Identical pricing rules apply\" tempts because many rivals still limit how far you can push prices.",
    "u7-oligopoly":
        "In an oligopoly, only a few firms compete, so each firm must anticipate rivals' reactions before choosing price or output. The other choices are simply false. \"Goods are always identical\" tempts because some oligopolies sell identical goods, but many do not.",
    "w1-budget-1":
        "3 grain and 1 wool costs 75 plus 50, which equals 125 coins, exceeding the 100-coin budget. The tempting trap is thinking 3 grain sounds modest, but adding even 1 wool pushes the total over the limit.",
    "w1-budget-2":
        "Spending exactly 120 coins requires 1 bread (60) plus 1 medicine (60), hitting the budget line precisely. The other options all cost 180, which exceeds your budget, making them tempting only if you miscalculate the total.",
    "w1-budget-3":
        "The price ratio determines the tradeoff: wool costs twice as much as grain (50/25 = 2), so selling one wool unit gives you exactly enough coin to buy 2 grain. \"1 grain\" tempts students who ignore the price ratio and assume a one-for-one swap.",
    "w1-budget-4":
        "The budget set shrinks and rotates toward less bread: you can afford fewer loaves at any given spending on other goods, so the bread axis intercept falls while the other axis intercept stays fixed. \"Unchanged\" tempts because your coin total is the same, but purchasing power over bread has dropped.",
    "w1-budget-diag":
        "Bundle C lies outside the budget line, meaning its total cost exceeds your income. A and B are tempting if you forget that points beyond the line, not just on it, are the unaffordable ones.",
    "w1-marg-2":
        "The 120c is a sunk cost: it is gone whether or not you work today. Only today's extra benefits and extra costs matter for this decision. Counting it against today's harvest is the classic trap because it feels like responsible accounting but distorts the choice.",
    "w1-marg-3":
        "Sell the first 3: each earns 60c revenue against 40c cost, a 20c gain. The extra two cost 70c each but bring only 60c, losing 10c apiece. Never produce units where marginal cost exceeds marginal benefit. \"A sale is a sale\" ignores that last units can lose money.",
    "w1-marg-4":
        "Stop when marginal benefit (expected catch value) falls below marginal cost (opportunity cost of your time and effort). \"Fish are free\" tempts because fish in the water cost nothing, but your time and effort are not free.",
    "w1-opp-1":
        "The grain forgone is the next-best use of those 10 effort points, so it is the opportunity cost. \"Coins from wool\" tempts because it sounds like a cost, but that is the benefit of the choice, not what you gave up.",
    "w1-opp-2":
        "Marginal benefit must exceed marginal cost: if fishing's expected return beats your next-best use of that effort, go for it. \"Enjoying fishing\" tempts many because it sounds reasonable, but personal enjoyment alone ignores what else that effort could produce.",
    "w1-opp-3":
        "The opportunity cost is what you give up by fishing: 3 wool worth about 90c total. Effort cost tempts because it feels like the real sacrifice, but opportunity cost is the forgone alternative's value, not the resource itself.",
    "w1-opp-4":
        "Keeping the wool means forgoing the coins you could earn by selling it now. \"It came free\" tempts many students, but the original cost is irrelevant; opportunity cost is always the best alternative you give up going forward, not what you paid before.",
    "w1-trade-1":
        "Each of you has a comparative advantage in one good, so specializing lets both produce more total output than if you split time evenly. Trade then shares those gains, raising both parties above what self-sufficiency allowed. \"Neither\" tempts because it sounds like a zero-sum swap, but specialization creates real surplus.",
    "w1-trade-2":
        "You have the lower opportunity cost for wool (giving up 1 grain) versus Rina's 2 grain, so you specialize there. The tempting wrong answer is Rina because she has absolute advantage in both goods, but comparative advantage, not absolute, determines who should specialize in what.",
    "w1-trade-3":
        "Voluntary trade happens only when both parties expect to be better off; if either side predicted a loss, they would simply walk away. The \"one side won, one lost\" choices are the classic zero-sum trap: trade creates gains for both, it does not redistribute a fixed prize.",
    "w2-demand-qd":
        "A price change moves you along an existing demand curve, not shift it. \"Shifted right\" is the classic trap: buying more feels like higher demand, but only non-price factors like income or tastes actually shift the curve.",
    "w2-diag-demand-shift":
        "More buyers entering the market is a demand shifter, moving the entire curve right. The trap is \"just a price change,\" which only moves you along an existing curve without shifting it.",
    "w2-diag-equil":
        "The market clears where the two curves cross, point E at price 50, because that is the only price where quantity supplied equals quantity demanded. \"Highest willingness to pay\" is a tempting trap; that is the demand intercept, not equilibrium.",
    "w2-diag-supply-shock":
        "When supply falls, sellers offer less at every price, so the curve shifts left. Buyers compete for the smaller quantity, bidding price up while the amount actually traded falls. \"Nothing changes until the Crown acts\" tempts those who confuse policy with market mechanics.",
    "w2-dvq-2":
        "Quantity demanded rises when price falls, moving us down the existing demand curve. \"Demand\" is the tempting wrong pick, but demand only changes when something outside the price, like income or tastes, shifts the whole curve.",
    "w2-dvq-3":
        "Demand shifted right because a taste change makes buyers want more at every price, moving the entire curve. The trap is \"quantity demanded only,\" which describes movement along a fixed curve caused by a price change, not by a new fashion.",
    "w2-eq-1":
        "The market price is where buyers' bids and sellers' asks continuously match, clearing trades. The tempting wrong answer is \"the highest ask anyone posts,\" but that is just one seller's wishful price, not the price where actual deals happen.",
    "w2-eq-5":
        "Unsold inventory means a surplus: quantity supplied exceeds quantity demanded at the current price. Sellers undercut rivals to clear stock, pushing price down toward equilibrium. \"Bread is scarce\" tempts because unsold goods sound wasteful, but surplus is the opposite of scarcity.",
    "w2-shift-1":
        "The festival increased consumers' desire to buy garments at every price, shifting demand right and driving prices up. Students often pick \"movement along demand\" thinking rising prices caused the shift, but the festival is the underlying cause, not the price change.",
    "w2-shift-2":
        "Higher prices motivated new producers to enter, expanding the quantity supplied at every price, which shifts the supply curve rightward. Students often confuse this with movement along supply, but that describes existing sellers reacting to price, not new producers entering the market.",
    "w2-shift-4":
        "Lower production costs let sellers profitably offer more at every price, shifting supply right. \"Movement along the curve\" tempts students who confuse a price change (which moves along the curve) with a cost change (which shifts it).",
    "w2-shift-5":
        "A price change moves buyers along the existing demand curve to a new quantity demanded. The tempting trap is confusing this with a demand shift: new buyers, income changes, or preference changes shift the whole curve, but price alone does not.",
    "w2-shortage-1":
        "Unfilled bids mean buyers want more than sellers are offering at that price, which is the definition of a shortage. \"Surplus\" tempts because a busy festival feels like excess activity, but a surplus means unsold goods piling up, not unmet buyers.",
    "w3-ceiling-1":
        "At the ceiling price, sellers could not cover rising grain costs, so they baked less, while buyers still wanted the old quantity. This gap between quantity demanded and quantity supplied emptied shelves. \"Demand fell\" tempts because empty shelves feel like nobody wanted bread, but the opposite is true.",
    "w3-ceiling-2":
        "The price ceiling kept bread cheap for lucky buyers who actually found it, but caused shortages that left many buyers empty-handed and hurt bakers who sold at a loss or stopped producing. Only successful buyers gained, making \"everyone\" a classic trap.",
    "w3-det-3":
        "Tapestries are a luxury with a free substitute, so buyers easily quit buying them when price rises. Medicine and bread are necessities with few substitutes, making demand inelastic. \"Equally elastic\" ignores that substitutes and necessity status both matter greatly.",
    "w3-det-4":
        "Demand becomes more elastic over time because buyers gradually discover and switch to substitutes like gas grills or wood pellets. The tempting wrong answer is \"perfectly inelastic forever,\" since charcoal feels essential for grilling, but substitutes always exist given enough time.",
    "w3-det-5":
        "Rent takes a big share of your budget, making its demand more elastic. Pins cost almost nothing relative to income, so a 10% pin price hike barely changes how many you buy. \"Ten percent is ten percent\" tempts but ignores that absolute impact matters.",
    "w3-diag-ceiling":
        "A price ceiling is set below equilibrium, so quantity demanded exceeds quantity supplied, creating a shortage of 40 units. The surplus option tempts because it looks like a price floor situation, but floors sit above equilibrium, not below.",
    "w3-diag-elastic":
        "The flat curve (B) shows quantity dropping sharply for a small price rise, meaning demand is elastic. A luxury with many substitutes behaves this way. The steep curve (A) tempts because \"steep\" sounds dramatic, but it actually means buyers barely react.",
    "w3-diag-floor":
        "A floor above equilibrium holds price too high, so sellers supply more (70) than buyers demand (30), creating a surplus of 40 units. The tempting wrong answer is \"shortage,\" which would follow a ceiling below equilibrium, not a floor above it.",
    "w3-diag-shortage-size":
        "At a price ceiling of 30, quantity demanded is 70 and quantity supplied is 30, so the shortage equals the gap between them: 70 minus 30 equals 40 units. A common trap is confusing the shortage size with the quantity demanded (70) or supplied (30) alone.",
    "w3-diag-tr":
        "With inelastic demand, a price increase raises total revenue because the percentage drop in quantity sold is smaller than the percentage price rise. \"Buyers flee to substitutes\" is tempting but wrong: inelastic demand means few good substitutes exist.",
    "w3-dwl-2":
        "The trade would have created 35 of surplus (80 minus 45), split between buyer and seller. Since it never happens, that value vanishes entirely. \"Coins stay in town\" tempts because money is visible, but the lost surplus was never money to begin with.",
    "w3-dwl-3":
        "Deadweight loss is value destroyed, not moved. When price controls block mutually beneficial trades, both the buyer's surplus and seller's surplus on those units disappear entirely. \"Money transferred\" tempts because price controls do redistribute income, but redistribution is a separate effect, not a loss.",
    "w3-dwl-4":
        "When a ceiling prevents a deal both sides want, the surplus that trade would have created simply vanishes rather than going to either party. Voluntary trades and price information cause no such loss; repealing a binding ceiling actually eliminates existing deadweight loss.",
    "w3-elast-3":
        "Elasticity = 25% / 10% = 2.5, which exceeds 1, so demand is elastic. \"Inelastic\" tempts students who see a price rise causing a quantity drop and assume consumers \"need\" clothing, forgetting that 25% far outpaces the 10% price change.",
    "w3-elast-4":
        "Elasticity equals percent change in quantity divided by percent change in price: 4 divided by 20 equals 0.2. Because that is well below 1, demand is deeply inelastic. Many students flip the ratio and get 5, which is the classic trap.",
    "w3-elastic-1":
        "Medicine is a necessity with few substitutes, so buyers keep purchasing even at high prices (inelastic). Tapestries are a luxury with alternatives, so a price rise causes a big drop in quantity demanded (elastic). \"Both inelastic\" tempts because both involve spending.",
    "w3-elastic-def":
        "Elasticity equals percent change in quantity divided by percent change in price: 30/10 = 3.0, which is elastic (magnitude above 1). A common trap is flipping the ratio, giving 0.33 and wrongly concluding demand is inelastic.",
    "w3-tr-1":
        "Revenue fell when price rose, meaning buyers cut quantity by more than enough to offset the higher price. That is the hallmark of elastic demand. \"Inelastic\" tempts because higher prices feel like they should mean more revenue, but that only holds when demand is inelastic.",
    "w3-tr-3":
        "Elastic demand means quantity rose enough to more than offset the lower price, so total revenue climbed. Inelastic is the classic trap: it sounds like \"not reacting,\" but inelastic demand would cause revenue to fall when you cut price.",
    "w3-tr-4":
        "Revenue rises when demand is inelastic because the price increase outweighs the small drop in quantity sold. \"Fall\" tempts students who forget that inelastic demand means buyers have few good substitutes and keep purchasing despite higher prices.",
    "w4-ac-2":
        "When marginal cost is below average cost, it drags the average down, just like a below-average score lowers your GPA. \"Up\" tempts because total cost rises, but that confuses total with average.",
    "w4-ac-3":
        "When a new unit costs more than the current average, it pulls the average up, just as one high test score raises your class average. \"Spreading fixed costs always helps\" tempts because fixed costs do spread, but rising marginal cost can outweigh that effect.",
    "w4-ac-4":
        "When MC is below AC, each extra unit pulls the average down; when MC rises above AC, it pulls the average up. So AC is at its minimum precisely where MC equals AC. The \"output is largest\" trap confuses maximum production with minimum cost.",
    "w4-ac-diag":
        "When MC is below AC, each extra unit costs less than the current average, dragging it down. When MC rises above AC, each unit costs more, pushing the average up. The minimum must fall exactly where they cross because that is the switch point between falling and rising.",
    "w4-cost-2":
        "Total cost adds fixed plus variable: 14c + (6c x 4) = 38c. The 24c trap is tempting because variable costs change with output, but fixed costs are real costs too and must be included.",
    "w4-cost-3":
        "Marginal cost is the added cost of one more unit, so it equals only the extra grain for that sack. The \"44c divided by five\" trap tempts students who confuse marginal cost with average total cost.",
    "w4-cost-4":
        "The nightly upkeep is owed regardless of output, making it fixed. The other choices all change with production level, which is the classic sign of a variable cost, not a fixed one.",
    "w4-diag-costs":
        "Fixed costs, like rent or equipment loans, do not change with output, so their line is horizontal. \"Costs always rise\" tempts because total cost does rise, but that reflects variable costs, not fixed.",
    "w4-diag-returns":
        "Diminishing marginal returns occur because capital (tools, space) is fixed, so each extra worker has less equipment to use. \"Rising fixed costs\" tempts students who confuse fixed inputs with fixed costs, but costs are not what the curve measures.",
    "w4-dim-1":
        "Diminishing marginal returns occurs when adding workers to a fixed input (the smithy) yields smaller and smaller output gains. Economies of scale is the classic trap: it sounds similar but refers to long-run cost savings from expanding all inputs together.",
    "w4-dr-3":
        "Marginal product is the *change* in output from adding one worker: 28 minus 24 equals 4. Choosing 28 is the classic trap because that is total output, not the addition the fourth worker alone contributes.",
    "w4-dr-4":
        "Fixed inputs like looms and floor space get shared among more workers, so each added worker contributes less new output. \"Later hires are lazier\" is a common trap: diminishing returns is about fixed resources, not worker quality.",
    "w4-fc-1":
        "Building cost does not change with output, so it is fixed. Flour consumption rises as you bake more, so it is variable. A common trap is calling both variable because both feel like \"costs of running the business.\"",
    "w4-mc-1":
        "Fixed build cost is spread across every unit produced, so each extra unit carries a smaller share of that overhead, pulling average cost down. \"Stays constant\" tempts students who confuse this with constant marginal cost, but average cost keeps falling here.",
    "w4-shut-1":
        "Shut down temporarily when price falls below variable cost, because fixed/sunk costs are already gone either way. \"Produce anyway\" tempts students who think sunk costs justify continued losses, but ignoring them is exactly right. Selling the factory confuses short-run with permanent exit.",
    "w4-shut-3":
        "Pausing is correct because price (25) falls below avoidable cost (30), so each tool made loses you an extra 5. The upkeep is sunk tonight either way, so it never tips the decision. \"Produce to help cover upkeep\" is the classic trap: sunk costs are irrelevant. Exiting forever is premature.",
    "w4-shut-4":
        "Price 25 exceeds avoidable cost 18, so each unit contributes 7 toward the fixed upkeep; producing reduces the loss compared to shutting down. The tempting wrong answer adds fixed cost to avoidable cost, but upkeep is owed regardless, so it should not affect the produce-or-pause decision.",
    "w5-bar-2":
        "The license restricts the number of sellers by law, so outsiders cannot legally enter and undercut the price. Quality certification tempts because licenses sometimes do that, but here the key effect is limiting competition, not verifying product standards.",
    "w5-bar-3":
        "A rival pricing lower than you is just competition in action, not a barrier to entry. Barriers block new firms from entering the market; a rival already inside competing on price actually breaks down monopoly power rather than protecting it.",
    "w5-bar-4":
        "Winning the license means no rival can legally sell glowdye, so the holder earns monopoly profits above competitive returns. \"Prestige\" tempts because auctions feel status-driven, but rational bidders actually pay for the stream of protected profits the entry barrier creates.",
    "w5-barrier-1":
        "A Crown license is a classic legal barrier: rivals cannot legally enter no matter how profitable the market looks, so the monopolist keeps its markup. \"Richer buyers\" tempts because high willingness to pay raises prices, but without a barrier, competition would still erode profits.",
    "w5-diag-mr":
        "Selling an extra unit requires dropping the price on all previous units too, so the revenue gained from the new unit is offset by losses on existing units, pushing MR below price. The \"barred from charging\" option tempts students who confuse price regulation with monopoly pricing.",
    "w5-entry-1":
        "New sellers increase supply, pushing prices down. Incumbents lose market power as competition erodes their above-normal profits. \"Both rise\" tempts students who confuse new entry with rising demand, but more sellers mean lower prices, not higher ones.",
    "w5-entry-2":
        "Entry shifts supply right, driving price down until profits normalize. Rising prices tempt because \"excitement\" feels real, but more sellers competing for the same buyers always pushes prices down, not up.",
    "w5-entry-3":
        "Entry stops when profits drop to normal, because that is the only point where new rivals have no financial incentive to join. Students often misread \"competition erodes profits\" as driving price to zero, but price only falls to the point covering all costs, including normal profit.",
    "w5-entry-diag":
        "Entry increases supply, driving the equilibrium price down and quantity up until profits shrink to normal. \"Price rises to reward newcomers\" is a common trap because students confuse rewarding sellers with what actually happens when competition intensifies.",
    "w5-mr-1":
        "Cutting price to sell one more unit gains revenue from that unit but loses revenue on every unit you were already selling at the higher price. That lost revenue makes marginal revenue fall short of the new price. Students often pick \"equal to price,\" confusing monopoly with perfect competition where price never needs to drop.",
    "w5-mr-4":
        "The fifth vial adds 55 in revenue but costs 5 dollars lost on each of the four existing units (4 x 5 = 20), so MR = 55 minus 20 = 35. Choosing 55 is the common trap because it ignores the price cut applied to all previous units.",
    "w5-mr-5":
        "The monopolist equates MR with MC, but MR is below price, so MC is below price at the chosen output, meaning fewer units are sold than in competition where price equals MC. The tempting wrong answer is \"producing anything at all,\" since monopolists do produce, just less than the efficient amount.",
    "w5-pt-2":
        "In a perfectly competitive market, identical goods from many sellers make buyers choose the cheapest option every time. Listing above the market price means zero sales, not loyalty. The tempting trap is thinking rivals will follow your lead, but they have no reason to.",
    "w5-pt-3":
        "A perfectly competitive seller has no power over price because rivals sell the same good at the market rate; charging more loses all customers instantly. The only real choice is quantity. \"What price to set\" tempts because sellers in other markets do set prices, but not here.",
    "w5-pt-4":
        "Without a binding agreement, each seller profits by undercutting rivals just slightly, capturing far more sales. That individual incentive is irresistible, so the cartel unravels. \"They can\" tempts because gentlemen's agreements sound stable, but they collapse without enforcement.",
    "w5-taker-1":
        "A price taker has no market power because buyers can instantly switch to identical grain from countless rivals, so any seller who charges even a penny more loses all customers. \"Price maker\" tempts because sellers do set a number, but they cannot choose one above the market rate.",
    "w6-com-4":
        "You capture only your own future share of the loss; the rest is spread across all other users. That gap between private and social cost is exactly what drives overuse. \"All of it\" tempts because it feels fair, but open access means costs are shared involuntarily.",
    "w6-com-5":
        "Owning a catch share means the future stock raises the share's resale value, so the owner profits personally by conserving. The poster tempts because it seems like it addresses behavior, but voluntary appeals fail when individual incentives still reward overuse.",
    "w6-commons-1":
        "Each fisher captures the full value of every fish caught but spreads the depletion cost across all users, so fishing more is individually rational even as it destroys the shared stock. \"Students are irrational\" tempts because the outcome looks foolish, but it is actually a predictable incentive problem.",
    "w6-commons-2":
        "Quotas cap total harvest at the sustainable level, and tradable catch shares let fishers buy and sell rights, so the catch stays limited while the fishery stays open. Subsidies are a classic trap because they lower costs and actually encourage more fishing, worsening overuse.",
    "w6-diag-commons":
        "Each fisher captures the full benefit of one more fish but shares the depletion cost across all users, so every individual keeps fishing past the point that is good for the group. \"Technology got worse\" tempts because declining catches feel like an equipment problem.",
    "w6-ext-1":
        "The damage your smog does to others is an external cost you impose but never pay, so social cost exceeds your private cost by exactly that amount. The smog tax is tempting but only corrects the gap; it does not define it.",
    "w6-pig-2":
        "The tax internalizes the externality: the polluter now bears the cost of harm imposed on neighbors, so it acts as if that cost were its own. The tempting wrong answer \"raises every price equally\" misses that the tax targets only the smoky good, changing relative costs.",
    "w6-pig-3":
        "The tax makes each firm compare its abatement cost against the tax per unit; firms with low abatement costs find cleaning up cheaper than paying, so they cut the most. \"Only largest producers\" tempts because size feels decisive, but cost efficiency is what actually drives the choice.",
    "w6-pig-4":
        "The scrubber pays off only if cumulative savings (60c per night times enough nights) exceed the 250c upfront cost. \"Never\" tempts because 250c feels large, but fixed costs are only relevant compared to future benefits, not as an absolute barrier.",
    "w6-pigou-1":
        "The tax adds the external harm directly to the firm's private cost, so it produces and pollutes only up to the point where the full social cost is covered. Revenue and punishment may follow, but they are side effects, not the economic purpose.",
    "w6-psc-2":
        "Social cost adds the external harm to the private cost: 30c you pay plus 10c your neighbors bear equals 40c. The 30c trap is tempting because your ledger is real, but it ignores costs shifted onto others.",
    "w6-psc-3":
        "Producers only face private costs, so the good looks cheaper to make than it truly is, and output expands past the social optimum. \"Exactly the right amount\" tempts students who forget that unpaid external costs mean private and social incentives diverge.",
    "w6-psc-4":
        "You capture only your own harvest gain, not the extra orchard yields your blossoms create for others, so your private benefit falls short of the social benefit and you plant less than the efficient amount. \"Flowers are seductive\" sounds plausible but confuses personal appeal with economic incentives.",
    "w6-pub-2":
        "Because no ship can be blocked from using the light, every captain has an incentive to let others pay and enjoy the benefit for free. This free-rider logic leaves the fund chronically short. \"Exactly sufficient\" tempts those who assume people voluntarily match social needs, but they rarely do.",
    "w6-pub-3":
        "Flood walls protect every shop whether or not each owner paid, so no one can be excluded and one shop's protection does not reduce another's. That non-excludability lets everyone free ride, so voluntary funding falls short of the socially optimal level.",
    "w6-pub-4":
        "A public good is both non-rival (one person's use does not reduce others') and non-excludable (no one can be kept out), so people free ride on others' contributions, and voluntary funding produces too little of it.",
    "w7-anti-1":
        "Divestiture breaks up monopoly control, pushing price down and output up toward the competitive equilibrium. The tax-revenue choice tempts because governments do benefit fiscally, but that is a side effect, not the economic justification for the remedy.",
    "w7-anti-2":
        "Antitrust law addresses market power that harms buyers through higher prices, not size alone. \"Any merchant who grows large\" is the classic trap: bigness is not itself illegal; only practices that suppress competition and raise prices are.",
    "w7-anti-3":
        "Fines directly punish the illegal agreement to fix prices. Divestiture tempts because Petra also has market power, but breaking up her holdings targets concentration, not the separate act of collusion. Price ceilings and subsidies address neither problem.",
    "w7-anti-4":
        "Antitrust law targets harm to competition and consumers, not size alone. A firm that dominates by innovating and cutting prices benefits buyers, so intervening would punish the very behavior markets are meant to encourage. \"Never\" is the trap: it confuses bigness with wrongdoing.",
    "w7-cart-3":
        "Every member faces the same temptation to shade price and steal sales, so defection is individually rational even though it destroys collective profits. \"The Crown forbids it\" tempts because real cartels sometimes invoke legal cover, but the instability is internal, not external.",
    "w7-cart-4":
        "Fewer members make monitoring simpler, so defection is caught quickly and punishment follows fast. Many members with secret sales is the classic trap: it sounds stable, but hidden deals make cheating nearly undetectable, which actually destroys cartels.",
    "w7-cart-5":
        "Public prices let cartel members instantly spot cheating, so the temptation to secretly undercut collapses. The trap is thinking transparency only helps the Crown; it cuts both ways, stabilizing collusion while also exposing it to regulators.",
    "w7-cartel-1":
        "Selling below 200 lets a cheater steal customers from rivals who still honor the agreement, boosting that firm's profit in the short run. Raising price to 250 tempts no one individually because customers would simply buy from the other members still charging 200.",
    "w7-diff-1":
        "Differentiation makes your product distinct enough that buyers will pay a bit more rather than switch instantly, giving you a small downward-sloping demand curve. \"Eliminates competition entirely\" tempts because premiums feel monopoly-like, but many tapestry makers still compete nearby.",
    "w7-diff-2":
        "A unique brand makes some buyers loyal to you specifically, so your demand curve slopes downward instead of lying flat, letting you raise price without losing everyone. \"Lowers costs\" tempts some, but differentiation is about demand, not cost savings.",
    "w7-diff-3":
        "Many sellers compete, but each product differs slightly, giving sellers some price-setting power without full monopoly control. Students often pick \"one seller\" because \"monopoly\" appears in the name, but that word refers to each firm's tiny pricing power, not market dominance.",
    "w7-diff-4":
        "Nearby substitutes let buyers switch if prices rise too far, so the seller faces a downward-sloping but elastic demand curve rather than full monopoly control. \"Nothing at all\" tempts because differentiation feels like monopoly power, but competition stays real.",
    "w7-inter-1":
        "Oligopoly is correct because firms are few enough that each one's profit depends on what rivals charge, making strategy interdependent. Monopoly tempts because it involves pricing power, but a monopolist has no rivals to react to.",
    "w7-oli-2":
        "Low gives you 140 versus 100, so undercutting your rival pays off when they price High. \"Dignity\" is not a payoff, and randomizing ignores a clear best response. Always compare actual numbers first.",
    "w7-oli-3":
        "With only a few firms, each must watch and react to named competitors. The tempting wrong answer is that buyers stop comparing prices; in reality buyers still compare, but sellers gain strategic power because their individual choices visibly affect rivals.",
    "w7-oli-4":
        "Both players follow the same logic: undercutting looks profitable no matter what the rival does, so both choose Low. That is the Nash equilibrium, even though Both High would pay more. \"Both High\" tempts because it looks mutually beneficial, but nothing enforces it.",
}
