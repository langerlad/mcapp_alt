# -------------------------------------------------------
# RowTemplate: Kriterium_Row
# client_code/Wizard_komp/Kriterium_Row/__init__.py
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
      # Získání aktuálních kritérií ze správce stavu
      kriteria = self.spravce.ziskej_kriteria()
      
      # Filtrace kritérií - odstranění zvoleného kritéria
      nova_kriteria = [
        k for k in kriteria
        if k['nazev_kriteria'] != self.item['nazev_kriteria']
      ]
      
      # Uložení aktualizovaných kritérií zpět do správce stavu
      self.spravce.uloz_kriteria(nova_kriteria)
      
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
        # Získání aktuálních kritérií ze správce stavu
        kriteria = self.spravce.ziskej_kriteria()
        
        # Aktualizace kritéria v seznamu
        for k in kriteria:
          if k['nazev_kriteria'] == self.item['nazev_kriteria']:
            k.update(updated_data)
            break
        
        # Uložení aktualizovaných kritérií zpět do správce stavu
        self.spravce.uloz_kriteria(kriteria)
        
        # Aktualizace UI
        self.parent.raise_event('x-refresh')
        break