# -------------------------------------------------------
# Modul: Navigace

# zajišťuje řízení navigace v rámci celé aplikace. 
# Hlavním vstupním bodem je funkce `go(stranka, **parametry)`, která přepne na požadovanou stránku (komponentu). 
# Ke každé stránce slouží nastavení ve slovníku `KONFIGURACE_NAVIGACE`, kde jsou definovány například 
# požadavky na přihlášení, parametry komponenty a nastavení, zda je třeba zrušit rozpracovanou analýzu.
# Tímto způsobem se v aplikaci centralizuje logika přepínání jednotlivých obrazovek, kontroluje se stav uživatele
# (přihlášení) a brání se ztrátě neuložených dat.

# -------------------------------------------------------
import anvil.server
import anvil.users
from anvil import *

from . import Konstanty, Spravce_stavu, Utils
from .Administrace_komp import Administrace_komp
from .Wizard_komp import Wizard_komp
from .Info_komp import Info_komp
from .Nastaveni_komp import Nastaveni_komp
from .HERO_komp import HERO_komp
from .Dashboard_uziv_komp import Dashboard_uziv_komp
from .Ucet_komp import Ucet_komp
from .Vyber_analyzy_komp import Vyber_analyzy_komp
from .Vystup_saw_komp import Vystup_saw_komp
from .Vystup_wsm_komp import Vystup_wsm_komp
from .Vystup_wpm_komp import Vystup_wpm_komp
from .Vystup_topsis_komp import Vystup_topsis_komp
from .Vystup_electre_komp import Vystup_electre_komp
from .Vystup_mabac_komp import Vystup_mabac_komp

# Komponenta hlavního okna
komponenta_hl_okna = None

def zapsat_chybu(zprava):
    """
    Funkce pro konzolové výpisy chyb v klientském kódu
    
    Args:
        zprava (str): Chybová zpráva k vypsání
    """
    print(f"[CHYBA] {zprava}")

# Konfigurace stránek a navigace
KONFIGURACE_NAVIGACE = {
    'domu': {
        'komponenta': HERO_komp,
        'dashboard_komponenta': Dashboard_uziv_komp,
        'vyzaduje_prihlaseni': False,
        'oznaceni_nav': 'domu',
        'kontrola_rozpracovane': True
    },
    'pridat_analyzu': {
        'komponenta': Wizard_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': 'pridat',
        'kontrola_rozpracovane': True
    },
    'uprava_analyzy': {
        'komponenta': Wizard_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': 'pridat',
        'kontrola_rozpracovane': False,
        'parametry': {'mode': Konstanty.STAV_ANALYZY['UPRAVA']}
    },
    'nastaveni': {
        'komponenta': Nastaveni_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': 'nastaveni',
        'kontrola_rozpracovane': True
    },
    'info': {
        'komponenta': Info_komp,
        'vyzaduje_prihlaseni': False,
        'oznaceni_nav': 'info',
        'kontrola_rozpracovane': True
    },
    'administrace': {
        'komponenta': Administrace_komp,
        'vyzaduje_prihlaseni': True,
        'vyzaduje_admin': True,
        'oznaceni_nav': 'administrace',
        'kontrola_rozpracovane': True
    },
    'ucet': {
        'komponenta': Ucet_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': 'ucet',
        'kontrola_rozpracovane': True
    },
    'saw_vstup': {
        'komponenta': Wizard_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': None,
        'kontrola_rozpracovane': False
    },
    'vystup_saw': {
        'komponenta': Vystup_saw_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': None,
        'kontrola_rozpracovane': False
    },
    'vystup_wsm': {
        'komponenta': Vystup_wsm_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': None,
        'kontrola_rozpracovane': False
    },
    'vystup_wpm': {
        'komponenta': Vystup_wpm_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': None,
        'kontrola_rozpracovane': False
    },
    'vystup_topsis': {
        'komponenta': Vystup_topsis_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': None,
        'kontrola_rozpracovane': False
    },
    'vystup_electre': {
        'komponenta': Vystup_electre_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': None,
        'kontrola_rozpracovane': False
    },
    'vystup_mabac': {
        'komponenta': Vystup_mabac_komp,
        'vyzaduje_prihlaseni': True,
        'oznaceni_nav': None,
        'kontrola_rozpracovane': False
    }
}

