# -------------------------------------------------------
# Form: Uprava_kriteria_form
# -------------------------------------------------------
from ._anvil_designer import Uprava_kriteria_formTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Uprava_kriteria_form(Uprava_kriteria_formTemplate):
  def __init__(self, item, **properties):
    self.init_components(**properties)
    self.text_box_nazev_kriteria.text = item['nazev_kriteria']
    self.drop_down_typ.selected_value = item['typ']
    self.text_box_vaha.text = str(item['vaha'])
    self._item = item
    self.label_chyba.visible = False
    self.vaha = None  # Store validated weight

  def validuj_vahu(self):
        """Validuje váhu a ukládá ji do self.vaha pro další použití"""
        if not self.text_box_vaha.text:
            self.label_chyba.text = "Zadejte hodnotu váhy kritéria"
            self.label_chyba.visible = True
            return False
            
        try:
            # Replace comma with decimal point
            vaha_text = self.text_box_vaha.text.replace(',', '.')
            self.vaha = float(vaha_text)
            
            if not (0 <= self.vaha <= 1):
                self.label_chyba.text = "Váha musí být číslo mezi 0 a 1"
                self.label_chyba.visible = True
                return False
                
            # Normalize display to use decimal point
            self.text_box_vaha.text = str(self.vaha)
            self.label_chyba.visible = False
            return True
            
        except ValueError:
            self.label_chyba.text = "Váha musí být platné číslo"
            self.label_chyba.visible = True
            return False

  def ziskej_upravena_data(self):
      """Z validovaných polí vrátí dict s aktualizovanými daty kritéria"""
      if not self.validuj_vahu():
          return None
          
      return {
          'nazev_kriteria': self.text_box_nazev_kriteria.text,
          'typ': self.drop_down_typ.selected_value,
          'vaha': self.vaha  # Use stored validated weight
      }

  def text_box_vaha_lost_focus(self, **event_args):
      """Validuje váhu při ztrátě fokusu"""
      self.validuj_vahu()