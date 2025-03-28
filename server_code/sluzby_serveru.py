# -------------------------------------------------------
# Modul: Sluzby_serveru
#
# Tento modul poskytuje serverové funkce, které jsou volány z klientského kódu.
# Klientský kód používá SpravceStavu pro správu lokálního stavu aplikace,
# který se synchronizuje se serverem pomocí těchto funkcí.
# -------------------------------------------------------
import datetime
import logging
import functools
import time
from anvil.tables import Transaction
from anvil.tables import TransactionConflict
from typing import Dict, List, Optional, Any
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import Konstanty

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
        raise ValueError(Konstanty.ZPRAVY_CHYB['NAZEV_PRAZDNY'])
    if len(nazev) > Konstanty.VALIDACE['MAX_DELKA_NAZEV']:
        raise ValueError(Konstanty.ZPRAVY_CHYB['NAZEV_DLOUHY'])

def validuj_kriteria(kriteria: List[Dict]) -> None:
    """
    Validuje seznam kritérií včetně kontroly součtu vah.
    
    Args:
        kriteria: Seznam kritérií k validaci
        
    Raises:
        ValueError: Pokud kritéria nejsou validní
    """
    if not kriteria:
        raise ValueError(Konstanty.ZPRAVY_CHYB['MIN_KRITERIA'])
    
    try:
        vahy_suma = sum(float(k['vaha']) for k in kriteria)
        if abs(vahy_suma - 1.0) > Konstanty.VALIDACE['TOLERANCE_SOUCTU_VAH']:
            raise ValueError(Konstanty.ZPRAVY_CHYB['SUMA_VAH'].format(vahy_suma))
    except (ValueError, TypeError):
        raise ValueError(Konstanty.ZPRAVY_CHYB['NEPLATNA_VAHA'])

# =============== Pomocné funkce pro práci s daty ===============

def _uloz_kriteria(analyza: Any, kriteria: List[Dict]) -> None:
    """
    Uloží kritéria k dané analýze.
    
    Args:
        analyza: Instance analýzy
        kriteria: Seznam kritérií k uložení
    """
    for krit in kriteria:
        try:
            vaha = float(krit['vaha'])
            app_tables.kriterium.add_row(
                analyza=analyza,
                nazev_kriteria=krit['nazev_kriteria'],
                typ=krit['typ'],
                vaha=vaha
            )
        except (ValueError, TypeError):
            raise ValueError(
                Konstanty.ZPRAVY_CHYB['NEPLATNA_VAHA_KRITERIA'].format(krit['nazev_kriteria'])
            )

def _uloz_varianty(analyza: Any, varianty: List[Dict]) -> None:
    """
    Uloží varianty k dané analýze.
    
    Args:
        analyza: Instance analýzy
        varianty: Seznam variant k uložení
    """
    for var in varianty:
        app_tables.varianta.add_row(
            analyza=analyza,
            nazev_varianty=var['nazev_varianty'],
            popis_varianty=var['popis_varianty']
        )

def _uloz_hodnoty(analyza: Any, hodnoty: Dict) -> None:
    """
    Uloží hodnoty pro kombinace variant a kritérií.
    
    Args:
        analyza: Instance analýzy
        hodnoty: Dictionary obsahující matici hodnot
    """
    if not isinstance(hodnoty, dict) or 'matice_hodnoty' not in hodnoty:
        raise ValueError("Neplatný formát dat pro hodnoty")
        
    for klic, hodnota in hodnoty['matice_hodnoty'].items():
        try:
            id_varianty, id_kriteria = klic.split('_')
            
            varianta = app_tables.varianta.get(
                analyza=analyza,
                nazev_varianty=id_varianty
            )
            kriterium = app_tables.kriterium.get(
                analyza=analyza,
                nazev_kriteria=id_kriteria
            )
            
            if varianta and kriterium:
                try:
                    if isinstance(hodnota, str):
                        hodnota = hodnota.replace(',', '.')
                    hodnota_float = float(hodnota)
                    app_tables.hodnota.add_row(
                        analyza=analyza,
                        varianta=varianta,
                        kriterium=kriterium,
                        hodnota=hodnota_float
                    )
                except (ValueError, TypeError):
                    raise ValueError(
                        Konstanty.ZPRAVY_CHYB['NEPLATNA_HODNOTA'].format(id_varianty, id_kriteria)
                    )
        except Exception as e:
            raise ValueError(f"Chyba při ukládání hodnoty: {str(e)}")

