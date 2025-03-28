# -------------------------------------------------------
# Modul: Sprava_uzivatelu
#
# Modul obsahuje funkce pro správu uživatelů a jejich analýz:
# - Správa uživatelských účtů (vytvoření, úprava, mazání)
# - Načítání seznamů analýz pro uživatele
# - Administrativní funkce
# - Pomocné funkce
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

# =============== Správa uživatelských účtů ===============

@anvil.server.callable
@handle_errors
def nacti_vsechny_uzivatele():
    """
    Načte všechny uživatele z databáze.
    Určeno pro administrátory.
    
    Returns:
        List[Row]: Seznam uživatelů nebo prázdný seznam při chybě
    """
    # Ověření, že volající je admin
    over_admin_prava()
    
    try:
        return list(app_tables.users.search())
    except Exception as e:
        zapsat_chybu(f"Chyba při načítání uživatelů: {str(e)}")
        raise ValueError("Nepodařilo se načíst seznam uživatelů")

@anvil.server.callable
@handle_errors
def vytvor_noveho_uzivatele(email: str, heslo: str, je_admin: bool = False):
    """
    Vytvoří nového uživatele z administrátorského rozhraní.
    
    Args:
        email: Email nového uživatele
        heslo: Heslo pro nový účet
        je_admin: True pokud má být uživatel administrátor
    
    Returns:
        dict: Informace o vytvořeném uživateli nebo None při chybě
    """
    # Ověření, že volající je admin
    over_admin_prava()
    
    try:
        zapsat_info(f"Vytvářím nového uživatele: {email}")

        # Uložení původního uživatele
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

        # Přihlášení zpět jako původní admin
        if puvodni_uzivatel:
            anvil.users.force_login(puvodni_uzivatel)
      
        zapsat_info(f"Uživatel {email} úspěšně vytvořen")
        
        return {
            'email': email,
            'signed_up': novy_uzivatel['signed_up'],
            'enabled': True,
            'role': 'admin' if je_admin else None
        }
        
    except Exception as e:
        zapsat_chybu(f"Chyba při vytváření uživatele {email}: {str(e)}")
        raise ValueError(f"Nepodařilo se vytvořit uživatele: {str(e)}")

@anvil.server.callable
@handle_errors
def zmenit_roli_uzivatele(email: str, nova_role: str) -> bool:
    """
    Změní roli uživatele.
    
    Args:
        email: Email uživatele
        nova_role: Nová role uživatele ('admin' nebo 'uživatel')
    
    Returns:
        bool: True pokud byla role úspěšně změněna
    """
    # Ověření, že volající je admin
    over_admin_prava()
    
    try:
        zapsat_info(f"Měním roli uživatele {email} na: {nova_role}")
        
        # Kontrola, zda nejde o aktuálně přihlášeného uživatele
        aktualni_uzivatel = anvil.users.get_user()
        if aktualni_uzivatel and aktualni_uzivatel['email'] == email:
            raise ValueError("Nemůžete měnit roli vlastního účtu.")
        
        uzivatel = app_tables.users.get(email=email)
        
        if not uzivatel:
            raise ValueError(f"Uživatel {email} nebyl nalezen")
            
        # Kontrola platnosti role
        if nova_role not in ('admin', 'uživatel'):
            raise ValueError(f"Neplatná role: {nova_role}")
            
        # Změna role
        uzivatel['role'] = nova_role if nova_role == 'admin' else None
        
        zapsat_info(f"Role uživatele {email} úspěšně změněna na {nova_role}")
        return True
        
    except Exception as e:
        zapsat_chybu(f"Chyba při změně role uživatele {email}: {str(e)}")
        raise ValueError(f"Nepodařilo se změnit roli uživatele: {str(e)}")

@anvil.server.callable
@handle_errors
def smaz_uzivatele(email: str) -> bool:
    """
    Smaže uživatele a všechny jeho analýzy.
    
    Args:
        email: Email uživatele ke smazání
    
    Returns:
        bool: True pokud byl uživatel úspěšně smazán
    """
    # Ověření, že volající je admin
    over_admin_prava()
    
    zapsat_info(f"Mažu uživatele: {email}")
    
    uzivatel = app_tables.users.get(email=email)

    # Kontrola, zda nejde o aktuálně přihlášeného uživatele
    aktualni_uzivatel = anvil.users.get_user()
    if aktualni_uzivatel and aktualni_uzivatel['email'] == email:
        raise ValueError("Nelze smazat vlastní účet, se kterým jste aktuálně přihlášeni.")
    
    if not uzivatel:
        raise ValueError(f"Uživatel {email} nebyl nalezen")
        
    # Nejprve získáme a smažeme všechny analýzy uživatele
    analyzy = app_tables.Analyzy.search(uzivatel=uzivatel)
    pocet_analyz = 0
    
    for analyza in analyzy:
        try:
            analyza.delete()
            pocet_analyz += 1
        except Exception as e:
            zapsat_chybu(f"Chyba při mazání analýzy: {str(e)}")
            # Pokračujeme s dalšími analýzami
    
    # Nakonec smažeme samotného uživatele
    uzivatel.delete()
    zapsat_info(f"Uživatel {email} a {pocet_analyz} analýz úspěšně smazáno")
    
    return True

# =============== Správa analýz uživatelů ===============

