"""
Seed the Valiquette Mechanical knowledge base into Pinecone and SQLite.
Run once: python seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from database import init_db, SessionLocal
from knowledge_base import create_entry

SEED_DATA = [
    # Company Info
    ("Company Info", "Company Overview",
     "Valiquette Mechanical Inc. Family-owned and operated HVAC contractor in Ottawa with 20+ years of experience. Founded by Eric Valiquette. Located at 6727 Du Palais St, Navan, ON K4B 1H9. Phone: 613-620-1000. Email: office@valiquettemechanical.ca. Website: valiquettemechanical.ca. Service in English and French. Business hours: Monday–Saturday, 7:00 AM – 6:00 PM."),
    ("Company Info", "Team",
     "Valiquette Mechanical is run by Eric Valiquette (co-founder and lead technician), Shanel Valiquette (office administrator), and Mat Valiquette (HVAC expert). A true family business dedicated to treating every customer like family."),
    ("Company Info", "Guarantees and Warranties",
     "Valiquette Mechanical provides a 100% satisfaction guarantee on all services — a job done right on the first try. 1-year installation guarantee on parts and labour. We are an authorized service contractor — if equipment is covered under manufacturer warranty, we handle it directly. All work built to code."),
    ("Company Info", "How Quoting Works",
     "All estimates at Valiquette Mechanical are FREE and no obligation. A technician visits your home to assess your needs and provide an accurate quote. We use digital quotations — customers receive professional quotes electronically and can approve, reject, or ask questions. No pressure, no surprises."),

    # Service Areas
    ("Service Areas", "Service Areas",
     "Valiquette Mechanical services Ottawa and surrounding areas including: Navan, Orleans, Kanata, Barrhaven, Nepean, Gloucester, Manotick, Rockland, Cumberland, Limoges, Embrun, Vanier, South Keys, Stittsville, Bells Corners, Blackburn Hamlet, Beacon Hill, Hunt Club Road, Greely, Bridlewood, and surrounding rural areas. Not sure if we cover your area? Just ask!"),

    # Furnaces
    ("Furnaces", "Furnace Brands",
     "Valiquette Mechanical supplies and installs furnaces from trusted brands including Amana, Goodman, Honeywell, and more. We favour equipment that offers exceptional value, reliability, and efficiency. If we wouldn't put it in our own home, we won't put it in yours."),
    ("Furnaces", "Furnace Types and Pricing",
     "Three types of furnaces available. Single-stage 95% AFUE: $3,500–$5,000 installed — basic, reliable, full blast or off. Two-stage 96% AFUE: $4,500–$6,500 installed — quieter, more even temperature, best value for most Ottawa homes, approximately $100/year gas savings over single-stage. Modulating 98% AFUE: $5,500–$7,500+ installed — whisper quiet, most consistent temperature, premium option. Canada mandates minimum 95% AFUE so all new furnaces are high-efficiency."),
    ("Furnaces", "Furnace Installation Details",
     "Furnace installation takes 4–8 hours, usually completed in one day. Time varies based on furnace location, accessibility, and old furnace removal. Ottawa homes typically need 60,000–120,000 BTU depending on square footage and insulation. High-efficiency furnaces use PVC sidewall venting instead of metal chimney — conversion cost $200–$500 one-time. Manufacturer warranty covers 10-year parts. Valiquette Mechanical adds 1-year installation guarantee on top."),
    ("Furnaces", "Furnace Features",
     "Modern furnaces offer features like ECM blower motors (50–75% less electricity than old PSC motors), two-stage heating for better comfort, smart AI-controlled functionality, WiFi connectivity and app control for temperature monitoring. Some models offer one-button warranty service through the furnace app."),
    ("Furnaces", "Furnace Rebates",
     "Check with Enbridge and Natural Resources Canada for current rebate programs on energy-efficient furnace upgrades. Enbridge offers $250 for ECM blower motors when paired with a qualifying furnace. Ask during your free estimate about currently running government programs."),
    ("Furnaces", "Furnace Recommendation",
     "For most Ottawa homes, a two-stage 96% AFUE furnace is the sweet spot. It costs $1,000–$1,500 more than single-stage but delivers noticeably better comfort, quieter operation, and approximately $100 per year in gas savings. The modulating 98% model costs an additional $1,000–$2,000 on top for only marginal improvements — that difference is better invested in ductwork, a smart thermostat, or a whole-home humidifier."),

    # Air Conditioning
    ("Air Conditioning", "AC Types and Pricing",
     "Three main cooling options for Ottawa homes. Central AC: $3,800–$7,500+ installed — cools entire home through existing ductwork, 15–20 year lifespan. Ductless Mini-Split: $3,000–$5,000 per zone — no ductwork required, wall-mounted units cool individual rooms. Heat Pump: $5,500–$12,000+ installed — cools in summer AND heats in winter, highest efficiency, qualifies for largest rebates."),
    ("Air Conditioning", "AC Brands and Recommendations",
     "Valiquette Mechanical installs trusted brands including Goodman, Amana, and other high-quality manufacturers. We are authorized installers so manufacturer warranty is fully backed. For most Ottawa homes with existing ductwork, a central air conditioner in the two-stage range (16–17 SEER) delivers the best balance of upfront cost, efficiency, and comfort. Homes without ductwork should consider a ductless mini-split or heat pump."),
    ("Air Conditioning", "AC Maintenance",
     "Regular AC maintenance increases reliability, efficiency, and lifespan. Valiquette Mechanical offers inspection, cleaning, and tune-up services. We recommend annual or bi-annual servicing — ideally in spring before the cooling season. Neglected systems work harder, cost more to run, and fail sooner."),
    ("Air Conditioning", "AC Rebates",
     "Direct rebates for standalone AC units are limited. Heat pumps qualify for much larger rebates — up to $5,000–$7,500 from federal and provincial programs. Consider a heat pump if maximizing rebates is a priority. Ask us during your free estimate."),

    # Heat Pumps
    ("Heat Pumps", "Heat Pump Overview",
     "Heat pumps heat your home in winter and cool it in summer at a fraction of the energy cost of traditional furnace-and-AC combinations. Modern cold-climate heat pumps work down to -25°C to -30°C, fully viable for Ottawa winters. Pricing: $5,500–$12,000+ installed. Rebates: Up to $7,500+ from federal and provincial programs."),
    ("Heat Pumps", "Heat Pump Savings",
     "Most Ottawa homeowners report 30–50% heating cost savings in shoulder seasons and 20–40% savings during peak winter when heat pump shares load with furnace. Total annual energy savings of $500–$1,200 realistic depending on home size and insulation. Dual-fuel setup (heat pump + gas furnace backup) is the most popular option for Ottawa."),
    ("Heat Pumps", "Heat Pump Installation",
     "Ducted heat pump replacing existing AC unit takes 6–10 hours, typically one day. Ductless single-zone installation takes 4–6 hours. Multi-zone ductless systems may require 1–2 days. Modern cold-climate models are quiet — 55–65 dB outdoor unit (normal conversation level), 20–30 dB indoor ductless heads (nearly silent)."),

    # Water Heaters
    ("Water Heaters", "Water Heater Overview",
     "Valiquette Mechanical installs and services both conventional tank water heaters and tankless (on-demand) systems. Conventional tanks: reliable, lower upfront cost, good for most households. Tankless: unlimited hot water on demand, wall-mounted to save space, energy efficient — only heats water when you use it. Brands include Navien and other trusted manufacturers."),
    ("Water Heaters", "Tankless Water Heater Sizing",
     "Tankless water heater sizing based on demand. Low demand: 130,000 BTU. Medium demand: 180,000 BTU. High demand: 350,000 BTU. Sizing depends on total GPM required for simultaneous fixtures (showers, dishwashers) and temperature rise needed to heat incoming groundwater to the desired temperature. We size correctly on the first visit."),
    ("Water Heaters", "Water Heater Maintenance and Repairs",
     "Regular maintenance recommended for tankless water heaters. Ottawa water has high calcium and magnesium that can build up inside, restricting flow. Common issues: mineral build-up, water demand too high, error codes, ignition and pilot light problems. Valiquette Mechanical is authorized to diagnose and repair all makes and models using genuine replacement parts. Priority same-day or next-day emergency repair available."),

    # Ductwork
    ("Ductwork", "Ductwork Services",
     "Valiquette Mechanical designs, installs, repairs, maintains, and cleans custom ductwork systems for residential and commercial properties. Properly designed ductwork is critical for HVAC efficiency, comfort, and air quality. We handle full duct system installations for new builds, duct extensions for home additions, repair of leaking or damaged ducts, and complete duct cleaning services."),
    ("Ductwork", "Ductwork Importance",
     "Leaky or poorly designed ductwork can waste 20–30% of your heating and cooling energy. Signs of duct problems: uneven temperatures room to room, higher than usual energy bills, excessive dust, rooms that are hard to heat or cool. A ductwork inspection during your free estimate can identify issues."),

    # Gas Piping
    ("Gas Piping", "Gas Piping Services",
     "Valiquette Mechanical installs, maintains, repairs, and removes gas line systems for residential and commercial properties. Applications: BBQ hookup, pool heaters, gas fireplaces, gas appliances, outdoor kitchens, landscaping features, gas stoves. Our trucks are equipped with commercial-grade pipe cutting and threading machines for custom fabrication on site. We use only safe, code-compliant materials."),
    ("Gas Piping", "BBQ Gas Line Installation",
     "Connecting your barbecue to natural gas provides unlimited, clean, and affordable fuel — no more propane tanks to swap. Installation takes just a few hours. Gas line piping cost: $200–$600 depending on distance and complexity. A permanent gas line is a great home upgrade."),

    # Gas Fireplaces
    ("Gas Fireplaces", "Gas Fireplace Services",
     "Valiquette Mechanical installs, repairs, and maintains gas and electric fireplace units. We service all major brands: Napoleon, Majestic, Kingsman, Continental, Regency, Heatilator, and more. Types: direct vent inserts, vent-free (strict Ontario regulations), log sets. Pricing: $2,500–$6,000+ installed. Gas fireplaces are excellent for zone heating. Annual professional maintenance is recommended — schedule in September–October before the heating season."),

    # Smart Thermostats
    ("Smart Thermostats", "Smart Thermostat Options",
     "Valiquette Mechanical installs and configures smart thermostats including Honeywell, Nest, and ecobee. Honeywell: reliable, professional grade, excellent compatibility. Nest: best for ease of use and Google Home integration. ecobee: comprehensive features with room sensors. Pricing: $130–$280 depending on brand. Savings: 8–23% on heating and cooling bills annually. Enbridge offers $75 rebate for ENERGY STAR certified models."),

    # Maintenance
    ("Maintenance", "HVAC Maintenance Services",
     "Regular maintenance by Valiquette Mechanical increases reliability, lifespan, and efficiency of all HVAC equipment. Recommended every 1–3 years depending on condition and use. Our technicians inspect, lubricate, test, and clean all mechanical and electrical components. Furnaces, ACs, heat pumps, water heaters, fireplaces — we service it all. Homeowners should regularly change furnace air filters between professional services."),

    # Emergency Procedures
    ("Emergency Procedures", "Emergency — Gas Smell",
     "CRITICAL SAFETY: If you smell gas, leave the house immediately. Do NOT turn on or off any lights or electrical switches. Call 911 first. Then call Valiquette Mechanical at 613-620-1000. Do not re-enter the home until emergency services clear it."),
    ("Emergency Procedures", "Emergency — No Heat",
     "If your furnace stops working: First check that the thermostat is set to HEAT and the temperature is set above room temperature. Check the furnace filter — a clogged filter can shut down the furnace. Check that the furnace power switch is ON. If none of these fix it, call Valiquette Mechanical at 613-620-1000 for emergency repair service. We prioritize emergency HVAC calls."),
    ("Emergency Procedures", "Emergency — Carbon Monoxide",
     "If your carbon monoxide detector is going off: Leave the house immediately with all family members and pets. Call 911. Do not re-enter until cleared by emergency services. Then call Valiquette Mechanical at 613-620-1000 — we can inspect your furnace and gas appliances for CO leaks. All our installations are built to code to prevent CO issues."),
    ("Emergency Procedures", "Emergency — Water Heater Failure",
     "If your water heater stops working: For tankless, try resetting the unit (check your manual for reset procedure). Check for error codes on the display. If the issue persists, call Valiquette Mechanical at 613-620-1000. We offer priority same-day or next-day emergency repair for water heater failures."),
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        from database import KnowledgeEntry
        existing = db.query(KnowledgeEntry).count()
        if existing > 0:
            print(f"Knowledge base already has {existing} entries. Skipping seed.")
            return

        print(f"Seeding {len(SEED_DATA)} knowledge base entries...")
        for i, (category, title, content) in enumerate(SEED_DATA, 1):
            print(f"  [{i}/{len(SEED_DATA)}] {category} — {title}")
            create_entry(db, category, title, content)
        print("Seed complete!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
