from ._anvil_designer import Administrace_kompTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from .. import Konstanty, Spravce_stavu, Navigace, Utils
from ..Pridej_uzivatele_form import Pridej_uzivatele_form


class Administrace_komp(Administrace_kompTemplate):
    def __init__(self, **properties):
        """Inicializace komponenty pro správu uživatelů."""
        self.init_components(**properties)
        
        # Inicializace správce stavu
        self.spravce = Spravce_stavu.Spravce_stavu()
        
        self.zvoleny_uzivatel = None
        
        # Nastavení handleru pro události z x_Row
        self.repeating_panel_uzvatele.set_event_handler('x-uzivatel-zvolen', self.nacti_analyzy_uzivatele)
        self.repeating_panel_uzvatele.set_event_handler('x-refresh', self.nacti_uzivatele)
        self.repeating_panel_uzvatele.set_event_handler('x-vycisti-analyzy', self.vycisti_analyzy)
        self.repeating_panel_analyzy.set_event_handler('x-zobraz-vystup', self.zobraz_vystup_analyzy)
        
        # Inicializace stavu analýz - na začátku není vybrán žádný uživatel
        self.data_grid_analyzy.visible = False
        self.label_vyberte_ucet.visible = True
        
        # Načtení seznamu uživatelů
        self.nacti_uzivatele()
  
    def nacti_uzivatele(self, sender=None, **event_args):
        """Načte seznam uživatelů a aktualizuje UI."""
        try:
            # Kontrola, zda je přihlášený uživatel admin
            if not self.spravce.je_admin():
                Utils.zapsat_chybu("Nedostatečná oprávnění pro přístup k administraci")
                alert("Pro přístup do administrativní sekce potřebujete administrátorská práva.")
                Navigace.go('domu')
                return

            Utils.zapsat_info("Načítám seznam uživatelů")
            uzivatele = anvil.server.call('nacti_vsechny_uzivatele')
            
            if not uzivatele:
                self.label_zadni_uzivatele.visible = True
                self.data_grid_uzivatele.visible = False
                Utils.zapsat_info("Nebyli nalezeni žádní uživatelé")
                return
            
            self.label_zadni_uzivatele.visible = False
            self.data_grid_uzivatele.visible = True
            
            # Formátování dat pro repeating panel
            self.repeating_panel_uzvatele.items = [
                {
                    'id': u.get_id(),
                    'email': u['email'],
                    'vytvoreni': u['signed_up'].strftime("%d.%m.%Y") if u['signed_up'] else '',
                    'prihlaseni': u['last_login'].strftime("%d.%m.%Y") if u['last_login'] else '',
                    'role': 'admin' if u['role'] == 'admin' else 'uživatel',
                    'pocet_analyz': anvil.server.call('vrat_pocet_analyz_pro_uzivatele', u)
                } 
                for u in uzivatele
            ]
            
            Utils.zapsat_info(f"Načteno {len(uzivatele)} uživatelů")
                
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při načítání uživatelů: {str(e)}")
            alert(Konstanty.ZPRAVY_CHYB['CHYBA_NACTENI_UZIVATELU'].format(str(e)))

    def nacti_analyzy_uzivatele(self, sender, uzivatel, **event_args):
        """Načte a zobrazí analýzy zvoleného uživatele."""
        try:
            Utils.zapsat_info(f"Načítám analýzy pro uživatele: {uzivatel['email']}")
            
            # Předáváme pouze email místo celého objektu uživatele
            analyzy = anvil.server.call('nacti_analyzy_uzivatele_admin', uzivatel['email'])

            # Aktualizace UI - skrytí zprávy o nutnosti výběru uživatele
            self.label_vyberte_ucet.visible = False
            
            # Aktualizace UI
            self.label_uzivatel.text = f"Zvolený uživatel: {uzivatel['email']}"
        
            # Zobrazení/skrytí datagridu podle toho, jestli jsou nalezeny analýzy
            self.data_grid_analyzy.visible = bool(analyzy)
            
            if not analyzy:
                Utils.zapsat_info("Žádné analýzy nenalezeny")
                return
            
            Utils.zapsat_info(f"Zpracovávám {len(analyzy)} analýz")
        
            self.repeating_panel_analyzy.items = [
                {
                    'id': a.get_id(),
                    'nazev': a['nazev'],
                    'popis': a['popis'],
                    'datum_vytvoreni': a['datum_vytvoreni'].strftime("%d.%m.%Y") if a['datum_vytvoreni'] else '',
                    'datum_upravy': a['datum_upravy'].strftime("%d.%m.%Y") if a['datum_upravy'] else ''
                }
                for a in analyzy
            ]
            Utils.zapsat_info("Analýzy načteny do UI")
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při načítání analýz: {str(e)}")
            alert(f"Chyba při načítání analýz: {str(e)}")

    def zobraz_vystup_analyzy(self, sender, analyza_id, **event_args):
        """
        Zobrazí výstup zvolené analýzy.
        
        Args:
            sender: Komponenta, která událost vyvolala
            analyza_id: ID zvolené analýzy
            event_args: Další argumenty události
        """
        try:
            Utils.zapsat_info(f"Zobrazuji výstup analýzy: {analyza_id}")
            
            # Nastavení aktivní analýzy ve správci stavu
            self.spravce.nastav_aktivni_analyzu(analyza_id, False)
            
            # Přesměrování na stránku s výstupem analýzy
            from .. import Navigace
            Navigace.go('saw_vystup', analyza_id=analyza_id)
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při zobrazování výstupu analýzy: {str(e)}")
            alert(f"Chyba při zobrazování výstupu analýzy: {str(e)}")

    def vycisti_analyzy(self, **event_args):
        """Vyčistí zobrazení analýz."""
        self.data_grid_analyzy.visible = False
        self.label_vyberte_ucet.visible = True
        self.label_uzivatel.text = ""
        self.repeating_panel_analyzy.items = []
        Utils.zapsat_info("Vyčištěno zobrazení analýz")

    def button_pridat_uzivatele_click(self, **event_args):
        """Handler pro tlačítko přidání nového uživatele."""     
        pridej_form = Pridej_uzivatele_form()
        
        while True:
            save_clicked = alert(
                content=pridej_form,
                title="Přidat uživatele",
                large=True,
                dismissible=True,
                buttons=[("Vytvořit", True), ("Zrušit", False)]
            )
            
            if not save_clicked:
                break
                
            user_data = pridej_form.ziskej_data_uzivatele()
            if user_data:
                try:
                    Utils.zapsat_info(f"Vytvářím nového uživatele: {user_data['email']}")
                    
                    # Zavolání serverové funkce
                    vysledek = anvil.server.call(
                        'vytvor_noveho_uzivatele', 
                        user_data['email'], 
                        user_data['heslo'], 
                        user_data['je_admin']
                    )
                    
                    if vysledek:
                        # Obnovíme seznam uživatelů
                        self.nacti_uzivatele()
                        
                        # Obnovíme stav uživatele, abychom zajistili, že vytvoření uživatele
                        # neovlivnilo přihlášeného admin uživatele
                        self.spravce.nacti_uzivatele()
                        
                        # Informujeme administrátora
                        alert(f"Uživatel {user_data['email']} byl úspěšně vytvořen.")
                        break
                        
                except Exception as e:
                    Utils.zapsat_chybu(f"Chyba při vytváření uživatele: {str(e)}")
                    pridej_form.label_chyba.text = str(e)
                    pridej_form.label_chyba.visible = True