@anvil.server.callable
@handle_errors
def nacti_analyzy_uzivatele(limit: Optional[int] = None, sort_by: str = "datum_vytvoreni") -> List[Dict]:
    """
    Načte seznam analýz přihlášeného uživatele.
    
    Args:
        limit: Maximální počet načtených analýz (volitelný)
        sort_by: Pole pro řazení ("datum_vytvoreni" nebo "datum_upravy")
        
    Returns:
        List[Dict]: Seznam analýz s metadaty
    """
    uzivatel = anvil.users.get_user()
    if not uzivatel:
        return []
        
    try:
        # Načtení analýz uživatele podle požadovaného řazení
        if sort_by == "datum_vytvoreni":
            analyzy = list(app_tables.Analyzy.search(
                tables.order_by("datum_vytvoreni", ascending=False),
                uzivatel=uzivatel
            ))
        elif sort_by == "datum_upravy":
            analyzy = list(app_tables.Analyzy.search(
                tables.order_by("datum_upravy", ascending=False),
                uzivatel=uzivatel
            ))
        else:
            analyzy = list(app_tables.Analyzy.search(
                uzivatel=uzivatel
            ))
            
        # Omezení počtu výsledků, pokud je požadováno
        if limit is not None:
            analyzy = analyzy[:limit]
            
        # Sestavení výstupních dat
        result = []
        for a in analyzy:
            item = {
                "id": a.get_id(),
                "nazev": a["nazev"],
                "datum_vytvoreni": a["datum_vytvoreni"],
                "datum_upravy": a["datum_upravy"],
                "popis": a["data_json"].get("popis", "")
            }
            result.append(item)
            
        return result
        
    except Exception as e:
        zapsat_chybu(f"Chyba při načítání analýz uživatele: {str(e)}")
        return []

@anvil.server.callable
@handle_errors
def nacti_analyzy_uzivatele_admin(email: str, sort_by: str = "datum_vytvoreni") -> List[Dict]:
    """
    Načte seznam analýz daného uživatele pro admin rozhraní.
    
    Args:
        email: Email uživatele
        sort_by: Pole pro řazení
        
    Returns:
        List[Dict]: Seznam analýz s metadaty
    """
    # Ověření, že volající je admin
    over_admin_prava()
    
    zapsat_info(f"Načítám analýzy pro uživatele: {email}")
    
    try:
        # Nejprve získáme objekt uživatele
        uzivatel = app_tables.users.get(email=email)
        if not uzivatel:
            raise ValueError(f"Uživatel {email} nenalezen")
        
        # Získání analýz uživatele
        if sort_by == "datum_vytvoreni":
            analyzy = list(app_tables.Analyzy.search(
                tables.order_by("datum_vytvoreni", ascending=False),
                uzivatel=uzivatel
            ))
        elif sort_by == "datum_upravy":
            analyzy = list(app_tables.Analyzy.search(
                tables.order_by("datum_upravy", ascending=False),
                uzivatel=uzivatel
            ))
        else:
            analyzy = list(app_tables.Analyzy.search(
                uzivatel=uzivatel
            ))
        
        # Sestavení výstupních dat
        result = []
        for a in analyzy:
            item = {
                "id": a.get_id(),
                "nazev": a["nazev"],
                "datum_vytvoreni": a["datum_vytvoreni"],
                "datum_upravy": a["datum_upravy"],
                "popis": a["data_json"].get("popis", "")
            }
            result.append(item)
        
        zapsat_info(f"Nalezeno {len(result)} analýz pro uživatele {email}")
        return result
        
    except Exception as e:
        zapsat_chybu(f"Chyba při načítání analýz pro uživatele {email}: {str(e)}")
        raise ValueError(f"Chyba při načítání analýz: {str(e)}")

@anvil.server.callable
@handle_errors
def vrat_pocet_analyz_pro_uzivatele(uzivatel) -> int:
    """
    Vrátí počet analýz přidružených k danému uživateli.
    
    Args:
        uzivatel: Řádek uživatele z tabulky 'users'
    
    Returns:
        int: Celkový počet analýz, které se vážou k danému uživateli
    """
    try:
        zapsat_info(f"Hledám analýzy pro uživatele: {uzivatel['email']}")
        
        # Převedeme výsledek vyhledávání na list a spočítáme jeho délku
        analyzy = list(app_tables.Analyzy.search(uzivatel=uzivatel))
        pocet = len(analyzy)
        
        zapsat_info(f"Nalezeno analýz: {pocet}")
        return pocet
        
    except Exception as e:
        zapsat_chybu(f"Chyba při načítání počtu analýz pro uživatele {uzivatel['email']}: {str(e)}")
        return 0

# =============== Administrativní funkce ===============

@anvil.server.callable
@handle_errors
def nastavit_roli_po_registraci(email: str) -> bool:
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
                zapsat_info(f"Automaticky přidělena admin role uživateli: {email}")
                return True
    
    except Exception as e:
        zapsat_chybu(f"Chyba při nastavování role: {str(e)}")
    
    return False

# =============== Pomocné funkce ===============

def over_admin_prava():
    """
    Ověří, zda má přihlášený uživatel administrátorská práva.
    
    Raises:
        ValueError: Pokud uživatel nemá administrátorská práva
    """
    uzivatel = anvil.users.get_user()
    if not uzivatel:
        raise ValueError("Pro tuto operaci musíte být přihlášen.")
    
    if uzivatel.get('role') != 'admin':
        raise ValueError("Pro tuto operaci potřebujete administrátorská práva.")