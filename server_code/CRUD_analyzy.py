# -------------------------------------------------------
# Modul: CRUD_analyzy
#
# Modul obsahuje základní operace pro práci s analýzami v JSON formátu:
# - Create: vytvoření nové analýzy (vytvor_analyzu)
# - Read: načtení analýzy podle ID (nacti_analyzu)
# - Update: aktualizace existující analýzy (uprav_analyzu)
# - Delete: smazání analýzy (smaz_analyzu)
#
# Pomocné funkce:
# - validuj_nazev_analyzy: Kontrola platnosti názvu analýzy
# - validuj_data_analyzy: Kontrola struktury JSON dat analýzy
# - validuj_kriteria: Kontrola kritérií včetně součtu vah
# - handle_errors: Dekorátor pro jednotné zachytávání a logování chyb
# -------------------------------------------------------
import datetime
import logging
import functools
from typing import Dict, List, Optional, Any
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

# ============= Pomocné funkce pro error handling =============

def zapsat_info(zprava):
    """Pomocná funkce pro serverové logování info zpráv"""
    logging.info(f"[INFO] {zprava}")
    
def zapsat_chybu(zprava):
    """Pomocná funkce pro serverové logování chyb"""
    logging.error(f"[CHYBA] {zprava}")

def handle_errors(func):
    """
    Dekorátor pro jednotné zpracování chyb v serverových funkcích.
    Zachytí výjimky, zaloguje je a přehodí klientovi.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            zprava = f"Chyba v {func.__name__}: {str(e)}"
            zapsat_chybu(zprava)
            raise ValueError(zprava) from e
    return wrapper

# =============== Validační funkce ===============

def validuj_nazev_analyzy(nazev: str) -> None:
    """
    Validuje název analýzy.
    
    Args:
        nazev: Název analýzy k validaci
        
    Raises:
        ValueError: Pokud název není validní
    """
    if not nazev:
        raise ValueError("Název analýzy nesmí být prázdný.")
    if len(nazev) > 100:  # Konstanty.VALIDACE['MAX_DELKA_NAZEV']
        raise ValueError("Název analýzy je příliš dlouhý (max 100 znaků).")

def validuj_data_analyzy(data: Dict) -> None:
    """
    Validuje strukturu dat analýzy.
    
    Args:
        data: Data analýzy k validaci
        
    Raises:
        ValueError: Pokud data nejsou validní
    """
    if not isinstance(data, dict):
        raise ValueError("Data analýzy musí být dictionary.")
    
    # Kontrola, zda obsahuje všechny potřebné klíče
    required_keys = ["popis", "kriteria", "varianty", "hodnoty"]
    missing_keys = [key for key in required_keys if key not in data]
    
    if missing_keys:
        raise ValueError(f"Chybí povinné klíče v datech analýzy: {', '.join(missing_keys)}")
        
    # Validace kritérií
    validuj_kriteria(data.get("kriteria", []))
    
    # Validace variant
    if not data.get("varianty", []):
        raise ValueError("Analýza musí obsahovat alespoň jednu variantu.")
    
    # Validace hodnot
    hodnoty = data.get("hodnoty", {})
    if not isinstance(hodnoty, dict) or "matice_hodnoty" not in hodnoty:
        raise ValueError("Data analýzy musí obsahovat klíč 'hodnoty' s podklíčem 'matice_hodnoty'.")

def validuj_kriteria(kriteria: List[Dict]) -> None:
    """
    Validuje seznam kritérií včetně kontroly součtu vah.
    
    Args:
        kriteria: Seznam kritérií k validaci
        
    Raises:
        ValueError: Pokud kritéria nejsou validní
    """
    if not kriteria:
        raise ValueError("Analýza musí obsahovat alespoň jedno kritérium.")
    
    try:
        vahy_suma = sum(float(k['vaha']) for k in kriteria)
        if abs(vahy_suma - 1.0) > 0.001:  # Konstanty.VALIDACE['TOLERANCE_SOUCTU_VAH']
            raise ValueError(f"Součet vah musí být 1.0 (aktuálně: {vahy_suma:.3f}).")
    except (ValueError, TypeError, KeyError):
        raise ValueError("Neplatná hodnota váhy u některého z kritérií.")

# =============== CRUD Operace ===============

@anvil.server.callable
@handle_errors
def vytvor_analyzu(nazev: str, popis: str = "") -> str:
    """
    Vytvoří novou analýzu v JSON formátu.
    
    Args:
        nazev: Název nové analýzy
        popis: Popis analýzy
        
    Returns:
        str: ID nově vytvořené analýzy
        
    Raises:
        ValueError: Pokud vytvoření selže nebo data nejsou validní
    """
    uzivatel = anvil.users.get_user()
    if not uzivatel:
        raise ValueError("Pro vytvoření analýzy musíte být přihlášen.")

    validuj_nazev_analyzy(nazev)
    
    try:
        # Vytvoření základní JSON struktury pro analýzu
        data_json = {
            "popis": popis,
            "kriteria": [],
            "varianty": [],
            "hodnoty": {"matice_hodnoty": {}}
        }
        
        # Vytvoření záznamu v databázi
        analyza = app_tables.analyzy.add_row(
            nazev=nazev,
            uzivatel=uzivatel,
            data_json=data_json,
            datum_vytvoreni=datetime.datetime.now(),
            datum_upravy=None
        )
        return analyza.get_id()
    except Exception as e:
        zapsat_chybu(f"Chyba při vytváření analýzy: {str(e)}")
        raise

@anvil.server.callable
@handle_errors
def nacti_analyzu(analyza_id: str) -> Dict:
    """
    Načte analýzu podle ID.
    
    Args:
        analyza_id: ID požadované analýzy
        
    Returns:
        Dict: Slovník s daty analýzy
    """
    try:
        analyza = app_tables.analyzy.get_by_id(analyza_id)
        if not analyza:
            raise ValueError(f"Analýza s ID {analyza_id} neexistuje.")
            
        # Sestavení kompletního slovníku dat
        result = {
            "id": analyza.get_id(),
            "nazev": analyza["nazev"],
            "datum_vytvoreni": analyza["datum_vytvoreni"],
            "datum_upravy": analyza["datum_upravy"],
        }
        
        # Přidání dat z JSON
        result.update(analyza["data_json"])
        
        return result
    except Exception as e:
        zapsat_chybu(f"Chyba při načítání analýzy {analyza_id}: {str(e)}")
        raise

@anvil.server.callable
@handle_errors
def uprav_analyzu(analyza_id: str, nazev: str = None, data: Dict = None) -> None:
    """
    Upraví existující analýzu.
    
    Args:
        analyza_id: ID analýzy k úpravě
        nazev: Nový název analýzy (volitelný)
        data: Nová data JSON (volitelné)
    """
    try:
        analyza = app_tables.analyzy.get_by_id(analyza_id)
        if not analyza:
            raise ValueError(f"Analýza s ID {analyza_id} neexistuje.")
        
        # Kontrola, zda má uživatel právo upravovat analýzu
        aktualni_uzivatel = anvil.users.get_user()
        if (aktualni_uzivatel != analyza["uzivatel"] and 
            not (aktualni_uzivatel and aktualni_uzivatel.get("role") == "admin")):
            raise ValueError("Nemáte oprávnění upravit tuto analýzu.")
        
        # Aktualizace názvu, pokud byl poskytnut
        if nazev is not None:
            validuj_nazev_analyzy(nazev)
            analyza["nazev"] = nazev
        
        # Aktualizace dat, pokud byla poskytnuta
        if data is not None:
            # Validace struktury dat
            validuj_data_analyzy(data)
            analyza["data_json"] = data
        
        # Aktualizace časového razítka
        analyza["datum_upravy"] = datetime.datetime.now()
        
    except Exception as e:
        zapsat_chybu(f"Chyba při úpravě analýzy {analyza_id}: {str(e)}")
        raise

@anvil.server.callable
@handle_errors
def smaz_analyzu(analyza_id: str) -> bool:
    """
    Smaže analýzu podle ID.
    
    Args:
        analyza_id: ID analýzy ke smazání
        
    Returns:
        bool: True pokud byla analýza úspěšně smazána
    """
    try:
        analyza = app_tables.analyzy.get_by_id(analyza_id)
        if not analyza:
            return False
            
        # Kontrola oprávnění - pouze vlastník nebo admin může mazat
        aktualni_uzivatel = anvil.users.get_user()
        if (aktualni_uzivatel != analyza["uzivatel"] and 
            not (aktualni_uzivatel and aktualni_uzivatel.get("role") == "admin")):
            raise ValueError("Nemáte oprávnění smazat tuto analýzu.")
            
        analyza.delete()
        return True
        
    except Exception as e:
        zapsat_chybu(f"Chyba při mazání analýzy {analyza_id}: {str(e)}")
        raise

@anvil.server.callable
@handle_errors
def klonuj_analyzu(analyza_id: str) -> str:
    """
    Vytvoří kopii existující analýzy.
    
    Args:
        analyza_id: ID analýzy ke klonování
        
    Returns:
        str: ID nově vytvořené analýzy (klonu)
    """
    try:
        # Načtení původní analýzy
        puvodni = app_tables.analyzy.get_by_id(analyza_id)
        if not puvodni:
            raise ValueError(f"Analýza s ID {analyza_id} neexistuje.")
        
        # Kontrola, zda má uživatel právo klonovat analýzu
        aktualni_uzivatel = anvil.users.get_user()
        if not aktualni_uzivatel:
            raise ValueError("Pro klonování analýzy musíte být přihlášen.")
        
        # Jen vlastník nebo admin může klonovat
        if (aktualni_uzivatel != puvodni["uzivatel"] and 
            not (aktualni_uzivatel and aktualni_uzivatel.get("role") == "admin")):
            raise ValueError("Nemáte oprávnění klonovat tuto analýzu.")
        
        # Vytvoření kopie analýzy
        novy_nazev = f"Kopie - {puvodni['nazev']}"
        
        # Vytvoření nové analýzy
        nova_analyza = app_tables.analyzy.add_row(
            nazev=novy_nazev,
            uzivatel=aktualni_uzivatel,
            data_json=puvodni["data_json"],
            datum_vytvoreni=datetime.datetime.now(),
            datum_upravy=None
        )
        
        zapsat_info(f"Analýza {analyza_id} úspěšně naklonována jako {nova_analyza.get_id()}")
        return nova_analyza.get_id()
        
    except Exception as e:
        zapsat_chybu(f"Chyba při klonování analýzy {analyza_id}: {str(e)}")
        raise ValueError(f"Nepodařilo se klonovat analýzu: {str(e)}")