# =============== Veřejné serverové funkce ===============

@anvil.server.callable
@handle_errors
def pridej_analyzu(nazev: str, popis: str) -> str:
    """
    Vytvoří novou analýzu.
    
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
        raise ValueError(Konstanty.ZPRAVY_CHYB['NEZNAMY_UZIVATEL'])

    validuj_nazev_analyzy(nazev)
    
    try:
        analyza = app_tables.analyza.add_row(
            nazev=nazev,
            popis=popis,
            datum_vytvoreni=datetime.datetime.now(),
            uzivatel=uzivatel,
            datum_upravy=None,
            stav=None
        )
        return analyza.get_id()
    except Exception as e:
        logging.error(f"Chyba při vytváření analýzy: {str(e)}")
        raise

@anvil.server.callable
@handle_errors
def nacti_analyzu(analyza_id: str) -> Dict:
    """
    Načte detaily konkrétní analýzy.
    
    Args:
        analyza_id: ID požadované analýzy
        
    Returns:
        Dict: Základní údaje o analýze
    """
    try:
        analyza = app_tables.analyza.get_by_id(analyza_id)
        if not analyza:
            raise ValueError(Konstanty.ZPRAVY_CHYB['ANALYZA_NEEXISTUJE'].format(analyza_id))
            
        return {
            'nazev': analyza['nazev'],
            'popis': analyza['popis'],
            'datum_vytvoreni': analyza['datum_vytvoreni']
        }
    except Exception as e:
        logging.error(f"Chyba při načítání analýzy {analyza_id}: {str(e)}")
        raise

@anvil.server.callable
@handle_errors
def nacti_analyzy_uzivatele() -> List[Any]:
    """
    Načte seznam analýz přihlášeného uživatele pro uživatelský dashboard.
    
    Returns:
        List[Any]: Seznam analýz s jejich základními údaji
    """
    uzivatel = anvil.users.get_user()
    if not uzivatel:
        return []
        
    try:
        return list(app_tables.analyza.search(
            tables.order_by("datum_vytvoreni", ascending=False),
            uzivatel=uzivatel
        ))
    except Exception as e:
        logging.error(f"Chyba při načítání analýz uživatele: {str(e)}")
        return []


@anvil.server.callable
@handle_errors
def nacti_kriteria(analyza_id: str) -> List[Dict]:
    """
    Načte kritéria pro danou analýzu.
    
    Args:
        analyza_id: ID analýzy
        
    Returns:
        List[Dict]: Seznam kritérií a jejich vlastností
    """
    try:
        analyza = app_tables.analyza.get_by_id(analyza_id)
        if analyza:
            kriteria = list(app_tables.kriterium.search(analyza=analyza))
            return [{
                'nazev_kriteria': k['nazev_kriteria'],
                'typ': k['typ'],
                'vaha': float(k['vaha'])
            } for k in kriteria]
        return []
    except Exception as e:
        logging.error(f"Chyba při načítání kritérií pro analýzu {analyza_id}: {str(e)}")
        raise

@anvil.server.callable
@handle_errors
def nacti_varianty(analyza_id: str) -> List[Dict]:
    """
    Načte varianty pro danou analýzu.
    
    Args:
        analyza_id: ID analýzy
        
    Returns:
        List[Dict]: Seznam variant a jejich vlastností
    """
    try:
        analyza = app_tables.analyza.get_by_id(analyza_id)
        if analyza:
            varianty = list(app_tables.varianta.search(analyza=analyza))
            return [{
                'nazev_varianty': v['nazev_varianty'],
                'popis_varianty': v['popis_varianty']
            } for v in varianty]
        return []
    except Exception as e:
        logging.error(f"Chyba při načítání variant pro analýzu {analyza_id}: {str(e)}")
        raise

@anvil.server.callable
@handle_errors
def nacti_hodnoty(analyza_id: str) -> Dict:
    """
    Načte matici hodnot pro danou analýzu.
    
    Args:
        analyza_id: ID analýzy
        
    Returns:
        Dict: Dictionary obsahující matici hodnot
    """
    try:
        analyza = app_tables.analyza.get_by_id(analyza_id)
        hodnoty = {'matice_hodnoty': {}}
        
        if analyza:
            for h in app_tables.hodnota.search(analyza=analyza):
                if h['varianta'] and h['kriterium']:
                    klic = f"{h['varianta']['nazev_varianty']}_{h['kriterium']['nazev_kriteria']}"
                    hodnoty['matice_hodnoty'][klic] = float(h['hodnota'])
        
        return hodnoty
    except Exception as e:
        logging.error(f"Chyba při načítání hodnot pro analýzu {analyza_id}: {str(e)}")
        raise

@anvil.server.callable
@handle_errors
def uprav_analyzu(analyza_id: str, nazev: str, popis: str) -> None:
    """
    Upraví základní údaje analýzy.
    
    Args:
        analyza_id: ID analýzy
        nazev: Nový název
        popis: Nový popis
    """
    try:
        analyza = app_tables.analyza.get_by_id(analyza_id)
        if not analyza:
            raise ValueError(Konstanty.ZPRAVY_CHYB['ANALYZA_NEEXISTUJE'].format(analyza_id))
            
        validuj_nazev_analyzy(nazev)
        
        analyza.update(
            nazev=nazev,
            popis=popis,
            datum_upravy=datetime.datetime.now()
        )
    except Exception as e:
        logging.error(f"Chyba při úpravě analýzy {analyza_id}: {str(e)}")
        raise

@anvil.server.callable
@handle_errors
def uloz_kompletni_analyzu(analyza_id, kriteria, varianty, hodnoty, max_retries=3):
    """
    Uloží kompletní analýzu, tedy kritéria, varianty a odpovídající hodnoty.
    Operace se provádí v rámci transakce, která zajistí konzistenci dat. Při konfliktu
    transakce se operace opakuje až do dosažení maximálního počtu pokusů.
    
    Args:
        analyza_id: ID analýzy, ke které se data ukládají.
        kriteria: Seznam slovníků s klíči 'nazev_kriteria', 'typ' a 'vaha'.
        varianty: Seznam slovníků s klíči 'nazev_varianty' a 'popis_varianty'.
        hodnoty: Slovník obsahující klíč 'matice_hodnoty'. Klíče v této matici mají formát 
                 "nazev_varianty_nazev_kriteria" a hodnota je číslo.
        max_retries: Maximální počet pokusů při konfliktu transakce.
        
    Returns:
        True, pokud operace proběhla úspěšně.
        
    Raises:
        ValueError: S chybovou zprávou v případě neúspěchu operace.
    """
    retry_count = 0
    while retry_count <= max_retries:
        try:
            with Transaction():
                # Načtení analýzy z databáze
                analyza = app_tables.analyza.get_by_id(analyza_id)
                if not analyza:
                    raise ValueError(f"Analýza s ID {analyza_id} neexistuje.")
                
                # Validace kritérií
                validuj_kriteria(kriteria)
                
                # Načtení existujících řádků z databáze
                existujici_kriteria = list(app_tables.kriterium.search(analyza=analyza))
                existujici_varianty = list(app_tables.varianta.search(analyza=analyza))
                existujici_hodnoty = list(app_tables.hodnota.search(analyza=analyza))
                
                # Vytvoření slovníků pro rychlý přístup podle názvu
                dict_kriteria = {k['nazev_kriteria']: k for k in existujici_kriteria}
                dict_varianty = {v['nazev_varianty']: v for v in existujici_varianty}
                
                # --- Zpracování kritérií ---
                aktualizovana_kriteria = {}
                for k in kriteria:
                    nazev = k['nazev_kriteria']
                    if nazev in dict_kriteria:
                        # Aktualizace existujícího kritéria
                        row = dict_kriteria[nazev]
                        row.update(typ=k['typ'], vaha=k['vaha'])
                        aktualizovana_kriteria[nazev] = row
                        # Odstranění z dict – zbylá kritéria budou smazána
                        del dict_kriteria[nazev]
                    else:
                        # Vložení nového kritéria
                        row = app_tables.kriterium.add_row(
                            analyza=analyza,
                            nazev_kriteria=nazev,
                            typ=k['typ'],
                            vaha=k['vaha']
                        )
                        aktualizovana_kriteria[nazev] = row
                # Smazání kritérií, která nejsou ve vstupních datech
                for row in dict_kriteria.values():
                    row.delete()
                    
                # --- Zpracování variant ---
                aktualizovane_varianty = {}
                for v in varianty:
                    nazev = v['nazev_varianty']
                    if nazev in dict_varianty:
                        row = dict_varianty[nazev]
                        row.update(popis_varianty=v['popis_varianty'])
                        aktualizovane_varianty[nazev] = row
                        del dict_varianty[nazev]
                    else:
                        row = app_tables.varianta.add_row(
                            analyza=analyza,
                            nazev_varianty=nazev,
                            popis_varianty=v['popis_varianty']
                        )
                        aktualizovane_varianty[nazev] = row
                # Smazání variant, které nejsou ve vstupních datech
                for row in dict_varianty.values():
                    row.delete()
                    
                # --- Zpracování hodnot ---
                # Vytvoření slovníku existujících hodnot s klíčem "nazev_varianty_nazev_kriteria"
                dict_hodnot = {}
                for h in existujici_hodnoty:
                    if h['varianta'] and h['kriterium']:
                        key = f"{h['varianta']['nazev_varianty']}_{h['kriterium']['nazev_kriteria']}"
                        dict_hodnot[key] = h
                
                nove_klice = set()
                for key, nova_hodnota in hodnoty.get('matice_hodnoty', {}).items():
                    # Rozdělení klíče na název varianty a kritéria
                    parts = key.split('_', 1)
                    if len(parts) != 2:
                        continue
                    nazev_varianty, nazev_kriteria = parts
                    if (nazev_varianty in aktualizovane_varianty and 
                        nazev_kriteria in aktualizovana_kriteria):
                        nove_klice.add(key)
                        if key in dict_hodnot:
                            # Aktualizace existující hodnoty, pokud se změnila
                            row = dict_hodnot[key]
                            if float(row['hodnota']) != float(nova_hodnota):
                                row.update(hodnota=nova_hodnota)
                            del dict_hodnot[key]
                        else:
                            # Vložení nové hodnoty
                            app_tables.hodnota.add_row(
                                analyza=analyza,
                                varianta=aktualizovane_varianty[nazev_varianty],
                                kriterium=aktualizovana_kriteria[nazev_kriteria],
                                hodnota=nova_hodnota
                            )
                # Smazání hodnot, které nejsou ve vstupních datech
                for row in dict_hodnot.values():
                    row.delete()
                    
                # --- Aktualizace analýzy ---
                analyza.update(datum_upravy=datetime.datetime.now())
            
            # Pokud dojde k úspěšnému dokončení transakce, vrátíme True
            return True
        except TransactionConflict:
            retry_count += 1
            if retry_count > max_retries:
                raise ValueError(f"Nepodařilo se dokončit transakci po {max_retries} pokusech.")
            time.sleep(0.5)  # Krátká pauza před opakováním transakce
        except Exception as e:
            raise ValueError(f"Chyba při ukládání analýzy: {str(e)}")

@anvil.server.callable
@handle_errors
def smaz_analyzu(analyza_id: str) -> None:
    """
    Smaže analýzu a všechna související data.
    
    Args:
        analyza_id: ID analýzy ke smazání
    """
    try:
        analyza = app_tables.analyza.get_by_id(analyza_id)
        if not analyza:
            return
            
        # Nejdřív smaže související data
        for hodnota in app_tables.hodnota.search(analyza=analyza):
            hodnota.delete()
        for varianta in app_tables.varianta.search(analyza=analyza):
            varianta.delete()
        for kriterium in app_tables.kriterium.search(analyza=analyza):
            kriterium.delete()
            
        # Nakonec smaže samotnou analýzu
        analyza.delete()
        
    except Exception as e:
        logging.error(f"Chyba při mazání analýzy {analyza_id}: {str(e)}")
        raise ValueError(Konstanty.ZPRAVY_CHYB['SMAZANI_SELHALO'])

@anvil.server.callable
@handle_errors
def set_edit_analyza_id(analyza_id: str) -> None:
    """
    Nastaví ID editované analýzy do session.
    
    Args:
        analyza_id: ID analýzy k editaci
    """
    anvil.server.session['edit_analyza_id'] = analyza_id

@anvil.server.callable
@handle_errors
def get_edit_analyza_id() -> Optional[str]:
    """
    Získá ID editované analýzy ze session.
    
    Returns:
        Optional[str]: ID analýzy nebo None
    """
    return anvil.server.session.get('edit_analyza_id')

@anvil.server.callable
@handle_errors
def nacti_kompletni_analyzu(analyza_id: str) -> Dict:
    """
    Načte kompletní data analýzy podle zadaného ID.
    Vrací slovník obsahující údaje o samotné analýze a k ní patřící kritéria,
    varianty a hodnoty.

    Args:
        analyza_id: ID analýzy k načtení

    Returns:
        Dict obsahující klíče:
            'analyza': dict s klíči 'id', 'nazev', 'popis', 'datum_vytvoreni', 'datum_upravy', 'stav'
            'kriteria': list slovníků s klíči 'nazev_kriteria', 'typ', 'vaha'
            'varianty': list slovníků s klíči 'nazev_varianty', 'popis_varianty'
            'hodnoty': dict, kde 'matice_hodnoty' je dict klíč = "{nazev_varianty}_{nazev_kriteria}", hodnota = float
    """
    analyza = app_tables.analyza.get_by_id(analyza_id)
    if not analyza:
        raise ValueError(Konstanty.ZPRAVY_CHYB['ANALYZA_NEEXISTUJE'].format(analyza_id))

    analyza_data = {
        'id': analyza.get_id(),
        'nazev': analyza['nazev'],
        'popis': analyza['popis'],
        'datum_vytvoreni': analyza['datum_vytvoreni'],
        'datum_upravy': analyza['datum_upravy'],
        'stav': analyza['stav']
    }

    [kriteria_query, varianty_query, hodnoty_query] = [
        app_tables.kriterium.search(analyza=analyza),
        app_tables.varianta.search(analyza=analyza),
        app_tables.hodnota.search(analyza=analyza)
    ]

    # Zpracuje výsledky dotazu
    kriteria = [
        {
            'nazev_kriteria': k['nazev_kriteria'],
            'typ': k['typ'],
            'vaha': float(k['vaha'])
        }
        for k in kriteria_query
    ]

    varianty = [
        {
            'nazev_varianty': v['nazev_varianty'],
            'popis_varianty': v['popis_varianty']
        }
        for v in varianty_query
    ]

    hodnoty = {'matice_hodnoty': {}}
    for h in hodnoty_query:
        if h['varianta'] and h['kriterium']:
            klic = f"{h['varianta']['nazev_varianty']}_{h['kriterium']['nazev_kriteria']}"
            hodnoty['matice_hodnoty'][klic] = float(h['hodnota'])

    return {
        'analyza': analyza_data,
        'kriteria': kriteria,
        'varianty': varianty,
        'hodnoty': hodnoty
    }

    return {
        'analyza': analyza_data,
        'kriteria': kriteria,
        'varianty': varianty,
        'hodnoty': hodnoty
    }

@anvil.server.callable
@handle_errors
def nacti_vsechny_uzivatele():
    """
    Načte všechny uživatele z databáze.
    
    Returns:
        List[Row]: Seznam uživatelů nebo prázdný seznam při chybě
    """
    try:
        return list(app_tables.users.search())
    except Exception as e:
        logging.error(f"Chyba při načítání uživatelů: {str(e)}")
        raise Exception("Nepodařilo se načíst seznam uživatelů")

@anvil.server.callable
@handle_errors
def vrat_pocet_analyz_pro_uzivatele(uzivatel):
  """
  Vrátí počet analýz přidružených k danému uživateli.
  
  Parametry:
      uzivatel: Řádek uživatele z tabulky 'users'
  
  Návratová hodnota:
      Celkový počet analýz, které se vážou k danému uživateli.
  """
  try:
    print(f"Hledám analýzy pro uživatele: {uzivatel['email']}")
    # Převedeme výsledek vyhledávání na list a spočítáme jeho délku
    analyzy = list(app_tables.analyza.search(uzivatel=uzivatel))
    pocet = len(analyzy)
    print(f"Nalezeno analýz: {pocet}")
    return pocet
  except Exception as e:
    print(f"Chyba při načítání počtu analýz: {str(e)}")
    logging.error(f"Chyba při načítání počtu analýz pro uživatele {uzivatel['email']}: {str(e)}")
    return 0

@anvil.server.callable
@handle_errors
def nacti_analyzy_uzivatele_admin(email, sort_by="datum_vytvoreni"):
    """
    Načte všechny analýzy daného uživatele pro admin rozhraní.
    
    Args:
        email: Email uživatele
        limit: Maximální počet načtených analýz
        sort_by: Pole pro řazení
        
    Returns:
        List[Row]: Seznam analýz uživatele
    """
    zapsat_info(f"Načítám analýzy pro uživatele: {email}")
    
    # Nejprve získáme správný Row objekt uživatele
    uzivatel = app_tables.users.get(email=email)
    if not uzivatel:
        raise ValueError(f"Uživatel {email} nenalezen")
        
    analyzy = list(app_tables.analyza.search(
        tables.order_by(sort_by, ascending=False),
        uzivatel=uzivatel,
    ))
    
    zapsat_info(f"Nalezeno {len(analyzy)} analýz pro uživatele {email}")
    return analyzy

@anvil.server.callable
@handle_errors
def smaz_uzivatele(email):
    """
    Smaže uživatele a všechny jeho analýzy.
    
    Args:
        email: Email uživatele ke smazání
    
    Returns:
        bool: True pokud byl uživatel úspěšně smazán
    """
    zapsat_info(f"Mažu uživatele: {email}")
    
    uzivatel = app_tables.users.get(email=email)

    # Kontrola, zda nejde o aktuálně přihlášeného uživatele
    aktualni_uzivatel = anvil.users.get_user()
    if aktualni_uzivatel and aktualni_uzivatel['email'] == email:
        raise ValueError("Nelze smazat vlastní účet, se kterým jste aktuálně přihlášeni.")
    
    if not uzivatel:
        raise ValueError(f"Uživatel {email} nebyl nalezen")
        
    # Nejprve získáme všechny analýzy uživatele
    analyzy = app_tables.analyza.search(uzivatel=uzivatel)
    pocet_analyz = 0
    
    # Použijeme existující, otestovanou funkci pro mazání jednotlivých analýz
    for analyza in analyzy:
        analyza_id = analyza.get_id()
        try:
            smaz_analyzu(analyza_id)
            pocet_analyz += 1
        except Exception as e:
            zapsat_chybu(f"Chyba při mazání analýzy {analyza_id}: {str(e)}")
            # Pokračujeme s dalšími analýzami
    
    # Nakonec smažeme samotného uživatele
    uzivatel.delete()
    zapsat_info(f"Uživatel {email} a {pocet_analyz} analýz úspěšně smazáno")
    
    return True

@anvil.server.callable
@handle_errors
def zmenit_roli_uzivatele(email, nova_role):
    """
    Změní roli uživatele.
    
    Args:
        email: Email uživatele
        nova_role: Nová role uživatele ('admin' nebo 'uživatel')
    
    Returns:
        bool: True pokud byla role úspěšně změněna
    """
    try:
        print(f"Měním roli uživatele {email} na: {nova_role}")
        
        # Kontrola, zda nejde o aktuálně přihlášeného uživatele
        aktualni_uzivatel = anvil.users.get_user()
        if aktualni_uzivatel and aktualni_uzivatel['email'] == email:
            raise ValueError("Nemůžete měnit roli vlastního účtu.")
        
        uzivatel = app_tables.users.get(email=email)
        
        if not uzivatel:
            raise ValueError(f"Uživatel {email} nebyl nalezen")
            
        # Změna role
        uzivatel['role'] = nova_role
        
        print(f"Role uživatele {email} úspěšně změněna na {nova_role}")
        return True
        
    except Exception as e:
        print(f"Chyba při změně role uživatele: {str(e)}")
        logging.error(f"Chyba při změně role uživatele {email}: {str(e)}")
        raise ValueError(f"Nepodařilo se změnit roli uživatele: {str(e)}")

@anvil.server.callable
@handle_errors
def vytvor_noveho_uzivatele(email, heslo, je_admin=False):
    """
    Vytvoří nového uživatele z administrátorského rozhraní.
    
    Args:
        email: Email nového uživatele
        heslo: Heslo pro nový účet
        je_admin: True pokud má být uživatel administrátor
    
    Returns:
        dict: Informace o vytvořeném uživateli nebo None při chybě
    """
    try:
        print(f"Vytvářím nového uživatele: {email}")

        # CRITICAL: Save the current user before creating a new one
        puvodni_uzivatel = anvil.users.get_user()

        # Kontrola, zda uživatel již neexistuje
        existujici = app_tables.users.get(email=email)
        if existujici:
            raise ValueError(f"Uživatel s emailem {email} již existuje")
        
        # Vytvoření uživatele pomocí signup_with_email
        novy_uzivatel = anvil.users.signup_with_email(email, heslo, remember=False)
        
        # Nastavení data vytvoření a aktivace účtu
        novy_uzivatel['signed_up'] = datetime.datetime.now()
        novy_uzivatel['enabled'] = True
        
        # Nastavení role pokud je admin
        if je_admin:
            novy_uzivatel['role'] = 'admin'

        # CRITICAL: Log back in as the original admin user
        if puvodni_uzivatel:
            # We use the internal login mechanism to restore the session
            anvil.users.force_login(puvodni_uzivatel)
      
        print(f"Uživatel {email} úspěšně vytvořen")
        
        # Vytvořit jednoduchý slovník místo použití get()
        return {
            'email': email,
            'signed_up': novy_uzivatel['signed_up'],
            'enabled': True,
            'role': 'admin' if je_admin else None
        }
        
    except Exception as e:
        print(f"Chyba při vytváření uživatele: {str(e)}")
        logging.error(f"Chyba při vytváření uživatele {email}: {str(e)}")
        raise ValueError(f"Nepodařilo se vytvořit uživatele: {str(e)}")

@anvil.server.callable
def nastavit_roli_po_registraci(email):
    """
    Kontroluje, zda nově registrovaný uživatel má mít automaticky admin roli.
    
    Args:
        email: Email registrovaného uživatele
        
    Returns:
        bool: True pokud byla přidělena role admin
    """
    try:
        # Seznam admin emailů
        admin_emaily = ['servisni_ucet@505.kg','saur@utb.cz','langer_l@utb.cz']
        
        # Kontrola, zda email patří mezi admin emaily
        if email in admin_emaily:
            # Získání uživatele podle emailu
            uzivatel = app_tables.users.get(email=email)
            if uzivatel:
                # Přidělení admin role
                uzivatel['role'] = 'admin'
                print(f"Automaticky přidělena admin role uživateli: {email}")
                return True
    
    except Exception as e:
        print(f"Chyba při nastavování role: {str(e)}")
    
    return False