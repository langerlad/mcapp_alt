# -------------------------------------------------------
# RowTemplate: Kriterium_Row
# client_code/Wizard_komp/Kriterium_Row/__init__.py
# Upraveno pro novou strukturu dat.
# -------------------------------------------------------
from ._anvil_designer import Kriterium_RowTemplate
from anvil import *
import anvil.server
from ...Uprava_kriteria_form import Uprava_kriteria_form
from ... import Spravce_stavu, Utils


class Kriterium_Row(Kriterium_RowTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.spravce = Spravce_stavu.Spravce_stavu()

  def link_smazat_kriterium_click(self, **event_args):
    """
    Zpracuje kliknutí na tlačítko pro smazání kritéria.
    Odstraní kritérium ze správce stavu a aktualizuje UI.
    """
    if Utils.zobraz_potvrzovaci_dialog("Opravdu chcete smazat toto kritérium?"):
      # Získáme název kritéria
      nazev_kriteria = self.item['nazev_kriteria']
      
      # Použijeme novou metodu pro smazání kritéria
      self.spravce.smaz_kriterium(nazev_kriteria)
      
      # Aktualizace UI
      self.parent.raise_event('x-refresh')

  def link_upravit_kriterium_click(self, **event_args):
    """
    Zpracuje kliknutí na tlačítko pro úpravu kritéria.
    Zobrazí dialog pro editaci a aktualizuje hodnoty ve správci stavu.
    """
    # Vytvoření kopie dat pro editaci
    kriterium_kopie = {
      'nazev_kriteria': self.item['nazev_kriteria'],
      'typ': self.item['typ'],
      'vaha': self.item['vaha']
    }
    
    # Vytvoření formuláře pro úpravu
    edit_form = Uprava_kriteria_form(item=kriterium_kopie)

    while True:
      # Zobrazení formuláře pro úpravu
      save_clicked = alert(
        content=edit_form,
        title="Upravit kritérium",
        large=True,
        dismissible=True,
        buttons=[("Uložit", True), ("Zrušit", False)]
      )
      
      if not save_clicked:
        break

      # Získání upravených dat
      updated_data = edit_form.ziskej_upravena_data()
      if updated_data:
        # Použijeme novou metodu pro úpravu kritéria
        self.spravce.uprav_kriterium(
            self.item['nazev_kriteria'],  # Původní název
            updated_data['nazev_kriteria'],  # Nový název
            updated_data['typ'], 
            updated_data['vaha']
        )
        
        # Aktualizace UI
        self.parent.raise_event('x-refresh')
        break