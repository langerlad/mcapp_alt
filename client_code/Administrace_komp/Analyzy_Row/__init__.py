# client_code/Administrace_komp/Analyzy_Row/__init__.py
from ._anvil_designer import Analyzy_RowTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ... import Spravce_stavu, Utils


class Analyzy_Row(Analyzy_RowTemplate):
    def __init__(self, **properties):
        """Inicializace řádku analýzy."""
        self.init_components(**properties)
        self.spravce = Spravce_stavu.Spravce_stavu()

    def link_zoom_click(self, **event_args):
        """Otevře výstup analýzy po kliknutí na zoom."""
        # Zkontrolujeme, zda máme k dispozici ID analýzy
        if 'id' not in self.item:
            Utils.zapsat_chybu("CHYBA: Chybí ID analýzy")
            return
            
        # Získáme ID analýzy a vyvoláme událost
        analyza_id = self.item['id']
        Utils.zapsat_info(f"Kliknutí na zoom pro analýzu: {analyza_id}")
        
        # Nastavení aktivní analýzy ve správci stavu
        self.spravce.nastav_aktivni_analyzu(analyza_id, False)
        
        self.parent.raise_event('x-zobraz-vystup', analyza_id=analyza_id)