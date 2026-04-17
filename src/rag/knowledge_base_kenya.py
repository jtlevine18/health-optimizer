"""
Kenya agricultural marketing knowledge base for RAG retrieval.

~25 knowledge chunks covering bimodal crop calendars, NCPB/KAMIS/county
institutions, post-harvest handling (aflatoxin, PICS, metal silos),
transport (A-roads vs feeder roads, Mombasa corridor), storage
(NCPB depots, CACs, warehouse receipts), and shocks (2022 Horn of
Africa drought, 2023-24 El Nino floods, IPC classifications).

Used by the recommendation agent when REGION=kenya. Sibling to
knowledge_base.py (Tamil Nadu / India). Schema matches the India
module exactly: KnowledgeChunk dataclass with id/title/source/category/text.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KnowledgeChunk:
    id: str
    title: str
    source: str
    category: str
    text: str


KNOWLEDGE_CHUNKS: list[KnowledgeChunk] = [

    # -- Crop Calendars -------------------------------------------------

    KnowledgeChunk(
        "CC-001", "Maize Long Rains Calendar - Rift Valley and Western Kenya",
        "MoALF Kenya Crop Production Guidelines 2023; FEWS NET Kenya Seasonal Monitor",
        "crop_calendar",
        "The Long Rains are Kenya's primary cropping season and produce roughly 70-80% of the national maize crop. "
        "Land preparation begins Feb-Mar, planting Mar-May as rains establish, vegetative growth Apr-Jun, "
        "and harvest Jul-Sep in most zones. Main producing counties: Trans-Nzoia, Uasin Gishu, Nakuru, Narok, "
        "Bungoma, Kakamega, Nyandarua. Rift Valley high-altitude zones (Trans-Nzoia, Uasin Gishu) harvest "
        "latest (Sep-Nov) because of longer maturation at altitude. Wholesale maize price troughs typically "
        "arrive Aug-Oct when Western and Rift Valley grain floods Nairobi, Kisumu, Eldoret, and Nakuru markets."
    ),
    KnowledgeChunk(
        "CC-002", "Maize Short Rains Calendar - Eastern and Coastal Kenya",
        "MoALF Kenya Crop Production Guidelines 2023; KALRO Maize Agronomy Manual",
        "crop_calendar",
        "The Short Rains (Oct-Dec) are the secondary season and dominate Eastern, lower Central, and Coastal "
        "Kenya, where a single unimodal rainy season is unreliable. Planting Oct-Nov, harvest Jan-Feb. "
        "Key counties: Machakos, Makueni, Kitui, Embu, Tharaka-Nithi, Kilifi, Kwale. Short Rains maize is "
        "far more vulnerable to dry spells -- the 2022 consecutive failure of five rainy seasons devastated "
        "this region. Short Rains harvest pushes a secondary price trough in Feb-Mar in Machakos, Mwingi, "
        "and Wote markets, though volumes are a fraction of the Long Rains crop."
    ),
    KnowledgeChunk(
        "CC-003", "Maize Moisture and Safe-Storage Thresholds",
        "KALRO Post-Harvest Handbook; FAO Kenya Aflatoxin Mitigation Guide",
        "crop_calendar",
        "Maize at harvest is typically 18-25% moisture and must be dried to 13.5% or below before storage. "
        "Above 13.5% moisture, Aspergillus flavus growth accelerates and aflatoxin contamination risk rises "
        "sharply; above 18% grain may rot within weeks. Sun-drying on raised tarpaulins or drying cribs over "
        "5-10 days is standard for smallholders; avoid drying on bare ground (soil contamination and re-wetting). "
        "NCPB rejects deliveries above 13.5% moisture. Traders discount roughly KES 100-200 per 90kg bag for "
        "each percentage point above 13.5%, and a heavily aflatoxin-positive lot may be unsellable entirely."
    ),
    KnowledgeChunk(
        "CC-004", "Bean Crop Calendar - Bimodal Smallholder Staple",
        "KALRO Legumes Research Programme; MoALF Pulses Strategy 2020-2025",
        "crop_calendar",
        "Beans (Rosecoco, Mwitemania, Mwezi Moja, Wairimu) are grown in both rainy seasons on 75-90 day cycles, "
        "shorter than maize, and are frequently intercropped with maize. Long Rains: plant Mar-Apr, harvest "
        "Jun-Jul. Short Rains: plant Oct-Nov, harvest Jan-Feb. Main counties: Nakuru, Narok, Bomet, Kirinyaga, "
        "Meru, Embu, Machakos. Beans are drought-sensitive at flowering (days 35-45); mid-season dry spells "
        "routinely cut yields 30-50%. Post-harvest beans must be dried to <13% moisture; bruchid weevils are "
        "the primary storage pest and destroy improperly-stored lots within 2-3 months."
    ),
    KnowledgeChunk(
        "CC-005", "Irish Potato Calendar - Nyandarua, Meru, and Nakuru",
        "National Potato Council of Kenya; KALRO Tigoni",
        "crop_calendar",
        "Irish potato (Shangi, Dutch Robijn, Asante) is grown at 1,800-3,000m altitude on a 3-4 month cycle "
        "tied to the rains. Long Rains planting Mar-Apr, harvest Jun-Aug. Short Rains planting Oct-Nov, "
        "harvest Feb-Mar. Production is concentrated in Nyandarua (~40% of national output), Meru, Elgeyo "
        "Marakwet, Nakuru, Bomet, and Bungoma. Shangi dominates (~80% of market) because it ripens quickly "
        "and handles transport, but it has very short dormancy (2-3 weeks) -- farmers cannot hold crop, "
        "which drives distress selling at harvest and extreme price swings. Nyandarua farm-gate prices have "
        "swung from KES 800 to KES 3,500 per 110kg bag within a single season."
    ),

    # -- Market Institutions --------------------------------------------

    KnowledgeChunk(
        "MI-001", "NCPB - National Cereals and Produce Board",
        "NCPB Annual Reports; MoALF Strategic Food Reserve Policy",
        "market_institution",
        "NCPB is Kenya's parastatal grain buyer of last resort and operator of the Strategic Food Reserve. "
        "When activated by the Cabinet Secretary, NCPB offers a Guaranteed Minimum Return Price (GMRP) for "
        "maize -- recent GMRP levels have ranged KES 3,000-5,200 per 90kg bag, well above distress-sale "
        "farm-gate levels in surplus seasons. NCPB operates ~110 depots nationwide with concentration in "
        "Rift Valley and Western counties. Payment delays of 30-90 days are common; smallholders need "
        "registration, ID, and land documentation. Intake quality standards: <13.5% moisture, <3% foreign "
        "matter, aflatoxin within codex limits. When GMRP is not activated, NCPB buys at market rates or not at all."
    ),
    KnowledgeChunk(
        "MI-002", "KAMIS - Kenya Agricultural Market Information System",
        "KAMIS Portal; MoALF Market Information Unit",
        "market_institution",
        "KAMIS is the MoALF-run market information service (kamis.kilimo.go.ke) that publishes daily, weekly, "
        "and monthly wholesale prices for 40+ commodities across 60+ markets nationwide. Coverage is strongest "
        "for Nairobi (Wakulima, Kangemi, Gikomba), Mombasa (Kongowea), Eldoret, Kisumu (Kibuye), and Nakuru. "
        "Daily prices reflect wholesale trades and typically sit 15-40% above farm-gate. KAMIS is the canonical "
        "source for price reconciliation and for retrospective benchmark panels. Gaps: farm-gate prices are "
        "not systematically collected, and rural market coverage thins outside the main trunk corridors."
    ),
    KnowledgeChunk(
        "MI-003", "County Governments Post-2013 Devolution",
        "Constitution of Kenya 2010, Fourth Schedule; Kenya Devolution Working Paper (World Bank 2020)",
        "market_institution",
        "Agriculture is a devolved function under Kenya's 2010 Constitution -- each of the 47 counties runs "
        "its own Department of Agriculture with budgets for extension, input subsidies (often fertilizer and "
        "certified seed), market infrastructure, and cooperative support. Practical consequences for farmers: "
        "input subsidy program eligibility, cooperative registration, and county market fees all vary by county. "
        "Meru and Nyandarua run active potato-sector programs; Kakamega and Bungoma run maize-and-dairy extension; "
        "ASAL counties (Kitui, Makueni, Turkana) focus on drought-tolerant sorghum and millet. National-level "
        "MoALF still sets price-support policy (NCPB, GMRP) and runs KAMIS."
    ),
    KnowledgeChunk(
        "MI-004", "SACCOs and Cooperatives for Rural Finance and Aggregation",
        "SASRA Annual Supervision Report; Co-operative Bank of Kenya Agri-SACCO Study",
        "market_institution",
        "SACCOs (Savings and Credit Cooperatives) are the backbone of Kenyan rural finance. Regulated by "
        "SASRA, farmer SACCOs pool member savings, provide input credit (fertilizer, seed on 3-6 month terms), "
        "and aggregate produce for bulk sale. Agricultural SACCOs are strongest in coffee (Mt. Kenya), dairy "
        "(Rift Valley), and tea (Kericho, Nandi) zones; maize and bean cooperatives are weaker but growing. "
        "Typical benefits of SACCO membership: input credit at 12-15% annual (vs. 25%+ from informal lenders), "
        "shared transport to terminal markets, and access to NCPB delivery letters. Dormant and weak-governance "
        "cooperatives are common -- farmers should verify SASRA registration before committing savings."
    ),

    # -- Post-Harvest Handling -----------------------------------------

    KnowledgeChunk(
        "PH-001", "Aflatoxin Risk in Kenya - Regions and History",
        "Kenya Ministry of Health Aflatoxin Surveillance; Lewis et al. 2005 (2004 Machakos Outbreak)",
        "post_harvest",
        "Aflatoxin contamination is Kenya's most severe post-harvest food-safety risk, caused by Aspergillus "
        "flavus on improperly-dried maize. The 2004 outbreak centered on Makueni and Machakos killed 125+ "
        "people from acute aflatoxicosis -- still among the largest aflatoxin mortality events ever recorded. "
        "High-risk zones: Eastern Kenya lower midlands (Machakos, Makueni, Kitui, Embu, Tharaka-Nithi) where "
        "Short Rains harvests coincide with lingering humidity, and coastal Kenya (Kilifi, Kwale, Taita-Taveta) "
        "year-round. Rift Valley Long Rains crops are lower-risk because harvest falls in the drier Jul-Sep "
        "window. Aflasafe KE01 biocontrol is available through KALRO and reduces field contamination 80-90% "
        "when applied 2-3 weeks before flowering."
    ),
    KnowledgeChunk(
        "PH-002", "PICS Bags - Hermetic Triple-Layer Storage",
        "Purdue Improved Crop Storage (PICS) Project; KENAFF Distribution Records",
        "post_harvest",
        "PICS (Purdue Improved Crop Storage) bags are triple-layer hermetic storage sacks -- two polyethylene "
        "liners inside a woven polypropylene outer bag -- that suffocate storage pests (maize weevil, larger "
        "grain borer, bruchid) within 10-14 days of sealing, without any chemicals. A 90kg PICS bag costs "
        "KES 250-400 in Kenyan agrovet shops (2024-2025), reusable 2-3 seasons. Storage loss drops from "
        "20-30% over 6 months (open-weave gunny bags + actellic dusting) to under 2% with PICS. Distribution "
        "in Kenya runs through KENAFF (Kenya National Farmers' Federation), KALRO, and private agrovet chains "
        "(Farmers Choice, Pwani, Amiran). Adoption is highest in Western Kenya and Rift Valley."
    ),
    KnowledgeChunk(
        "PH-003", "Metal Silo Program - CIMMYT, KALRO, EGSP",
        "CIMMYT Effective Grain Storage Project (EGSP) 2008-2016; KALRO Post-Harvest Unit",
        "post_harvest",
        "Metal silos (galvanized sheet steel, 180-3,000kg capacity) are the premium on-farm storage option, "
        "disseminated in Kenya through the CIMMYT-led Effective Grain Storage Project with KALRO and the "
        "Ministry of Agriculture (2008-2016). A 900kg silo costs KES 18,000-30,000 through trained artisans "
        "in Nakuru, Bungoma, and Embu. Storage losses drop to near zero over 12+ months. Economics work for "
        "farmers with >10 bags to store who want to capture the Oct-trough to Mar-peak maize price cycle "
        "(15-25% seasonal spread). Adoption remains limited by upfront cost; SACCOs and county agriculture "
        "departments occasionally subsidize silos for smallholder cooperatives."
    ),
    KnowledgeChunk(
        "PH-004", "WFP and FAO Post-Harvest Programs (P4P and Successors)",
        "WFP Kenya Country Strategic Plan; FAO Kenya Resilience Programme",
        "post_harvest",
        "WFP's Purchase for Progress (P4P, 2008-2014) demonstrated smallholder aggregation into WFP's Kenya "
        "food-aid supply chain, sourcing maize and pulses from producer organizations at prices above farm-gate "
        "in exchange for quality and volume commitments. P4P successors under WFP Country Strategic Plans "
        "continue smallholder sourcing in Bungoma, Busia, Makueni, Kitui, and Trans-Nzoia. FAO's Kenya "
        "Resilience and Food Systems programmes fund post-harvest training, hermetic storage subsidies, and "
        "aflatoxin testing equipment at county level. Participating farmer groups typically see 20-30% price "
        "uplift on the sold portion plus training in quality grading and moisture testing."
    ),

    # -- Transport ------------------------------------------------------

    KnowledgeChunk(
        "TR-001", "Kenya Road Network - Classes A, B, C and Corridor Geography",
        "Kenya National Highways Authority (KeNHA); Kenya Rural Roads Authority (KeRRA)",
        "transport",
        "Kenya's classified road network has roughly 161,000 km, of which only ~14,000 km is paved. "
        "Class A roads are international trunk corridors (A1 Malaba-Kisumu-Kisii-Isebania west corridor and "
        "A109 Nairobi-Mombasa, the Northern Corridor). Class B are national trunks linking regions. "
        "Class C are primary feeder roads. Classes D and E are rural feeders, almost entirely unpaved and "
        "often impassable in heavy rain. Almost all maize moves on paved A/B roads once aggregated, but the "
        "first 5-50 km from farm to market centre is on D/E feeders -- this is where weather disruption, "
        "broken bridges, and seasonal impassability hit smallholders hardest."
    ),
    KnowledgeChunk(
        "TR-002", "Transport Cost Deltas - Paved vs Unpaved",
        "Kenya Transport Sector Study (World Bank 2022); KENHA Haulage Cost Schedules",
        "transport",
        "Typical truckage costs (2024) for maize and produce: Paved trunk road (A/B), 30-tonne truck: "
        "KES 7-12 per tonne-km. Gravel/unpaved feeder road: KES 15-25 per tonne-km, sometimes higher in wet "
        "season because of reduced load factors and longer transit time. Small-vehicle rates: pickup (1-2t) "
        "KES 25-40 per tonne-km; matatu-sized 7t lorries KES 15-20 per tonne-km. Farmers selling 5-20 bags "
        "typically cannot fill a full truck and pay a premium for shared or piecemeal transport. Concrete "
        "example: Trans-Nzoia to Nairobi (~380 km paved trunk) runs ~KES 180-220 per 90kg bag on a full lorry; "
        "the final 15 km from farm to Kitale collection point can cost another KES 40-80 per bag."
    ),
    KnowledgeChunk(
        "TR-003", "Aggregators, Brokers, and Farmer Transport Options",
        "Tegemeo Institute Smallholder Market Access Study 2021",
        "transport",
        "Most Kenyan smallholders sell to itinerant middlemen (brokers, 'madalali') who bring lorries or "
        "pickups to the farm gate or village market. Broker margins are typically 10-25% above farm-gate to "
        "wholesale-market prices, reflecting risk, financing, and transport. Alternatives for farmers: "
        "deliver to a county NCPB depot (requires registration and the depot being open for GMRP intake), "
        "aggregate through a SACCO or cooperative for shared truckage, or use a matatu/boda-boda for very "
        "small volumes to the nearest market centre. The smaller the volume, the weaker the farmer's "
        "bargaining position -- sub-10-bag smallholders routinely accept 20-35% below the KAMIS wholesale "
        "price reported for the nearest town."
    ),
    KnowledgeChunk(
        "TR-004", "Mombasa Port Bottlenecks and Seasonal Congestion",
        "Kenya Ports Authority Performance Reports; Shippers Council of Eastern Africa",
        "transport",
        "The Nairobi-Mombasa A109 corridor is Kenya's transport spine. Mombasa Port handles imports for the "
        "entire Northern Corridor (including landlocked Uganda, Rwanda, South Sudan, eastern DRC), which "
        "competes with outbound agricultural freight for the same truck fleet. Peak congestion windows: "
        "Nov-Jan (holiday consumer imports) and Mar-May (fertilizer and agro-input imports before Long Rains) "
        "push per-tonne-km haulage rates up 15-30%. The 2023-24 El Nino floods cut the A109 at multiple "
        "points (including the long-running Mtito Andei washout) and diverted freight for weeks. SGR "
        "(Standard Gauge Railway) handles containerized freight but has limited relevance for bulk "
        "agricultural produce moving on short domestic hops."
    ),
    KnowledgeChunk(
        "TR-005", "County Road Quality - Nyandarua Potato Case",
        "Nyandarua County Integrated Development Plan; National Potato Council of Kenya",
        "transport",
        "Road quality varies dramatically by county and is a first-order determinant of farm-gate price. "
        "Nyandarua -- Kenya's largest potato producer -- is notorious for poor feeder roads connecting "
        "Kinangop, Ol Kalou, and Ndaragwa to the tarmac network. In the Mar-May Long Rains, Nyandarua feeder "
        "roads become impassable for days at a time, trapping potato harvests at the farm and forcing distress "
        "sales to brokers who own 4WD trucks at steep discounts. By contrast, Meru and Nakuru potato zones "
        "have better C-class road coverage and farm-gate to wholesale price spreads are 15-20 percentage "
        "points narrower. Farmers and aggregators in rain-affected counties should plan sales windows around "
        "forecast dry spells."
    ),

    # -- Storage --------------------------------------------------------

    KnowledgeChunk(
        "ST-001", "NCPB Depot Storage - Access, Fees, Capacity",
        "NCPB Operations Manual; Kenya Grain Council Storage Directory",
        "storage",
        "NCPB operates ~110 depots with combined storage capacity around 2.0 million bags (180,000 MT) of "
        "grain. Beyond buyer-of-last-resort procurement, NCPB also rents storage to traders and farmer "
        "groups at KES 8-15 per 90kg bag per month (varies by depot and season). Access for smallholders "
        "is mediated by registration requirements (national ID, KRA PIN, cooperative or group membership). "
        "Major depots: Eldoret, Kitale, Bungoma, Nakuru, Meru, Nairobi Industrial Area. Smallholder "
        "deposits have to meet intake quality standards (<13.5% moisture, clean). Warehouse-receipt-backed "
        "lending against NCPB stock exists but is limited in practice."
    ),
    KnowledgeChunk(
        "ST-002", "Community Aggregation Centres (CACs)",
        "AGRA Kenya Smallholder Aggregation Review; MoALF Cooperative Sub-Sector Report",
        "storage",
        "Community Aggregation Centres are smallholder-focused collection and short-term storage facilities, "
        "typically county-government-built or AGRA/NGO-funded structures of 50-500 MT capacity. CACs allow "
        "farmers to pool grain, share drying floors and moisture meters, and negotiate as a unit with traders "
        "or with NCPB. Strongest CAC networks are in Bungoma, Busia, Trans-Nzoia, and Meru. Storage fees are "
        "nominal (KES 5-10 per bag per month) but capacity is limited and governance is uneven -- some CACs "
        "are effectively dormant. CAC membership typically provides the bridge smallholders need to access "
        "the warehouse receipt system or direct NCPB delivery."
    ),
    KnowledgeChunk(
        "ST-003", "Warehouse Receipt System - KACE and WRC",
        "Kenya Agricultural Commodity Exchange (KACE); Warehouse Receipt System Council Act 2019",
        "storage",
        "Kenya's Warehouse Receipt System, formalized under the Warehouse Receipt System Council Act 2019, "
        "remains nascent relative to more mature counterparts (e.g., Zambia, Uganda). KACE (Kenya Agricultural "
        "Commodity Exchange) pioneered receipt-based trading and price-discovery bulletin services, and a "
        "small network of licensed warehouses issues negotiable receipts usable as loan collateral. Typical "
        "all-in cost (storage + fumigation + receipt fees): KES 40-80 per 90kg bag per month. Pledge-loan "
        "advance against receipt: 50-70% of market value at 12-15% annual. System is most functional for "
        "maize in Rift Valley warehouses; coverage for pulses, sorghum, and perishables is thin."
    ),

    # -- Shocks ---------------------------------------------------------

    KnowledgeChunk(
        "SH-001", "2020-2023 Horn of Africa Drought - Five Failed Rainy Seasons",
        "FEWS NET Horn of Africa Special Report 2023; WFP VAM Kenya Drought Impact Assessment",
        "shock",
        "The 2020-2023 Horn of Africa drought was the longest and most severe drought in the region since "
        "at least 1981, defined by five consecutive below-average rainy seasons (2020 Short Rains through "
        "2022 Short Rains). In Kenya the ASAL counties -- Turkana, Marsabit, Mandera, Wajir, Garissa, "
        "Isiolo, Samburu, Tana River, Kitui, Makueni -- bore the brunt, with ~4.4 million people food-"
        "insecure at the 2022 peak. Maize wholesale prices in affected northern and eastern markets "
        "(Garissa, Wajir, Mandera, Kitui, Marsabit) spiked 60-100% above five-year averages. Short Rains "
        "2023 brought partial recovery but the humanitarian caseload remained elevated into 2024. The "
        "drought is the signature shock in the first half of the LastMileBench Kenya benchmark window."
    ),
    KnowledgeChunk(
        "SH-002", "2023-24 El Nino Floods - October Onwards",
        "Kenya Red Cross Situation Reports 2023-24; World Weather Attribution El Nino Kenya Analysis",
        "shock",
        "The Short Rains 2023 season (Oct-Dec) delivered an El Nino-driven above-average rainfall that "
        "tipped into widespread flooding from late October 2023 through April 2024. Impacts: Tana River "
        "overflow and dam spillover (Garsen, Tana Delta), landslide-driven road closures in Rift Valley "
        "(Elgeyo Marakwet, West Pokot), inundated maize-harvest areas in lower Eastern Kenya just as Short "
        "Rains crops were being brought in, and multiple cuts to the A109 Nairobi-Mombasa highway. More "
        "than 300 deaths and 500,000 displaced at peak in April-May 2024. Maize transit times from "
        "Trans-Nzoia and Uasin Gishu to Nairobi lengthened by 30-60% for weeks, widening producer-to-"
        "wholesale spreads. This is the second signature shock in the LastMileBench Kenya benchmark window."
    ),
    KnowledgeChunk(
        "SH-003", "IPC/FEWS NET Food Security Classifications for Kenya",
        "IPC Global Partners; FEWS NET Kenya Food Security Outlook (https://fews.net/east-africa/kenya)",
        "shock",
        "FEWS NET and the IPC (Integrated Food Security Phase Classification) use a five-phase scale: "
        "1-Minimal, 2-Stressed, 3-Crisis, 4-Emergency, 5-Famine. Kenya's ASAL counties have been chronically "
        "in Phase 2 (Stressed) or Phase 3 (Crisis) since the mid-2000s, with brief escalations to Phase 4 "
        "(Emergency) during acute drought peaks -- including much of 2022 across northern and eastern "
        "counties. Agricultural high-potential zones (Rift Valley, Western, Central) typically sit in Phase 1. "
        "FEWS NET publishes a Kenya Food Security Outlook every four months with updated county-level maps, "
        "the canonical reference for cross-regional food-security context in the benchmark panel."
    ),
]

KNOWLEDGE_BASE = KNOWLEDGE_CHUNKS
