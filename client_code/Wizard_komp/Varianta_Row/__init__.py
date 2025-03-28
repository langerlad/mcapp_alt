# -------------------------------------------------------
# RowTemplate: Varianta_Row
# client_code/Wizard_komp/Varianta_Row/__init__.py
# -------------------------------------------------------
from ._anvil_designer import Varianta_RowTemplate
from anvil import *
import anvil.server
from ... import Spravce_stavu, Utils


class Varianta_Row(Varianta_RowTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.spravce = Spravce_stavu.Spravce_stavu()

  def link_smazat_variantu_click(self, **event_args):
    """
    Zpracuje kliknutí na tlačítko pro smazání varianty.
    Odstraní variantu ze správce stavu a aktualizuje UI.
    """
    if Utils.zobraz_potvrzovaci_dialog("Opravdu chcete smazat tuto variantu?"):
      # Získání aktuálních variant ze správce stavu
      varianty = self.spravce.ziskej_varianty()
      
      # Filtrace variant - odstranění zvolené varianty
      nove_varianty = [
        v for v in varianty
        if v['nazev_varianty'] != self.item['nazev_varianty']
      ]
      
      # Uložení aktualizovaných variant zpět do správce stavu
      self.spravce.uloz_varianty(nove_varianty)
      
      # Aktualizace UI
      self.parent.raise_event('x-refresh')