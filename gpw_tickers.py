"""
GPW and NewConnect Ticker Universe for Turtle Trading System.
Baza tickerów dla Giełdy Papierów Wartościowych w Warszawie (GPW) oraz rynku NewConnect (NC).

Źródło danych:
- Notowania pobierane są z Yahoo Finance (yfinance), który dla polskiego rynku stosuje sufiks '.WA'.
- Baza zawiera predefiniowane spółki z WIG20, mWIG40, sWIG80, szerokiego WIG oraz NewConnect,
  a także moduł automatycznego pobierania pełnej listy spółek online (ze Stooq / GPW).
"""

import urllib.request
import re

# ==============================================================================
# 1. BAZA GŁÓWNYCH SPÓŁEK GPW I NEWCONNECT (Z SUFIKSEM .WA)
# ==============================================================================
GPW_TICKERS = {
    # ------------------ WIG20 (Największe spółki GPW) ------------------
    "PKN.WA": {"name": "Orlen", "index": "WIG20", "sector": "Paliwa i Energetyka"},
    "PKO.WA": {"name": "PKO Bank Polski", "index": "WIG20", "sector": "Bankowość"},
    "PEO.WA": {"name": "Bank Pekao", "index": "WIG20", "sector": "Bankowość"},
    "KGH.WA": {"name": "KGHM Polska Miedź", "index": "WIG20", "sector": "Górnictwo i Hutnictwo"},
    "CDR.WA": {"name": "CD Projekt", "index": "WIG20", "sector": "Gry Wideo"},
    "DNP.WA": {"name": "Dino Polska", "index": "WIG20", "sector": "Handel Detaliczny"},
    "ALE.WA": {"name": "Allegro.eu", "index": "WIG20", "sector": "E-commerce"},
    "PZU.WA": {"name": "PZU", "index": "WIG20", "sector": "Ubezpieczenia"},
    "LPP.WA": {"name": "LPP", "index": "WIG20", "sector": "Odzież i Obuwie"},
    "SPL.WA": {"name": "Santander Bank Polska", "index": "WIG20", "sector": "Bankowość"},
    "MBK.WA": {"name": "mBank", "index": "WIG20", "sector": "Bankowość"},
    "KRU.WA": {"name": "Kruk", "index": "WIG20", "sector": "Finanse / Windykacja"},
    "KTY.WA": {"name": "Grupa Kęty", "index": "WIG20", "sector": "Przemysł Aluminiowy"},
    "JSW.WA": {"name": "Jastrzębska Spółka Węglowa", "index": "WIG20", "sector": "Górnictwo"},
    "PGE.WA": {"name": "PGE Polska Grupa Energetyczna", "index": "WIG20", "sector": "Energetyka"},
    "TPE.WA": {"name": "Tauron PE", "index": "WIG20", "sector": "Energetyka"},
    "OPL.WA": {"name": "Orange Polska", "index": "WIG20", "sector": "Telekomunikacja"},
    "CPS.WA": {"name": "Cyfrowy Polsat", "index": "WIG20", "sector": "Media i Telekomunikacja"},
    "BFT.WA": {"name": "Benefit Systems", "index": "WIG20", "sector": "Usługi / Rekreacja"},
    "BDX.WA": {"name": "Budimex", "index": "WIG20", "sector": "Budownictwo"},

    # ------------------ mWIG40 (Średnie spółki GPW) ------------------
    "ACP.WA": {"name": "Asseco Poland", "index": "mWIG40", "sector": "IT / Oprogramowanie"},
    "MIL.WA": {"name": "Bank Millennium", "index": "mWIG40", "sector": "Bankowość"},
    "ING.WA": {"name": "ING Bank Śląski", "index": "mWIG40", "sector": "Bankowość"},
    "BHW.WA": {"name": "Bank Handlowy", "index": "mWIG40", "sector": "Bankowość"},
    "XTB.WA": {"name": "XTB", "index": "mWIG40", "sector": "Finanse / Broker"},
    "CCC.WA": {"name": "CCC", "index": "mWIG40", "sector": "Obuwie i Retail"},
    "ENA.WA": {"name": "Enea", "index": "mWIG40", "sector": "Energetyka"},
    "TEN.WA": {"name": "Ten Square Games", "index": "mWIG40", "sector": "Gry Wideo"},
    "11B.WA": {"name": "11 bit studios", "index": "mWIG40", "sector": "Gry Wideo"},
    "CIE.WA": {"name": "Ciech / Qemetica", "index": "mWIG40", "sector": "Chemia"},
    "ATT.WA": {"name": "Grupa Azoty", "index": "mWIG40", "sector": "Chemia"},
    "CAR.WA": {"name": "Inter Cars", "index": "mWIG40", "sector": "Motoryzacja / Dystrybucja"},
    "DOM.WA": {"name": "Dom Development", "index": "mWIG40", "sector": "Deweloperzy"},
    "ATD.WA": {"name": "Autopartner", "index": "mWIG40", "sector": "Części Samochodowe"},
    "NEU.WA": {"name": "Neuca", "index": "mWIG40", "sector": "Farmacja i Zdrowie"},
    "TXT.WA": {"name": "Text (LiveChat Software)", "index": "mWIG40", "sector": "IT / SaaS"},
    "GPP.WA": {"name": "Grupa Pracuj", "index": "mWIG40", "sector": "HR / Internet"},
    "APR.WA": {"name": "Auto Partner", "index": "mWIG40", "sector": "Dystrybucja Części"},
    "EUR.WA": {"name": "Eurocash", "index": "mWIG40", "sector": "Dystrybucja FMCG"},
    "WPL.WA": {"name": "Wirtualna Polska Holding", "index": "mWIG40", "sector": "Media Internetowe"},
    "EAT.WA": {"name": "AmRest Holdings", "index": "mWIG40", "sector": "Gastronomia / Retail"},
    "CLN.WA": {"name": "Celon Pharma", "index": "mWIG40", "sector": "Biotechnologia"},
    "SNT.WA": {"name": "Synektik", "index": "mWIG40", "sector": "Sprzęt Medyczny"},
    "MRB.WA": {"name": "Mo-BRUK", "index": "mWIG40", "sector": "Ekologia / Recykling"},
    "ASB.WA": {"name": "ASBISc Enterprises", "index": "mWIG40", "sector": "Dystrybucja IT"},
    "ALR.WA": {"name": "Alior Bank", "index": "mWIG40", "sector": "Bankowość"},
    "HUG.WA": {"name": "Huuuge Inc", "index": "mWIG40", "sector": "Gry Wideo"},
    "GPW.WA": {"name": "Giełda Papierów Wartościowych", "index": "mWIG40", "sector": "Finanse"},
    "BRP.WA": {"name": "Bumech", "index": "mWIG40", "sector": "Górnictwo"},

    # ------------------ sWIG80 (Mniejsze spółki GPW) ------------------
    "VGO.WA": {"name": "Voxel", "index": "sWIG80", "sector": "Diagnostyka Medyczna"},
    "ARX.WA": {"name": "Arctic Paper", "index": "sWIG80", "sector": "Papier i Celuloza"},
    "COG.WA": {"name": "Cognor Holding", "index": "sWIG80", "sector": "Hutnictwo"},
    "UNT.WA": {"name": "Unimot", "index": "sWIG80", "sector": "Paliwa i Gaz"},
    "TOA.WA": {"name": "TOYA", "index": "sWIG80", "sector": "Narzędzia i Przemysł"},
    "SNK.WA": {"name": "Sanok Rubber Company", "index": "sWIG80", "sector": "Przemysł Gumowy"},
    "ASE.WA": {"name": "Asseco South Eastern Europe", "index": "sWIG80", "sector": "IT"},
    "TOR.WA": {"name": "Torpol", "index": "sWIG80", "sector": "Infrastruktura Kolejowa"},
    "STX.WA": {"name": "Stalexport Autostrady", "index": "sWIG80", "sector": "Infrastruktura"},
    "BOW.WA": {"name": "Bowim", "index": "sWIG80", "sector": "Dystrybucja Stali"},
    "VRG.WA": {"name": "VRG", "index": "sWIG80", "sector": "Odzież / Biżuteria"},
    "ACG.WA": {"name": "AC", "index": "sWIG80", "sector": "Autogaz / Automotive"},
    "MLS.WA": {"name": "ML System", "index": "sWIG80", "sector": "Fotowoltaika / OZE"},
    "DAT.WA": {"name": "DataWalk", "index": "sWIG80", "sector": "Big Data / IT"},
    "CTX.WA": {"name": "Captor Therapeutics", "index": "sWIG80", "sector": "Biotech"},
    "SHO.WA": {"name": "Shoper", "index": "sWIG80", "sector": "E-commerce SaaS"},
    "MCI.WA": {"name": "MCI Capital", "index": "sWIG80", "sector": "Fundusz VC / PE"},
    "SNX.WA": {"name": "Sunex", "index": "sWIG80", "sector": "Odnawialne Źródła Energii"},
    "ECH.WA": {"name": "Echo Investment", "index": "sWIG80", "sector": "Deweloperzy"},
    "DEK.WA": {"name": "Dekpol", "index": "sWIG80", "sector": "Budownictwo"},
    "RAW.WA": {"name": "Rawlplug", "index": "sWIG80", "sector": "Mocowania Budowlane"},
    "FTE.WA": {"name": "Forte", "index": "sWIG80", "sector": "Meble"},
    "ABS.WA": {"name": "Asseco Business Solutions", "index": "sWIG80", "sector": "IT"},
    "OAT.WA": {"name": "Moje Bermudy Ostrów", "index": "sWIG80", "sector": "Medycyna"},
    "OPN.WA": {"name": "Oponeo.pl", "index": "sWIG80", "sector": "E-commerce Opony"},
    "AMB.WA": {"name": "Ambra", "index": "sWIG80", "sector": "Wina i Alkohole"},
    "CIG.WA": {"name": "CI Games", "index": "sWIG80", "sector": "Gry Wideo"},
    "AST.WA": {"name": "Astarta Holding", "index": "sWIG80", "sector": "Rolnictwo i Cukier"},
    "KER.WA": {"name": "Kernel Holding", "index": "sWIG80", "sector": "Rolnictwo"},
    "OVO.WA": {"name": "Ovostar Union", "index": "sWIG80", "sector": "Rolnictwo"},

    # ------------------ NewConnect & Dynamiczne Spółki Growth ------------------
    "G4M.WA": {"name": "GreenX Metals", "index": "NewConnect", "sector": "Surowce"},
    "ALL.WA": {"name": "All in! Games", "index": "NewConnect", "sector": "Gry Wideo"},
    "SFD.WA": {"name": "SFD", "index": "NewConnect", "sector": "Odżywki i Suplementy"},
    "VEE.WA": {"name": "Vee", "index": "NewConnect", "sector": "Voice AI / IT"},
    "BLO.WA": {"name": "Bloober Team", "index": "GPW/NC", "sector": "Gry Wideo"},
    "PCF.WA": {"name": "People Can Fly Group", "index": "GPW/NC", "sector": "Gry Wideo"},
    "PLW.WA": {"name": "PlayWay", "index": "GPW/NC", "sector": "Gry Wideo"},
    "XTP.WA": {"name": "XTPL", "index": "GPW/NC", "sector": "Nanotechnologia"},
    "CRE.WA": {"name": "Creepy Jar", "index": "GPW/NC", "sector": "Gry Wideo"},
    "BVT.WA": {"name": "BioMaxima", "index": "NewConnect", "sector": "Biotechnologia"},
    "PND.WA": {"name": "Pure Biologics", "index": "NewConnect", "sector": "Biotech"},
    "MED.WA": {"name": "MedApp", "index": "NewConnect", "sector": "Telemedycyna"},
    "GLC.WA": {"name": "Genomtec", "index": "NewConnect", "sector": "Diagnostyka Genetyczna"},
    "SNT_NC.WA": {"name": "Scanway", "index": "NewConnect", "sector": "Technologie Kosmiczne"},
    "SEV.WA": {"name": "Sevenet", "index": "NewConnect", "sector": "IT / Sieci"},
    "ERB.WA": {"name": "Erbud", "index": "GPW", "sector": "Budownictwo"},
    "STP.WA": {"name": "Stalprodukt", "index": "GPW", "sector": "Hutnictwo"},
}


