# client_code/Dashboard_uziv_komp/__init__.py
from ._anvil_designer import Dashboard_uziv_kompTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
from .. import Navigace, Spravce_stavu, Utils


class Dashboard_uziv_komp(Dashboard_uziv_kompTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        # Inicializace správce stavu
        self.spravce = Spravce_stavu.Spravce_stavu()
        
        # Nastavení handleru pro aktualizaci seznamu analýz
        self.repeating_panel_dashboard.set_event_handler('x-refresh', self.nahraj_analyzy)
        
        # Načtení analýz při startu
        self.nahraj_analyzy()
    
    def form_show(self, **event_args):
        """
        Aktualizuje seznam analýz při zobrazení formuláře.
        """
        # Ujistíme se, že máme aktuálního uživatele
        self.spravce.nacti_uzivatele()
        self.nahraj_analyzy()
    
    def nahraj_analyzy(self, **event_args):
        """
        Načte seznam analýz ze serveru a zobrazí je v UI.
        """
        Utils.zapsat_info("Načítám seznam analýz")
        try:
            # Načtení analýz z nového serverového modulu
            analyzy = anvil.server.call('nacti_analyzy_uzivatele')
            
            if not analyzy:
                # Žádné analýzy k zobrazení
                self.label_no_analyzy.visible = True
                self.repeating_panel_dashboard.visible = False
                Utils.zapsat_info("Žádné analýzy nenalezeny")
                return
            
            # Máme analýzy k zobrazení
            self.label_no_analyzy.visible = False
            self.repeating_panel_dashboard.visible = True
            
            # Formátování dat pro repeating panel
            self.repeating_panel_dashboard.items = [
                {
                    'id': a['id'],
                    'nazev': a['nazev'],
                    'popis': a.get('popis', ''),
                    'datum_vytvoreni': a['datum_vytvoreni'].strftime("%d.%m.%Y") if a['datum_vytvoreni'] else "",
                    'datum_upravy': a['datum_upravy'].strftime("%d.%m.%Y") if a['datum_upravy'] else ""
                } for a in analyzy
            ]
            
            Utils.zapsat_info(f"Načteno {len(analyzy)} analýz")
            
        except Exception as e:
            Utils.zapsat_chybu(f"Chyba při načítání analýz: {str(e)}")
            alert(f"Chyba při načítání analýz: {str(e)}")

    def button_pridat_analyzu_click(self, **event_args):
        """
        Přechod na stránku pro přidání nové analýzy.
        """
        # Vyčistíme předchozí stav analýzy před vytvořením nové
        self.spravce.vycisti_data_analyzy()
        
        # Přejdeme na stránku pro zadání dat analýzy
        Navigace.go('pridat_analyzu')