def go(stranka, **parametry):
    """
    Centrální navigační funkce.

    Args:
        stranka (str): Identifikátor cílové stránky
        parametry (dict): Volitelné parametry pro komponentu
    """
    try:
        # Získání konfigurace stránky
        konfig = KONFIGURACE_NAVIGACE.get(stranka)
        if not konfig:
            raise ValueError(f"Neznámá stránka: {stranka}")

        # Inicializace správce stavu
        spravce = Spravce_stavu.Spravce_stavu()

        # Kontrola přihlášení
        if konfig['vyzaduje_prihlaseni']:
            uzivatel = kontrola_prihlaseni()
            if not uzivatel:
                go('domu')
                return

        # Kontrola admin práv
        if konfig.get('vyzaduje_admin', False):
            if not spravce.je_admin():
                alert("Pro přístup do této sekce potřebujete administrátorská práva.")
                go('domu')
                return
              
        # Kontrola rozpracované analýzy
        if konfig['kontrola_rozpracovane']:
            if not over_a_smaz_rozpracovanou(stranka):
                return

        # Nastavení aktivní položky v navigaci
        if konfig['oznaceni_nav']:
            komp = ziskej_komponentu()
            komp.set_active_nav(konfig['oznaceni_nav'])

        # Speciální případy
        if stranka == 'domu':
            komp = ziskej_komponentu()
            uzivatel = spravce.je_prihlasen()
            komponenta = konfig['dashboard_komponenta'] if uzivatel else konfig['komponenta']
            komp.nahraj_komponentu(komponenta())
            return

        # Standardní navigace
        komp = ziskej_komponentu()
        # Sloučení výchozích parametrů z konfigurace s předanými parametry
        vsechny_parametry = {**(konfig.get('parametry', {})), **parametry}
        komp.nahraj_komponentu(konfig['komponenta'](**vsechny_parametry))

    except Exception as e:
        Utils.zapsat_chybu(f"Chyba při navigaci na stránku {stranka}: {str(e)}")
        alert("Došlo k chybě při navigaci")
        go('domu')


def ziskej_komponentu():
    """
    Získá instanci hlavní komponenty.

    Returns:
        Instance hlavní komponenty

    Raises:
        Exception: Pokud není komponenta inicializována
    """
    if komponenta_hl_okna is None:
        raise Exception("Není zvolena žádná komponenta hlavního okna")
    return komponenta_hl_okna


def kontrola_prihlaseni():
    """
    Zkontroluje, zda je uživatel přihlášen, případně zobrazí přihlašovací dialog.

    Returns:
        Instance přihlášeného uživatele nebo None
    """
    spravce = Spravce_stavu.Spravce_stavu()
    uzivatel = spravce.nacti_uzivatele()
    
    if uzivatel:
        return uzivatel

    uzivatel = anvil.users.login_with_form(allow_cancel=True)
    if uzivatel:
        spravce.nacti_uzivatele()  # Aktualizace správce stavu
        
    komp = ziskej_komponentu()
    komp.nastav_ucet(uzivatel)
    return uzivatel


def over_a_smaz_rozpracovanou(cilova_stranka):
    """
    Zkontroluje, zda v hlavním panelu není rozdělaná analýza.

    Args:
        cilova_stranka: Identifikátor cílové stránky

    Returns:
        True pokud lze pokračovat v navigaci, False pokud byla zrušena
    """
    try:
        spravce = Spravce_stavu.Spravce_stavu()
        komp = ziskej_komponentu()
        
        if hasattr(komp, 'pravy_panel'):
            components = komp.pravy_panel.get_components()
            if components and isinstance(components[0], Wizard_komp):
                wizard = components[0]

                # Kontrola nové analýzy - nyní jen kontrolujeme, zda má správce neukládaná data
                if wizard.mode == Konstanty.STAV_ANALYZY['NOVY'] and spravce.ma_neulozena_data():
                    if Utils.zobraz_potvrzovaci_dialog(Konstanty.ZPRAVY_CHYB['POTVRZENI_ZRUSENI_NOVE']):
                        # Stačí vyčistit data ve správci stavu
                        spravce.vycisti_data_analyzy()
                        return True
                    return False

                # Kontrola upravované analýzy
                elif wizard.mode == Konstanty.STAV_ANALYZY['UPRAVA'] and wizard.mode != Konstanty.STAV_ANALYZY['ULOZENY']:
                    if Utils.zobraz_potvrzovaci_dialog(Konstanty.ZPRAVY_CHYB['POTVRZENI_ZRUSENI_UPRAVY']):
                        spravce.vycisti_data_analyzy()
                        return True
                    return False
        return True

    except Exception as e:
        Utils.zapsat_chybu(f"Chyba při kontrole rozpracované analýzy: {str(e)}")
        return True