def get_ticker_list(universe: str = "ALL"):
    """
    Zwraca listę symboli w zależności od wybranego uniwersum:
    - 'ALL': wszystkie zdefiniowane spółki
    - 'WIG20': tylko WIG20
    - 'mWIG40': tylko mWIG40
    - 'sWIG80': tylko sWIG80
    - 'GPW_MAIN': WIG20 + mWIG40 + sWIG80
    - 'NewConnect': tylko NewConnect
    """
    if universe == "ALL":
        return sorted(list(GPW_TICKERS.keys()))
    elif universe == "GPW_MAIN":
        return sorted([sym for sym, inf in GPW_TICKERS.items() if inf.get("index") in ["WIG20", "mWIG40", "sWIG80"]])
    elif universe == "WIG20":
        return sorted([sym for sym, inf in GPW_TICKERS.items() if inf.get("index") == "WIG20"])
    elif universe == "mWIG40":
        return sorted([sym for sym, inf in GPW_TICKERS.items() if inf.get("index") == "mWIG40"])
    elif universe == "sWIG80":
        return sorted([sym for sym, inf in GPW_TICKERS.items() if inf.get("index") == "sWIG80"])
    elif universe == "NewConnect":
        return sorted([sym for sym, inf in GPW_TICKERS.items() if "NewConnect" in inf.get("index", "") or "NC" in inf.get("index", "")])
    return sorted(list(GPW_TICKERS.keys()))


def get_ticker_info(symbol: str):
    """Zwraca metadane spółki (nazwa, indeks, sektor)."""
    return GPW_TICKERS.get(symbol, {"name": symbol.replace(".WA", ""), "index": "Inne", "sector": "Inne"})


def fetch_online_all_gpw_nc_tickers():
    """
    Opcjonalna funkcja: dynamicznie pobiera pełną listę aktualnych tickerów
    notowanych na GPW i NewConnect z publicznych serwisów giełdowych (Stooq / GPW).
    Zwraca listę tickerów w formacie z sufiksem '.WA'.
    """
    tickers = set(GPW_TICKERS.keys())
    try:
        # Pobieranie listy spółek z rynku polskiego (przykładowo Stooq GPW)
        url = "https://stooq.pl/q/i/?s=wig"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode("utf-8", errors="ignore")
            # Wyciągamy symbole 3-5 znakowe
            found = re.findall(r'/q/\?s=([a-z0-9]{3,6})', html)
            for t in found:
                sym = f"{t.upper()}.WA"
                tickers.add(sym)
    except Exception:
        pass
    return sorted(list(tickers))
