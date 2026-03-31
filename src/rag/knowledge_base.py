"""
Curated knowledge base for health supply chain RAG.

Contains ~103 text chunks drawn from WHO essential medicines lists, MSH
procurement guidelines, IDSR protocols, treatment standards, cold chain
management, supply chain best practices, pharmacovigilance, inventory
management, community health worker programs, disease epidemiology,
maternal and child health, emergency response, health information systems,
and laboratory diagnostics. Each chunk has an id, title, source, category,
and text body.
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

    # ── Pharmacovigilance & Drug Safety ──────────────────────────────────────
    KnowledgeChunk(
        id="pharma-001",
        title="Antimicrobial Resistance Surveillance in Supply Chains",
        source="WHO Global Action Plan on Antimicrobial Resistance (2015)",
        category="Pharmacovigilance & Drug Safety",
        text=(
            "Antimicrobial resistance (AMR) threatens the effectiveness of first-line "
            "antibiotics used widely in primary care, including amoxicillin and cotrimoxazole. "
            "WHO recommends national AMR surveillance through the Global Antimicrobial "
            "Resistance and Use Surveillance System (GLASS). Supply chain managers must track "
            "shifts in prescribing from first-line to second-line antibiotics as a proxy "
            "indicator of emerging resistance. A sustained increase of more than 15% in "
            "second-line antibiotic consumption over two quarters may signal resistance-driven "
            "treatment failures requiring formulary review and updated quantification."
        ),
    ),
    KnowledgeChunk(
        id="pharma-002",
        title="Adverse Drug Reaction Reporting",
        source="WHO Safety Monitoring of Medicinal Products: Guidelines for Setting Up and Running a Pharmacovigilance Centre (2000, updated 2020)",
        category="Pharmacovigilance & Drug Safety",
        text=(
            "Pharmacovigilance systems at health facility level should capture adverse drug "
            "reactions (ADRs) through spontaneous reporting using the Individual Case Safety "
            "Report (ICSR) format compatible with the WHO Programme for International Drug "
            "Monitoring (VigiBase). Common ADRs affecting supply decisions include severe "
            "skin reactions to cotrimoxazole (Stevens-Johnson syndrome, incidence ~1 in "
            "10,000) and hepatotoxicity from anti-TB medications. Facilities reporting "
            "clusters of ADRs for a specific batch should quarantine remaining stock and "
            "report to the national pharmacovigilance centre within 24 hours."
        ),
    ),
    KnowledgeChunk(
        id="pharma-003",
        title="Counterfeit and Substandard Medicine Detection",
        source="WHO Global Surveillance and Monitoring System for Substandard and Falsified Medical Products (2017)",
        category="Pharmacovigilance & Drug Safety",
        text=(
            "WHO estimates that 1 in 10 medical products in low- and middle-income countries "
            "is substandard or falsified. Antimalarials and antibiotics are the most commonly "
            "counterfeited drug classes. Facility-level detection methods include visual "
            "inspection of packaging (holograms, batch numbers, spelling errors), verification "
            "using mobile authentication technologies (scratch-and-text codes), and basic "
            "quality testing with Minilab kits for thin-layer chromatography. Supply chain "
            "professionals should procure only from WHO-prequalified manufacturers or national "
            "regulatory authority-approved sources to reduce counterfeit risk."
        ),
    ),
    KnowledgeChunk(
        id="pharma-004",
        title="Drug Quality Assurance in Tropical Climates",
        source="WHO Technical Report Series No. 957: Stability Testing of Active Pharmaceutical Ingredients (2010)",
        category="Pharmacovigilance & Drug Safety",
        text=(
            "WHO climatic zone IVb (hot and very humid, common in tropical Africa and "
            "Southeast Asia) imposes accelerated stability testing conditions of 30 C/75% RH. "
            "Many essential medicines degrade faster in these conditions than their labeled "
            "shelf life suggests, particularly dispersible tablets and liquid formulations. "
            "Amoxicillin suspension reconstituted in high ambient temperatures (>30 C) may "
            "lose therapeutic potency within 7 days rather than the labeled 14 days. Facilities "
            "should counsel patients on storage and prioritize solid dosage forms over liquids "
            "where clinically equivalent options exist."
        ),
    ),
    KnowledgeChunk(
        id="pharma-005",
        title="Drug-Drug Interactions in Multi-Disease Settings",
        source="WHO Model Formulary (2008, updated 2021)",
        category="Pharmacovigilance & Drug Safety",
        text=(
            "In settings with high HIV, TB, and malaria co-infection, drug-drug interactions "
            "pose significant clinical and supply chain challenges. Rifampicin (TB treatment) "
            "reduces the plasma concentration of many antiretrovirals, particularly nevirapine "
            "and lopinavir, by 40-80% through CYP3A4 induction. Artemether-lumefantrine "
            "concentrations are also reduced by concurrent rifampicin use. Supply chain "
            "managers in high co-infection settings must stock alternative regimens (efavirenz-"
            "based ART, artesunate-amodiaquine for malaria) and anticipate more complex "
            "commodity baskets than single-disease programs."
        ),
    ),
    KnowledgeChunk(
        id="pharma-006",
        title="Storage-Related Degradation of Essential Medicines",
        source="MSH MDS: Storage and Distribution of Pharmaceuticals (2012)",
        category="Pharmacovigilance & Drug Safety",
        text=(
            "Temperature excursions during storage and transport are the leading cause of "
            "drug degradation in tropical supply chains. Ergometrine, another uterotonic, is "
            "even more heat-sensitive than oxytocin, losing up to 20% potency after 1 month "
            "at 30 C. Suppositories (e.g., artesunate rectal capsules for pre-referral severe "
            "malaria) melt above 35 C and must be stored in climate-controlled environments. "
            "Facilities should maintain temperature logs for all storage areas, and any product "
            "exposed to confirmed excursions beyond manufacturer specifications should be "
            "removed from dispensing stock and reported for disposal."
        ),
    ),
    KnowledgeChunk(
        id="pharma-007",
        title="Post-Market Surveillance for Vaccines",
        source="WHO Global Manual on Surveillance of Adverse Events Following Immunization (AEFI) (2016)",
        category="Pharmacovigilance & Drug Safety",
        text=(
            "Post-market surveillance for vaccines requires monitoring of Adverse Events "
            "Following Immunization (AEFIs) through both passive and active surveillance. "
            "Serious AEFIs (hospitalization, disability, death) must be reported within 24 "
            "hours. Causality assessment uses the WHO algorithm classifying events as "
            "vaccine-product related, immunization-error related, coincidental, or "
            "indeterminate. AEFI rates exceeding background rates trigger signal investigation. "
            "Supply chain actions include batch-level quarantine and enhanced cold chain "
            "auditing, as programmatic errors (cold chain failure) are the most common "
            "preventable cause of vaccine-related adverse events."
        ),
    ),
    KnowledgeChunk(
        id="pharma-008",
        title="Antimicrobial Stewardship and Supply Planning",
        source="WHO AWaRe Classification of Antibiotics (2021)",
        category="Pharmacovigilance & Drug Safety",
        text=(
            "The WHO AWaRe (Access, Watch, Reserve) classification system guides antibiotic "
            "procurement and use. Access antibiotics (e.g., amoxicillin, metronidazole) "
            "should constitute at least 60% of total antibiotic consumption at national "
            "level. Watch antibiotics (e.g., ciprofloxacin, azithromycin) have higher "
            "resistance potential and require monitoring. Reserve antibiotics (e.g., "
            "meropenem, colistin) are last-resort treatments. Supply chain managers should "
            "track the Access-to-Watch ratio monthly. A declining ratio below 60% Access "
            "signals inappropriate prescribing patterns and potential resistance emergence "
            "requiring intervention from drug and therapeutics committees."
        ),
    ),

    # ── Inventory Management ─────────────────────────────────────────────────
    KnowledgeChunk(
        id="inv-001",
        title="Bin Card Management for Health Commodities",
        source="USAID | DELIVER PROJECT: Logistics Handbook (2011)",
        category="Inventory Management",
        text=(
            "Bin cards (stock cards) are the primary inventory record at health facility "
            "level, maintained for each product at the storage location. Each transaction "
            "(receipt, issue, adjustment, loss) must be recorded with date, quantity, batch "
            "number, expiry date, and running balance. Physical stock should match the bin "
            "card balance; discrepancies exceeding 5% trigger investigation. Bin cards should "
            "be updated at the time of each transaction, not retrospectively. In USAID-"
            "supported programs, bin card accuracy rates above 90% are considered acceptable, "
            "with best-performing facilities achieving 95-98% concordance with physical counts."
        ),
    ),
    KnowledgeChunk(
        id="inv-002",
        title="Physical Inventory Count Procedures",
        source="MSH Managing Drug Supply, 3rd Edition (2012)",
        category="Inventory Management",
        text=(
            "Physical inventory counts should be conducted monthly for high-value and "
            "fast-moving items (VEN category V and A items in ABC analysis), and quarterly "
            "for slow-moving items. The count procedure requires: (1) suspending dispensing "
            "during the count or using a count-and-freeze method, (2) two independent "
            "counters for verification, (3) recording batch numbers and expiry dates, "
            "(4) reconciling count results against bin card and LMIS balances. Discrepancies "
            "above 2% for controlled substances or 5% for general stock require documented "
            "investigation and corrective action within 48 hours."
        ),
    ),
    KnowledgeChunk(
        id="inv-003",
        title="Stock Accuracy Metrics and Benchmarks",
        source="USAID GHSC-PSM: Supply Chain Indicators Guide (2020)",
        category="Inventory Management",
        text=(
            "Stock accuracy is measured as the percentage of items where physical count "
            "matches the system record within an acceptable tolerance (typically plus or "
            "minus 5%). USAID GHSC-PSM benchmarks define three performance tiers: high "
            "accuracy (above 95% of items within tolerance), moderate accuracy (80-95%), "
            "and low accuracy (below 80%). Root causes of poor stock accuracy include "
            "delayed bin card updates, unrecorded dispensing, pilferage, and data entry "
            "errors in electronic systems. Facilities consistently below 80% stock accuracy "
            "should receive targeted supportive supervision and may require transition from "
            "paper-based to electronic inventory management systems."
        ),
    ),
    KnowledgeChunk(
        id="inv-004",
        title="Min-Max Inventory Control Systems",
        source="MSH Managing Drug Supply, 3rd Edition (2012)",
        category="Inventory Management",
        text=(
            "The min-max inventory system sets two stock level thresholds for each product. "
            "The minimum stock level (reorder point) equals average monthly consumption "
            "multiplied by lead time plus safety stock. The maximum stock level equals "
            "minimum stock level plus average monthly consumption multiplied by the review "
            "period. When stock falls to or below the minimum, an order is placed to bring "
            "stock up to the maximum level. This system is preferred for facilities with "
            "irregular supply schedules. Order quantity equals maximum stock level minus "
            "current stock on hand minus stock on order. Typically, minimum is set at 2 "
            "months and maximum at 4 months of supply for facility-level stores."
        ),
    ),
    KnowledgeChunk(
        id="inv-005",
        title="ABC Analysis for Inventory Prioritization",
        source="USAID | DELIVER PROJECT: Guidelines for Managing the HIV/AIDS Supply Chain (2009)",
        category="Inventory Management",
        text=(
            "ABC analysis applied to inventory management classifies items by their annual "
            "consumption value to focus management attention. Category A items (typically "
            "10-20% of items representing 70-80% of total value) include antiretrovirals, "
            "ACTs, and injectable antibiotics requiring tight inventory control with weekly "
            "cycle counts. Category B items (20-30% of items, 15-20% of value) need monthly "
            "review. Category C items (50-70% of items, 5-10% of value) can be managed with "
            "simpler periodic review systems. Facilities should combine ABC with VEN analysis "
            "to ensure that clinically vital low-cost items receive adequate attention."
        ),
    ),
    KnowledgeChunk(
        id="inv-006",
        title="FEFO Implementation at Facility Level",
        source="USAID | DELIVER PROJECT: Logistics Handbook (2011)",
        category="Inventory Management",
        text=(
            "First Expiry First Out (FEFO) implementation requires physical organization of "
            "storage areas so that products with the earliest expiry date are most accessible "
            "for dispensing. Practical steps include: arranging cartons so labels with expiry "
            "dates face outward, placing newer stock behind older stock on shelves, using "
            "color-coded expiry date labels (red for less than 3 months, yellow for 3-6 "
            "months, green for more than 6 months), and conducting weekly expiry date reviews. "
            "Products within 3 months of expiry should be flagged for redistribution to "
            "higher-volume facilities or expedited use. Products past expiry must be "
            "physically separated and documented for disposal."
        ),
    ),
    KnowledgeChunk(
        id="inv-007",
        title="Automated Inventory Management Systems",
        source="USAID GHSC-PSM: Digital Health and Supply Chain Integration (2021)",
        category="Inventory Management",
        text=(
            "Automated inventory management systems using barcode or QR code scanning "
            "improve data accuracy and reduce the labor burden of manual record-keeping. "
            "Implementation requires handheld scanners or smartphones with camera "
            "capability, pre-printed barcode labels matching product master data, and "
            "connectivity for data synchronization with central eLMIS. Studies in Tanzania "
            "and Ethiopia show barcode-based systems improve stock accuracy from 78% to "
            "94% and reduce average order processing time from 3 days to 4 hours. Key "
            "challenges include initial hardware costs (approximately 200-400 USD per "
            "facility), reliable internet connectivity, and staff training requirements "
            "averaging 3-5 days for proficiency."
        ),
    ),
    KnowledgeChunk(
        id="inv-008",
        title="Shrinkage and Pilferage Prevention",
        source="WHO Good Distribution Practices for Pharmaceutical Products, Technical Report Series No. 957 (2010)",
        category="Inventory Management",
        text=(
            "Inventory shrinkage in pharmaceutical supply chains encompasses pilferage, "
            "administrative errors, and unrecorded damage or expiry. WHO Good Distribution "
            "Practice guidelines recommend physical access controls (locked storage with "
            "limited key holders), segregation of duties (different staff for receiving, "
            "storing, and dispensing), and regular unannounced spot checks. Shrinkage rates "
            "exceeding 2% of total stock value warrant formal investigation. High-value "
            "items (ARVs, injectable antibiotics) and items with street resale value "
            "(analgesics, antimalarials) are most susceptible. Facilities should maintain "
            "a shrinkage log documenting each identified loss with quantity, value, suspected "
            "cause, and corrective action taken."
        ),
    ),
    KnowledgeChunk(
        id="inv-009",
        title="Warehouse Layout for Health Commodities",
        source="MSH MDS: Guidelines for the Storage of Essential Medicines and Other Health Commodities (2003)",
        category="Inventory Management",
        text=(
            "Warehouse layout for health commodities should follow a systematic arrangement: "
            "separate zones for receiving/inspection, bulk storage, active picking, cold "
            "chain, flammables, and quarantine/expired stock. Products should be stored "
            "alphabetically by generic name within each zone to facilitate retrieval. "
            "Pallets must be raised 10 cm from the floor and positioned 30 cm from walls "
            "to prevent moisture damage and allow air circulation. Heavy and fast-moving "
            "items should be placed near the dispatch area. A clear flow from receipt to "
            "dispatch minimizes handling errors. Floor markings, signage, and organized "
            "shelf labeling reduce picking errors by an estimated 30-40%."
        ),
    ),
    KnowledgeChunk(
        id="inv-010",
        title="Inventory Key Performance Indicators",
        source="USAID GHSC-PSM: Supply Chain Indicators Guide (2020)",
        category="Inventory Management",
        text=(
            "Key performance indicators for inventory management in health supply chains "
            "include: stock accuracy rate (target above 95%), stockout rate (target below "
            "5% of tracer items), order fill rate (target above 90%), inventory turnover "
            "ratio (optimal 4-6 turns per year for essential medicines), wastage rate due "
            "to expiry (target below 3%), and reporting rate (target above 90% of facilities "
            "reporting on time). These KPIs should be tracked monthly at facility level and "
            "aggregated quarterly at district and national levels. Dashboard visualization "
            "with red-yellow-green thresholds enables rapid identification of underperforming "
            "facilities for targeted supportive supervision visits."
        ),
    ),

    # ── Community Health Worker Programs ─────────────────────────────────────
    KnowledgeChunk(
        id="chw-001",
        title="iCCM Drug Kit Composition and Resupply",
        source="WHO/UNICEF Joint Statement on integrated Community Case Management (iCCM) (2012)",
        category="Community Health Worker Programs",
        text=(
            "Integrated community case management (iCCM) drug kits for CHWs typically "
            "contain ACTs in age-appropriate packs (infant, child, adolescent), malaria "
            "RDTs, amoxicillin dispersible tablets (250mg), ORS sachets, zinc dispersible "
            "tablets (20mg), and a respiratory timer for pneumonia assessment. Standard kit "
            "composition is calibrated for approximately 50 cases per month. Resupply "
            "should occur at least monthly, tied to submission of the CHW activity report. "
            "Kit-based resupply (fixed quantities) is simpler but leads to imbalances; "
            "consumption-based resupply (replacing what was used) is more efficient but "
            "requires accurate CHW record-keeping."
        ),
    ),
    KnowledgeChunk(
        id="chw-002",
        title="CHW Reporting Tools and Stock Tracking",
        source="UNICEF iCCM Implementation Guide (2014)",
        category="Community Health Worker Programs",
        text=(
            "CHW reporting tools for supply management include the patient register "
            "(recording each case treated with commodities used), the monthly activity "
            "report (aggregating cases and commodity consumption), and the stock management "
            "form (tracking receipts, usage, losses, and closing balance). Paper-based "
            "systems remain common, but errors in tallying and transcription lead to "
            "inaccuracies in 20-30% of reports. WHO recommends simplified pictorial forms "
            "for CHWs with limited literacy. Integration of CHW reports into the facility "
            "LMIS ensures their consumption data informs district-level quantification and "
            "prevents systematic underestimation of commodity needs."
        ),
    ),
    KnowledgeChunk(
        id="chw-003",
        title="CHW Supervision and Supply Chain Quality",
        source="WHO Guideline on Health Policy and System Support to Optimize CHW Programmes (2018)",
        category="Community Health Worker Programs",
        text=(
            "Regular supportive supervision is critical for maintaining CHW supply chain "
            "performance. WHO recommends monthly supervision visits that include physical "
            "stock verification, review of patient registers for treatment appropriateness, "
            "assessment of storage conditions at the CHW's home or community health post, "
            "and on-the-job training for stock management. Studies in Mozambique and Malawi "
            "show that CHWs receiving monthly supervision have 40-50% lower stockout rates "
            "than unsupervised CHWs. Supervision checklists should include verification of "
            "FEFO practice, expired stock removal, and accuracy of the monthly consumption "
            "report."
        ),
    ),
    KnowledgeChunk(
        id="chw-004",
        title="mHealth Ordering Systems for CHWs",
        source="Medic Mobile / Community Health Toolkit Documentation (2020)",
        category="Community Health Worker Programs",
        text=(
            "Mobile health (mHealth) platforms enable CHWs to submit stock reports and "
            "resupply requests via SMS or smartphone applications, reducing the delay "
            "between stock depletion and reorder. Systems such as the Community Health "
            "Toolkit use structured SMS workflows where CHWs report closing balances for "
            "each commodity using short codes. The system calculates resupply quantities "
            "automatically and routes the order to the supervising facility. Pilot programs "
            "in Kenya and Uganda report order-to-delivery time reductions from 14-21 days "
            "(paper-based) to 3-7 days (mHealth-based) and improved data completeness from "
            "60% to over 85%."
        ),
    ),
    KnowledgeChunk(
        id="chw-005",
        title="Community-Based Distribution of Health Commodities",
        source="USAID Community-Based Distribution Best Practices Guide (2016)",
        category="Community Health Worker Programs",
        text=(
            "Community-based distribution (CBD) extends the reach of health supply chains "
            "to populations more than 5 km from the nearest health facility. CHWs serve "
            "as the final link in the chain, dispensing a limited formulary of prepackaged "
            "treatments. CBD programs for family planning commodities (condoms, oral "
            "contraceptive pills, injectable contraceptives) have demonstrated coverage "
            "increases of 15-25 percentage points. Success factors include reliable "
            "resupply mechanisms, community trust, appropriate CHW selection criteria, and "
            "clear referral pathways for cases exceeding CHW treatment protocols. Stock "
            "visibility at the CHW level remains a persistent challenge in most programs."
        ),
    ),
    KnowledgeChunk(
        id="chw-006",
        title="Drug Management Training for CHWs",
        source="WHO/UNICEF Caring for the Sick Child in the Community Training Package (2011)",
        category="Community Health Worker Programs",
        text=(
            "CHW training on drug management should cover proper storage (cool, dry, away "
            "from sunlight and moisture), FEFO principles, recognition of damaged or expired "
            "products, correct dosing using age-based or weight-based protocols, and basic "
            "record-keeping for stock accountability. Training typically requires 3-5 days "
            "for initial competency with annual refresher sessions. Common errors identified "
            "during post-training assessments include incorrect dosing of amoxicillin for "
            "pneumonia (28% of CHWs), failure to complete zinc course for diarrhea (35%), "
            "and dispensing expired products (12%). Competency-based assessment should gate "
            "authorization to dispense."
        ),
    ),
    KnowledgeChunk(
        id="chw-007",
        title="CHW Stock Visibility and Real-Time Tracking",
        source="JSI/USAID cStock Program Evaluation: Malawi (2017)",
        category="Community Health Worker Programs",
        text=(
            "Real-time stock visibility at the CHW level enables proactive resupply before "
            "stockouts occur. The cStock system in Malawi demonstrated that SMS-based "
            "reporting of CHW stock levels, combined with automated alerts to Health "
            "Surveillance Assistants (HSAs) and facility staff, reduced CHW stockout rates "
            "for essential iCCM commodities from 68% to 26% over 18 months. The system "
            "triggers alerts when a CHW's reported stock falls below a 2-week threshold. "
            "Key implementation lessons include the need for airtime subsidies to sustain "
            "CHW reporting, weekly rather than monthly reporting frequency for high-turnover "
            "items, and supervisor dashboards for performance monitoring."
        ),
    ),
    KnowledgeChunk(
        id="chw-008",
        title="CHW Performance Monitoring and Supply Metrics",
        source="WHO CHW Guideline: Monitoring and Evaluation Framework (2018)",
        category="Community Health Worker Programs",
        text=(
            "CHW performance monitoring should integrate both service delivery and supply "
            "chain indicators. Key supply metrics include: percentage of days with complete "
            "stock of all iCCM commodities (target above 80%), average resupply interval "
            "(target 30 days or less), report submission rate (target above 90%), and stock "
            "accuracy during supervision visits (target above 85%). CHW attrition "
            "disproportionately affects supply chain continuity, as departing CHWs may "
            "retain unaccounted stock. Programs should implement formal stock handover "
            "procedures when CHWs exit and track commodity losses associated with attrition "
            "as a distinct wastage category."
        ),
    ),

    # ── Disease Epidemiology ─────────────────────────────────────────────────
    KnowledgeChunk(
        id="epi-001",
        title="Plasmodium falciparum Lifecycle and Transmission Dynamics",
        source="WHO World Malaria Report (2023); CDC Malaria Biology Reference (2022)",
        category="Disease Epidemiology",
        text=(
            "The Plasmodium falciparum lifecycle involves the female Anopheles mosquito "
            "vector and human host. Sporozoites injected during a mosquito bite travel to "
            "the liver for 7-10 days of asexual replication before merozoites enter the "
            "bloodstream, causing clinical symptoms. The intrinsic incubation period is "
            "9-14 days; the extrinsic incubation period in the mosquito is 10-18 days, "
            "temperature-dependent. Transmission intensity is measured by the entomological "
            "inoculation rate (EIR), ranging from under 1 (low transmission) to over 300 "
            "(holoendemic). Supply planning must account for this lifecycle lag between "
            "rainfall, vector breeding, and clinical case presentation."
        ),
    ),
    KnowledgeChunk(
        id="epi-002",
        title="Diarrhoeal Disease Seasonality and Burden",
        source="GBD 2019 Study: Lancet (2020); WHO Diarrhoeal Disease Fact Sheet (2023)",
        category="Disease Epidemiology",
        text=(
            "Diarrhoeal diseases remain the second leading cause of death in children "
            "under 5, responsible for approximately 525,000 child deaths annually. "
            "Seasonality patterns differ by pathogen: rotavirus peaks in dry/cool seasons "
            "in tropical settings, while bacterial diarrhea (Shigella, cholera, ETEC) peaks "
            "during rainy seasons due to water contamination. The Global Burden of Disease "
            "study estimates 1.7 billion episodes of childhood diarrhea annually. ORS and "
            "zinc procurement should be weighted toward seasonal peaks, with a 40-60% "
            "increase in allocation during the expected high-transmission quarter to prevent "
            "stockouts at the point of highest need."
        ),
    ),
    KnowledgeChunk(
        id="epi-003",
        title="Acute Respiratory Infection Burden in Children",
        source="WHO/UNICEF IMCI Chart Booklet (2014); IHME GBD Cause-Specific Mortality (2019)",
        category="Disease Epidemiology",
        text=(
            "Acute respiratory infections (ARIs), primarily pneumonia, kill approximately "
            "740,000 children under 5 annually, making pneumonia the single largest "
            "infectious cause of death in children. In sub-Saharan Africa, the incidence "
            "is 0.27 episodes per child-year, approximately double the global average. "
            "Streptococcus pneumoniae and Haemophilus influenzae type b are the leading "
            "bacterial pathogens. Amoxicillin remains the first-line treatment where "
            "resistance rates are below 20%. Facility-level amoxicillin quantification "
            "should use the formula: catchment population under 5 multiplied by 0.27 "
            "multiplied by treatment course size multiplied by the facility utilization rate."
        ),
    ),
    KnowledgeChunk(
        id="epi-004",
        title="HIV Commodity Requirements and Epidemiology",
        source="UNAIDS Global AIDS Update (2023); WHO Consolidated Guidelines on HIV (2021)",
        category="Disease Epidemiology",
        text=(
            "Approximately 39 million people globally are living with HIV, with 25.6 "
            "million in sub-Saharan Africa. Each patient on antiretroviral therapy (ART) "
            "requires a continuous, uninterrupted supply of typically 3 antiretroviral "
            "drugs. The shift to dolutegravir-based regimens (TLD: tenofovir + lamivudine "
            "+ dolutegravir) has simplified procurement, as a single fixed-dose combination "
            "tablet covers first-line treatment. HIV commodity planning is cohort-driven "
            "rather than seasonal, requiring accurate patient enrollment data. Even brief "
            "ART interruptions of 48 hours or more risk viral rebound and resistance "
            "development, making stockout prevention especially critical."
        ),
    ),
    KnowledgeChunk(
        id="epi-005",
        title="TB Drug Supply and Treatment Regimens",
        source="WHO Guidelines for Treatment of Drug-Susceptible Tuberculosis (2022)",
        category="Disease Epidemiology",
        text=(
            "Drug-susceptible tuberculosis treatment uses the 2HRZE/4HR regimen: 2 months "
            "of intensive phase with isoniazid (H), rifampicin (R), pyrazinamide (Z), and "
            "ethambutol (E), followed by 4 months of continuation phase with isoniazid and "
            "rifampicin. Fixed-dose combination (FDC) tablets simplify procurement and "
            "adherence. Each new TB patient requires approximately 672 FDC tablets for the "
            "full 6-month course. TB drug quantification is based on case notification "
            "rates plus a buffer for retreatment cases (typically 15-20% of new cases). "
            "Drug-resistant TB (MDR-TB) regimens are 4-10 times more expensive and require "
            "separate procurement channels and storage."
        ),
    ),
    KnowledgeChunk(
        id="epi-006",
        title="Neglected Tropical Diseases and Mass Drug Administration",
        source="WHO Roadmap for Neglected Tropical Diseases 2021-2030 (2020)",
        category="Disease Epidemiology",
        text=(
            "Five NTDs are targeted through preventive chemotherapy via mass drug "
            "administration (MDA): lymphatic filariasis, onchocerciasis, soil-transmitted "
            "helminthiasis, schistosomiasis, and trachoma. MDA programs distribute "
            "ivermectin, albendazole, praziquantel, and azithromycin to entire at-risk "
            "populations annually. Procurement quantities are based on census population "
            "in endemic districts, with standard dosing requiring single tablets for most "
            "adults. MDA campaigns require surge supply chain capacity, as millions of "
            "tablets must be pre-positioned within a 1-2 week campaign window. Leftover "
            "stock must be accounted for and securely stored for the next campaign cycle."
        ),
    ),
    KnowledgeChunk(
        id="epi-007",
        title="Childhood Vaccination Coverage and Supply Implications",
        source="WHO/UNICEF Estimates of National Immunization Coverage (WUENIC) (2023)",
        category="Disease Epidemiology",
        text=(
            "The Expanded Programme on Immunization (EPI) targets coverage of over 90% "
            "for DPT3 (diphtheria-pertussis-tetanus, 3rd dose) as a benchmark indicator. "
            "Global DPT3 coverage was 84% in 2022, with 14.3 million zero-dose children. "
            "Vaccine supply planning uses the target population (surviving infants) "
            "multiplied by number of doses per schedule multiplied by a wastage factor. "
            "WHO-recommended wastage rates vary by vaccine presentation: 5% for single-dose "
            "vials, 10-25% for 10-dose vials (BCG has the highest wastage at 50% for "
            "20-dose vials due to the open-vial policy requiring discard after 6 hours). "
            "Accurate birth cohort data is essential for vaccine quantification."
        ),
    ),
    KnowledgeChunk(
        id="epi-008",
        title="Disease Surveillance Methods and Data Sources",
        source="WHO IDSR Technical Guidelines, 3rd Edition (2019)",
        category="Disease Epidemiology",
        text=(
            "Disease surveillance employs multiple methods with distinct supply chain "
            "implications. Passive surveillance relies on health facility case reports and "
            "is the backbone of routine IDSR, but underestimates true incidence by 2-10x "
            "depending on health-seeking behavior. Active surveillance through community "
            "case searches detects more cases and drives higher commodity consumption. "
            "Sentinel surveillance at selected sites provides higher-quality data for "
            "trend analysis. Syndromic surveillance uses clinical presentations rather than "
            "confirmed diagnoses, useful for early outbreak detection but may overestimate "
            "specific disease burden. Supply planners should understand which surveillance "
            "method generated the data informing their commodity quantification."
        ),
    ),
    KnowledgeChunk(
        id="epi-009",
        title="Outbreak Investigation Steps and Supply Needs",
        source="CDC Field Epidemiology Manual, 3rd Edition (2018)",
        category="Disease Epidemiology",
        text=(
            "Outbreak investigation follows a structured sequence: verify the diagnosis, "
            "confirm the outbreak (cases exceeding expected baseline), define and count "
            "cases, orient data by time-place-person, develop hypotheses, evaluate with "
            "analytic studies, implement control measures, and communicate findings. Each "
            "step has commodity implications. Case confirmation requires laboratory "
            "supplies (culture media, rapid tests, specimen transport media). Contact "
            "tracing may require prophylactic medications. Control measures require surge "
            "quantities of treatment drugs, personal protective equipment, and "
            "disinfection supplies. Outbreak investigation kits should be pre-positioned "
            "at district level with a defined commodity list and budget allocation."
        ),
    ),
    KnowledgeChunk(
        id="epi-010",
        title="Epidemic Curves and Supply Chain Forecasting",
        source="WHO Communicable Disease Surveillance and Response Field Guide (2006)",
        category="Disease Epidemiology",
        text=(
            "Epidemic curves (epi curves) plot case counts over time and are essential for "
            "supply chain forecasting during outbreaks. A point-source curve (single peak) "
            "suggests a common exposure and a predictable decline. A propagated curve "
            "(successive peaks at intervals equal to the incubation period) indicates "
            "person-to-person transmission and ongoing commodity needs. The doubling time "
            "(days for case count to double) during the exponential growth phase determines "
            "the urgency of emergency procurement. Commodity projections during outbreaks "
            "should use the case doubling time to estimate needs 2-4 weeks ahead, with "
            "procurement triggered before the curve peaks to account for lead time."
        ),
    ),

    # ── Maternal & Child Health ──────────────────────────────────────────────
    KnowledgeChunk(
        id="mch-001",
        title="Essential Maternal and Child Health Commodities",
        source="UN Commission on Life-Saving Commodities for Women and Children (2012)",
        category="Maternal & Child Health",
        text=(
            "The UN Commission identified 13 life-saving commodities for women and children "
            "grouped into three categories: maternal health (oxytocin, misoprostol, "
            "magnesium sulfate, injectable antibiotics for maternal sepsis), newborn health "
            "(injectable antibiotics for neonatal sepsis, antenatal corticosteroids, "
            "chlorhexidine, resuscitation equipment), and child health (amoxicillin DT, "
            "ORS, zinc, artemisinin-based combination therapies). These 13 commodities "
            "address the leading causes of maternal, newborn, and child death. National "
            "essential medicines lists should include all 13 commodities, and supply chain "
            "systems should treat them as VEN category V (vital) items for procurement "
            "prioritization."
        ),
    ),
    KnowledgeChunk(
        id="mch-002",
        title="Neonatal Care Commodities and Supply Requirements",
        source="WHO Recommendations on Newborn Health (2017)",
        category="Maternal & Child Health",
        text=(
            "Essential neonatal care commodities include chlorhexidine 7.1% gel or solution "
            "for umbilical cord care (reduces neonatal sepsis by 23%), gentamicin injection "
            "for neonatal sepsis treatment (first dose within 1 hour of diagnosis), "
            "antenatal dexamethasone for preterm birth management (given to mothers at "
            "24-34 weeks gestation when preterm delivery is anticipated), and neonatal "
            "resuscitation equipment (bag-valve-mask device, suction). Chlorhexidine is "
            "inexpensive (approximately 0.10 USD per application) but frequently stocked "
            "out due to low procurement priority. Neonatal commodity needs are forecast from "
            "expected delivery volume multiplied by complication rates: approximately 10% "
            "of neonates require some resuscitation, and 3-5% develop neonatal sepsis."
        ),
    ),
    KnowledgeChunk(
        id="mch-003",
        title="Family Planning Commodity Logistics",
        source="USAID/UNFPA Global Programme to Enhance Reproductive Health Commodity Security (2020)",
        category="Maternal & Child Health",
        text=(
            "Family planning (FP) commodity logistics require demand forecasting based on "
            "couple-years of protection (CYP) targets and method mix. Commodity requirements "
            "per CYP vary by method: oral contraceptive pills (15 cycles), injectable "
            "contraceptives (4 doses of DMPA-SC or DMPA-IM), male condoms (120 units), "
            "implants (1 unit lasting 3-5 years), and IUDs (1 unit lasting 5-10 years). "
            "The method mix significantly affects supply chain complexity; programs with "
            "high implant and IUD uptake need fewer total commodity units but require "
            "trained providers and specialized insertion kits. FP commodity stockouts are "
            "associated with increased unintended pregnancy rates within 3-6 months."
        ),
    ),
    KnowledgeChunk(
        id="mch-004",
        title="Nutrition Supplement Supply for MCH Programs",
        source="WHO Guideline on Use of Multiple Micronutrient Powders for Home Fortification (2016)",
        category="Maternal & Child Health",
        text=(
            "Micronutrient supplementation programs for pregnant women and children under 5 "
            "require sustained commodity supply. Iron-folic acid (IFA) tablets for pregnant "
            "women (60mg iron + 400mcg folic acid daily for 6 months minimum) require 180 "
            "tablets per pregnancy. Multiple micronutrient powders (MNPs) for children 6-23 "
            "months require 60 sachets per child per 6-month cycle. Ready-to-use therapeutic "
            "food (RUTF) for severe acute malnutrition treatment requires approximately "
            "10-15 kg per child per 6-8 week treatment course. Nutrition supplements often "
            "have short shelf lives (12-18 months for RUTF) and must be integrated into FEFO "
            "stock rotation protocols."
        ),
    ),
    KnowledgeChunk(
        id="mch-005",
        title="PMTCT Commodity Planning",
        source="WHO Consolidated Guidelines on HIV Prevention, Testing, Treatment, and Care (2021)",
        category="Maternal & Child Health",
        text=(
            "Prevention of mother-to-child transmission (PMTCT) programs require integrated "
            "commodity planning across HIV testing, ART, and early infant diagnosis. Every "
            "pregnant woman should be tested for HIV; positive women require immediate ART "
            "initiation with a dolutegravir-based regimen and continued lifelong. Infant "
            "nevirapine prophylaxis (birth to 6 weeks) requires approximately 42 doses of "
            "oral suspension. Early infant diagnosis uses HIV DNA PCR testing at 6 weeks, "
            "requiring dried blood spot (DBS) collection kits and sample transport to "
            "reference laboratories. PMTCT commodity needs are forecast from antenatal "
            "attendance multiplied by HIV prevalence, typically 5-25% in high-burden "
            "countries in sub-Saharan Africa."
        ),
    ),
    KnowledgeChunk(
        id="mch-006",
        title="Emergency Obstetric and Neonatal Care Supplies",
        source="WHO/UNFPA/UNICEF/AMDD: Monitoring Emergency Obstetric Care (2009)",
        category="Maternal & Child Health",
        text=(
            "Comprehensive Emergency Obstetric and Neonatal Care (CEmONC) facilities must "
            "maintain supplies for 9 signal functions: parenteral antibiotics (ampicillin, "
            "gentamicin, metronidazole), parenteral oxytocics, parenteral anticonvulsants "
            "(magnesium sulfate), manual removal of placenta, removal of retained products, "
            "assisted vaginal delivery (vacuum extraction), neonatal resuscitation, blood "
            "transfusion, and cesarean section. Basic EmONC (BEmONC) facilities must provide "
            "the first 7 functions. The recommended minimum density is 5 EmONC facilities "
            "per 500,000 population, with at least 1 CEmONC facility. EmONC commodity kits "
            "should be pre-packed and inspected quarterly for completeness and expiry."
        ),
    ),
    KnowledgeChunk(
        id="mch-007",
        title="Immunization Cold Chain for Maternal and Child Vaccines",
        source="WHO Immunization in Practice: A Practical Guide for Health Staff (2015)",
        category="Maternal & Child Health",
        text=(
            "Vaccines require continuous cold chain maintenance at 2-8 C from manufacturer "
            "to point of administration. The EPI schedule for infants includes BCG, OPV, "
            "IPV, pentavalent (DPT-HepB-Hib), PCV, rotavirus, measles, and yellow fever "
            "vaccines over the first 9-15 months of life. Cold chain capacity planning "
            "uses net vaccine volume per fully immunized child (approximately 3-4 cm3 per "
            "dose, varying by presentation). Solar direct-drive refrigerators are recommended "
            "for off-grid facilities, with capacity to maintain temperature for 4+ days "
            "without sunlight. Freeze-sensitive vaccines (pentavalent, PCV, IPV, HepB) "
            "must never be frozen; the shake test identifies freeze-damaged vaccines that "
            "must be discarded."
        ),
    ),
    KnowledgeChunk(
        id="mch-008",
        title="Growth Monitoring and Nutrition Supply Chain",
        source="WHO Child Growth Standards (2006); UNICEF Nutrition Programme Guidance (2020)",
        category="Maternal & Child Health",
        text=(
            "Growth monitoring and promotion (GMP) programs require standardized equipment "
            "including MUAC (mid-upper arm circumference) tapes for screening acute "
            "malnutrition (red zone below 115 mm indicates severe acute malnutrition in "
            "children 6-59 months), height boards/stadiometers, and calibrated scales. "
            "Therapeutic supplies linked to GMP referrals include RUTF (Plumpy'Nut or "
            "equivalent), F-75 and F-100 therapeutic milk for inpatient management, and "
            "ReSoMal (rehydration solution for malnourished children). RUTF procurement "
            "volumes are driven by SAM (severe acute malnutrition) prevalence, typically "
            "1-5% of children under 5 in food-insecure settings, with each case requiring "
            "150-200 sachets over a 6-8 week treatment course."
        ),
    ),

    # ── Emergency & Outbreak Response ────────────────────────────────────────
    KnowledgeChunk(
        id="emerg-001",
        title="Cholera Treatment Kit Composition",
        source="WHO Cholera Kit Interagency Diarrhoeal Disease Kit (2017)",
        category="Emergency & Outbreak Response",
        text=(
            "The WHO Interagency Diarrhoeal Disease Kit (IDDK) is designed for cholera "
            "outbreak response and treats approximately 100 moderate and 10 severe cases. "
            "Kit contents include oral rehydration salts (sufficient for 100 patients), "
            "Ringer's Lactate IV fluids (for severe cases), IV giving sets, doxycycline "
            "and azithromycin for antibiotic treatment, water purification tablets, "
            "chlorine solution for disinfection, and basic PPE (gloves, aprons). One "
            "complete kit weighs approximately 150 kg and costs 800-1,200 USD. Pre-"
            "positioning kits at district hospitals in cholera-endemic areas enables "
            "response within 24-48 hours of outbreak confirmation rather than the 7-14 "
            "days required for international procurement."
        ),
    ),
    KnowledgeChunk(
        id="emerg-002",
        title="Epidemic Stockpiling and Buffer Strategy",
        source="WHO Strategic Stockpile Guidance for Epidemic-Prone Diseases (2020)",
        category="Emergency & Outbreak Response",
        text=(
            "WHO recommends strategic stockpiling of commodities for epidemic-prone diseases "
            "at national and regional levels. Stockpile sizing uses the formula: estimated "
            "attack rate multiplied by population at risk multiplied by treatment course "
            "per case, for the first 3 months of an anticipated outbreak. Rotation of "
            "stockpile items into routine supply chains before expiry prevents wastage. "
            "The International Coordinating Group (ICG) manages global emergency stockpiles "
            "for meningococcal, cholera, and yellow fever vaccines. National stockpiles "
            "should cover initial response for 1-4 weeks while international deployments "
            "are mobilized. Stockpile management costs (storage, rotation, insurance) "
            "typically add 8-12% annually to the commodity value."
        ),
    ),
    KnowledgeChunk(
        id="emerg-003",
        title="Mass Casualty Pharmaceutical Preparedness",
        source="WHO Mass Casualty Management Systems (2007); ICRC War Surgery Manual (2010)",
        category="Emergency & Outbreak Response",
        text=(
            "Mass casualty events (natural disasters, conflict, industrial accidents) "
            "require surge pharmaceutical supply focused on trauma care. The WHO Emergency "
            "Health Kit (formerly IEHK) serves 10,000 displaced persons for 3 months and "
            "contains analgesics, antibiotics, anesthetics, wound care supplies, IV fluids, "
            "and basic surgical instruments. The supplementary surgical module adds "
            "ketamine, diazepam, suturing materials, and additional wound dressings. "
            "Procurement for mass casualty preparedness should include items not commonly "
            "stocked at primary health facilities: tramadol, lidocaine, burn dressings, "
            "and tetanus immunoglobulin. Emergency kits should be inspected every 6 months "
            "to replace expired items and verify completeness."
        ),
    ),
    KnowledgeChunk(
        id="emerg-004",
        title="Ebola and Viral Hemorrhagic Fever PPE Supply",
        source="WHO Infection Prevention and Control Guidance for Ebola (2014, updated 2019)",
        category="Emergency & Outbreak Response",
        text=(
            "Personal protective equipment (PPE) for viral hemorrhagic fever (VHF) response "
            "includes coveralls or fluid-resistant gowns, double nitrile gloves, N95 "
            "respirators or powered air-purifying respirators (PAPRs), face shields or "
            "goggles, waterproof aprons, and rubber boots. A single healthcare worker "
            "requires approximately 4-6 full PPE sets per shift due to the requirement "
            "to change between patients or after any contamination. A 20-bed Ebola "
            "treatment unit consumes approximately 500 PPE sets per week. Procurement "
            "must include a safe donning/doffing protocol training supply and buddy system "
            "equipment. PPE stockpile rotation is critical as elastic components degrade "
            "in humid tropical storage conditions."
        ),
    ),
    KnowledgeChunk(
        id="emerg-005",
        title="Meningitis Outbreak Response and Vaccine Deployment",
        source="WHO Meningitis Outbreak Response in Sub-Saharan Africa: ICG Guidelines (2014)",
        category="Emergency & Outbreak Response",
        text=(
            "Epidemic meningococcal meningitis in the African meningitis belt (Sahel region, "
            "Senegal to Ethiopia) follows a seasonal pattern peaking in the dry season "
            "(January-April). The epidemic threshold is 10 cases per 100,000 population "
            "per week in districts with populations over 30,000. When the threshold is "
            "crossed, reactive vaccination campaigns using meningococcal polysaccharide or "
            "conjugate vaccine must begin within 4 weeks. The ICG maintains a global "
            "stockpile of approximately 5 million doses. Vaccine deployment requires "
            "concurrent supply of auto-disable syringes (1 per dose), safety boxes for "
            "sharps disposal, cold chain equipment, and vaccination cards. Campaign "
            "planning uses target coverage of 80% of the population aged 1-29 years."
        ),
    ),
    KnowledgeChunk(
        id="emerg-006",
        title="Flood Response Health Commodity Needs",
        source="WHO/PAHO Health Sector Self-Assessment Tool for Disaster Risk Reduction (2016)",
        category="Emergency & Outbreak Response",
        text=(
            "Flooding events create compound health commodity needs spanning trauma care, "
            "waterborne disease prevention, and management of disrupted chronic disease "
            "treatment. Priority commodities include: ORS and IV fluids for acute diarrheal "
            "disease surge (anticipate 3-5x baseline), water purification tablets (chlorine "
            "or flocculant-disinfectant sachets, 1 tablet per 20 liters per household per "
            "day), wound care supplies for flood injuries, tetanus toxoid for wound "
            "prophylaxis, and chronic disease medications for displaced populations whose "
            "personal supplies were lost. Pre-positioning of flood response kits in "
            "historically flood-prone districts reduces response time from weeks to days."
        ),
    ),
    KnowledgeChunk(
        id="emerg-007",
        title="Health Supply Planning for Internally Displaced Populations",
        source="UNHCR/WHO Clinical Guidelines for Refugee and IDP Health Settings (2018)",
        category="Emergency & Outbreak Response",
        text=(
            "Internally displaced population (IDP) health supply planning uses Sphere "
            "Standards minimum requirements: 1 health facility per 10,000 displaced persons, "
            "50 consultations per clinician per day, and essential medicines for the top 10 "
            "presenting conditions. The WHO Interagency Emergency Health Kit (IEHK) provides "
            "a starter commodity package calibrated for 10,000 people for 3 months. Beyond "
            "the initial kit, ongoing supply quantification uses morbidity data from the "
            "health information system established at displacement sites. Measles vaccination "
            "campaign supplies are a first-priority commodity for displaced populations, as "
            "measles outbreaks in crowded camp settings cause disproportionate child mortality "
            "with case fatality rates of 3-5% among malnourished children."
        ),
    ),
    KnowledgeChunk(
        id="emerg-008",
        title="Emergency Procurement Procedures and Waivers",
        source="UNDP/WHO Emergency Procurement Guidelines (2019)",
        category="Emergency & Outbreak Response",
        text=(
            "Emergency procurement during disease outbreaks permits deviation from standard "
            "competitive bidding procedures to accelerate supply. WHO and major donors "
            "authorize direct procurement from pre-qualified suppliers when a formal "
            "emergency declaration is in effect. Key safeguards include: retroactive "
            "documentation of procurement decisions within 30 days, price benchmarking "
            "against recent competitive tenders (acceptable premium of up to 15-25%), "
            "post-delivery quality testing of emergency-procured medicines, and senior "
            "management sign-off for single-source contracts exceeding 50,000 USD. "
            "Emergency procurement authority should be pre-delegated to designated officers "
            "to avoid bureaucratic delays during the critical first 72 hours of response."
        ),
    ),

    # ── Health Information Systems ───────────────────────────────────────────
    KnowledgeChunk(
        id="his-001",
        title="DHIS2 Integration with Supply Chain Data",
        source="DHIS2 Documentation: LMIS Module (2022); WHO Digital Health Guidelines (2019)",
        category="Health Information Systems",
        text=(
            "DHIS2 (District Health Information Software 2) is the most widely adopted "
            "health management information system in low- and middle-income countries, "
            "deployed in over 80 countries. DHIS2 can aggregate supply chain data alongside "
            "disease surveillance through its Tracker and aggregate data modules. Integration "
            "enables cross-validation of reported disease cases against commodity consumption. "
            "DHIS2 dashboards can display stock status, consumption trends, and stockout "
            "alerts at facility, district, and national levels. Data exchange with dedicated "
            "eLMIS platforms (OpenLMIS, openBoxes) uses the FHIR or ADX interoperability "
            "standards. Successful integration requires harmonized facility registries, "
            "consistent reporting periods, and governance over shared data elements."
        ),
    ),
    KnowledgeChunk(
        id="his-002",
        title="Electronic Logistics Management Information Systems",
        source="USAID GHSC-PSM: eLMIS Implementation Guide (2020)",
        category="Health Information Systems",
        text=(
            "Electronic logistics management information systems (eLMIS) replace paper-based "
            "stock management with digital record-keeping, automated calculations, and "
            "centralized visibility. Leading open-source eLMIS platforms include OpenLMIS "
            "(used in Mozambique, Zambia, Malawi) and mSupply (Pacific Islands, Myanmar). "
            "Key features include automated reorder point calculations, expiry date "
            "tracking, consumption trend analysis, and integration with national HMIS. "
            "Implementation timelines average 18-24 months for nationwide rollout, with "
            "costs of 2-5 USD per facility per month for cloud-hosted solutions. Critical "
            "success factors include sustained internet connectivity (minimum 2G for data "
            "synchronization), ongoing user training, and dedicated IT support staff at "
            "district level."
        ),
    ),
    KnowledgeChunk(
        id="his-003",
        title="Mobile Data Collection for Supply Chain Monitoring",
        source="WHO Digital Health Guideline: Recommendations on Digital Interventions for Health System Strengthening (2019)",
        category="Health Information Systems",
        text=(
            "Mobile data collection using smartphones or basic feature phones improves "
            "timeliness and accuracy of supply chain reporting from last-mile facilities. "
            "Platforms such as ODK (Open Data Kit), KoboToolbox, and CommCare support "
            "offline data collection with automatic synchronization when connectivity is "
            "available. WHO recommends mobile-based stock reporting for health workers at "
            "community and primary care levels where paper-based systems show poor data "
            "quality. Studies across 12 countries show mobile reporting improves report "
            "completeness from 55-65% (paper-based) to 80-90% and reduces data "
            "transcription errors by 60-80%. Implementation requires device procurement "
            "or BYOD policies, data plan subsidies, and clear data ownership protocols."
        ),
    ),
    KnowledgeChunk(
        id="his-004",
        title="Data Quality Assessment Frameworks",
        source="WHO Data Quality Review Toolkit (2017)",
        category="Health Information Systems",
        text=(
            "The WHO Data Quality Review (DQR) toolkit provides a standardized framework "
            "for assessing health data quality across four dimensions: completeness and "
            "timeliness of reporting, internal consistency of reported data, external "
            "consistency with other data sources, and external comparisons with population-"
            "based surveys. For supply chain data, internal consistency checks include "
            "verifying that closing stock equals opening stock plus receipts minus "
            "consumption minus losses. Month-over-month consumption should not vary by "
            "more than 50% without a documented explanation such as an outbreak or stockout. "
            "Facilities with more than 3 consistency errors per quarter should be flagged "
            "for data quality improvement interventions including refresher training and "
            "more frequent supervision."
        ),
    ),
    KnowledgeChunk(
        id="his-005",
        title="Dashboard Design for Supply Chain Decision-Making",
        source="PATH Visualizing Health Data Toolkit (2018)",
        category="Health Information Systems",
        text=(
            "Effective supply chain dashboards for health program managers should follow "
            "the information hierarchy principle: the landing page shows 3-5 top-level KPIs "
            "(stockout rate, reporting rate, order fill rate), drill-down pages show "
            "geographic and facility-level detail, and data tables enable export for "
            "analysis. Color coding should follow intuitive conventions: red for stockout "
            "or critical thresholds, amber for warning levels, green for adequate stock. "
            "Dashboards should be updated at least weekly for stock status indicators and "
            "monthly for consumption trend analysis. The most actionable dashboards "
            "highlight facilities requiring intervention rather than displaying system-wide "
            "averages that mask underperforming sites."
        ),
    ),
    KnowledgeChunk(
        id="his-006",
        title="Interoperability Standards for Health Supply Data",
        source="HL7 FHIR Supply Module (2021); GS1 Healthcare Standards (2020)",
        category="Health Information Systems",
        text=(
            "Interoperability between health supply chain systems relies on standard data "
            "exchange formats. HL7 FHIR (Fast Healthcare Interoperability Resources) "
            "provides RESTful APIs for exchanging supply chain resources including "
            "SupplyRequest, SupplyDelivery, and InventoryReport. GS1 standards provide "
            "unique product identification through Global Trade Item Numbers (GTINs) "
            "enabling end-to-end traceability from manufacturer to patient. ADX (Aggregate "
            "Data Exchange) is the WHO-recommended format for aggregate reporting to DHIS2. "
            "Implementing interoperability requires a master facility list, a product "
            "master catalog with standardized coding, and agreed data sharing protocols "
            "between national health information and supply chain management units."
        ),
    ),
    KnowledgeChunk(
        id="his-007",
        title="Building a Data Use Culture for Supply Chain",
        source="MEASURE Evaluation: Data Demand and Use Manual (2011, updated 2019)",
        category="Health Information Systems",
        text=(
            "Data use culture in health supply chains refers to the routine practice of "
            "using data for decision-making at every level, from facility stock management "
            "to national procurement planning. MEASURE Evaluation identifies 5 enablers: "
            "data availability (systems produce timely, accessible reports), data quality "
            "(users trust the data), organizational support (leadership promotes data use), "
            "data use competency (staff can interpret and act on data), and feedback loops "
            "(decisions are communicated back to data producers). In a 2019 assessment "
            "across 8 African countries, only 35% of district health managers reported "
            "using LMIS data routinely for supply decisions, with most relying on ad hoc "
            "requests or emergency reports rather than proactive monitoring."
        ),
    ),
    KnowledgeChunk(
        id="his-008",
        title="Routine Data Quality Audits for LMIS",
        source="USAID GHSC-PSM: LMIS Data Quality Audit Protocol (2021)",
        category="Health Information Systems",
        text=(
            "Routine data quality audits (RDQAs) for logistics management information "
            "systems should be conducted quarterly at a random sample of facilities "
            "(minimum 10% of facilities per district). The audit protocol includes: "
            "comparing electronic records against source documents (bin cards, dispensing "
            "registers), conducting physical stock counts for a sample of tracer products, "
            "verifying arithmetic accuracy of reported calculations, and assessing "
            "timeliness of report submission. Verification factors (ratio of recounted "
            "data to reported data) outside the 0.90-1.10 range indicate systematic "
            "data quality problems. Audit findings should be shared with facility staff "
            "within 2 weeks, with corrective action plans for facilities scoring below "
            "80% accuracy on any dimension."
        ),
    ),

    # ── Laboratory & Diagnostics ─────────────────────────────────────────────
    KnowledgeChunk(
        id="lab-001",
        title="Point-of-Care Testing and Supply Chain Implications",
        source="WHO Essential Diagnostics List, 3rd Edition (2021)",
        category="Laboratory & Diagnostics",
        text=(
            "Point-of-care (POC) diagnostics reduce time to treatment by providing results "
            "at the site of patient care. The WHO Essential Diagnostics List includes POC "
            "tests for malaria (RDTs), HIV (rapid antibody tests), syphilis (rapid treponemal "
            "tests), hepatitis B surface antigen, blood glucose (glucometers), and hemoglobin "
            "(HemoCue devices). Supply chain requirements for POC tests differ from "
            "laboratory reagents: lower storage requirements (ambient temperature for most "
            "RDTs), shorter shelf lives (18-24 months), and consumption driven by patient "
            "volume rather than batch processing. POC test procurement should be paired "
            "with quality assurance supplies including positive and negative controls and "
            "proficiency testing panels distributed quarterly."
        ),
    ),
    KnowledgeChunk(
        id="lab-002",
        title="Microscopy Supplies for Malaria and TB Diagnosis",
        source="WHO Bench Aids for Malaria Microscopy (2009); WHO Laboratory Strengthening Guide (2018)",
        category="Laboratory & Diagnostics",
        text=(
            "Light microscopy remains the gold standard for malaria species identification "
            "and TB diagnosis via Ziehl-Neelsen acid-fast staining. Microscopy supply "
            "requirements include glass slides (2-3 per patient examination), Giemsa stain "
            "for malaria (10% solution, approximately 1 mL per slide), Ziehl-Neelsen "
            "reagents for TB (carbol fuchsin, acid-alcohol, methylene blue), immersion oil, "
            "and lens paper. A functional microscope requires annual maintenance including "
            "bulb replacement, alignment, and cleaning. Quality assurance requires blinded "
            "re-reading of 10% of slides monthly and participation in external quality "
            "assessment (EQA) schemes. Microscopy supplies are low-cost but frequently "
            "stocked out, as they are often categorized as low-priority C items in ABC analysis."
        ),
    ),
    KnowledgeChunk(
        id="lab-003",
        title="CD4 Count Testing and Monitoring Supplies",
        source="WHO Consolidated Guidelines on HIV (2021); PEPFAR COP Guidance (2022)",
        category="Laboratory & Diagnostics",
        text=(
            "CD4 count testing, while largely replaced by viral load monitoring for ART "
            "treatment decisions, remains essential for identifying advanced HIV disease "
            "(CD4 below 200 cells/mm3) requiring enhanced prophylaxis. POC CD4 devices "
            "(PIMA, FACSPresto) use disposable cartridges costing 5-12 USD each. Each "
            "cartridge has a shelf life of 12-18 months and requires storage at 2-30 C. "
            "Cartridge procurement is based on the number of patients needing baseline CD4 "
            "(all new ART initiations) plus those with suspected treatment failure. Annual "
            "quality control requires external quality assessment panels (2-4 per year at "
            "8-15 USD each) and internal quality control materials run with each new "
            "cartridge lot."
        ),
    ),
    KnowledgeChunk(
        id="lab-004",
        title="GeneXpert MTB/RIF Platform and Cartridge Supply",
        source="WHO Rapid Communication on GeneXpert MTB/RIF Ultra (2021); FIND Diagnostics Strategy (2021)",
        category="Laboratory & Diagnostics",
        text=(
            "The GeneXpert MTB/RIF platform provides same-day TB diagnosis with "
            "simultaneous rifampicin resistance detection in under 2 hours. Each test "
            "requires one single-use cartridge (negotiated price approximately 10 USD "
            "through the Global Drug Facility). Cartridges require storage at 2-28 C and "
            "have an 18-month shelf life. Module calibration is required annually using "
            "the Cepheid calibration kit. A 4-module GeneXpert instrument can process "
            "approximately 16-20 tests per 8-hour shift. Cartridge quantification uses "
            "the expected number of presumptive TB patients multiplied by the testing "
            "algorithm yield (typically 15-25% positivity rate). Facilities must also "
            "maintain uninterrupted power supply, as power failure during a run invalidates "
            "the cartridge and result."
        ),
    ),
    KnowledgeChunk(
        id="lab-005",
        title="Sample Transport Networks for Reference Testing",
        source="WHO Guidance on Sample Transport Systems (2020); ASLM Sample Referral Framework (2019)",
        category="Laboratory & Diagnostics",
        text=(
            "Sample transport networks link peripheral health facilities to reference "
            "laboratories for tests not available at point of care (viral load, culture, "
            "drug susceptibility testing, EID). Effective networks use a hub-and-spoke "
            "model with scheduled motorcycle courier services operating on fixed routes "
            "2-3 times per week. Supply requirements include triple-packaging specimen "
            "transport containers (UN3373-compliant), cold chain packs for temperature-"
            "sensitive samples, requisition forms, biohazard bags, and absorbent materials. "
            "Sample rejection rates above 5% indicate supply or training deficiencies. "
            "Common rejection reasons include hemolyzed samples, incorrect specimen type, "
            "missing labels, and temperature excursions during transport."
        ),
    ),
    KnowledgeChunk(
        id="lab-006",
        title="Reagent Storage and Inventory Management",
        source="WHO Laboratory Quality Standards, 2nd Edition (2011)",
        category="Laboratory & Diagnostics",
        text=(
            "Laboratory reagents have diverse storage requirements that complicate inventory "
            "management. Hematology and chemistry analyzer reagents typically require "
            "refrigeration (2-8 C) and have shelf lives of 6-12 months. Many reagents have "
            "reduced stability once opened (e.g., Giemsa stock solution is stable for 12 "
            "months unopened but only 6 months after opening). Reconstituted reagents "
            "(culture media, staining solutions) may be stable for only 7-30 days. "
            "Reagent inventory management requires tracking both unopened and opened "
            "expiry dates, batch numbers for traceability, and consumption patterns "
            "aligned with test volumes. Reagent rental agreements, where instrument "
            "manufacturers supply reagents bundled with equipment maintenance, can simplify "
            "procurement but may reduce supply chain flexibility."
        ),
    ),
    KnowledgeChunk(
        id="lab-007",
        title="Laboratory Quality Assurance Programs",
        source="WHO AFRO Stepwise Laboratory Quality Improvement Process Towards Accreditation (SLIPTA) (2015)",
        category="Laboratory & Diagnostics",
        text=(
            "The SLIPTA framework guides laboratories through progressive quality "
            "improvement toward ISO 15189 accreditation using a star rating system (0-5 "
            "stars). Supply chain-relevant quality elements include: documented procedures "
            "for reagent receipt and inspection, storage temperature monitoring logs, "
            "equipment maintenance records with service schedules and calibration dates, "
            "lot-to-lot verification protocols for new reagent batches, and proficiency "
            "testing participation records. Laboratories at 3 stars and above demonstrate "
            "95% or higher concordance in proficiency testing panels. Supply chain managers "
            "should align reagent procurement schedules with laboratory testing volumes and "
            "ensure a 2-month buffer stock of critical reagents to prevent test interruptions."
        ),
    ),
    KnowledgeChunk(
        id="lab-008",
        title="Diagnostic Algorithm-Based Supply Planning",
        source="WHO Integrated Management of Childhood Illness (IMCI) Chart Booklet (2014)",
        category="Laboratory & Diagnostics",
        text=(
            "Diagnostic algorithms define the sequence of tests performed based on clinical "
            "presentation, directly determining commodity needs. The IMCI algorithm for a "
            "child with fever in a malaria-endemic area requires 1 malaria RDT as the first "
            "step; a negative result may trigger additional diagnostics (blood culture, "
            "urinalysis). The HIV testing algorithm uses a serial rapid test strategy: a "
            "positive result on Test 1 (screening assay) is confirmed with Test 2 "
            "(confirmatory assay from a different manufacturer); discordant results require "
            "Test 3 (tiebreaker). Supply planners must stock all tests in the algorithm. "
            "For HIV testing, the ratio of Test 1 to Test 2 to Test 3 kits depends on "
            "population prevalence: at 5% prevalence, approximately 100:6:1 ratio; at 20% "
            "prevalence, approximately 100:22:2 ratio."
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
