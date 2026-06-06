"""
============================================================
  SECTOR MAP
  Maps each NSE stock to its sector.
  Enforces max 3 stocks per sector in final watchlist.
============================================================
"""

SECTOR_MAP = {
    "Banking":     ["HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS","AXISBANK.NS","SBIN.NS",
                    "INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS",
                    "AUBANK.NS","KARURVYSYA.NS","PNB.NS","BANKBARODA.NS","CANBK.NS",
                    "INDIANB.NS","YESBANK.NS","UNIONBANK.NS","UCOBANK.NS"],
    "IT":          ["TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS","LTIM.NS",
                    "LTIMINDTCH.NS","MPHASIS.NS","COFORGE.NS","PERSISTENT.NS",
                    "KPITTECH.NS","TATAELXSI.NS","LTTS.NS","CYIENT.NS","ZENSARTECH.NS","OFSS.NS"],
    "Finance":     ["BAJFINANCE.NS","BAJAJFINSV.NS","MUTHOOTFIN.NS","CHOLAFIN.NS",
                    "ABCAPITAL.NS","MOTILALOFS.NS","CANFINHOME.NS","LICHSGFIN.NS",
                    "HDFCLIFE.NS","SBILIFE.NS","MFSL.NS","STARHEALTH.NS",
                    "NAM-INDIA.NS","CAMS.NS","MCX.NS","IEX.NS"],
    "Pharma":      ["SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","LUPIN.NS",
                    "BIOCON.NS","AUROPHARMA.NS","GLENMARK.NS","TORNTPHARM.NS",
                    "GRANULES.NS","LAURUSLABS.NS","LALPATHLAB.NS","METROPOLIS.NS",
                    "THYROCARE.NS","SYNGENE.NS","PFIZER.NS","NAVINFLUOR.NS"],
    "Auto":        ["MARUTI.NS","TATAMOTORS.NS","M&M.NS","EICHERMOT.NS","HEROMOTOCO.NS",
                    "BAJAJ-AUTO.NS","TVSMOTOR.NS","TVSHLTD.NS","BHARATFORG.NS",
                    "BALKRISIND.NS","SONACOMS.NS","TIINDIA.NS","UNOMINDA.NS"],
    "FMCG":        ["HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS","DABUR.NS",
                    "MARICO.NS","GODREJCP.NS","COLPAL.NS","EMAMILTD.NS","UBL.NS",
                    "RADICO.NS","TATACONSUM.NS","PATANJALI.NS","VBL.NS","BIKAJI.NS"],
    "Energy":      ["RELIANCE.NS","ONGC.NS","BPCL.NS","IOC.NS","COALINDIA.NS",
                    "NTPC.NS","POWERGRID.NS","TATAPOWER.NS","JSWENERGY.NS",
                    "PETRONET.NS","OIL.NS","GSPL.NS","MRPL.NS","TORNTPOWER.NS","CESC.NS","MGL.NS"],
    "Metals":      ["TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","VEDL.NS","SAIL.NS",
                    "NATIONALUM.NS","NMDC.NS","WELCORP.NS","APLAPOLLO.NS"],
    "Infra":       ["LT.NS","ADANIPORTS.NS","ADANIENT.NS","GMRAIRPORT.NS","NCC.NS",
                    "KEC.NS","ENGINERSIN.NS","NBCC.NS","RITES.NS","RAILTEL.NS",
                    "BEL.NS","BHEL.NS","CGPOWER.NS"],
    "Cement":      ["ULTRACEMCO.NS","SHREECEM.NS","AMBUJACEM.NS","DALBHARAT.NS",
                    "JKCEMENT.NS","RAMCOCEM.NS"],
    "Consumer":    ["ASIANPAINT.NS","TITAN.NS","BERGEPAINT.NS","HAVELLS.NS",
                    "VOLTAS.NS","CROMPTON.NS","BLUESTARCO.NS","WHIRLPOOL.NS",
                    "PIDILITIND.NS","KANSAINER.NS","NILKAMAL.NS","SUPREMEIND.NS"],
    "Realty":      ["DLF.NS","GODREJPROP.NS","OBEROIRLTY.NS","PRESTIGE.NS",
                    "SOBHA.NS","PHOENIXLTD.NS"],
    "Healthcare":  ["APOLLOHOSP.NS","MAXHEALTH.NS","INDHOTEL.NS"],
    "Internet":    ["ZOMATO.NS","NAUKRI.NS","INDIAMART.NS","PAYTM.NS",
                    "NYKAA.NS","POLICYBZR.NS","DMART.NS"],
    "Chemicals":   ["UPL.NS","SRF.NS","DEEPAKNTR.NS","ATUL.NS","GNFC.NS",
                    "VINATIORGA.NS","NAVINFLUOR.NS"],
    "Telecom":     ["BHARTIARTL.NS","TATACOMM.NS","HFCL.NS","RAILTEL.NS","TTML.NS"],
    "Diversified": ["SIEMENS.NS","BOSCHLTD.NS","HONAUT.NS","SCHAEFFLER.NS",
                    "TIMKEN.NS","SKFINDIA.NS","ELGIEQUIP.NS","CUMMINSIND.NS"],
}

GRADE_ORDER = {"A++": 0, "A+": 1, "A": 2, "B": 3, "C": 4}


def get_sector(symbol):
    """Return sector name for a given symbol."""
    for sector, stocks in SECTOR_MAP.items():
        if symbol in stocks:
            return sector
    return "Other"


def apply_sector_cap(results, max_per_sector=3):
    """
    Keep max N stocks per sector.
    Priority: best grade first, then best risk:reward.
    """
    sector_count   = {}
    final          = []
    sorted_results = sorted(
        results,
        key=lambda x: (GRADE_ORDER.get(x["Grade"], 9), -x.get("RR_Ratio", 0))
    )
    for r in sorted_results:
        sec   = r["Sector"]
        count = sector_count.get(sec, 0)
        if count < max_per_sector:
            final.append(r)
            sector_count[sec] = count + 1
    return final
