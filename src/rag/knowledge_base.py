"""
Curated knowledge base for health supply chain RAG.

Contains ~35 text chunks drawn from WHO essential medicines lists, MSH
procurement guidelines, IDSR protocols, treatment standards, cold chain
management, and supply chain best practices. Each chunk has an id, title,
source, category, and text body.
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


KNOWLEDGE_BASE: list[KnowledgeChunk] = [
    # ── WHO Essential Medicines ──────────────────────────────────────────────
    KnowledgeChunk(
        id="who-em-001",
        title="ACT First-Line Malaria Treatment",
        source="WHO Model List of Essential Medicines, 23rd List (2023)",
        category="WHO Essential Medicines",
        text=(
            "Artemisinin-based combination therapy (ACT), specifically artemether-lumefantrine "
            "(AL) 20/120mg, is the WHO-recommended first-line treatment for uncomplicated "
            "P. falciparum malaria. A full adult course is 6 doses over 3 days (24 tablets). "
            "Pediatric dosing is weight-based. WHO recommends maintaining a minimum 2-month "
            "safety stock of ACTs at health facility level to prevent stockouts during "
            "seasonal malaria surges. Stockout of ACTs directly increases malaria mortality, "
            "particularly in children under 5."
        ),
    ),
    KnowledgeChunk(
        id="who-em-002",
        title="ORS and Zinc for Diarrhoeal Disease",
        source="WHO/UNICEF Joint Statement on Clinical Management of Acute Diarrhoea (2004, updated 2013)",
        category="WHO Essential Medicines",
        text=(
            "Oral Rehydration Salts (ORS) combined with Zinc supplementation is the "
            "recommended treatment for acute watery diarrhoea in children under 5. Each "
            "episode requires approximately 2 sachets of ORS (1L formulation) and a 10-day "
            "course of Zinc 20mg dispersible tablets (10 tablets for children under 6 months "
            "at 10mg/day, 20mg/day for older children). ORS reduces mortality from acute "
            "diarrhoea by up to 93%. Zinc supplementation reduces duration and severity of "
            "the episode and decreases incidence of diarrhoea for 2-3 months after treatment."
        ),
    ),
    KnowledgeChunk(
        id="who-em-003",
        title="Amoxicillin for Pneumonia",
        source="WHO Pocket Book of Hospital Care for Children, 2nd Edition (2013)",
        category="WHO Essential Medicines",
        text=(
            "Amoxicillin 500mg is the first-line antibiotic for non-severe community-acquired "
            "pneumonia in children and adults. For children, dosing is 40mg/kg/day in 2 divided "
            "doses for 5 days. Amoxicillin is preferred over cotrimoxazole due to increasing "
            "resistance patterns. Facilities should maintain at least 1 month safety stock. "
            "During rainy seasons in tropical regions, respiratory infection rates typically "
            "increase 20-40%, requiring proportional increases in amoxicillin procurement."
        ),
    ),
    KnowledgeChunk(
        id="who-em-004",
        title="Oxytocin for Postpartum Haemorrhage",
        source="WHO Recommendations for Prevention and Treatment of PPH (2012, updated 2018)",
        category="WHO Essential Medicines",
        text=(
            "Oxytocin 10 IU (intramuscular or intravenous) is the recommended first-line "
            "uterotonic for prevention and treatment of postpartum haemorrhage (PPH). PPH is "
            "the leading cause of maternal death globally. Oxytocin must be stored at 2-8 C "
            "and is sensitive to heat and light. Facilities without reliable cold chain should "
            "consider heat-stable alternatives (carbetocin, misoprostol). Every facility "
            "conducting deliveries must maintain oxytocin stock."
        ),
    ),
    KnowledgeChunk(
        id="who-em-005",
        title="Malaria Rapid Diagnostic Tests",
        source="WHO Guidelines for Malaria Diagnosis (2022)",
        category="WHO Essential Medicines",
        text=(
            "Malaria rapid diagnostic tests (RDTs) detecting P. falciparum histidine-rich "
            "protein 2 (HRP2) or pan-Plasmodium lactate dehydrogenase (pLDH) should be "
            "available at all levels of the health system. WHO recommends parasitological "
            "confirmation before treatment in all cases. RDT consumption should roughly "
            "track ACT consumption — a facility using significantly more ACTs than RDTs may "
            "be treating without diagnosis (presumptive treatment), which WHO discourages. "
            "RDTs should be stored below 40 C and away from direct sunlight. Shelf life is "
            "typically 18-24 months from manufacture."
        ),
    ),
    KnowledgeChunk(
        id="who-em-006",
        title="Cotrimoxazole Prophylaxis",
        source="WHO Guidelines on Post-Exposure Prophylaxis for HIV (2014)",
        category="WHO Essential Medicines",
        text=(
            "Cotrimoxazole 480mg (sulfamethoxazole 400mg + trimethoprim 80mg) is used for "
            "prophylaxis in HIV-positive patients and for treatment of various infections. "
            "It is on the WHO Essential Medicines List. For HIV prophylaxis, 1 tablet daily "
            "is the standard adult dose. Cotrimoxazole has broad-spectrum activity against "
            "bacteria, protozoa, and fungi. Facilities serving populations with high HIV "
            "prevalence should maintain higher stocks proportional to their ART cohort size."
        ),
    ),
    KnowledgeChunk(
        id="who-em-007",
        title="Essential Medicines for NCDs",
        source="WHO Package of Essential NCD Interventions (WHO PEN, 2020)",
        category="WHO Essential Medicines",
        text=(
            "Metformin 500mg is the first-line treatment for type 2 diabetes. Amlodipine 5mg "
            "is a preferred first-line antihypertensive. Both are on the WHO Essential "
            "Medicines List. Unlike infectious disease drugs, NCD medications show minimal "
            "seasonal variation in demand. Consumption is driven by the facility's chronic "
            "disease cohort size. Stockouts of NCD medications lead to treatment interruptions "
            "that increase cardiovascular events and diabetes complications. Facilities should "
            "maintain continuous supply with at least 1-month buffer."
        ),
    ),

    # ── MSH Procurement Guide ────────────────────────────────────────────────
    KnowledgeChunk(
        id="msh-proc-001",
        title="Emergency Procurement Thresholds",
        source="MSH Managing Drug Supply, 3rd Edition (2012)",
        category="MSH Procurement Guide",
        text=(
            "Emergency procurement should be triggered when stock of any essential medicine "
            "falls below 2 weeks of average monthly consumption (AMC). The emergency "
            "procurement channel typically reduces lead time from 14 days (routine) to 5 days, "
            "but at a 15-20% cost premium. Facilities should weigh the cost of emergency "
            "procurement against the clinical cost of stockout. For critical medicines "
            "(ACTs, ORS, oxytocin), emergency procurement is always justified when stock "
            "falls below the minimum threshold."
        ),
    ),
    KnowledgeChunk(
        id="msh-proc-002",
        title="Safety Stock Calculation",
        source="MSH Managing Drug Supply, 3rd Edition (2012)",
        category="MSH Procurement Guide",
        text=(
            "Safety stock should equal the lead time demand multiplied by a service level "
            "factor. For essential medicines at facility level, the standard formula is: "
            "Safety Stock = Average Monthly Consumption x Lead Time (months) x 1.5. The 1.5 "
            "factor provides a ~95% service level. For facilities with unreliable supply "
            "chains or highly variable demand (e.g., malaria-endemic areas during rainy "
            "season), increase the factor to 2.0. Maximum stock level = Safety Stock + "
            "Average Monthly Consumption x Review Period."
        ),
    ),
    KnowledgeChunk(
        id="msh-proc-003",
        title="Budget-Constrained Procurement",
        source="MSH Managing Drug Supply, 3rd Edition (2012)",
        category="MSH Procurement Guide",
        text=(
            "When budget is insufficient to procure all needed medicines, prioritize using "
            "the VEN (Vital-Essential-Necessary) classification. Vital medicines (ACTs, ORS, "
            "oxytocin, antibiotics for pneumonia) must be funded first, even if it means "
            "zero procurement of Necessary items. A common allocation rule: Vital 60%, "
            "Essential 30%, Necessary 10% of the procurement budget. Never reduce Vital "
            "medicine quantities to fund Necessary items."
        ),
    ),
    KnowledgeChunk(
        id="msh-proc-004",
        title="Quantification Methods",
        source="MSH Managing Drug Supply, 3rd Edition (2012)",
        category="MSH Procurement Guide",
        text=(
            "Drug quantification can use three methods: (1) Consumption-based: extrapolate "
            "from historical consumption data, adjusted for stockouts and seasonality. Most "
            "accurate when historical data quality is good. (2) Morbidity-based: calculate "
            "from disease incidence and standard treatment protocols. Preferred when "
            "consumption data is unreliable. (3) Service-level projection: based on expected "
            "patient visits and prescribing patterns. Ideally, triangulate all three methods "
            "and investigate discrepancies. A 20%+ discrepancy between consumption and "
            "morbidity methods signals potential data quality issues, prescribing "
            "irregularities, or stock theft."
        ),
    ),
    KnowledgeChunk(
        id="msh-proc-005",
        title="Lead Time Management",
        source="MSH Managing Drug Supply, 3rd Edition (2012)",
        category="MSH Procurement Guide",
        text=(
            "Lead times vary significantly by procurement source. Central/national warehouse: "
            "5-10 days. Regional medical store: 10-21 days. International procurement: "
            "30-90 days. Emergency/local purchase: 1-5 days. Facilities must factor lead "
            "time into reorder points. The reorder point = Average Daily Consumption x Lead "
            "Time (days) + Safety Stock. Facilities with longer lead times need higher "
            "reorder points and larger safety stocks. During peak disease seasons, lead "
            "times often increase by 30-50% due to supply chain congestion."
        ),
    ),

    # ── Treatment Protocols ──────────────────────────────────────────────────
    KnowledgeChunk(
        id="tx-proto-001",
        title="Malaria Treatment Protocol",
        source="WHO Guidelines for Malaria Treatment, 3rd Edition (2015, updated 2022)",
        category="Treatment Protocols",
        text=(
            "For uncomplicated P. falciparum malaria: Artemether-lumefantrine (AL) is given "
            "as a 3-day course. Adults (>35kg): 4 tablets per dose, 6 doses total (at 0, 8, "
            "24, 36, 48, and 60 hours). Each confirmed malaria case consumes 1 full course "
            "(24 tablets or 1 course unit). Presumptive treatment without RDT confirmation "
            "is discouraged. For severe malaria: injectable artesunate followed by oral ACT "
            "once patient can take oral medication. Children under 5 account for "
            "approximately 80% of malaria deaths in sub-Saharan Africa."
        ),
    ),
    KnowledgeChunk(
        id="tx-proto-002",
        title="Diarrhoea Treatment Protocol",
        source="WHO/UNICEF Integrated Management of Childhood Illness (IMCI)",
        category="Treatment Protocols",
        text=(
            "Acute watery diarrhoea treatment: (1) Assess dehydration status. (2) Give ORS "
            "for rehydration — Plan A (no dehydration): ORS after each loose stool, Plan B "
            "(some dehydration): 75ml/kg ORS over 4 hours, Plan C (severe): IV Ringer's "
            "Lactate. (3) Give Zinc: 20mg/day for 10 days (10mg for infants <6 months). "
            "(4) Continue feeding. Per episode, expect consumption of 2-4 ORS sachets and "
            "10 Zinc tablets. During cholera outbreaks, ORS consumption can spike 5-10x "
            "above normal baseline, requiring emergency procurement."
        ),
    ),
    KnowledgeChunk(
        id="tx-proto-003",
        title="Pneumonia Treatment Protocol",
        source="WHO Pocket Book of Hospital Care for Children (2013)",
        category="Treatment Protocols",
        text=(
            "Non-severe pneumonia: Oral amoxicillin 40mg/kg/dose twice daily for 5 days. "
            "Severe pneumonia: IV/IM ampicillin 50mg/kg every 6 hours plus gentamicin "
            "7.5mg/kg once daily for at least 5 days. If no improvement in 48 hours, switch "
            "to ceftriaxone. Treatment failure with first-line antibiotics occurs in "
            "approximately 15-20% of cases. Facilities should maintain second-line "
            "antibiotics at 20% of first-line stock levels."
        ),
    ),

    # ── Cold Chain Management ────────────────────────────────────────────────
    KnowledgeChunk(
        id="cold-001",
        title="Oxytocin Cold Chain Requirements",
        source="WHO Technical Report on Oxytocin Storage (2019)",
        category="Cold Chain Management",
        text=(
            "Oxytocin must be stored at 2-8 C (refrigerator temperature). If cold chain "
            "is compromised, oxytocin potency degrades significantly: at 25 C, potency "
            "drops below 90% within 3 months; at 30 C, degradation accelerates to within "
            "1 month; above 40 C, oxytocin may lose clinically significant potency within "
            "48 hours. Visual inspection cannot detect potency loss. Facilities without "
            "reliable cold chain (refrigerator + backup power) should not store oxytocin "
            "for more than 72 hours and should use heat-stable carbetocin or misoprostol "
            "as alternatives."
        ),
    ),
    KnowledgeChunk(
        id="cold-002",
        title="RDT Storage Requirements",
        source="WHO Malaria RDT Product Testing (2018)",
        category="Cold Chain Management",
        text=(
            "Malaria RDTs should be stored below 40 C in a cool, dry place. While not "
            "requiring strict cold chain like vaccines, prolonged exposure to temperatures "
            "above 40 C or high humidity (>70%) degrades test accuracy. False-negative rates "
            "increase from baseline 5% to 15-20% after storage above 45 C for 90 days. "
            "RDTs stored in direct sunlight or metal shipping containers in tropical "
            "climates may exceed temperature limits. Transport in insulated containers is "
            "recommended. Expiry dates assume proper storage conditions and may not be "
            "valid if storage was suboptimal."
        ),
    ),
    KnowledgeChunk(
        id="cold-003",
        title="Cold Chain Monitoring Best Practices",
        source="WHO Effective Vaccine Store Management (2005, updated 2020)",
        category="Cold Chain Management",
        text=(
            "Temperature monitoring for cold chain medicines should include: continuous "
            "electronic logging (30-minute intervals minimum), twice-daily manual checks, "
            "use of Vaccine Vial Monitors (VVMs) or similar irreversible temperature "
            "indicators. Cold chain failure is defined as temperature excursion outside "
            "2-8 C for more than 60 minutes. All cold chain failures must be documented "
            "with duration, peak temperature, and affected stock. Affected medicines should "
            "be quarantined and assessed by a pharmacist before use."
        ),
    ),

    # ── IDSR Guidelines ──────────────────────────────────────────────────────
    KnowledgeChunk(
        id="idsr-001",
        title="Cholera Alert Thresholds",
        source="WHO IDSR Technical Guidelines, 3rd Edition (2019)",
        category="IDSR Guidelines",
        text=(
            "Cholera: alert threshold is 1 suspected case (acute watery diarrhoea with "
            "severe dehydration or death) in a non-endemic area, or doubling of cases in "
            "an endemic area within a 2-week period. Epidemic threshold is confirmed Vibrio "
            "cholerae in stool culture. During cholera outbreaks, ORS consumption increases "
            "5-10x above baseline. Facilities within 50km of an outbreak should immediately "
            "increase ORS stock to 3-month supply. Cholera case fatality rate drops from "
            ">50% without treatment to <1% with proper rehydration therapy."
        ),
    ),
    KnowledgeChunk(
        id="idsr-002",
        title="Malaria Epidemic Detection",
        source="WHO IDSR Technical Guidelines, 3rd Edition (2019)",
        category="IDSR Guidelines",
        text=(
            "Malaria epidemic threshold: when weekly malaria cases exceed the third "
            "quartile of cases for the same week over the previous 5 years, OR when cases "
            "exceed 2 standard deviations above the weekly mean. In areas with seasonal "
            "malaria, the beginning of the transmission season is not an epidemic — it is "
            "the expected seasonal increase. Epidemic response requires 3-4x normal ACT "
            "and RDT stock levels. District-level case data must be reported weekly during "
            "epidemic periods."
        ),
    ),
    KnowledgeChunk(
        id="idsr-003",
        title="IDSR Reporting Timelines",
        source="WHO IDSR Technical Guidelines, 3rd Edition (2019)",
        category="IDSR Guidelines",
        text=(
            "Immediately notifiable diseases (within 24 hours): cholera, measles, yellow "
            "fever, viral haemorrhagic fever, plague, meningococcal meningitis. Weekly "
            "reportable: malaria, acute watery diarrhoea, acute respiratory infection, "
            "pneumonia, typhoid. Monthly reportable: HIV, TB, diabetes, hypertension. "
            "Reporting completeness target: 80% of facilities reporting on time. Facilities "
            "with reporting rates below 60% should have their surveillance data adjusted "
            "upward by 1/(reporting rate) to estimate true disease burden."
        ),
    ),
    KnowledgeChunk(
        id="idsr-004",
        title="Cross-Validating Surveillance and Supply Data",
        source="WHO Health Facility Survey Manual (2018)",
        category="IDSR Guidelines",
        text=(
            "IDSR disease case counts should be cross-validated against drug consumption "
            "data. Expected relationships: each malaria case = 1 ACT course + 1 RDT. Each "
            "diarrhoea case in children <5 = 2 ORS sachets + 10 Zinc tablets. Each pneumonia "
            "case = 10 amoxicillin capsules (5-day course). Significant discrepancies (>30%) "
            "between cases and consumption indicate: (a) undertreating (cases > consumption), "
            "(b) over-prescribing or stock diversion (consumption > cases), (c) data quality "
            "issues in one or both systems, or (d) referral patients not captured in local "
            "IDSR data."
        ),
    ),

    # ── Supply Chain Best Practices ──────────────────────────────────────────
    KnowledgeChunk(
        id="sc-bp-001",
        title="FEFO Stock Rotation",
        source="USAID | DELIVER PROJECT Task Order 4 (2011)",
        category="Supply Chain Best Practices",
        text=(
            "First Expiry, First Out (FEFO) must be enforced at all facility levels. "
            "Products with the nearest expiry date should be dispensed first, regardless "
            "of when they were received. Average wastage rates for essential medicines "
            "range from 5-15% depending on storage conditions, with highest wastage in "
            "facilities with poor stock rotation practices. Expiry-related wastage can be "
            "reduced to below 3% with proper FEFO implementation and regular stock reviews. "
            "Monthly physical inventory counts should include expiry date checks."
        ),
    ),
    KnowledgeChunk(
        id="sc-bp-002",
        title="ABC-VEN Analysis for Procurement",
        source="USAID | DELIVER PROJECT (2011)",
        category="Supply Chain Best Practices",
        text=(
            "ABC analysis classifies drugs by annual expenditure: A items (top 20% of drugs "
            "consuming 80% of budget), B items (next 30% consuming 15%), C items (bottom "
            "50% consuming 5%). VEN classifies by clinical importance: Vital (life-saving, "
            "no alternative), Essential (important but alternatives exist), Necessary "
            "(symptomatic relief). Procurement priority should follow ABC-VEN cross-matrix: "
            "AV (high cost + vital) gets highest attention, CN (low cost + necessary) gets "
            "minimum monitoring. ACTs, ORS, and oxytocin are typically AV or BV items."
        ),
    ),
    KnowledgeChunk(
        id="sc-bp-003",
        title="Stockout Root Cause Analysis",
        source="WHO Service Availability and Readiness Assessment (SARA) Manual (2015)",
        category="Supply Chain Best Practices",
        text=(
            "Common root causes of stockouts in Sub-Saharan African health facilities: "
            "(1) Inaccurate forecasting (35% of stockouts): demand underestimated due to "
            "poor data or failure to account for seasonality. (2) Supply chain delays "
            "(25%): transport failures, customs delays, warehouse stock-outs. (3) Budget "
            "constraints (20%): insufficient allocation or delayed disbursement. (4) Data "
            "quality (12%): inaccurate stock counts, unreported losses, data entry errors. "
            "(5) Stock theft/diversion (8%): medicines diverted to private pharmacies or "
            "personal use. SARA surveys show 36% of facilities in Sub-Saharan Africa "
            "experience stockout of at least one tracer medicine on the day of assessment."
        ),
    ),
    KnowledgeChunk(
        id="sc-bp-004",
        title="Last-Mile Distribution Challenges",
        source="JSI/USAID GHSC-PSM Annual Report (2022)",
        category="Supply Chain Best Practices",
        text=(
            "Last-mile distribution in rural Sub-Saharan Africa faces unique challenges: "
            "poor road infrastructure (especially during rainy season), limited vehicle "
            "availability, high transport costs per unit. Strategies to improve last-mile "
            "delivery: (1) Hub-and-spoke distribution with district depots serving "
            "10-15 facilities. (2) Community-based distribution through CHWs for high-volume "
            "items (ORS, Zinc, ACTs). (3) SMS-based ordering systems to reduce order "
            "processing time. (4) Consolidated delivery schedules to reduce transport costs. "
            "Average last-mile delivery cost: $0.05-0.15 per unit, highest for cold chain "
            "products."
        ),
    ),
    KnowledgeChunk(
        id="sc-bp-005",
        title="Data Quality in LMIS",
        source="WHO Health Metrics Network Framework (2008, updated 2019)",
        category="Supply Chain Best Practices",
        text=(
            "LMIS data quality assessment should evaluate 5 dimensions: (1) Completeness: "
            "% of expected reports received (target >90%). (2) Timeliness: % of reports "
            "received by deadline (target >80%). (3) Accuracy: stock balances verified "
            "against physical count (within +/-5%). (4) Consistency: consumption patterns "
            "consistent with disease burden and population. (5) Reliability: same data "
            "reported across parallel systems (DHIS2, paper registers, eLMIS). Poor "
            "reporting facilities (completeness <60%) should have stock estimates adjusted "
            "using peer facility data or population-based consumption rates."
        ),
    ),
    KnowledgeChunk(
        id="sc-bp-006",
        title="Seasonal Demand Planning",
        source="PMI/USAID Malaria Operational Plan Guidelines (2023)",
        category="Supply Chain Best Practices",
        text=(
            "Seasonal demand planning for malaria-endemic areas: Pre-position ACTs and RDTs "
            "6-8 weeks before the expected start of the rainy/transmission season. Stock "
            "levels at the start of the season should be at maximum stock level (3-4 months "
            "supply for facility level). During peak season, monthly consumption of ACTs "
            "may increase 2-3x above dry-season baseline. Failure to pre-position leads to "
            "stockouts at peak transmission, when clinical need is highest. Post-season, "
            "monitor expiry dates on excess stock carefully — FEFO is critical."
        ),
    ),
    KnowledgeChunk(
        id="sc-bp-007",
        title="CHW Supply Chain Integration",
        source="WHO Guideline on Health Policy and System Support to Optimize CHW Programmes (2018)",
        category="Supply Chain Best Practices",
        text=(
            "Community Health Workers (CHWs) managing community case management (iCCM) of "
            "malaria, pneumonia, and diarrhoea need reliable supply of ACTs, RDTs, "
            "amoxicillin, ORS, and Zinc. CHW stock data should be integrated into facility "
            "LMIS to ensure accurate consumption tracking. CHW-reported stock levels often "
            "provide earlier warning of stockouts than facility LMIS, as CHWs are the first "
            "to exhaust high-demand items. When CHW reports conflict with facility stock "
            "records, the CHW report should be weighted more heavily if it is more recent "
            "(within 48 hours) and the facility has poor reporting quality."
        ),
    ),

    # ── Climate-Health Nexus ─────────────────────────────────────────────────
    KnowledgeChunk(
        id="clim-001",
        title="Rainfall and Malaria Transmission",
        source="Mordecai et al. (2013), Ecology Letters; WHO World Malaria Report (2023)",
        category="Climate-Health Nexus",
        text=(
            "Malaria transmission is temperature- and rainfall-dependent. The Mordecai "
            "temperature-transmission curve shows peak P. falciparum suitability at 25 C, "
            "with transmission dropping to zero below 18 C and above 34 C. Rainfall creates "
            "breeding sites for Anopheles mosquitoes; peak breeding occurs at 8-12mm/day "
            "average daily precipitation. Very heavy rainfall (>20mm/day sustained) can "
            "actually reduce transmission by flushing breeding sites. Malaria case incidence "
            "typically lags rainfall onset by 4-6 weeks (time for mosquito population "
            "growth and parasite development)."
        ),
    ),
    KnowledgeChunk(
        id="clim-002",
        title="Flooding and Diarrhoeal Disease",
        source="WHO Climate Change and Health Fact Sheet (2023); Levy et al., Environmental Health Perspectives (2016)",
        category="Climate-Health Nexus",
        text=(
            "Heavy rainfall events (>15mm/day) are associated with increased diarrhoeal "
            "disease through multiple pathways: (1) Contamination of drinking water sources "
            "with faecal matter. (2) Flooding of latrines and sewage systems. (3) Disruption "
            "of water treatment facilities. (4) Population displacement to crowded shelters. "
            "The relationship is non-linear: moderate rainfall may reduce diarrhoea by "
            "improving water access, while extreme rainfall increases it. Cholera outbreaks "
            "commonly follow 2-4 weeks after major flooding events. Urban informal "
            "settlements are most vulnerable due to poor drainage and sanitation."
        ),
    ),
    KnowledgeChunk(
        id="clim-003",
        title="Climate and Respiratory Infections",
        source="Tamerius et al., PLOS Pathogens (2013)",
        category="Climate-Health Nexus",
        text=(
            "In tropical regions, respiratory infection incidence shows different seasonal "
            "patterns than temperate zones. Instead of winter peaks, tropical respiratory "
            "infections tend to peak during rainy seasons, driven by: (1) Increased humidity "
            "favoring viral survival and aerosol transmission. (2) Indoor crowding during "
            "heavy rains. (3) Dampness in housing promoting mold growth. Humidity above 80% "
            "increases respiratory infection risk by approximately 15-25%. Temperature is "
            "less of a driver in tropical settings compared to rainfall and humidity."
        ),
    ),
    KnowledgeChunk(
        id="clim-004",
        title="El Nino and Disease Outbreaks in West Africa",
        source="WHO Health and Climate Change Country Profile: Nigeria (2022)",
        category="Climate-Health Nexus",
        text=(
            "El Nino Southern Oscillation (ENSO) events affect disease patterns in West "
            "Africa. El Nino years are associated with: increased rainfall in the Gulf of "
            "Guinea coast (Southern Nigeria, Ghana), leading to increased malaria and "
            "diarrhoeal disease; drought in the Sahel (Northern Nigeria), reducing malaria "
            "but increasing malnutrition. La Nina years show opposite patterns. Health "
            "commodity planning should incorporate ENSO forecasts (available 6+ months in "
            "advance from NOAA/IRI) to pre-position supplies. A strong El Nino can increase "
            "malaria burden by 20-40% in coastal West Africa."
        ),
    ),
]


def get_knowledge_base() -> list[KnowledgeChunk]:
    """Return the full knowledge base."""
    return KNOWLEDGE_BASE


def get_chunks_by_category(category: str) -> list[KnowledgeChunk]:
    """Return chunks filtered by category."""
    return [c for c in KNOWLEDGE_BASE if c.category == category]


def get_chunk_by_id(chunk_id: str) -> KnowledgeChunk | None:
    """Look up a single chunk by ID."""
    for c in KNOWLEDGE_BASE:
        if c.id == chunk_id:
            return c
    return None


CATEGORIES = sorted(set(c.category for c in KNOWLEDGE_BASE))
